"""
File: lambda_function.py
Project: ccda_step5_dataset_builder
File Created: Friday, 17th July 2020 7:04:34 pm
Author: Canivel, Danilo (dccanive@amazon.com)
Description: Generate the FHIR Datasets currently used by Rush and return the FHIR Bundle 
to be converted into resources
-----
Last Modified: Wednesday, 6th January 2021 12:38:15 pm
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
import awswrangler as wr
from datetime import datetime

from utils.ccd_load_delta import build_datasets
from utils.exceptions import FhirDatasetsGenerationError

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

CCDS_SQSMESSAGE_TABLE_LOG = os.environ["CCDS_SQSMESSAGE_TABLE_LOG"]
BUCKET_PROCESSED_FHIR_DATASETS = os.environ["BUCKET_PROCESSED_FHIR_DATASETS"]
FOLDER_PROCESSED_FHIRS_DATASETS = os.environ["FOLDER_PROCESSED_FHIRS_DATASETS"]

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


def generate_datasets(fhir_content, filename, message_id, event):

    year = str(datetime.today().year)
    month = str(datetime.today().month)
    day = str(datetime.today().day)
    is_datasets_created = False
    try:
        if "fhirResource" in fhir_content:
            datasets = build_datasets(fhir_content["fhirResource"], filename)

            if datasets:
                for k, v in datasets.items():
                    if v.shape[0] > 0:
                        _file = f"s3://{BUCKET_PROCESSED_FHIR_DATASETS}/{FOLDER_PROCESSED_FHIRS_DATASETS}/resource_type={k}/year={year}/month={month}/day={day}/message_id={message_id}/{filename}.parquet"
                        wr.s3.to_parquet(v, _file)
                        # res = add_new_partition(
                        #     'AwsDataCatalog', 'fhir', k, year, month, day)
                is_datasets_created = True
    except (Exception, AttributeError) as err:
        raise FhirDatasetsGenerationError(event, str(err))

    return is_datasets_created


def lambda_handler(event, context):
    if event["Status"] == "CONVERTED":

        sqs_message_id = event["Source"]["sqs_message_id"]

        fhir_bucket = event["Fhir"]["bucket"]
        fhir_filename = event["Fhir"]["key"]

        fhir_file = S3_CLIENT.get_object(Bucket=fhir_bucket, Key=fhir_filename)
        fhir_content = json.loads(fhir_file["Body"].read())

        f_name = os.path.basename(fhir_filename).replace(".json", "")

        if generate_datasets(fhir_content, f_name, sqs_message_id, event):
            # process the dataset builder over the fhir bundle
            event["Status"] = "DATASETS_GENERATED"
            update_dynamodb_log(sqs_message_id, event["Status"], "")
        else:
            event["Status"] = "FAILED"
            update_dynamodb_log(sqs_message_id, event["Status"], "ERROR: STEP5, Failed to generate dataset from FHIR")
            raise FhirDatasetsGenerationError(event, "Failed to generate dataset from FHIR")
    else:
        event["Status"] = "FAILED"
        update_dynamodb_log(
            sqs_message_id, event["Status"], "ERROR: STEP5, Cant generate datasets from not Converted FHIR"
        )
        raise Exception("Can't generate datasets from not Converted FHIR")

    return event
