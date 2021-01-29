"""
File: lambda_function.py
Project: aws-rush-fhir
File Created: Monday, 18th January 2021 5:02:19 pm
Author: Lakshmikanth Pandre (pandrel@amazon.com)
-----
Last Modified: Friday, 29th January 2021 9:00:20 am
Modified By: Canivel, Danilo (dccanive@amazon.com>)
-----
(c) 2020 - 2021 Amazon Web Services, Inc. or its affiliates. All Rights Reserved. 
This AWS Content is provided subject to the terms of the AWS Customer Agreement available at
http://aws.amazon.com/agreement or other written agreement between Customer and either
Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
"""

import json
import base64
import boto3
import uuid
import os

BUCKET_NAME = os.environ["BUCKET_LANDING_API"]


def lambda_handler(event, context):

    FILE_NAME = f"{context.aws_request_id}.xml"

    res = json.loads(json.dumps(event))
    xml = base64.b64decode(res["body"])

    print(json.dumps(event))
    print(context.aws_request_id)

    s3 = boto3.client("s3")

    try:
        s3_response = s3.put_object(Bucket=BUCKET_NAME, Key=FILE_NAME, Body=xml)
    except Exception as e:
        print("Error: {}.".format(e.response["Error"]["Message"]))
        raise IOError(e)

    return {"statusCode": 200, "body": json.dumps("Filename: " + FILE_NAME)}
