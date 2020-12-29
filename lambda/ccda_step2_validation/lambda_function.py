'''
File: lambda_function.py
Project: ccda_step2_validation
File Created: Friday, 17th July 2020 7:04:34 pm
Author: Canivel, Danilo (dccanive@amazon.com)
Description: Check if content is valid and send to deduplication
-----
Last Modified: Tuesday, 22nd December 2020 8:38:38 am
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

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


def lambda_handler(event, context):
    LOGGER.info(f'Validation Step Triggered')
    LOGGER.info(event)
    if event['Status'] == 'SINGLE_FILE':
        event['Status'] = 'VALID'

    return event
