'''
File: lambda_function.py
Project: ccda_step0_start_state_machine
File Created: Friday, 18th December 2020 5:22:24 pm
Author: Canivel, Danilo (dccanive@amazon.com)
Description: Get a message from the SQS and Start the StepFunction to Process it
-----
Last Modified: Tuesday, 22nd December 2020 8:39:49 am
Modified By: Canivel, Danilo (dccanive@amazon.com>)
-----
Copyright 2020 - 2020 Amazon Web Services, Amazon
'''

#from utils.exception_handler import ProcessingError, SQSMessageDuplicateError
from utils.enums import Status, Key
import time
import json
import boto3
import os
from datetime import datetime
import logging
from botocore.exceptions import ClientError

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)
CCDS_SQSMESSAGE_TABLE_LOG = os.environ['CCDS_SQSMESSAGE_TABLE_LOG']
SFN_ARN = os.environ['SFN_ARN']

DYNAMODB_CLIENT = boto3.client('dynamodb')
STEPFUNCTIONS_CLIENT = boto3.client('stepfunctions')


def put_dynamodb_log(lambdaId, messageId, status, creation_date, error_result):
    try:
        DYNAMODB_CLIENT.put_item(TableName=CCDS_SQSMESSAGE_TABLE_LOG,
                                 Item={'id': {'S': messageId},
                                       'lambdaId': {'S': lambdaId},
                                       'creation_date': {'N': f'{creation_date}'},
                                       'status': {'S': status},
                                       'error': {'S': json.dumps(error_result)}
                                       })
    except Exception as e:
        LOGGER.error(f'## DYNAMODB PUT MESSAGEID EXCEPTION: {str(e)}')


def is_message_processed(aws_requestID, messageId) -> bool:
    """
    Query the DynamoDB 'message' table for the item containing the given message ID
    :param message_id: the message ID to be included in the query
    :return: the item containing the message ID if it exists, otherwise None
    """
    try:
        response = DYNAMODB_CLIENT.get_item(
            TableName=CCDS_SQSMESSAGE_TABLE_LOG, Key={'id': {
                'S': f'{messageId}'
            }})

        if Key.ITEM.value in response:
            LOGGER.info(
                f'Item with ID {messageId} FOUND on DynamoDB table ')
            return True
        else:
            now = datetime.now()
            creation_date = int(now.timestamp())
            put_dynamodb_log(aws_requestID, messageId, Status.IN_PROGRESS.value,
                             creation_date, {})
            return False
    except Exception as err:
        # @TODO
        # check if the error is empty, if yes move to Dead-Letter
        LOGGER.info(err)
        raise err

    return False


def lambda_handler(event, context):
    start = time.time()

    AWS_REQUEST_ID = context.aws_request_id
    LOGGER.info(f'Start processing message {AWS_REQUEST_ID}')

    input_sfn = {
        'aws_request_id': AWS_REQUEST_ID,
        'Records': []
    }

    for main_record in event['Records']:

        # CHECK IF MESSAGE IS ALREADY PROCESSED OR IN PROCESS
        MESSAGE_ID = main_record['messageId']

        if is_message_processed(AWS_REQUEST_ID, MESSAGE_ID):
            # Go to next if Item is present, message is already been processed
            LOGGER.error(
                f'## SQS Messsage id: {str(MESSAGE_ID)} was already processed, going to next message.')

            raise Exception('Message is already Processed or been Processed')

        body = json.loads(main_record['body'])
        LOGGER.info(body)
        if 'Records' in body:
            source = {
                'Source': {
                    'sqs_message_id': MESSAGE_ID
                },
                'Record': body['Records'][0]
            }

            input_sfn['Records'].append(source)
        else:
            continue

    LOGGER.info(input_sfn)
    response = STEPFUNCTIONS_CLIENT.start_execution(
        stateMachineArn=SFN_ARN,
        input=json.dumps(input_sfn)
    )

    return response
