"""
File: lambda_function.py
Project: aws-rush-fhir
File Created: Wednesday, 6th January 2021 2:12:57 pm
Author: Canivel, Danilo (dccanive@amazon.com)
-----
Last Modified: Thursday, 7th January 2021 8:37:06 pm
Modified By: Canivel, Danilo (dccanive@amazon.com>)
-----
Copyright 2020 - 2021 Amazon Web Services, Amazon
"""

import os
import boto3
from datetime import datetime
import xlrd
import csv
import uuid
import time
from urllib.parse import unquote_plus
import logging
import json
import hashlib
from utils import dynamodb_helper, athena_helper

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

S3_CLIENT = boto3.client("s3")
SNS_CLIENT = boto3.client("sns")

BUCKET_PROCESSED_JUVARE = os.environ["BUCKET_PROCESSED_JUVARE"]  # rush-poc-ccd-preprocessed
BUCKET_PROCESSED_JUVARE_PREFIX = os.environ["BUCKET_PROCESSED_JUVARE"]  # daily_havbed
BUCKET_RAW_JUVARE_FOLDER = os.environ["BUCKET_RAW_JUVARE_FOLDER"]  # raw_daily_havbed

GLUE_CATALOG_NAME = os.environ["GLUE_CATALOG_NAME"]
GLUE_DB_NAME = os.environ["GLUE_DB_NAME"]


SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]


def csv_from_excel(filename, bucket_landing, job_id):
    # copy the file to processed to maintain the raw data
    temp_folder = "/tmp"
    f_name = os.path.basename(filename)
    f_name_date = f_name.split(" ")[0]
    year = f_name_date.split("-")[0]
    month = f_name_date.split("-")[1]
    day = f_name_date.split("-")[2]

    processed = False

    try:
        # copy the file to processed bucket
        copy_response = S3_CLIENT.copy_object(
            Bucket=f"{BUCKET_PROCESSED_JUVARE}",
            CopySource=f"/{bucket_landing}/{filename}",
            Key=f"juavare/{BUCKET_RAW_JUVARE_FOLDER}/{year}/{month}/{day}/{f_name}",
        )

        # read the ccd file
        xlsx_file = S3_CLIENT.get_object(Bucket=bucket_landing, Key=filename)
        xlsx_file_content = xlsx_file["Body"].read()

        juvare_hash = str(hashlib.md5(xlsx_file_content).hexdigest())
        # print(ccd_hash)

        is_hash_found = dynamodb_helper.is_hash_existent(job_id, juvare_hash)

        if is_hash_found:
            LOGGER.info("-------DUPLICATED JUVARE FILE-------")
            dynamodb_helper.update_dynamodb_log(job_id, "EXCEPTION", "DUPLICATED CCDA")
            raise Exception("DUPLICATED: Juvare File was Already imported")

        # read the file using xlrd
        xls = xlrd.open_workbook(file_contents=xlsx_file_content)
        sheets = xls.sheet_names()

        for s in sheets:
            LOGGER.info(f"---- Juvare: Processing Daily Bed - {s} - {f_name_date} ----")
            # load the sheet name
            sh = xls.sheet_by_name(s)

            # write to the '/tmp' in lambda.
            csv_filename = f"{temp_folder}/{job_id}.csv"
            temp_csv_file = open(csv_filename, "w")
            wr = csv.writer(temp_csv_file)

            # write to the '/tmp' in lambda. skip first line with date metadata
            for rownum in range(1, sh.nrows):
                wr.writerow(sh.row_values(rownum))

            temp_csv_file.close()
            # when is done upload to s3

            S3_CLIENT.upload_file(
                csv_filename,
                BUCKET_PROCESSED_JUVARE,
                f"{BUCKET_PROCESSED_JUVARE_PREFIX}/{s}/year={year}/month={month}/day={day}/{job_id}.csv",
            )
            LOGGER.info(f"---- Juvare: Daily Bed SAVED in S3 - {s} - {f_name_date} ----")
            res = athena_helper.add_new_partition(GLUE_CATALOG_NAME, GLUE_DB_NAME, s, year, month, day)

            return True

    except Exception as err:
        LOGGER.error(f"## JUVARE DAILY BED PROCESSING EXCEPTION: {str(err)}")
        # send to SNS topic
        SNS_CLIENT.publish(TopicArn=SNS_TOPIC_ARN, Message=str(err), Subject="JUVARE DAILY BED PROCESSING EXCEPTION")
        raise err

    return False


def lambda_handler(event, context):
    LOGGER.info("---- JUVARE DAILY BED START PROCESSING ---")
    LOGGER.info(event)

    start = time.time()
    creation_date = int(datetime.now().timestamp())
    lambdaId = context.aws_request_id
    status = "IN_PROGRESS"
    dynamodb_helper.put_dynamodb_log(lambdaId, status, creation_date, json.dumps(event), "")

    try:
        filename = event["Records"][0]["s3"]["object"]["key"]
        filename = unquote_plus(filename)
        bucket_landing = event["Records"][0]["s3"]["bucket"]["name"]

    except Exception as err:
        LOGGER.error(f"---- JUVARE DAILY BED EXCEPTION: {str(err)}")
        LOGGER.info(event)
        status = "FAILED"
        dynamodb_helper.put_dynamodb_log(lambdaId, status, creation_date, json.dumps(event), str(err))
        SNS_CLIENT.publish(TopicArn=SNS_TOPIC_ARN, Message=str(err), Subject="JUVARE DAILY BED PROCESSING EXCEPTION")
        raise err

    result_convertion = csv_from_excel(filename, bucket_landing, lambdaId)
    end = time.time()
    if result_convertion:
        status = "COMPLETED"
        dynamodb_helper.put_dynamodb_log(lambdaId, status, creation_date, json.dumps(event), "")
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
