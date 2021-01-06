import json
import base64
import boto3
import uuid
import os

BUCKET_NAME=os.environ['BUCKET_LANDING_API']


def lambda_handler(event, context):

    FILE_NAME=f"{context.aws_request_id}.xml"

    res = json.loads(json.dumps(event))
    xml = res['body'].read()

    print(json.dumps(event))
    print(context.aws_request_id)

    s3 = boto3.client('s3')

    try:
        s3_response = s3.put_object(Bucket=BUCKET_NAME, Key=FILE_NAME, Body=xml)
    except Exception as e:
        print('Error: {}.'.format(e.response['Error']['Message']))
        raise IOError(e)

    return {
        'statusCode': 200,
        'body': json.dumps('Filename: '+FILE_NAME)
    }
