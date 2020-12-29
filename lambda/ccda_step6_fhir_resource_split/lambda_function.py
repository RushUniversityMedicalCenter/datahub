'''
File: lambda_function.py
Project: ccda_step6_fhir_resource_split
File Created: Friday, 17th July 2020 7:04:34 pm
Author: Canivel, Danilo (dccanive@amazon.com)
Description: Split the FHIR Batch into Bundles, split each Resource by the Resource type
and POST it to Health Lake
-----
Last Modified: Tuesday, 22nd December 2020 8:37:25 am
Modified By: Canivel, Danilo (dccanive@amazon.com>)
-----
Copyright 2020 - 2020 Amazon Web Services, Amazon
'''

import json


def lambda_handler(event, context):
    # TODO implement
    # REad the FHIr file content
    # Split each entry and each Resource Type and send it to Health Lake
    # Save log in each iteration/resource persist
    # completes the Iterator
    if event['Status'] == 'DATASETS_GENERATED':
        # process the fhir bundle and split each resource
        # persist to health lake
        # save each resource to the Process bucket
        event['Status'] = 'COMPLETED'
    else:
        event['Status'] = 'FAILED'
        raise Exception

    return event
