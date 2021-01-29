"""
File: lambda_function.py
Project: aws-rush-fhir
File Created: Thursday, 28th January 2021 8:41:02 am
Author: Canivel, Danilo (dccanive@amazon.com)
-----
Last Modified: Friday, 29th January 2021 10:25:36 am
Modified By: Canivel, Danilo (dccanive@amazon.com>)
-----
(c) 2020 - 2021 Amazon Web Services, Inc. or its affiliates. All Rights Reserved. 
This AWS Content is provided subject to the terms of the AWS Customer Agreement available at
http://aws.amazon.com/agreement or other written agreement between Customer and either
Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
"""

import os
import boto3
from datetime import datetime
import csv
import uuid
import time
from urllib.parse import unquote_plus
import logging
import json
import hashlib
from utils import dynamodb_helper

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

S3_CLIENT = boto3.client("s3")
SNS_CLIENT = boto3.client("sns")
GLUE_CLIENT = boto3.client("glue")

BUCKET_PROCESSED_HHS = os.environ["BUCKET_PROCESSED_HHS"]  # rush-poc-hhs-preprocessed

GLUE_CRAWLER_HHS = os.environ["GLUE_CRAWLER_HHS"]

SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]


def csv_processing(filename, bucket_landing, job_id):

    if "emr" in filename:
        hhs_type = "emr"
    else:
        hhs_type = "hhs2"

    f_name = os.path.basename(filename)

    try:
        # copy the file to processed bucket
        copy_response = S3_CLIENT.copy_object(
            Bucket=f"{BUCKET_PROCESSED_HHS}",
            CopySource=f"/{bucket_landing}/{filename}",
            Key=f"hhs/{hhs_type}/year={datetime.now().year}/month={datetime.now().month}/day={datetime.now().day}/{f_name}",
        )

        # read the ccd file
        hhs_file = S3_CLIENT.get_object(Bucket=bucket_landing, Key=filename)
        hhs_file_content = hhs_file["Body"].read()

        hhs_hash = str(hashlib.md5(hhs_file_content).hexdigest())
        # print(ccd_hash)

        is_hash_found = dynamodb_helper.is_hash_existent(job_id, hhs_hash, filename)

        if is_hash_found:
            LOGGER.error("-------DUPLICATED HHS FILE-------")
            dynamodb_helper.update_dynamodb_log(job_id, "EXCEPTION", "DUPLICATED HHS FILE")
            raise Exception("DUPLICATED: HHS File was Already imported")

        return True

    except Exception as err:
        LOGGER.error(f"## HHS PROCESSING EXCEPTION: {str(err)}")
        # send to SNS topic
        SNS_CLIENT.publish(TopicArn=SNS_TOPIC_ARN, Message=str(err), Subject="HHS PROCESSING EXCEPTION")
        raise err

    return False


def lambda_handler(event, context):
    LOGGER.info("---- HHS START PROCESSING ---")
    LOGGER.info(json.dumps(event))

    filename = event["Records"][0]["s3"]["object"]["key"]
    filename = unquote_plus(filename)
    bucket_landing = event["Records"][0]["s3"]["bucket"]["name"]

    start = time.time()
    creation_date = int(datetime.now().timestamp())
    lambdaId = context.aws_request_id

    try:
        status = "IN_PROGRESS"
        dynamodb_helper.put_dynamodb_log(lambdaId, filename, status, creation_date, json.dumps(event), "")
    except Exception as err:
        LOGGER.error(f"---- HHS EXCEPTION: {str(err)}")
        LOGGER.info(event)
        status = "FAILED"
        dynamodb_helper.put_dynamodb_log(lambdaId, filename, status, creation_date, json.dumps(event), str(err))
        SNS_CLIENT.publish(TopicArn=SNS_TOPIC_ARN, Message=str(err), Subject="HHS PROCESSING EXCEPTION")
        raise err

    result_convertion = csv_processing(filename, bucket_landing, lambdaId)

    try:
        response = GLUE_CLIENT.start_crawler(Name=GLUE_CRAWLER_HHS)
    except Exception as err:
        LOGGER.error("---- ERROR RUNING HHS CRAWLER ----")
        LOGGER.error(str(err))

    end = time.time()
    if result_convertion:
        status = "COMPLETED"
        dynamodb_helper.put_dynamodb_log(lambdaId, filename, status, creation_date, json.dumps(event), "")
        result = {
            "statusCode": 200,
            "execution_time": round(end - start, 2),
            "message": f"{filename} sheets converted to csv.",
        }
        LOGGER.info(result)
        # remove the landing data
        S3_CLIENT.delete_object(Bucket=bucket_landing, Key=f"{filename}")
    else:
        result = {
            "statusCode": 500,
            "execution_time": round(end - start, 2),
            "message": f"{filename} Failed to be converted to csv.",
        }
        LOGGER.error(result)

    return result
