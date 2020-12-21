import s3 = require('@aws-cdk/aws-s3');
import kms = require('@aws-cdk/aws-kms');
import iam = require('@aws-cdk/aws-iam');
import {Duration, App, Stack, StackProps, CfnParameter, Fn} from "@aws-cdk/core";
import {creates3bucket} from "./helpers";


export interface securityStackProps extends StackProps {
  readonly envName: string;
}

export class securityStack extends Stack {
  constructor(app: App, id: string, props: securityStackProps) {
    super(app, id, props);

    const envName = props.envName

    //
    // IAM roles
    //

    // IAM role for processCCDA, .. add more tbd

    const roleProcessLambda = new iam.Role(this, 'roleProcessLambda',{
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com")
    });
    roleProcessLambda.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaVPCAccessExecutionRole'))
    roleProcessLambda.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonDynamoDBFullAccess'))
    // add dynamodb access
    // add s3 access

    // glue service role
    const roleGlueService = new iam.Role(this, 'roleGlueService',{
      assumedBy: new iam.CompositePrincipal(
        new iam.ServicePrincipal("glue.amazonaws.com"),
        new iam.ServicePrincipal("lambda.amazonaws.com")
      ),
      roleName: "AWSGlueServiceRole-"+envName
    })
    roleGlueService.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSGlueServiceRole'))


    //
    // KMS keys
    //

    const kmsLandingKey = new kms.Key(this, 'kmsLandingKey',{
      alias: envName+'-landing-key'
    })
    kmsLandingKey.grantEncryptDecrypt(roleProcessLambda)
    // kmsLandingKey.grantEncryptDecrypt(roleGlueService)


    const kmsProcessedKey = new kms.Key(this, 'kmsProcessedKey',{
      alias: envName+'-processed-key'
    })
    kmsProcessedKey.grantEncryptDecrypt(roleProcessLambda)
    kmsProcessedKey.grantEncryptDecrypt(roleGlueService)

    const kmsDatabaseKey = new kms.Key(this, 'kmsDatabaseKey',{
      alias: envName+'-database-key'
    })
    kmsDatabaseKey.grantEncryptDecrypt(roleProcessLambda)


    //
    // S3 buckets
    //

    // Landing Buckets - Direct, Api, SFTP
    const s3LandingDirect = new s3.Bucket(this, envName+'-landing-direct',{
      encryption: s3.BucketEncryption.KMS,
      encryptionKey: kmsLandingKey,
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
    s3LandingDirect.grantReadWrite(roleProcessLambda)

    const s3LandingApi = new s3.Bucket(this, envName+'-landing-api',{
      encryption: s3.BucketEncryption.KMS,
      encryptionKey: kmsLandingKey,
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
    s3LandingApi.grantReadWrite(roleProcessLambda)

    const s3LandingSftp = new s3.Bucket(this, envName+'-landing-sftp',{
      encryption: s3.BucketEncryption.KMS,
      encryptionKey: kmsLandingKey,
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
    s3LandingSftp.grantReadWrite(roleProcessLambda)


    const s3LandingJuvare = new s3.Bucket(this, envName+'-landing-juvare',{
      encryption: s3.BucketEncryption.KMS,
      encryptionKey: kmsLandingKey,
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
    s3LandingJuvare.grantReadWrite(roleProcessLambda)

    // athena queries
    // processed
    // const s3Processed = new s3.Bucket(this, envName+'-processed',{
    //   encryption: s3.BucketEncryption.KMS,
    //   encryptionKey: kmsLandingKey,
    //   blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
    //   versioned: true,
    //   lifecycleRules: [
    //     {
    //       transitions: [
    //         {
    //           storageClass: s3.StorageClass.GLACIER,
    //           transitionAfter: Duration.days(30)
    //         }
    //       ]
    //     }
    //   ]
    // });
    // s3Processed.grantReadWrite(roleProcessLambda)
    // s3Processed.grantReadWrite(roleGlueService)
    //
    // const s3AthenaQueries = new s3.Bucket(this, envName+'-athena-queries',{
    //   encryption: s3.BucketEncryption.S3_MANAGED,
    //   blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
    //   versioned: true,
    //   lifecycleRules: [
    //     {
    //       transitions: [
    //         {
    //           storageClass: s3.StorageClass.GLACIER,
    //           transitionAfter: Duration.days(30)
    //         }
    //       ]
    //     }
    //   ]
    // });
    // s3AthenaQueries.grantReadWrite(roleGlueService)

    const testbucket = new creates3bucket(this, envName,'testbucket',kmsLandingKey)
    console.log(testbucket.bucket.bucketName)

  }
}
