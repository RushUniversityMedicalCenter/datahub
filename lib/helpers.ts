import s3 = require('@aws-cdk/aws-s3');
import kms = require('@aws-cdk/aws-kms');
import lambda = require('@aws-cdk/aws-lambda');
import iam = require('@aws-cdk/aws-iam');
import {Duration, RemovalPolicy, Stack} from "@aws-cdk/core";
import {FunctionProps} from "@aws-cdk/aws-lambda";

export class creates3bucket {
  bucket: s3.Bucket
  constructor(private stack: Stack,private bucketPrefix: string,private kmsKey: kms.IKey) {

   this.bucket = new s3.Bucket(stack, this.bucketPrefix, {
      encryption: s3.BucketEncryption.KMS,
      encryptionKey: this.kmsKey,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      versioned: true,
      removalPolicy: RemovalPolicy.DESTROY,
      lifecycleRules: [
        {
          transitions: [
            {
              storageClass: s3.StorageClass.GLACIER,
              transitionAfter: Duration.days(30)
            }
          ]
        }
      ]
    });
  }
}

export class createLambda {
  lambdaFunction: lambda.Function
  constructor(private stack: Stack, private envName: string, private execRole: iam.IRole, private functionName: string, private envVars: { [key: string]: string; }) {

    this.lambdaFunction = new lambda.Function(stack, functionName, {
      functionName: envName + '-' + functionName,
      runtime: lambda.Runtime.PYTHON_3_8,
      handler: functionName+'/lambda_function.lambda_handler',
      code: lambda.Code.fromAsset('lambda/'),
      role: execRole,
      environment: envVars,
    });
  }


}
