"""
File: lambda_function.py
Project: ccda_step2_validation
File Created: Friday, 17th July 2020 7:04:34 pm
Author: Canivel, Danilo (dccanive@amazon.com)
Description: Check if content is valid and send to deduplication
-----
Last Modified: Monday, 11th January 2021 8:47:50 pm
Modified By: Canivel, Danilo (dccanive@amazon.com>)
-----
Copyright 2020 - 2020 Amazon Web Services, Amazon
"""

# Import the libraries
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

# Instatiate the Logger to save messages to Cloudwatch
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

# Instantiate the service clients
S3_CLIENT = boto3.client("s3")
DYNAMODB_CLIENT = boto3.client("dynamodb")

# Define types of HL7
hl7_supported_types = ["ADT", "VXU", "ORM", "ORU", "PPR", "SIU", "MDM", "ACK", "OML"]

# Load the enviroment variables
CCDS_SQSMESSAGE_TABLE_LOG = os.environ["CCDS_SQSMESSAGE_TABLE_LOG"]


def update_dynamodb_log(messageId, status, error_result):
    """Updates the current status of the message log

    Args:
        messageId (str): SQS message id, comes with each Record inside Records
        status (str): Current Status of the pipeline
        error_result (str): Error description, empty if None

    Raises:
        e: Client Exception if error updating the record

    Returns:
        dict: Object updated
    """
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
    """Lambda Handler that executes step 2 of the pipeline
    Check if the Status is a SINGLE_FILE, if True, get the object from S3 landing bucket
    reads, and try to parse as XML, if an error is raised, try to split the file by pipe(|) and validate the position 8 of the file.
    If any value of the list hl7_supported_types is in the position 8 value it's an HL7, otherwise,
    raises an Exception of Unsuported File.

    Args:
        event (dict): Lambda Event
        context (dict): Lambda Context

    Raises:
        Exception: Unsuported File Type

    Returns:
        dict: Event updated with the Filetype to be converted
    """

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
            hl7_type = [x.split("|")[8] for x in s3_filedata.decode("utf-8").splitlines() if x.startswith("MSH")][0]
            # hl7_type = s3_filedata.decode().split("|")[8]

            if len([x for x in hl7_supported_types if x in hl7_type]) == 1:
                event["Object"]["Type"] = "HL7"
                update_dynamodb_log(sqs_message_id, event["Status"], "")
            else:
                update_dynamodb_log(sqs_message_id, event["Status"], str(err))
                raise Exception("Not Supported File type")

    return event
