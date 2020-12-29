'''
File: lambda_function.py
Project: ccda_step1_new_files
File Created: Friday, 17th July 2020 7:04:34 pm
Author: Canivel, Danilo (dccanive@amazon.com)
Description: Process the SQS message, transform into a list of objects.
Each object represents 1 file that can contain a .zip of XMLs
or a single XML file to be later converted into FHIR.

If a file is zip, gzip or tar, we send the file to DecompressionStep,
and from the DecompressionStep each file is sent to ValidateFile Step.
Otherwise we send it straight to ValidataFile Step
-----
Last Modified: Tuesday, 22nd December 2020 8:38:57 am
Modified By: Canivel, Danilo (dccanive@amazon.com>)
-----
Copyright 2020 - 2020 Amazon Web Services, Amazon
'''

import json
import time
import boto3
import os
from datetime import datetime
import logging
from botocore.exceptions import ClientError
from urllib.parse import unquote_plus
from pathlib import Path
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)
DYNAMODB_CLIENT = boto3.client('dynamodb')
CCDS_SQSMESSAGE_TABLE_LOG = os.environ['CCDS_SQSMESSAGE_TABLE_LOG']
BUCKET_PROCESSED_CCDS = os.environ['BUCKET_PROCESSED_CCDS']
FOLDER_PROCESSED_CCDS = os.environ['FOLDER_PROCESSED_CCDS']
S3_CLIENT = boto3.client('s3')

BATCH_TYPES = ['.zip', '.gz']


def check_suffix(filepath):
    suffix = Path(filepath).suffix
    return suffix


def lambda_handler(event, context):
    LOGGER.info(event)

    sqs_message_id = event['Source']['sqs_message_id']
    aws_request_id = event['Source']['aws_request_id']

    input_next_step = {
        'Records': []
    }

    if 'Records' in event:
        for record in event['Records']:
            if record['eventSource'] == 'aws:s3':
                filename = record['s3']['object']['key']
                bucket_landing = record['s3']['bucket']['name']

                filename = unquote_plus(filename)
                f_name = os.path.basename(filename)

                suffix = check_suffix(f_name)

                try:
                    # copy the file to processed bucket
                    copy_response = S3_CLIENT.copy_object(
                        Bucket=f'{BUCKET_PROCESSED_CCDS}',
                        CopySource=f'/{bucket_landing}/{filename}',
                        Key=f'{FOLDER_PROCESSED_CCDS}/{sqs_message_id}/{f_name}',
                    )

                    file_record = {
                        'Source': {
                            'sqs_message_id': sqs_message_id,
                            'aws_request_id': aws_request_id,
                        },
                        'Object': {
                            'bucket': bucket_landing,
                            'key': filename
                        }
                    }

                    if suffix in BATCH_TYPES:
                        # unzip and add each file separated to the list
                        pass
                    else:
                        file_record['Status'] = 'SINGLE_FILE'

                    input_next_step['Records'].append(file_record)

                except Exception as err:
                    # @TODO Save Fail copy to DB
                    file_record = {
                        'Source': {
                            'sqs_message_id': sqs_message_id,
                            'aws_request_id': aws_request_id,
                        },
                        'Object': {
                            'bucket': bucket_landing,
                            'key': filename
                        },
                        "Status": "FAILED"
                    }
                    input_next_step['Records'].append(file_record)
                    LOGGER.error(err)
                    raise err

    return input_next_step
