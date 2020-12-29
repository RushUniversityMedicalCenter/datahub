'''
File: lambda_function.py
Project: ccda_step3_deduplication
File Created: Friday, 17th July 2020 7:04:34 pm
Author: Canivel, Danilo (dccanive@amazon.com)
Description: Generate a MD5 hash save to Dynamodb if the Hash does not exist
If the hash exists, terminate the loop, save log of file duplicated
-----
Last Modified: Tuesday, 22nd December 2020 8:37:57 am
Modified By: Canivel, Danilo (dccanive@amazon.com>)
-----
Copyright 2020 - 2020 Amazon Web Services, Amazon
'''

import json
import os
import boto3
import logging
from botocore.exceptions import ClientError
import hashlib
from datetime import datetime

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

DYNAMODB_CLIENT = boto3.client('dynamodb')
CCDS_HASH_TABLE_LOG = os.environ['CCDS_HASH_TABLE_LOG']

S3_CLIENT = boto3.client('s3')


def put_dynamodb_hash(messageId, creation_date, ccd_hash):
    try:
        DYNAMODB_CLIENT.put_item(TableName=CCDS_HASH_TABLE_LOG,
                                 Item={'ccd_hash': {'S': ccd_hash},
                                       'messageId': {'S': messageId},
                                       'creation_date': {'N': f'{creation_date}'}
                                       })
    except Exception as err:
        LOGGER.error(f'## DYNAMODB PUT HASH EXCEPTION: {str(err)}')
        raise err('Error adding hash to table')


def is_hash_existent(messageId, ccd_hash) -> bool:
    """
    Query the DynamoDB 'message' table for the item containing the given message ID
    :param message_id: the message ID to be included in the query
    :return: the item containing the message ID if it exists, otherwise None
    """
    try:
        response = DYNAMODB_CLIENT.get_item(
            TableName=CCDS_HASH_TABLE_LOG, Key={'ccd_hash': {
                'S': ccd_hash
            }})

        if 'Item' in response:
            LOGGER.info(
                f'HASH {ccd_hash} found ibn table ')
            return True
        else:
            now = datetime.now()
            creation_date = int(now.timestamp())
            put_dynamodb_hash(messageId,
                              creation_date, ccd_hash)
            return False
    except Exception as err:
        # @TODO
        # check if the error is empty, if yes move to Dead-Letter
        LOGGER.info(err)
        raise err

    return False


def lambda_handler(event, context):
    # TODO implement
    # 1. read the file in the Processed Bucket
    # 2. generate the MD5 hash
    # 3. check the dynamodb table if hash exists
    # 4. if not exists continue else stop and save log that is duplicate
    if event['Status'] == 'VALID':

        sqs_message_id = event['Source']['sqs_message_id']

        try:
            bucketname = event['Object']['bucket']
            filename = event['Object']['key']

            ccd_file = S3_CLIENT.get_object(Bucket=bucketname, Key=filename)
            ccd_content = ccd_file['Body'].read()

            ccd_hash = str(hashlib.md5(ccd_content).hexdigest())
            # print(ccd_hash)

            is_hash_found = is_hash_existent(sqs_message_id, ccd_hash)

            if is_hash_found:
                event['Status'] = 'DUPLICATED'
                raise Exception(
                    'Error hash already found into the table: FILE IS DUPLICATED')
            else:
                event['Status'] = 'VALID'

        except Exception as err:
            event['Status'] = 'FAILED'
            LOGGER.info('-------ERROR READING FILE-------')
            LOGGER.info(err)
            raise err
    else:
        event['Status'] = 'FAILED'
        raise Exception('Not valid file')

    return event
