import json
import os
import boto3
import logging
from botocore.exceptions import ClientError
from datetime import datetime

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

DYNAMODB_CLIENT = boto3.client("dynamodb")
DYNAMODB_JUVARE_HASH_TABLE_LOG = os.environ["DYNAMODB_JUVARE_HASH_TABLE_LOG"]
DYNAMODB_JUVARE_EXECUTION_LOG = os.environ["DYNAMODB_JUVARE_EXECUTION_LOG"]


def put_dynamodb_log(lambdaId, filename, status, creation_date, event, error_result):
    try:
        DYNAMODB_CLIENT.put_item(
            TableName=DYNAMODB_JUVARE_EXECUTION_LOG,
            Item={
                "lambdaId": {"S": lambdaId},
                "filename": {"S": filename},
                "creation_date": {"N": f"{creation_date}"},
                "status": {"S": status},
                "event": {"S": event},
                "error": {"S": json.dumps(error_result)},
            },
        )
    except Exception as e:
        LOGGER.error(f"## DYNAMODB PUT MESSAGEID EXCEPTION: {str(e)}")


def update_dynamodb_log(lambdaId, status, error_result):
    try:
        response = DYNAMODB_CLIENT.update_item(
            TableName=DYNAMODB_JUVARE_EXECUTION_LOG,
            Key={"lambdaId": {"S": lambdaId}},
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
        LOGGER.error(f"## DYNAMODB PUT lambdaId EXCEPTION: {str(e)}")
        raise e


def put_dynamodb_hash(lambdaId, creation_date, ccd_hash, filename):
    try:
        DYNAMODB_CLIENT.put_item(
            TableName=DYNAMODB_JUVARE_HASH_TABLE_LOG,
            Item={
                "md5Digest": {"S": ccd_hash},
                "lambdaId": {"S": lambdaId},
                "filename": {"S": filename},
                "creation_date": {"N": f"{creation_date}"},
            },
        )
    except ClientError as err:
        LOGGER.error(f"## DYNAMODB PUT HASH EXCEPTION: {str(err)}")
        raise err("Error adding hash to table")


def is_hash_existent(lambdaId, md5_digest, filename) -> bool:
    """
    Query the DynamoDB 'message' table for the item containing the given message ID
    :param message_id: the message ID to be included in the query
    :return: the item containing the message ID if it exists, otherwise None
    """
    try:
        response = DYNAMODB_CLIENT.get_item(
            TableName=DYNAMODB_JUVARE_HASH_TABLE_LOG, Key={"md5Digest": {"S": md5_digest}}
        )

        if "Item" in response:
            lambdaId_hash = response["Item"]["lambdaId"]["S"]
            LOGGER.info(f"JUVARE HASH {md5_digest} already found in table, lambdaId {lambdaId_hash}")

            message_log_response = DYNAMODB_CLIENT.get_item(
                TableName=DYNAMODB_JUVARE_EXECUTION_LOG, Key={"lambdaId": {"S": lambdaId_hash}}
            )
            if "Item" in message_log_response:
                if message_log_response["Item"]["status"]["S"] == "COMPLETED":
                    LOGGER.info(f"message_log_response: {message_log_response}")
                    return True
                else:
                    return False
            else:
                return False
        else:
            now = datetime.now()
            creation_date = int(now.timestamp())
            put_dynamodb_hash(lambdaId, creation_date, md5_digest, filename)
            return False
    except ClientError as err:
        LOGGER.error(err)
        raise err

    return False