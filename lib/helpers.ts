import s3 = require('@aws-cdk/aws-s3');
import kms = require('@aws-cdk/aws-kms');
import iam = require('@aws-cdk/aws-iam');
import {Construct, Duration, Stack} from "@aws-cdk/core";

export class creates3bucket {
  bucket: s3.Bucket
  constructor(private stack: Stack,private envName: string, private bucketPrefix: string,private kmsKey: kms.Key) {

   this.bucket = new s3.Bucket(stack, this.envName + bucketPrefix, {
      encryption: s3.BucketEncryption.KMS,
      encryptionKey: this.kmsKey,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      versioned: true,
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
