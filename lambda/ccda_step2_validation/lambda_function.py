"""
File: lambda_function.py
Project: ccda_step2_validation
File Created: Friday, 17th July 2020 7:04:34 pm
Author: Canivel, Danilo (dccanive@amazon.com)
Description: Check if content is valid and send to deduplication
-----
Last Modified: Tuesday, 22nd December 2020 8:38:38 am
Modified By: Canivel, Danilo (dccanive@amazon.com>)
-----
Copyright 2020 - 2020 Amazon Web Services, Amazon
"""

import json
import time
import boto3
import os
from datetime import datetime
import logging
from botocore.exceptions import ClientError
from urllib.parse import unquote_plus
import xml.etree.ElementTree as ET
import xml.parsers

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

S3_CLIENT = boto3.client("s3")
hl7_supported_types = ["ADT", "VXU", "ORM", "ORU", "PPR", "SIU", "MDM", "ACK", "OML"]

CCDS_SQSMESSAGE_TABLE_LOG = os.environ["CCDS_SQSMESSAGE_TABLE_LOG"]
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


def lambda_handler(event, context):
    LOGGER.info(f"Validation Step Triggered")
    LOGGER.info(event)

    sqs_message_id = event["Source"]["sqs_message_id"]

    bucketname = event["Object"]["bucket"]
    filename = event["Object"]["key"]

    if event["Status"] == "SINGLE_FILE":

        s3_file = S3_CLIENT.get_object(Bucket=bucketname, Key=filename)
        s3_filedata = s3_file["Body"].read()

        try:
            tree = ET.ElementTree(ET.fromstring(s3_filedata))
            event["Status"] = "VALID"
            event["Object"]["Type"] = "CCD"
            update_dynamodb_log(sqs_message_id, event["Status"], "")
        except ET.ParseError as err:
            event["Status"] = "VALID"
            hl7_type = s3_filedata.decode().split("|")[8]

            if len([x for x in hl7_supported_types if x in hl7_type]) == 1:
                event["Object"]["Type"] = "HL7"
                update_dynamodb_log(sqs_message_id, event["Status"], "")
            else:
                update_dynamodb_log(sqs_message_id, event["Status"], str(err))
                raise Exception("Not Supported HL7 type")

    return event
