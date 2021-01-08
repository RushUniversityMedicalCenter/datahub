"""
File: lambda_function.py
Project: juvare_cdph_idph_process
File Created: Wednesday, 6th January 2021 2:12:37 pm
Author: Canivel, Danilo (dccanive@amazon.com)
-----
Last Modified: Wednesday, 6th January 2021 2:41:52 pm
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
import os
from urllib.parse import unquote_plus
import logging
import json
from utils import dynamodb_helper, athena_helper

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

S3_CLIENT = boto3.client("s3")
SNS_CLIENT = boto3.client("sns")

BUCKET_PROCESSED_JUVARE = os.environ["BUCKET_PROCESSED_JUVARE"]  # rush-poc-ccd-preprocessed
BUCKET_PROCESSED_JUVARE_PREFIX = os.environ["BUCKET_PROCESSED_JUVARE"]  # daily_havbed
BUCKET_RAW_JUVARE_PREFIX = os.environ["BUCKET_RAW_JUVARE"]  # raw_daily_havbed

GLUE_CATALOG_NAME = os.environ["GLUE_CATALOG_NAME"]
GLUE_DB_NAME = os.environ["GLUE_DB_NAME"]


SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]


def csv_from_excel(filename, bucket_landing, job_id):

    filename = unquote_plus(filename)
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
            Key=f"juavare/{BUCKET_RAW_JUVARE_PREFIX}/{year}/{month}/{day}/{f_name}",
        )

        # read the ccd file
        xlsx_file = S3_CLIENT.get_object(Bucket=bucket_landing, Key=filename)
        xlsx_file_content = xlsx_file["Body"].read()

        # read the file using xlrd
        xls = xlrd.open_workbook(file_contents=xlsx_file_content)
        sheets = xls.sheet_names()

        for s in sheets:
            LOGGER.info(f"---- Juvare: Processing Daily CDPH_IDPH - {s} - {f_name_date} ----")
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
            LOGGER.info(f"---- Juvare: Daily CDPH_IDPH SAVED in S3 - {s} - {f_name_date} ----")
            res = athena_helper.add_new_partition(GLUE_CATALOG_NAME, GLUE_DB_NAME, s, year, month, day)

            # remove the landing data
            S3_CLIENT.delete_object(Bucket=bucket_landing, Key=f"{filename}")

    except Exception as err:
        LOGGER.error(f"## JUVARE CDPH_IDPH PROCESSING EXCEPTION: {str(err)}")
        # send to SNS topic
        SNS_CLIENT.publish(TopicArn=SNS_TOPIC_ARN, Message=str(err), Subject="JUVARE CDPH_IDPH PROCESSING EXCEPTION")
        raise err


def lambda_handler(event, context):

    start = time.time()
    creation_date = int(datetime.now().timestamp())
    lambdaId = context.aws_request_id
    status = "IN_PROGRESS"
    dynamodb_helper.put_dynamodb_log(lambdaId, status, creation_date, "")

    try:
        filename = event["Records"][0]["s3"]["object"]["key"]
        bucket_landing = event["Records"][0]["s3"]["bucket"]["name"]
    except Exception as err:
        LOGGER.error(f"---- JUVARE CDPH_IDPH EXCEPTION: {str(err)}")
        LOGGER.info(event)
        status = "FAILED"
        dynamodb_helper.put_dynamodb_log(lambdaId, status, creation_date, str(err))
        SNS_CLIENT.publish(TopicArn=SNS_TOPIC_ARN, Message=str(err), Subject="JUVARE CDPH_IDPH PROCESSING EXCEPTION")
        raise err
    # convert the to CSV
    try:
        csv_from_excel(filename, bucket_landing, lambdaId)
    except Exception as err:
        LOGGER.error(f"---- JUVARE CDPH_IDPH EXCEPTION: {str(err)}")
        LOGGER.info(event)
        status = "FAILED"
        dynamodb_helper.put_dynamodb_log(lambdaId, status, creation_date, str(err))
        SNS_CLIENT.publish(TopicArn=SNS_TOPIC_ARN, Message=str(err), Subject="JUVARE CDPH_IDPH PROCESSING EXCEPTION")
        raise err

    status = "COMPLETED"
    dynamodb_helper.put_dynamodb_log(lambdaId, status, creation_date, str(err))
    end = time.time()
    result = {
        "statusCode": 200,
        "execution_time": round(end - start, 2),
        "message": f"{filename} sheets converted to csv.",
    }
    LOGGER.info(result)

    return result
