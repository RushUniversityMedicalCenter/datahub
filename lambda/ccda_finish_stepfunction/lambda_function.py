"""
File: lambda_function.py
Project: ccda_finish_stepfunction
File Created: Friday, 17th July 2020 7:04:34 pm
Author: Canivel, Danilo (dccanive@amazon.com)
Description: Wraps up the CCD processing saving the log as complete for the message
-----
Last Modified: Monday, 11th January 2021 2:25:48 pm
Modified By: Canivel, Danilo (dccanive@amazon.com>)
-----
(c) 2020 - 2021 Amazon Web Services, Inc. or its affiliates. All Rights Reserved. 
This AWS Content is provided subject to the terms of the AWS Customer Agreement available at
http://aws.amazon.com/agreement or other written agreement between Customer and either
Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
"""

# Import the libraries
import json
import boto3
import os
import logging

# Instatiate the Logger to save messages to Cloudwatch
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

# Instantiate the service clients
S3_CLIENT = boto3.client("s3")
SQS_CLIENT = boto3.client("sqs")

# Load the enviroment variables
SQS_QUEUE_URL = os.environ["SQS_QUEUE_URL"]


def lambda_handler(event, context):
    """Lambda Handler that finishes the Step machine pipeline
        Get the receiptHandle and Status from the event, if the status is COMPLETED, remove the message from the queue

    Args:
        event (dict): Lambda Event
        context (dict): Lambda Context
    Returns:
        dict: Dictionary with event updated Status
    """

    # SQS receiptHandle token, used to confirm receipt and remove message from Queue
    receiptHandle = event[0]["Source"]["receiptHandle"]
    # Validate the input save the logs and complete the state machine
    if event[0]["Status"] == "COMPLETED":
        SQS_CLIENT.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=receiptHandle)
        event[0]["Status"] = "COMPLETED"
    else:
        event[0]["Status"] = "FAILED"

    return event[0]
