import s3 = require('@aws-cdk/aws-s3');
import s3n = require('@aws-cdk/aws-s3-notifications')
import kms = require('@aws-cdk/aws-kms');
import iam = require('@aws-cdk/aws-iam');
import dynamodb = require('@aws-cdk/aws-dynamodb');
import sqs = require('@aws-cdk/aws-sqs');
import {App, CfnOutput, Duration, Stack, StackProps} from "@aws-cdk/core";
import {creates3bucket} from "./helpers";
import {QueueEncryption} from "@aws-cdk/aws-sqs";
import {prefix} from "aws-cdk/lib/logging";


export interface dataStackProps extends StackProps {
  readonly envName: string;
}

export class dataStack extends Stack {
  constructor(app: App, id: string, props: dataStackProps) {
    super(app, id, props);

    const envName = props.envName

    //
    // IAM roles
    //

    // IAM role for processCCDA, .. add more tbd

    const roleLambdaProcessCCD = new iam.Role(this, 'roleLambdaProcessCCD',{
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com")
    });
    roleLambdaProcessCCD.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaVPCAccessExecutionRole'))
    // roleLambdaProcessCCD.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonDynamoDBFullAccess'))
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
    kmsLandingKey.grantEncryptDecrypt(roleLambdaProcessCCD)

    const kmsProcessedKey = new kms.Key(this, 'kmsProcessedKey',{
      alias: envName+'-processed-key'
    })
    kmsProcessedKey.grantEncryptDecrypt(roleLambdaProcessCCD)
    kmsProcessedKey.grantEncryptDecrypt(roleGlueService)

    const kmsDatabaseKey = new kms.Key(this, 'kmsDatabaseKey',{
      alias: envName+'-database-key'
    })
    kmsDatabaseKey.grantEncryptDecrypt(roleLambdaProcessCCD)


    //
    // S3 Buckets
    // Landing Buckets - Direct, Api, SFTP
    const s3LandingDirect = new creates3bucket(this, 'landing-direct', kmsLandingKey)
    s3LandingDirect.bucket.grantReadWrite(roleLambdaProcessCCD)

    const s3LandingApi = new creates3bucket(this, 'landing-api', kmsLandingKey)
    s3LandingApi.bucket.grantReadWrite(roleLambdaProcessCCD)

    const s3LandingSftp = new creates3bucket(this, 'landing-sftp', kmsLandingKey)
    s3LandingSftp.bucket.grantReadWrite(roleLambdaProcessCCD)

    const s3LandingJuvare = new creates3bucket(this, 'landing-juvare', kmsLandingKey)
    s3LandingJuvare.bucket.grantReadWrite(roleLambdaProcessCCD)

    // Processed Bucket
    const s3Processed = new creates3bucket(this, 'processed', kmsProcessedKey)
    s3Processed.bucket.grantReadWrite(roleLambdaProcessCCD)
    s3Processed.bucket.grantReadWrite(roleGlueService)

    // Athena Queries bucket. AES256 encrypted to allow users to use the bucket for athena queries
    const s3AthenaQueries = new s3.Bucket(this, 'athena-queries',{
      encryption: s3.BucketEncryption.S3_MANAGED,
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
    s3AthenaQueries.grantReadWrite(roleGlueService)


    // dynamodb
    const ddb = new dynamodb.Table(this, 'ddb', {
      tableName: envName+'-ccd-conversion-log',
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: kmsDatabaseKey,
      partitionKey: {name: 'id', type: dynamodb.AttributeType.STRING},
    })
    ddb.grantFullAccess(roleLambdaProcessCCD)

    //
    // SQS
    //

    const ccdDeadLetterQueue = new sqs.Queue(this, 'ccdDeadLetterQueue',{
    })

    const ccdQueue = new sqs.Queue(this, 'ccdQueue',{
      deadLetterQueue: {
        maxReceiveCount: 10,
        queue: ccdDeadLetterQueue
      },
    })

    // S3 Triggers/Notifications

    s3LandingDirect.bucket.addEventNotification(s3.EventType.OBJECT_CREATED, new s3n.SqsDestination(ccdQueue))
    s3LandingApi.bucket.addEventNotification(s3.EventType.OBJECT_CREATED, new s3n.SqsDestination(ccdQueue))
    s3LandingSftp.bucket.addEventNotification(s3.EventType.OBJECT_CREATED, new s3n.SqsDestination(ccdQueue))
    s3LandingJuvare.bucket.addEventNotification(s3.EventType.OBJECT_CREATED, new s3n.SqsDestination(ccdQueue))

    //
    // Cloudformation exports
    //


    new CfnOutput(this, 'kmsLandingKeyExport', {
      value: kmsLandingKey.keyArn,
      exportName: envName+'-kmsLandingKey'
    });

    new CfnOutput(this, 'kmsProcessedKeyExport', {
      value: kmsProcessedKey.keyArn,
      exportName: envName+'-kmsProcessedKey'
    });

    new CfnOutput(this, 'kmsDatabaseKeyExport', {
      value: kmsDatabaseKey.keyArn,
      exportName: envName+'-kmsDatabaseKey'
    });

    new CfnOutput(this, 'roleGlueServiceExport', {
      value: roleGlueService.roleArn,
      exportName: envName+'-roleGlueService'
    });

    new CfnOutput(this, 'roleLambdaProcessCCDExport', {
      value: roleLambdaProcessCCD.roleArn,
      exportName: envName+'-roleLambdaProcessCCD'
    });


  }
}
