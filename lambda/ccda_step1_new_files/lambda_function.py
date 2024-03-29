"""
File: lambda_function.py
Project: ccda_step1_new_files
File Created: Friday, 17th July 2020 7:04:34 pm
Author: Canivel, Danilo (dccanive@amazon.com)
Description: Process the SQS message, transform into a list of objects.
Each object represents 1 file that can contain a single XML file to be later converted into FHIR.
-----
Last Modified: Wednesday, 6th January 2021 11:58:49 am
Modified By: Canivel, Danilo (dccanive@amazon.com>)
-----
(c) 2020 - 2021 Amazon Web Services, Inc. or its affiliates. All Rights Reserved. 
This AWS Content is provided subject to the terms of the AWS Customer Agreement available at
http://aws.amazon.com/agreement or other written agreement between Customer and either
Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
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
from pathlib import Path
import importlib

# Instatiate the Logger to save messages to Cloudwatch
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

# Load the enviroment variables
CCDS_SQSMESSAGE_TABLE_LOG = os.environ["CCDS_SQSMESSAGE_TABLE_LOG"]
BUCKET_PROCESSED_CCDS = os.environ["BUCKET_PROCESSED_CCDS"]
FOLDER_PROCESSED_CCDS = os.environ["FOLDER_PROCESSED_CCDS"]

# Instantiate the service clients
DYNAMODB_CLIENT = boto3.client("dynamodb")
S3_CLIENT = boto3.client("s3")

"""@TODO
Currently not supported, needs more validation if there is usecase to handle compressed batches.
"""
BATCH_TYPES = [".zip", ".gz"]


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


def check_suffix(filepath):
    """Get the suffix of a filepath

    Args:
        filepath (str): File path

    Returns:
        str: Suffix of the file path
    """
    suffix = Path(filepath).suffix
    return suffix


def lambda_handler(event, context):
    """Lambda Handler that executes Step 1 of the Pipeline
        Check if there is a 'Records' key in the event and for each Record check the type of file by the filetype
        If the file is in the compress list:
            @TODO:
                - open the compressed list locally, copy each file to the Raw folder
                - Add each Record to the list of Records

        If not int the compress list, add the record to the list.

    Args:
        event (dict): Lambda Event
        context (dict): Lambda Context
    Returns:
        dict: Dictionary with list of Records to be processed in the next step
    """
    LOGGER.info(event)

    year = str(datetime.today().year)
    month = str(datetime.today().month)
    day = str(datetime.today().day)

    aws_request_id = event["aws_request_id"]

    input_next_step = {"Records": []}

    if "Records" in event:
        for record in event["Records"]:
            if record["Record"]["eventSource"] == "aws:s3":

                sqs_message_id = record["Source"]["sqs_message_id"]
                receiptHandle = record["Source"]["receiptHandle"]

                filename = record["Record"]["s3"]["object"]["key"]
                bucket_landing = record["Record"]["s3"]["bucket"]["name"]

                filename = unquote_plus(filename)
                f_name = os.path.basename(filename)

                suffix = check_suffix(f_name)

                try:
                    # copy the file to processed bucket
                    copy_response = S3_CLIENT.copy_object(
                        Bucket=f"{BUCKET_PROCESSED_CCDS}",
                        CopySource=f"/{bucket_landing}/{filename}",
                        Key=f"{FOLDER_PROCESSED_CCDS}/year={year}/month={month}/day={day}/message_id={sqs_message_id}/{f_name}",
                    )

                    file_record = {
                        "Source": {
                            "sqs_message_id": sqs_message_id,
                            "aws_request_id": aws_request_id,
                            "receiptHandle": receiptHandle,
                        },
                        "Object": {"bucket": bucket_landing, "key": filename},
                    }

                    if suffix in BATCH_TYPES:
                        # @TODO: unzip and add each file separated to the list
                        file_record["Status"] = "COMPRESSED_FILE"
                        error_results = "Compressed Files are not supported at this moment"
                        update_dynamodb_log(sqs_message_id, file_record["Status"], error_results)
                        raise Exception("Compressed Files are not supported at this moment")
                    else:
                        file_record["Status"] = "SINGLE_FILE"
                        update_dynamodb_log(sqs_message_id, file_record["Status"], "")

                    input_next_step["Records"].append(file_record)

                except Exception as err:
                    file_record = {
                        "Source": {
                            "sqs_message_id": sqs_message_id,
                            "aws_request_id": aws_request_id,
                            "receiptHandle": receiptHandle,
                        },
                        "Object": {"bucket": bucket_landing, "key": filename},
                        "Status": "FAILED",
                    }
                    input_next_step["Records"].append(file_record)
                    update_dynamodb_log(sqs_message_id, file_record["Status"], str(err))
                    LOGGER.error(err)
                    raise err

    return input_next_step
