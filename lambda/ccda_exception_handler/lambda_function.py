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
Last Modified: Monday, 11th January 2021 2:20:10 pm
Modified By: Canivel, Danilo (dccanive@amazon.com>)
-----
Copyright 2020 - 2020 Amazon Web Services, Amazon
"""

# Import the libraries
import time
import json
import boto3
import os
from datetime import datetime
import logging
from botocore.exceptions import ClientError


# Instatiate the Logger to save messages to Cloudwatch
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

# Load the enviroment variables
CCDS_SFN_EXCEPTIONS_LOG = os.environ["CCDS_SFN_EXCEPTIONS_LOG"]
CCDS_HASH_TABLE_LOG = os.environ["CCDS_HASH_TABLE_LOG"]

# Instantiate the service clients
DYNAMODB_CLIENT = boto3.client("dynamodb")


def save_dynamodb_log(aws_request_id, sqs_message_id, source_event, creation_date, error_type):
    """Save log into DynamoDB table for the sqs messages log

    Args:
        aws_request_id (str): AWS request id (Lambda id), generated from the main Lambda execution
        sqs_message_id (str): SQS message id, comes with each Record inside Records
        source_event (str): Json string with the full event from the handler
        creation_date (int): Timestamp of the event
        error_type (str): Error description, empty if None
    """
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
    """Remove the hash from the DynamoDB Hash table log if needed

    Args:
        md5_digest (str): String with md5 digest hash

    Returns:
        bool: If deleted returns True otherwise False
    """
    try:
        resp = DYNAMODB_CLIENT.delete_item(TableName=CCDS_HASH_TABLE_LOG, Key={"ccd_hash": {"S": md5_digest}})
        LOGGER.info(resp)
        return True
    except Exception as e:
        LOGGER.error(f"## DYNAMODB PUT MESSAGEID EXCEPTION: {str(e)}")
        return False


def lambda_handler(event, context):
    """Lambda Handler that executes the exception handler
        First check if the event has a Error key, if True, collect information from the event
    and send an SNS notification with the error
        If the error type is not CCDADuplicatedError, save the the log to DynamoDB and,
    if md5_digest is in the event, we delete the hash from the hash table.
        Otherwise, we save the log to dynamodb only.

    Args:
        event (dict): Lambda Event
        context (dict): Lambda Context
    Returns:
        dict: Dictionary with the notification content to be sent to the SNS Topic
    """

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
            save_dynamodb_log(aws_request_id, sqs_message_id, source_event, creation_date, error_type)
            if "md5_digest" in source_event["Object"]:
                is_dup_deleted = delete_hash_log(source_event["Object"]["md5_digest"])
                notification_event["IsDupHashDeleted"] = is_dup_deleted
        else:
            save_dynamodb_log(aws_request_id, sqs_message_id, source_event, creation_date, error_type)

    else:
        notification_event["Status"] = "MISSING_ERROR"

    return notification_event
