"""
File: lambda_function.py
Project: ccda_step6_fhir_resource_split
File Created: Friday, 17th July 2020 7:04:34 pm
Author: Canivel, Danilo (dccanive@amazon.com)
Description: Persist the FHIR Batch into HealthLake, changing the type to transaction
and POST it to Health Lake
-----
Last Modified: Wednesday, 6th January 2021 12:42:21 pm
Modified By: Canivel, Danilo (dccanive@amazon.com>)
-----
Copyright 2020 - 2020 Amazon Web Services, Amazon
"""


import sys
import os
import base64
import hashlib
import hmac
import time
import logging
import json
import requests
from datetime import datetime
import boto3
from utils import aws_signature
from utils.exceptions import HealthLakePostError, AWSKeyMissingError, HealthLakePostTooManyRequestsError

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

CCDS_SQSMESSAGE_TABLE_LOG = os.environ["CCDS_SQSMESSAGE_TABLE_LOG"]
BUCKET_PROCESSED_FHIR_RESOURCES = os.environ["BUCKET_PROCESSED_FHIR_RESOURCES"]
FOLDER_PROCESSED_FHIR_RESOURCES = os.environ["FOLDER_PROCESSED_FHIR_RESOURCES"]
HEALTHLAKE_ENDPOINT = os.environ["HEALTHLAKE_ENDPOINT"]
HEALTHLAKE_CANONICAL_URI = os.environ["HEALTHLAKE_CANONICAL_URI"]

S3_CLIENT = boto3.client("s3")
SQS_CLIENT = boto3.client("sqs")
DYNAMODB_CLIENT = boto3.client("dynamodb")

HEALTHLAKE_LIMIT_TPS = 1

# ACCESS_KEY = os.environ.get("ACCESS_KEY")
# SECRET_ACCESS = os.environ.get("SECRET_ACCESS")
ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
SECRET_ACCESS = os.environ.get("AWS_SECRET_ACCESS_KEY")
SESSION_TOKEN = os.environ.get("AWS_SESSION_TOKEN")

NOT_SUPPORTED_OPERATIONS = ["Composition"]


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


def post_healthlake(full_url, headers, fhir_resource, event):

    LOGGER.info(f"HEALTHLAKE POST REQUEST URL: {full_url}")
    LOGGER.info(f"HEALTHLAKE POST Headers: {headers}")
    LOGGER.info(f"HEALTHLAKE POST fhir_resource: {fhir_resource}")

    try:
        response = requests.post(full_url, headers=headers, data=fhir_resource)
        response.raise_for_status()
        return response
    except Exception as err:
        if response.status_code == 429:
            LOGGER.error("----- HEALTHLAKE TOO MANY REQUESTS ERROR -----")
            LOGGER.error(err)
            LOGGER.error(response.text)
            raise HealthLakePostTooManyRequestsError(event, str(err))
        else:
            LOGGER.info(f"----- HEALTHLAKE ERROR CODE {response.status_code} ----- ")
            raise HealthLakePostError(event, str(err))


def lambda_handler(event, context):
    # REad the FHIr file content
    # Split each entry and each Resource Type and send it to Health Lake
    # Save log in each iteration/resource persist
    # completes the Iterator
    sqs_message_id = event["Source"]["sqs_message_id"]

    if ACCESS_KEY is None or SECRET_ACCESS is None:
        event["Status"] = "FAILED"
        update_dynamodb_log(sqs_message_id, event["Status"], "ERROR: STEP6, No access key is available")
        raise AWSKeyMissingError(event, "No access key is available.")

    if event["Status"] == "DATASETS_GENERATED":
        # process the fhir bundle and split each resource
        # persist to health lake
        # save each resource to the Process bucket
        year = str(datetime.today().year)
        month = str(datetime.today().month)
        day = str(datetime.today().day)

        fhir_bucket = event["Fhir"]["bucket"]
        fhir_filename = event["Fhir"]["key"]

        fhir_file = S3_CLIENT.get_object(Bucket=fhir_bucket, Key=fhir_filename)
        fhir_content = json.loads(fhir_file["Body"].read())

        f_name = os.path.basename(fhir_filename)

        event["HealthLake"] = []

        now = datetime.now()
        creation_date = int(now.timestamp())
        fhir_bundle = fhir_content["fhirResource"]
        resource_type = "Bundle"
        fhir_content["fhirResource"]["type"] = "transaction"

        request_parameters = json.dumps(fhir_content["fhirResource"])

        canonical_uri = f"{HEALTHLAKE_CANONICAL_URI}{resource_type}"

        full_url = f"{HEALTHLAKE_ENDPOINT}{resource_type}"

        # headers = aws_signature.generate_headers(ACCESS_KEY, SECRET_ACCESS, request_parameters, canonical_uri)
        headers = aws_signature.generate_headers(ACCESS_KEY, SECRET_ACCESS, SESSION_TOKEN, request_parameters, canonical_uri)

        response = post_healthlake(full_url, headers, request_parameters, event)

        if response:

            fhir_resource_json = json.dumps(fhir_content["fhirResource"])

            fhir_json_str = str(json.dumps(fhir_resource_json))

            # add extra sufix for multiple values like Observations
            prefix_fname = f"{creation_date}_{f_name}"
            key_fhir_json = f"{FOLDER_PROCESSED_FHIR_RESOURCES}/resource_type={resource_type}/year={year}/month={month}/day={day}/message_id={sqs_message_id}/{prefix_fname}"
            S3_CLIENT.put_object(Body=fhir_json_str, Bucket=BUCKET_PROCESSED_FHIR_RESOURCES, Key=key_fhir_json)

            event["HealthLake"].append(
                {
                    "ResourceType": resource_type,
                    "CreationDate": creation_date,
                    "Status": "CREATED",
                    "FhirResource": {"bucket": BUCKET_PROCESSED_FHIR_RESOURCES, "key": key_fhir_json},
                }
            )
        else:
            event["HealthLake"].append(
                {
                    "ResourceType": resource_type,
                    "CreationDate": creation_date,
                    "Status": "FAILED",
                    "Response": response.text,
                }
            )

        time.sleep(HEALTHLAKE_LIMIT_TPS)

        event["Status"] = "COMPLETED"
        bucket_landing = event["Object"]["bucket"]
        key = event["Object"]["key"]
        S3_CLIENT.delete_object(Bucket=bucket_landing, Key=f"{key}")
        update_dynamodb_log(sqs_message_id, event["Status"], "")
    else:
        event["Status"] = "FAILED"
        update_dynamodb_log(sqs_message_id, event["Status"], "ERROR: STEP6, Fail to save FHIR Bundle to HelathLake")
        raise Exception("Fail to save FHIR Bundle to HelathLake")

    return event
