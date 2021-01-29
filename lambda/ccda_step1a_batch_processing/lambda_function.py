"""
File: lambda_function.py
Project: ccda_step1a_batch_processing
File Created: Friday, 17th July 2020 7:04:34 pm
Author: Canivel, Danilo (dccanive@amazon.com)
Description: Process Zip or Gzip files as a Batch sending each CCD to the Iterator
-----
Last Modified: Tuesday, 22nd December 2020 8:34:36 am
Modified By: Canivel, Danilo (dccanive@amazon.com>)
-----
(c) 2020 - 2021 Amazon Web Services, Inc. or its affiliates. All Rights Reserved. 
This AWS Content is provided subject to the terms of the AWS Customer Agreement available at
http://aws.amazon.com/agreement or other written agreement between Customer and either
Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
"""


import json


def lambda_handler(event, context):
    # TODO implement
    # Validate the input save the logs and complete the state machine
    if event["Status"] == "BATCH":
        # save the logs with the operation to the master log table
        pass
    else:
        event["Status"] == "FAILED"

    return event
