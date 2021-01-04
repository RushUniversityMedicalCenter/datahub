"""
File: exception_handler.py
Project: utils
File Created: Monday, 21st December 2020 11:19:23 am
Author: Canivel, Danilo (dccanive@amazon.com)
Description: Handles Exceptions and Generate the DeadLetter Queue for reprocessing
-----
Last Modified: Tuesday, 30nd December 2020 8:40:39 am
Modified By: Canivel, Danilo (dccanive@amazon.com>)
-----
Copyright 2020 - 2020 Amazon Web Services, Amazon
"""
import logging
import json

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


class HealthLakePostError(Exception):
    """Raised when the HealthLake Respond with a 400 Error """

    def __init__(self, event, message="HealthLake Post Failed"):
        self.event = event
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        error_message = {"error": self.message, "event": self.event}
        LOGGER.error(error_message)
        return json.dumps(error_message)


class AWSKeyMissingError(Exception):
    """Raised when the AWS Access Key and/or Secret Key is missing"""

    def __init__(self, event, message="AWS Access Key and/or Secret Key is missing"):
        self.event = event
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        error_message = {"error": self.message, "event": self.event}
        LOGGER.error(error_message)
        return json.dumps(error_message)


class HealthLakePostTooManyRequestsError(Exception):
    """Raised when the HealthLake response returns a 429 error: Too Many Requests for url"""

    def __init__(self, event, message="HealthLake Post Failed: Too Many Requests for url"):
        self.event = event
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        error_message = {"error": self.message, "event": self.event}
        LOGGER.error(error_message)
        return json.dumps(error_message)