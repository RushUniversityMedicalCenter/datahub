/*
 * File: helpers.ts
 * Project: aws-rush-fhir
 * File Created: Monday, 18th January 2021 5:02:20 pm
 * Author: Lakshmikanth Pandre (pandrel@amazon.com)
 * -----
 * Last Modified: Friday, 29th January 2021 9:03:32 am
 * Modified By: Canivel, Danilo (dccanive@amazon.com>)
 * -----
 * (c) 2020 - 2021 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
 * This AWS Content is provided subject to the terms of the AWS Customer Agreement available at
 * http://aws.amazon.com/agreement or other written agreement between Customer and either
 * Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
 */

import s3 = require("@aws-cdk/aws-s3");
import kms = require("@aws-cdk/aws-kms");
import lambda = require("@aws-cdk/aws-lambda");
import iam = require("@aws-cdk/aws-iam");
import { Duration, RemovalPolicy, Stack } from "@aws-cdk/core";

export class creates3bucket {
  bucket: s3.Bucket;
  constructor(private stack: Stack, private bucketPrefix: string, private kmsKey: kms.IKey) {
    this.bucket = new s3.Bucket(stack, this.bucketPrefix, {
      encryption: s3.BucketEncryption.KMS,
      encryptionKey: this.kmsKey,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      versioned: true,
      removalPolicy: RemovalPolicy.RETAIN, // otherwise it will fail deleting stack if bucket is not empty
      lifecycleRules: [
        {
          transitions: [
            {
              storageClass: s3.StorageClass.GLACIER,
              transitionAfter: Duration.days(30),
            },
          ],
        },
      ],
    });
  }
}

export class createLambda {
  lambdaFunction: lambda.Function;
  constructor(
    private stack: Stack,
    private envName: string,
    private execRole: iam.IRole,
    private functionName: string,
    private envVars: { [key: string]: string }
  ) {
    this.lambdaFunction = new lambda.Function(stack, functionName, {
      functionName: envName + "-" + functionName,
      runtime: lambda.Runtime.PYTHON_3_8,
      timeout: Duration.seconds(300),
      handler: "lambda_function.lambda_handler",
      code: lambda.Code.fromAsset("lambda/" + functionName),
      role: execRole,
      environment: envVars,
    });
  }
}

export class createLambdaWithLayer {
  lambdaFunction: lambda.Function;
  constructor(
    private stack: Stack,
    private envName: string,
    private execRole: iam.IRole,
    private functionName: string,
    private layer: lambda.LayerVersion,
    private envVars: { [key: string]: string }
  ) {
    this.lambdaFunction = new lambda.Function(stack, functionName, {
      functionName: envName + "-" + functionName,
      runtime: lambda.Runtime.PYTHON_3_8,
      timeout: Duration.seconds(300),
      handler: "lambda_function.lambda_handler",
      code: lambda.Code.fromAsset("lambda/" + functionName),
      layers: [layer],
      role: execRole,
      environment: envVars,
    });
  }
}
