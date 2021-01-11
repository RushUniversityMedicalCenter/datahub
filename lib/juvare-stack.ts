import s3 = require('@aws-cdk/aws-s3');
import s3n = require('@aws-cdk/aws-s3-notifications');
import kms = require('@aws-cdk/aws-kms');
import iam = require('@aws-cdk/aws-iam');
import dynamodb = require('@aws-cdk/aws-dynamodb');
import sqs = require('@aws-cdk/aws-sqs');
import sns = require('@aws-cdk/aws-sns');
import lambda = require('@aws-cdk/aws-lambda');
import {App, CfnOutput, Duration, Fn, Stack, StackProps} from "@aws-cdk/core";
import {createLambda, createLambdaWithLayer, creates3bucket} from "./helpers";

export interface dataStackProps extends StackProps {
  readonly envName: string;
}

export class dataStack extends Stack {
  constructor(app: App, id: string, props: dataStackProps) {
    super(app, id, props);

    const envName = props.envName

    // IAM role for processCCDA, .. add more tbd

    const roleLambdaProcessJuvare = new iam.Role(this, 'roleLambdaProcessJuvare',{
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
      roleName: envName+'LambdaProcessJuvare'
    });
    roleLambdaProcessJuvare.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaVPCAccessExecutionRole'))
    roleLambdaProcessJuvare.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaRole'))

    // glue service role
    const roleGlueService = new iam.Role(this, 'roleGlueService',{
      assumedBy: new iam.CompositePrincipal(
        new iam.ServicePrincipal("glue.amazonaws.com"),
        new iam.ServicePrincipal("lambda.amazonaws.com")
      ),
      // Glue role name must follow the below syntax. AWSGlueServiceRole Prefix is required for Glue to work properly.
      roleName: "AWSGlueServiceRole-"+envName
    })
    roleGlueService.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSGlueServiceRole'))


    // KMS

    const kmsJuvareKey = new kms.Key(this, 'kmsJuvareKey',{
      alias: envName+'-juvare-key'
    })
    kmsJuvareKey.grantEncryptDecrypt(roleLambdaProcessJuvare)

    // S3 Buckets


    const s3LandingJuvare = new creates3bucket(this, 'landing-juvare', kmsJuvareKey)
    s3LandingJuvare.bucket.grantReadWrite(roleLambdaProcessJuvare)

    const s3ProcessedJuvare = new creates3bucket(this, 'processed-juvare', kmsJuvareKey)
    s3ProcessedJuvare.bucket.grantReadWrite(roleLambdaProcessJuvare)

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
    const juvare_hash_table_log = new dynamodb.Table(this, 'juvare_hash_table_log', {
      tableName: envName+'-juvare_hash_table_log',
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: kmsJuvareKey,
      partitionKey: {name: 'md5Digest', type: dynamodb.AttributeType.STRING},
    })
    juvare_hash_table_log.grantFullAccess(roleLambdaProcessJuvare)

    const juvare_execution_log = new dynamodb.Table(this, 'juvare_execution_log', {
      tableName: envName+'-juvare_execution_log',
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: kmsJuvareKey,
      partitionKey: {name: 'id', type: dynamodb.AttributeType.STRING},
    })
    juvare_execution_log.grantFullAccess(roleLambdaProcessJuvare)


    //
    // SNS
    //

    const JuvareProcessingTopic = new sns.Topic(this, 'snsJuvareProcessingTopic', {
      displayName: envName+'JuvareProcessingTopic'
    })




    // lambda layers
    const layerXlrd = new lambda.LayerVersion(this, 'xlrd', {
      code: lambda.Code.fromAsset('lambda_layer/xlrd.zip'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_8],
      layerVersionName: envName+'-xlrd'
    })

    // lambda

    const juvare_cdph_idph_process = new createLambdaWithLayer(this, envName, roleLambdaProcessJuvare, 'juvare_cdph_idph_process',layerXlrd,
      {
        BUCKET_PROCESSED_JUVARE: s3ProcessedJuvare.bucket.bucketName,
        BUCKET_PROCESSED_JUVARE_PREFIX: 'juavare/cdph_idph',
        BUCKET_RAW_JUVARE_PREFIX: 'juavare/raw_cdph_idph',
        GLUE_CATALOG_NAME: 'AwsDataCatalog',
        GLUE_DB_NAME: 'juavare',
        SNS_TOPIC_ARN: JuvareProcessingTopic.topicArn
      });

    // todo add crawler, glue db

    const juvare_have_bed_process = new createLambdaWithLayer(this, envName, roleLambdaProcessJuvare, 'juvare_have_bed_process',layerXlrd,
      {
        BUCKET_PROCESSED_JUVARE: s3ProcessedJuvare.bucket.bucketName,
        BUCKET_PROCESSED_JUVARE_FOLDER: 'daily_havbed',
        BUCKET_RAW_JUVARE_FOLDER: 'juavare/raw_cdph_idph',
        DYNAMODB_JUVARE_EXECUTION_LOG: 'AwsDataCatalog',
        DYNAMODB_JUVARE_HASH_TABLE_LOG: 'juavare',
        GLUE_CATALOG_NAME: '',
        GLUE_CRAWLER_PREFIX: '',
        GLUE_DB_NAME: '',
        S3_URI_ATHENA_QUERIES: 's3://'+s3AthenaQueries.bucketName+'/queries/',
        SNS_TOPIC_ARN: JuvareProcessingTopic.topicArn
      });

    // S3 Triggers/Notifications

    s3LandingJuvare.bucket.addEventNotification(s3.EventType.OBJECT_CREATED, new s3n.LambdaDestination(juvare_cdph_idph_process.lambdaFunction))


    new CfnOutput(this, 'roleGlueServiceExport', {
      value: roleGlueService.roleArn,
      exportName: envName+'-roleGlueService'
    });


  }
}
