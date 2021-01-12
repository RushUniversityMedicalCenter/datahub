"""
File: lambda_function.py
Project: ccda_step6_fhir_resource_split
File Created: Friday, 17th July 2020 7:04:34 pm
Author: Canivel, Danilo (dccanive@amazon.com)
Description: Persist the FHIR Batch into HealthLake, changing the type to transaction
and POST it to Health Lake
-----
Last Modified: Tuesday, 12th January 2021 9:16:53 am
Modified By: Canivel, Danilo (dccanive@amazon.com>)
-----
Copyright 2020 - 2020 Amazon Web Services, Amazon
"""

# Import the libraries
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

# Instatiate the Logger to save messages to Cloudwatch
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

# Load the enviroment variables
CCDS_SQSMESSAGE_TABLE_LOG = os.environ["CCDS_SQSMESSAGE_TABLE_LOG"]
BUCKET_PROCESSED_FHIR_RESOURCES = os.environ["BUCKET_PROCESSED_FHIR_RESOURCES"]
FOLDER_PROCESSED_FHIR_RESOURCES = os.environ["FOLDER_PROCESSED_FHIR_RESOURCES"]
HEALTHLAKE_ENDPOINT = os.environ["HEALTHLAKE_ENDPOINT"]
HEALTHLAKE_CANONICAL_URI = os.environ["HEALTHLAKE_CANONICAL_URI"]

# Instantiate the service clients
S3_CLIENT = boto3.client("s3")
SQS_CLIENT = boto3.client("sqs")
DYNAMODB_CLIENT = boto3.client("dynamodb")

HEALTHLAKE_LIMIT_TPS = 1

# Lambda runtime Access Keys and Session Token
ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
SECRET_ACCESS = os.environ.get("AWS_SECRET_ACCESS_KEY")
SESSION_TOKEN = os.environ.get("AWS_SESSION_TOKEN")

# Resources Types not supported without a Bundle
NOT_SUPPORTED_OPERATIONS = ["Composition"]


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


def post_healthlake(full_url, headers, fhir_resource, event):
    """Send the FHIR resource to HealthLake endpoint
    If a 429 error is returned, the step function will catch the exception wait for 10s and try again.
    Any other error raises a exception that goes to the Exception Handler
    Args:
        full_url (str): HealthLake endpoint
        headers (dict): Headers for HealthLake authentication containing the AWS Signature
        fhir_resource (str): FHIR Bundle string content
        event (dict): Current event to be logged with the exception if occurss

    Raises:
        HealthLakePostTooManyRequestsError: Exception raised if there is a 429 Error, too many request.
        HealthLakePostError: Exception raised for any other exception

    Returns:
        Response: Response from the requests.post
    """

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
    """Persist the FHIR Resource to HealthLake
    Get the Fhir Bundle from the event and persist to HealthLake
    Removes the RAW file from the Landing bucket, since the files are all copied to the Processed bucket
    Add the HealthLake status to the event
    Finish the Iteration
    Args:
        event (dict): Lambda Event
        context (dict): Lambda Context

    Raises:
        AWSKeyMissingError: Raised if can't find the AWS Keys in the Lambda
        Exception: Raised for any other Exceprtion

    Returns:
        dict: Event updated with the status COMPLETED if everything works.
    """
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
        headers = aws_signature.generate_headers(
            ACCESS_KEY, SECRET_ACCESS, SESSION_TOKEN, request_parameters, canonical_uri
        )

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
