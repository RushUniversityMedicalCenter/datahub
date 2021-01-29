"""
File: athena_helper.py
Project: aws-rush-fhir
File Created: Monday, 18th January 2021 5:02:19 pm
Author: Canivel, Danilo (dccanive@amazon.com)
-----
Last Modified: Friday, 29th January 2021 8:59:41 am
Modified By: Canivel, Danilo (dccanive@amazon.com>)
-----
(c) 2020 - 2021 Amazon Web Services, Inc. or its affiliates. All Rights Reserved. 
This AWS Content is provided subject to the terms of the AWS Customer Agreement available at
http://aws.amazon.com/agreement or other written agreement between Customer and either
Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
"""

import os
import boto3
import logging

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

S3_URI_ATHENA_QUERIES = os.environ["S3_URI_ATHENA_QUERIES"]  # s3://poc-rush-athenaqueries/queries/

GLUE_CRAWLER_PREFIX = os.environ["GLUE_CRAWLER_PREFIX"]  # daily_cpdh_idph_
BUCKET_PROCESSED_JUVARE = os.environ["BUCKET_PROCESSED_JUVARE"]  # rush-poc-ccd-preprocessed
BUCKET_PROCESSED_JUVARE_PREFIX = os.environ["BUCKET_PROCESSED_JUVARE"]  # daily_havbed

ATHENA_CLIENT = boto3.client("athena")


def add_new_partition(catalog_name, db_name, table_name, year, month, day):
    folder_name = table_name
    table_name = table_name.lower().replace(" ", "_").replace("-", "_")
    LOGGER.info(table_name)
    try:
        query = f"""
            ALTER TABLE {catalog_name}.{db_name}.{GLUE_CRAWLER_PREFIX}{table_name} ADD IF NOT EXISTS
            PARTITION(year='{year}', month='{month}', day='{day}')
            LOCATION 's3://{BUCKET_PROCESSED_JUVARE}/{BUCKET_PROCESSED_JUVARE_PREFIX}/{folder_name}/year={year}/month={month}/day={day}/'
        """

        ATHENA_CLIENT.start_query_execution(
            QueryString=query,
            QueryExecutionContext={"Database": db_name, "Catalog": catalog_name},
            ResultConfiguration={"OutputLocation": S3_URI_ATHENA_QUERIES},
        )
        return True
    except ATHENA_CLIENT.exceptions.InvalidRequestException as err:
        LOGGER.error(f'## EXCEPTION: {str(err.response["Error"]["Message"])}')
        raise err