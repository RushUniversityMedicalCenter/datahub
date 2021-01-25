"""
File: exception_handler.py
Project: utils
File Created: Monday, 21st December 2020 11:19:23 am
Author: Canivel, Danilo (dccanive@amazon.com)
Description: Handles Exceptions and Generate the DeadLetter Queue for reprocessing
-----
Last Modified: Tuesday, 22nd December 2020 8:40:39 am
Modified By: Canivel, Danilo (dccanive@amazon.com>)
-----
Copyright 2020 - 2020 Amazon Web Services, Amazon
"""

# Import the libraries
import logging

# Instatiate the Logger to save messages to Cloudwatch
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


class SQSMessageDuplicateError(BaseException):
    """Raised when the sqs message is already in DynamoDB

    Args:
        BaseException (BaseException): The base class for all built-in exceptions.
    """

    def __init__(self, message_id, message="Error checking if SQS message is in dynamodb"):
        self.message_id = message_id
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        error_message = f"{self.message_id} -> {self.message}"
        LOGGER.info(error_message)
        return f"{error_message}"


class ProcessingError(BaseException):
    """Raised when there is a Unknown processing error

    Args:
        BaseException (BaseException): The base class for all built-in exceptions.
    """

    pass
