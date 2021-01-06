'''
File: lambda_function.py
Project: ccda_finish_stepfunction
File Created: Friday, 17th July 2020 7:04:34 pm
Author: Canivel, Danilo (dccanive@amazon.com)
Description: Wraps up the CCD processing saving the log as complete for the message
-----
Last Modified: Tuesday, 22nd December 2020 8:55:35 am
Modified By: Canivel, Danilo (dccanive@amazon.com>)
-----
Copyright 2020 - 2020 Amazon Web Services, Amazon
'''

import json
import boto3

S3_CLIENT = boto3.client('s3')

def lambda_handler(event, context):
    # TODO implement
    # Validate the input save the logs and complete the state machine
    if event[0]['Status'] == 'COMPLETED':
        # save the logs with the operation to the master log table
        # confirm that the CCD file is stored in a versioned bucket
        # confirm that the FHIR BUNDLE BATCH file is stored in a versioned bucket
        # confirm that the FHIR BUNDLE RESOURCES files are stored in a versioned bucket
        bucket_landing = event[0]['Object']['bucket']
        key = event[0]['Object']['key']
        S3_CLIENT.delete_object(Bucket=bucket_landing, Key=f"{key}")
        event[0]['Status'] = 'COMPLETED'
    else:
        event[0]['Status'] = 'FAILED'

    return event[0]
