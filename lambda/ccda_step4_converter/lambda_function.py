"""
File: lambda_function.py
Project: ccda_step4_converter
File Created: Friday, 17th July 2020 7:04:34 pm
Author: Canivel, Danilo (dccanive@amazon.com)
Description: Execute the conversion to generate a FHIR Bundle typer Batch
-----
Last Modified: Wednesday, 6th January 2021 12:35:26 pm
Modified By: Canivel, Danilo (dccanive@amazon.com>)
-----
Copyright 2020 - 2020 Amazon Web Services, Amazon
"""

import json
import requests
import os
import boto3
import logging
from botocore.exceptions import ClientError
from urllib.parse import unquote_plus
from pathlib import Path
from datetime import datetime

from utils.exceptions import ConverterError

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

HEADERS = {"Content-type": "text/plain"}
CCD_FHIR_CONVERTER_ENDPOINT = (
    os.environ["FHIR_CONVERTER_URL"]
    + os.environ["CCD_FHIR_CONVERTER_ENDPOINT"]
    + os.environ["CCD_FHIR_CONVERTER_TEMPLATENAME"]
)

HL7_FHIR_CONVERTER_URL = (
    os.environ["FHIR_CONVERTER_URL"]
    + os.environ["HL7_FHIR_CONVERTER_ENDPOINT"]
    + os.environ["HL7_FHIR_CONVERTER_TEMPLATENAME"]
)

CCDS_SQSMESSAGE_TABLE_LOG = os.environ["CCDS_SQSMESSAGE_TABLE_LOG"]
BUCKET_PROCESSED_CCDS = os.environ["BUCKET_PROCESSED_CCDS"]
FOLDER_PROCESSED_CCDS = os.environ["FOLDER_PROCESSED_CCDS"]

S3_CLIENT = boto3.client("s3")
DYNAMODB_CLIENT = boto3.client("dynamodb")


def update_dynamodb_log(messageId, status, error_result):
    try:
        response = DYNAMODB_CLIENT.update_item(
            TableName=CCDS_SQSMESSAGE_TABLE_LOG,
            Key={"id": {"S": messageId}},
            ExpressionAttributeValues={
                ":s": {
                    "S": status,
                },
                ":e": {
                    "S": error_result,
                },
            },
            ExpressionAttributeNames={"#status_message": "status", "#error_message": "error"},
            UpdateExpression="SET #status_message=:s, #error_message=:e",
            ReturnValues="UPDATED_NEW",
        )
        return response
    except Exception as e:
        LOGGER.error(f"## DYNAMODB PUT MESSAGEID EXCEPTION: {str(e)}")
        raise e


def convert_to_fhir(url, headers, ccd_content, event):

    # check if server is up
    try:
        res_get = requests.get(os.environ["FHIR_CONVERTER_URL"])
        res_get.raise_for_status()
        # check if up POST
        if res_get:
            try:
                response = requests.post(url, headers=headers, data=ccd_content)
                response.raise_for_status()
                if response:
                    return response.text
            except Exception as err:
                LOGGER.error("---- CONVERTER POST ERROR ----")
                LOGGER.error(err)
                LOGGER.info(event)
                event["Status"] = "FAILED"
                raise ConverterError(event, str(err))
    except Exception as err:
        LOGGER.error("---- CONVERTER GET ERROR ----")
        LOGGER.error(err)
        LOGGER.info(event)
        raise ConverterError(event, str(err))


def lambda_handler(event, context):
    # TODO implement
    # 1. Read the CCD file and send to the FHIR converter
    # 2. If returns 200, save the FHIR into the same folder as the original CCD
    # 3. save the log
    # 4. forward the Fhir bucket and filename

    year = str(datetime.today().year)
    month = str(datetime.today().month)
    day = str(datetime.today().day)

    if event["Status"] == "VALID":

        sqs_message_id = event["Source"]["sqs_message_id"]
        bucketname = event["Object"]["bucket"]
        filename = event["Object"]["key"]
        filetype = event["Object"]["Type"]

        ccd_file = S3_CLIENT.get_object(Bucket=bucketname, Key=filename)
        ccd_content = ccd_file["Body"].read()

        if filetype == "CCD":
            LOGGER.info("---- CCDA Convertion Started -----")
            fhir_bundle_content = convert_to_fhir(CCD_FHIR_CONVERTER_ENDPOINT, HEADERS, ccd_content, event)
        else:
            LOGGER.info("---- HL7 Convertion Started -----")
            fhir_bundle_content = convert_to_fhir(HL7_FHIR_CONVERTER_URL, HEADERS, ccd_content, event)

        if fhir_bundle_content:

            filename = unquote_plus(filename)
            f_name = os.path.basename(filename)

            # convert to json
            fhir_json = json.loads(fhir_bundle_content)
            fhir_filename = f"{f_name}.fhir.json"
            key_fhir_json = f"{FOLDER_PROCESSED_CCDS}/year={year}/month={month}/day={day}/message_id={sqs_message_id}/{fhir_filename}"
            fhir_json_str = str(json.dumps(fhir_json))
            S3_CLIENT.put_object(Body=fhir_json_str, Bucket=BUCKET_PROCESSED_CCDS, Key=key_fhir_json)

            event["Fhir"] = {"bucket": BUCKET_PROCESSED_CCDS, "key": key_fhir_json}

            event["Status"] = "CONVERTED"
            update_dynamodb_log(sqs_message_id, event["Status"], "")
        else:
            event["Status"] = "FAILED"
            LOGGER.info("---- FHIR Convertion Failed -----")
            update_dynamodb_log(sqs_message_id, event["Status"], "ERROR: STEP4, FHIR Convertion Failed")
            raise ConverterError(event)
    else:
        event["Status"] = "FAILED"
        update_dynamodb_log(sqs_message_id, event["Status"], "ERROR: STEP4, FHIR Convertion Failed")

    return event
