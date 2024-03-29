"""
File: lambda_function.py
Project: ccda_step6_fhir_resource_split
File Created: Friday, 17th July 2020 7:04:34 pm
Author: Canivel, Danilo (dccanive@amazon.com)
Description: Split the FHIR Batch into Bundles, split each Resource by the Resource type
and POST it to Health Lake
-----
Last Modified: Tuesday, 29nd December 2020 11:37:25 am
Modified By: Canivel, Danilo (dccanive@amazon.com>)
-----
(c) 2020 - 2021 Amazon Web Services, Inc. or its affiliates. All Rights Reserved. 
This AWS Content is provided subject to the terms of the AWS Customer Agreement available at
http://aws.amazon.com/agreement or other written agreement between Customer and either
Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
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
from utils.exceptions import HealthLakePostError, AWSKeyMissingError

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

CCDS_SQSMESSAGE_TABLE_LOG = os.environ["CCDS_SQSMESSAGE_TABLE_LOG"]
BUCKET_PROCESSED_FHIR_RESOURCES = os.environ["BUCKET_PROCESSED_FHIR_RESOURCES"]
FOLDER_PROCESSED_FHIR_RESOURCES = os.environ["FOLDER_PROCESSED_FHIR_RESOURCES"]
HEALTHLAKE_ENDPOINT = os.environ["HEALTHLAKE_ENDPOINT"]
HEALTHLAKE_CANONICAL_URI = os.environ["HEALTHLAKE_CANONICAL_URI"]


S3_CLIENT = boto3.client("s3")


HEALTHLAKE_LIMIT_TPS = 2

ACCESS_KEY = os.environ.get("ACCESS_KEY")
SECRET_ACCESS = os.environ.get("SECRET_ACCESS")

NOT_SUPPORTED_OPERATIONS = ["Composition"]


def post_healthlake(full_url, headers, fhir_resource, event):

    LOGGER.info(f"HEALTHLAKE POST REQUEST URL: {full_url}")
    LOGGER.info(f"HEALTHLAKE POST Headers: {headers}")
    LOGGER.info(f"HEALTHLAKE POST fhir_resource: {fhir_resource}")

    try:
        response = requests.post(full_url, headers=headers, data=fhir_resource)
        response.raise_for_status()
        return response
    except Exception as err:
        if response.status_code == 400:
            LOGGER.error("----- HEALTHLAKE METHOD NOT SUPPORTED -----")
            LOGGER.error(err)
            LOGGER.error(response.text)
            raise err
        elif response.status_code != 400:
            raise HealthLakePostError(event, str(err))
            return response
        else:
            LOGGER.error(err)
            LOGGER.error(response.text)


def lambda_handler(event, context):
    # REad the FHIr file content
    # Split each entry and each Resource Type and send it to Health Lake
    # Save log in each iteration/resource persist
    # completes the Iterator
    if ACCESS_KEY is None or SECRET_ACCESS is None:
        event["Status"] = "FAILED"
        raise AWSKeyMissingError(event, "No access key is available.")

    if event["Status"] == "DATASETS_GENERATED":
        # process the fhir bundle and split each resource
        # persist to health lake
        # save each resource to the Process bucket
        year = str(datetime.today().year)
        month = str(datetime.today().month)
        day = str(datetime.today().day)

        sqs_message_id = event["Source"]["sqs_message_id"]

        fhir_bucket = event["Fhir"]["bucket"]
        fhir_filename = event["Fhir"]["key"]

        fhir_file = S3_CLIENT.get_object(Bucket=fhir_bucket, Key=fhir_filename)
        fhir_content = json.loads(fhir_file["Body"].read())

        f_name = os.path.basename(fhir_filename)

        event["HealthLake"] = []

        # Code to create resource by resource
        for entry in fhir_content["fhirResource"]["entry"]:
            now = datetime.now()
            creation_date = int(now.timestamp())
            resource_type = entry["resource"]["resourceType"]

            if resource_type in NOT_SUPPORTED_OPERATIONS:
                error_message = f"Operation {resource_type} not supported"
                event["HealthLake"].append(
                    {
                        "ResourceType": resource_type,
                        "CreationDate": creation_date,
                        "Status": "FAILED",
                        "Response": error_message,
                    }
                )
                LOGGER.error(error_message)
                continue

            request_parameters = json.dumps(entry["resource"])

            canonical_uri = f"{HEALTHLAKE_CANONICAL_URI}{resource_type}"

            full_url = f"{HEALTHLAKE_ENDPOINT}{resource_type}"

            headers = aws_signature.generate_headers(ACCESS_KEY, SECRET_ACCESS, request_parameters, canonical_uri)

            response = post_healthlake(full_url, headers, request_parameters, event)

            if response:

                fhir_resource_json = json.dumps(entry["resource"])

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
                break

            time.sleep(HEALTHLAKE_LIMIT_TPS)

        event["Status"] = "COMPLETED"
    else:
        event["Status"] = "FAILED"
        raise Exception

    return event
