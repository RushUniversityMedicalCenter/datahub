# Step 3 - De-duplication

#### lambda_function.py

Lambda Handler that executes Step 3 of the Pipeline and validate if the file was already processed.

For each file in the pipeline a MD5 digest hash is generated from the file content, and saved as a partition key in DynamoDB Hash table if does not exists in the table yet.

If the hash key already exists an Exception CCDADeduplicationError is Raised and is handle by the Exception Handler.

If the hash does not exists, the md5digest hash is added to the Object key in the output

#### Enviroment Variables

| Enviroment Variable       | Description                                 |
| ------------------------- | ------------------------------------------- |
| CCDS_SQSMESSAGE_TABLE_LOG | Table in DynamoDB where the logs are saved  |
| CCDS_HASH_TABLE_LOG       | Table in DynamoDB where MD5 hashs are saved |

#### Exceptions

@TODO

![Step3](../../images/stepfunctions/step3.png)

#### State input sample:

```
{
  "Source": {
    "sqs_message_id": "bfe78a99-a6d5-45c9-a0d5-7e9283889bf9",
    "aws_request_id": "302107e8-f3f4-5e08-90f2-5f9a4b8a936d",
    "receiptHandle": "AQEBhbG/A1BdKrDR9IdcjKCglXELZ4H5AlEIKxMRm+b3auWL9izpswMgNWK/A6cB26yiJ+28UQgxYj7XriO09gZVOYC/ZVwzY8WaO2GJ1uvHJzu/m0uzIVF/O4WgIWyeUOwZgtYl5Y0gh9XHc+v1WeqeapvGVhsJ5sTiFDfNdkDNFO37mN9weOc0Ii6hJSQtw6pG5NBwj1kVpKUHvhckfu+GX47YHvzdUruStijQNdB7JKfLyrmiMX5FvBf0O8j08072kT9yYD2UkYF5zCu3H1qxxSosFqlOcUK8hN+XIRP5KB3xn11BNL89RI+46VlYqKbV+SabR4YUdrL4MyWztsiPo05qqAGW+oodRhb1g2uCFEmsuz8rImYzFDGZlbvheGNA3yRSEM0Jq993xRrBZdnMsagMYMtMA+wxTBWdDkDOsSI="
  },
  "Object": {
    "bucket": "devdatastack-landingdirectcad59385-16lw97bb7fhkp",
    "key": "0ffd6412-554f-c218-0211-3a912f683b5e.xml",
    "Type": "CCD"
  },
  "Status": "VALID"
}
```

#### State output sample:

```
{
  "Source": {
    "sqs_message_id": "bfe78a99-a6d5-45c9-a0d5-7e9283889bf9",
    "aws_request_id": "302107e8-f3f4-5e08-90f2-5f9a4b8a936d",
    "receiptHandle": "AQEBhbG/A1BdKrDR9IdcjKCglXELZ4H5AlEIKxMRm+b3auWL9izpswMgNWK/A6cB26yiJ+28UQgxYj7XriO09gZVOYC/ZVwzY8WaO2GJ1uvHJzu/m0uzIVF/O4WgIWyeUOwZgtYl5Y0gh9XHc+v1WeqeapvGVhsJ5sTiFDfNdkDNFO37mN9weOc0Ii6hJSQtw6pG5NBwj1kVpKUHvhckfu+GX47YHvzdUruStijQNdB7JKfLyrmiMX5FvBf0O8j08072kT9yYD2UkYF5zCu3H1qxxSosFqlOcUK8hN+XIRP5KB3xn11BNL89RI+46VlYqKbV+SabR4YUdrL4MyWztsiPo05qqAGW+oodRhb1g2uCFEmsuz8rImYzFDGZlbvheGNA3yRSEM0Jq993xRrBZdnMsagMYMtMA+wxTBWdDkDOsSI="
  },
  "Object": {
    "bucket": "devdatastack-landingdirectcad59385-16lw97bb7fhkp",
    "key": "0ffd6412-554f-c218-0211-3a912f683b5e.xml",
    "Type": "CCD",
    "md5_digest": "69aacbfef722f78fddb59aadfc3a036f"
  },
  "Status": "VALID"
}
```
