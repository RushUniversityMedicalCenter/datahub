'''
File: lambda_function.py
Project: ccda_step4_converter
File Created: Friday, 17th July 2020 7:04:34 pm
Author: Canivel, Danilo (dccanive@amazon.com)
Description: Execute the conversion to generate a FHIR Bundle typer Batch
-----
Last Modified: Tuesday, 22nd December 2020 8:36:56 am
Modified By: Canivel, Danilo (dccanive@amazon.com>)
-----
Copyright 2020 - 2020 Amazon Web Services, Amazon
'''

import json
import requests
import os
import boto3
import logging
from botocore.exceptions import ClientError
from urllib.parse import unquote_plus
from pathlib import Path
from datetime import datetime

from utils.exceptions import ConverterError

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

HEADERS = {'Content-type': 'text/plain'}
FHIR_CONVERTER_URL = os.environ['FHIR_CONVERTER_URL'] + os.environ['FHIR_CONVERTER_ENDPOINT'] + \
    os.environ['FHIR_CONVERTER_TEMPLATENAME']

CCDS_SQSMESSAGE_TABLE_LOG = os.environ['CCDS_SQSMESSAGE_TABLE_LOG']
BUCKET_PROCESSED_CCDS = os.environ['BUCKET_PROCESSED_CCDS']
FOLDER_PROCESSED_CCDS = os.environ['FOLDER_PROCESSED_CCDS']

S3_CLIENT = boto3.client('s3')


def convert_ccd_to_fhir(url, headers, ccd_content, event):
    try:
        response = requests.post(url, headers=headers, data=ccd_content)
        response.raise_for_status()
        if response:
            return response.text
    except Exception as err:
        event['Status'] = 'FAILED'
        raise ConverterError(event, str(err))


def lambda_handler(event, context):
    # TODO implement
    # 1. Read the CCD file and send to the FHIR converter
    # 2. If returns 200, save the FHIR into the same folder as the original CCD
    # 3. save the log
    # 4. forward the Fhir bucket and filename

    year = str(datetime.today().year)
    month = str(datetime.today().month)
    day = str(datetime.today().day)

    if event['Status'] == 'VALID':

        sqs_message_id = event['Source']['sqs_message_id']
        bucketname = event['Object']['bucket']
        filename = event['Object']['key']

        ccd_file = S3_CLIENT.get_object(Bucket=bucketname, Key=filename)
        ccd_content = ccd_file['Body'].read()

        fhir_bundle_content = convert_ccd_to_fhir(
            FHIR_CONVERTER_URL, HEADERS, ccd_content, event)

        if fhir_bundle_content:

            filename = unquote_plus(filename)
            f_name = os.path.basename(filename)

            # convert to json
            fhir_json = json.loads(fhir_bundle_content)
            fhir_filename = f"{f_name}.fhir.json"
            key_fhir_json = f'{FOLDER_PROCESSED_CCDS}/year={year}/month={month}/day={day}/message_id={sqs_message_id}/{fhir_filename}'
            fhir_json_str = str(json.dumps(fhir_json))
            S3_CLIENT.put_object(
                Body=fhir_json_str, Bucket=BUCKET_PROCESSED_CCDS, Key=key_fhir_json)

            event['Fhir'] = {
                'bucket': BUCKET_PROCESSED_CCDS,
                'key': key_fhir_json
            }

            event['Status'] = 'CONVERTED'
        else:
            event['Status'] = 'FAILED'
            LOGGER.info("---- CCDA Convertion to FHIR Failed -----")
            raise ConverterError(event)
    else:
        event['Status'] = 'FAILED'

    return event
