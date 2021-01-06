"""
File: lambda_function.py
Project: ccda_expection_handler
File Created: Friday, 18th December 2020 5:07:40 pm
Author: Canivel, Danilo (dccanive@amazon.com)
Description: Handle Step Functions Exceptions and save the log for reprocessing
    1 - If Exception is raised and the process stop, remove the deduplication id from the Dynamodb Table
    2 - Handles methods not supported by HealthLake
Exceptions types:
    1- CCDADuplicatedError: Happens when a CCDA hash is already found on the Dynamodb
    2 - ConverterError: Occurrs when the Converter returns a 4xx or 5xx error
    3 - FhirDatasetsGenerationError: Occurrs when the Dataset generation from the FHIR resources are not generated
-----
Last Modified: Wednesday, 6th January 2021 9:08:08 am
Modified By: Canivel, Danilo (dccanive@amazon.com>)
-----
Copyright 2020 - 2020 Amazon Web Services, Amazon
"""


import time
import json
import boto3
import os
from datetime import datetime
import logging
from botocore.exceptions import ClientError

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)
CCDS_SFN_EXCEPTIONS_LOG = os.environ["CCDS_SFN_EXCEPTIONS_LOG"]
CCDS_HASH_TABLE_LOG = os.environ["CCDS_HASH_TABLE_LOG"]

DYNAMODB_CLIENT = boto3.client("dynamodb")


def save_dynamodb_log(aws_request_id, sqs_message_id, source_event, creation_date, error_type):
    try:
        DYNAMODB_CLIENT.put_item(
            TableName=CCDS_SFN_EXCEPTIONS_LOG,
            Item={
                "id": {"S": sqs_message_id},
                "aws_request_id": {"S": aws_request_id},
                "creation_date": {"N": f"{creation_date}"},
                "source_event": {"S": json.dumps(source_event)},
                "exception": {"S": error_type},
            },
        )
    except Exception as e:
        LOGGER.error(f"## DYNAMODB PUT MESSAGEID EXCEPTION: {str(e)}")


def delete_hash_log(md5_digest):
    try:
        resp = DYNAMODB_CLIENT.delete_item(TableName=CCDS_HASH_TABLE_LOG, Key={"ccd_hash": {"S": md5_digest}})
        LOGGER.info(resp)
        return True
    except Exception as e:
        LOGGER.error(f"## DYNAMODB PUT MESSAGEID EXCEPTION: {str(e)}")
        return False


def lambda_handler(event, context):
    # TODO implement
    error_type = event.get("Error")

    notification_event = {}

    if error_type:
        error_message = json.loads(event["Cause"])
        error_message = json.loads(error_message["errorMessage"])
        error = error_message["error"]
        source_event = error_message["event"]
        aws_request_id = source_event["Source"]["aws_request_id"]
        sqs_message_id = source_event["Source"]["sqs_message_id"]
        bucket = source_event["Object"]["bucket"]
        key = source_event["Object"]["key"]
        status = source_event["Status"]

        creation_date = int(datetime.now().timestamp())

        notification_event["Message"] = error
        notification_event["Exception"] = error_type
        notification_event["Timestamp"] = creation_date
        notification_event["Source"] = source_event["Source"]
        notification_event["Object"] = source_event["Object"]
        notification_event["Status"] = "EXCEPTION"
        notification_event["IsDupHashDeleted"] = False

        if error_type != "CCDADuplicatedError":
            # @TODO Send message to Dead-Letter with Error Status
            save_dynamodb_log(aws_request_id, sqs_message_id, source_event, creation_date, error_type)
            if "md5_digest" in source_event["Object"]:
                is_dup_deleted = delete_hash_log(source_event["Object"]["md5_digest"])
                notification_event["IsDupHashDeleted"] = is_dup_deleted
        else:
            save_dynamodb_log(aws_request_id, sqs_message_id, source_event, creation_date, error_type)

    else:
        notification_event["Status"] = "MISSING_ERROR"

    return notification_event
