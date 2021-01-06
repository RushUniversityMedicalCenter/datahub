'''
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
'''
import logging
import json

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


class FhirDatasetsGenerationError(Exception):
    """Raised when the Fhir Datasets are not generated """

    def __init__(self, event, message="Fhir Datasets Generation Failed"):
        self.event = event
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        error_message = {'error': self.message, 'event': self.event}
        LOGGER.error(error_message)
        return json.dumps(error_message)