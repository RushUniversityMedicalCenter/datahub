### Final Step - Finish step function execution

Lambda responsible to finish the step function execution.

At this point all the iterations finish Sucessfully, and the result is a Succesull End trigger.

This will save the logs at DynamoDB and Cloudwatch, and will remove the raw data from the landing bucket, since all the data is been saved and manteined into raw\_\* folder at processed layer.

![Step1](../../images/stepfunctions/full_sfn.png)

#### State input sample:

```
[
  {
    "Source": {
      "sqs_message_id": "bfe78a99-a6d5-45c9-a0d5-7e9283889bf9",
      "aws_request_id": "302107e8-f3f4-5e08-90f2-5f9a4b8a936d",
      "receiptHandle": "AQEBhbG/A1BdKrDR9IdcjKCglXELZ4H5AlEIKxMRm+b3auWL9izpswMgNWK/A6cB26yiJ+28UQgxYj7XriO09gZVOYC/ZVwzY8WaO2GJ1uvHJzu/m0uzIVF/O4WgIWyeUOwZgtYl5Y0gh9XHc+v1WeqeapvGVhsJ5sTiFDfNdkDNFO37mN9weOc0Ii6hJSQtw6pG5NBwj1kVpKUHvhckfu+GX47YHvzdUruStijQNdB7JKfLyrmiMX5FvBf0O8j08072kT9yYD2UkYF5zCu3H1qxxSosFqlOcUK8hN+XIRP5KB3xn11BNL89RI+46VlYqKbV+SabR4YUdrL4MyWztsiPo05qqAGW+oodRhb1g2uCFEmsuz8rImYzFDGZlbvheGNA3yRSEM0Jq993xRrBZdnMsagMYMtMA+wxTBWdDkDOsSI="
    },
    "Object": {
      "bucket": "devdatastack-landingdirectcad59385-16lw97bb7fhkp",
      "key": "Kala987_Braun514_0ffd6412-554f-c218-0211-3a912f683b5e.xml",
      "Type": "CCD",
      "md5_digest": "69aacbfef722f78fddb59aadfc3a036f"
    },
    "Status": "COMPLETED",
    "Fhir": {
      "bucket": "devdatastack-processedeabdebfd-m9jgldc6h55v",
      "key": "converted/year=2021/month=1/day=8/message_id=bfe78a99-a6d5-45c9-a0d5-7e9283889bf9/Kala987_Braun514_0ffd6412-554f-c218-0211-3a912f683b5e.xml.fhir.json"
    },
    "HealthLake": [
      {
        "ResourceType": "Bundle",
        "CreationDate": 1610135116,
        "Status": "CREATED",
        "FhirResource": {
          "bucket": "devdatastack-processedeabdebfd-m9jgldc6h55v",
          "key": "fhir_resources/resource_type=Bundle/year=2021/month=1/day=8/message_id=bfe78a99-a6d5-45c9-a0d5-7e9283889bf9/1610135116_Kala987_Braun514_0ffd6412-554f-c218-0211-3a912f683b5e.xml.fhir.json"
        }
      }
    ]
  }
]
```

#### State output sample:

```
{
  "ExecutedVersion": "$LATEST",
  "Payload": {
    "Source": {
      "sqs_message_id": "bfe78a99-a6d5-45c9-a0d5-7e9283889bf9",
      "aws_request_id": "302107e8-f3f4-5e08-90f2-5f9a4b8a936d",
      "receiptHandle": "AQEBhbG/A1BdKrDR9IdcjKCglXELZ4H5AlEIKxMRm+b3auWL9izpswMgNWK/A6cB26yiJ+28UQgxYj7XriO09gZVOYC/ZVwzY8WaO2GJ1uvHJzu/m0uzIVF/O4WgIWyeUOwZgtYl5Y0gh9XHc+v1WeqeapvGVhsJ5sTiFDfNdkDNFO37mN9weOc0Ii6hJSQtw6pG5NBwj1kVpKUHvhckfu+GX47YHvzdUruStijQNdB7JKfLyrmiMX5FvBf0O8j08072kT9yYD2UkYF5zCu3H1qxxSosFqlOcUK8hN+XIRP5KB3xn11BNL89RI+46VlYqKbV+SabR4YUdrL4MyWztsiPo05qqAGW+oodRhb1g2uCFEmsuz8rImYzFDGZlbvheGNA3yRSEM0Jq993xRrBZdnMsagMYMtMA+wxTBWdDkDOsSI="
    },
    "Object": {
      "bucket": "devdatastack-landingdirectcad59385-16lw97bb7fhkp",
      "key": "Kala987_Braun514_0ffd6412-554f-c218-0211-3a912f683b5e.xml",
      "Type": "CCD",
      "md5_digest": "69aacbfef722f78fddb59aadfc3a036f"
    },
    "Status": "COMPLETED",
    "Fhir": {
      "bucket": "devdatastack-processedeabdebfd-m9jgldc6h55v",
      "key": "converted/year=2021/month=1/day=8/message_id=bfe78a99-a6d5-45c9-a0d5-7e9283889bf9/Kala987_Braun514_0ffd6412-554f-c218-0211-3a912f683b5e.xml.fhir.json"
    },
    "HealthLake": [
      {
        "ResourceType": "Bundle",
        "CreationDate": 1610135116,
        "Status": "CREATED",
        "FhirResource": {
          "bucket": "devdatastack-processedeabdebfd-m9jgldc6h55v",
          "key": "fhir_resources/resource_type=Bundle/year=2021/month=1/day=8/message_id=bfe78a99-a6d5-45c9-a0d5-7e9283889bf9/1610135116_Kala987_Braun514_0ffd6412-554f-c218-0211-3a912f683b5e.xml.fhir.json"
        }
      }
    ]
  },
  "SdkHttpMetadata": {
    "AllHttpHeaders": {
      "X-Amz-Executed-Version": [
        "$LATEST"
      ],
      "x-amzn-Remapped-Content-Length": [
        "0"
      ],
      "Connection": [
        "keep-alive"
      ],
      "x-amzn-RequestId": [
        "990339c4-9ada-4a32-a31b-c0946876aa15"
      ],
      "Content-Length": [
        "1403"
      ],
      "Date": [
        "Fri, 08 Jan 2021 19:45:29 GMT"
      ],
      "X-Amzn-Trace-Id": [
        "root=1-5ff8b659-3b7af2a26a7b43197035bd58;sampled=0"
      ],
      "Content-Type": [
        "application/json"
      ]
    },
    "HttpHeaders": {
      "Connection": "keep-alive",
      "Content-Length": "1403",
      "Content-Type": "application/json",
      "Date": "Fri, 08 Jan 2021 19:45:29 GMT",
      "X-Amz-Executed-Version": "$LATEST",
      "x-amzn-Remapped-Content-Length": "0",
      "x-amzn-RequestId": "990339c4-9ada-4a32-a31b-c0946876aa15",
      "X-Amzn-Trace-Id": "root=1-5ff8b659-3b7af2a26a7b43197035bd58;sampled=0"
    },
    "HttpStatusCode": 200
  },
  "SdkResponseMetadata": {
    "RequestId": "990339c4-9ada-4a32-a31b-c0946876aa15"
  },
  "StatusCode": 200
}
```
