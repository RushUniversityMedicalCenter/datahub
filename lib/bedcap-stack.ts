/**
File: bedcap-stack.ts
Project: aws-rush-fhir
File Created: Wednesday, 6th January 2021 2:12:57 pm
Author: Pandre, Lakshmikanth (pandrel@amazon.com)
-----
  Last Modified: Friday, 29th January 2021 2:10:06 pm
Modified By: Pandre, Lakshmikanth (pandrel@amazon.com)
-----
 © 2020 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.

 This AWS Content is provided subject to the terms of the AWS Customer Agreement
 available at http://aws.amazon.com/agreement or other written agreement between
 Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
**/

import s3 = require('@aws-cdk/aws-s3');
import s3n = require('@aws-cdk/aws-s3-notifications');
import s3deploy = require('@aws-cdk/aws-s3-deployment');
import kms = require('@aws-cdk/aws-kms');
import iam = require('@aws-cdk/aws-iam');
import dynamodb = require('@aws-cdk/aws-dynamodb');
import glue = require('@aws-cdk/aws-glue');
import sns = require('@aws-cdk/aws-sns');
import lambda = require('@aws-cdk/aws-lambda');
import {App, CfnOutput, Duration, RemovalPolicy, Stack, StackProps} from "@aws-cdk/core";
import {createLambda, createLambdaWithLayer, creates3bucket} from "./helpers";

export interface juvareStackProps extends StackProps {
  readonly envName: string;
}

export class bedcapStack extends Stack {
  constructor(app: App, id: string, props: juvareStackProps) {
    super(app, id, props);

    const envName = props.envName

    // IAM role for processCCDA, .. add more tbd

    const roleLambdaProcessBedCap = new iam.Role(this, 'roleLambdaProcessBedCap',{
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
      roleName: envName+'LambdaProcessBedCap'
    });
    roleLambdaProcessBedCap.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaVPCAccessExecutionRole'))
    roleLambdaProcessBedCap.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaRole'))
    roleLambdaProcessBedCap.addToPolicy(new iam.PolicyStatement(
      {
        resources: ['*'],
        actions: ['glue:StartCrawler']
      }))

    // glue service role
    //const roleGlueService = iam.Role.fromRoleArn(this, 'roleGlueService','arn:aws:iam::'+this.account+':role/AWSGlueServiceRole-'+envName)
    const roleGlueService = new iam.Role(this, 'roleGlueService',{
      assumedBy: new iam.CompositePrincipal(
        new iam.ServicePrincipal("glue.amazonaws.com"),
        new iam.ServicePrincipal("lambda.amazonaws.com")
      ),
      // Glue role name must follow the below syntax. AWSGlueServiceRole Prefix is required for Glue to work properly.
      roleName: "AWSGlueServiceRole-"+envName+'BedCap'
    })
    roleGlueService.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSGlueServiceRole'))


    // KMS

    const kmsBedCapKey = new kms.Key(this, 'kmsBedCapKey',{
      alias: envName+'-bedcap-key',
      enableKeyRotation: true
    })
    kmsBedCapKey.grantEncryptDecrypt(roleLambdaProcessBedCap)

    // S3 Buckets


    const s3LandingBedCap = new creates3bucket(this, 'landing-bedcap', kmsBedCapKey)
    s3LandingBedCap.bucket.grantReadWrite(roleLambdaProcessBedCap)

    // Create folder structure in BedCap Landing bucket
    new s3deploy.BucketDeployment(this, 'bedcap_folder_structure',{
      sources: [s3deploy.Source.asset('./bedcap_folder_structure/')],
      destinationBucket: s3LandingBedCap.bucket,
      //destinationKeyPrefix: '',
    })

    const s3ProcessedBedCap = new creates3bucket(this, 'processed-bedcap', kmsBedCapKey)
    s3ProcessedBedCap.bucket.grantReadWrite(roleLambdaProcessBedCap)
    s3ProcessedBedCap.bucket.grantReadWrite(roleGlueService)

    // Athena Queries bucket. AES256 encrypted to allow users to use the bucket for athena queries
    const s3AthenaQueries = new s3.Bucket(this, 'athena-queries',{
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: RemovalPolicy.RETAIN,
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
    const bedcap_hash_table_log = new dynamodb.Table(this, 'bedcap_hash_table_log', {
      tableName: envName+'-bedcap_hash_table_log',
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: kmsBedCapKey,
      partitionKey: {name: 'md5Digest', type: dynamodb.AttributeType.STRING},
      removalPolicy: RemovalPolicy.DESTROY,
    })
    bedcap_hash_table_log.grantFullAccess(roleLambdaProcessBedCap)

    const bedcap_execution_log = new dynamodb.Table(this, 'bedcap_execution_log', {
      tableName: envName+'-bedcap_execution_log',
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: kmsBedCapKey,
      partitionKey: {name: 'lambdaId', type: dynamodb.AttributeType.STRING},
      removalPolicy: RemovalPolicy.DESTROY,
    })
    bedcap_execution_log.grantFullAccess(roleLambdaProcessBedCap)


    //
    // SNS
    //

    const BedCapProcessingTopic = new sns.Topic(this, 'snsBedCapProcessingTopic', {
      displayName: envName+'BedCapProcessingTopic'
    })

    //
    // Glue
    //

    const glueDbBedCap = new glue.Database(this, envName+'bedcap', {
      databaseName: envName+'-bedcap'
    })



    const JuvareDailyCDPHIDPHCrawler = new glue.CfnCrawler(this, 'JuvareDailyCDPHIDPHCrawler',{
      name: envName+'JuvareDailyCDPHIDPHCrawler',
      role: roleGlueService.roleArn,
      databaseName: glueDbBedCap.databaseName,
      schedule: {"scheduleExpression": "cron(0 0 * * ? *)"},
      tablePrefix: 'daily_cpdh_idph_',
      targets: {
        s3Targets: [{
          path: 's3://'+s3ProcessedBedCap.bucket.bucketName+'/juvare/cdph_idph/'
        }]
      }
    })

    const JuvareDailyHaveBedCrawler = new glue.CfnCrawler(this, 'JuvareDailyHaveBedCrawler',{
      name: envName+'JuvareDailyHaveBedCrawler',
      role: roleGlueService.roleArn,
      databaseName: glueDbBedCap.databaseName,
      tablePrefix: 'daily_have_bed_',
      schedule: {"scheduleExpression": "cron(0 0 * * ? *)"},
      targets: {
        s3Targets: [{
          path: 's3://'+s3ProcessedBedCap.bucket.bucketName+'/juvare/daily_havbed/'
        }]
      }
    })

    const HHSBedCapacityCrawler = new glue.CfnCrawler(this, 'HHSBedCapacityCrawler',{
      name: envName+'HHSBedCapacityCrawler',
      role: roleGlueService.roleArn,
      databaseName: glueDbBedCap.databaseName,
      tablePrefix: 'hhs_',
      schedule: {"scheduleExpression": "cron(0 0 * * ? *)"},
      targets: {
        s3Targets: [{
          path: 's3://'+s3ProcessedBedCap.bucket.bucketName+'/hhs/'
        }]
      }
    })

    // lambda layers
    const layerXlrd = new lambda.LayerVersion(this, 'xlrd', {
      code: lambda.Code.fromAsset('lambda_layer/xlrd.zip'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_8],
      layerVersionName: envName+'-xlrd'
    })

    // lambda

    const bedcap_cdph_idph_process = new createLambdaWithLayer(this, envName, roleLambdaProcessBedCap, 'bedcap_cdph_idph_process',layerXlrd,
      {
        BUCKET_PROCESSED_JUVARE: s3ProcessedBedCap.bucket.bucketName,
        BUCKET_PROCESSED_JUVARE_FOLDER: 'cdph_idph',
        BUCKET_RAW_JUVARE_FOLDER: 'raw_cdph_idph',
        DYNAMODB_JUVARE_EXECUTION_LOG: bedcap_execution_log.tableName,
        DYNAMODB_JUVARE_HASH_TABLE_LOG: bedcap_hash_table_log.tableName,
        GLUE_CRAWLER_JUVARE_CDPH_IDPH: envName+'JuvareDailyCDPHIDPHCrawler',
        SNS_TOPIC_ARN: BedCapProcessingTopic.topicArn
      });

    // todo add crawler, glue db

    const bedcap_have_bed_process = new createLambdaWithLayer(this, envName, roleLambdaProcessBedCap, 'bedcap_have_bed_process',layerXlrd,
      {
        BUCKET_PROCESSED_JUVARE: s3ProcessedBedCap.bucket.bucketName,
        BUCKET_PROCESSED_JUVARE_FOLDER: 'daily_havbed',
        BUCKET_RAW_JUVARE_FOLDER: 'raw_daily_havbed',
        DYNAMODB_JUVARE_EXECUTION_LOG: bedcap_execution_log.tableName,
        DYNAMODB_JUVARE_HASH_TABLE_LOG: bedcap_hash_table_log.tableName,
        GLUE_CRAWLER_JUVARE_HAVE_BED: envName+'JuvareDailyHaveBedCrawler',
        SNS_TOPIC_ARN: BedCapProcessingTopic.topicArn
      });

    const hhs_bed_capacity_process = new createLambda(this, envName,roleLambdaProcessBedCap, 'hhs_bed_capacity_process',
      {
        BUCKET_PROCESSED_HHS: s3ProcessedBedCap.bucket.bucketName,
        DYNAMODB_HHS_EXECUTION_LOG: bedcap_execution_log.tableName,
        DYNAMODB_HHS_HASH_TABLE_LOG: bedcap_hash_table_log.tableName,
        GLUE_CRAWLER_HHS: envName+'HHSBedCapacityCrawler',
        SNS_TOPIC_ARN: BedCapProcessingTopic.topicArn
      })


    // S3 Triggers/Notifications

    s3LandingBedCap.bucket.addEventNotification(s3.EventType.OBJECT_CREATED,
      new s3n.LambdaDestination(bedcap_cdph_idph_process.lambdaFunction),
      {
        prefix: 'juvare/cdph_idph/'
      })

    s3LandingBedCap.bucket.addEventNotification(s3.EventType.OBJECT_CREATED,
      new s3n.LambdaDestination(bedcap_have_bed_process.lambdaFunction),
      {
        prefix: 'juvare/daily_havbed/'
      })

    s3LandingBedCap.bucket.addEventNotification(s3.EventType.OBJECT_CREATED,
      new s3n.LambdaDestination(hhs_bed_capacity_process.lambdaFunction),
      {
        prefix: 'hhs/'
      })

    new CfnOutput(this, 'roleGlueServiceExport', {
      value: roleGlueService.roleArn,
    });
    new CfnOutput(this, 's3LandingBedCap', {
      value: s3LandingBedCap.bucket.bucketName,
    });
    new CfnOutput(this, 's3ProcessedBedCap', {
      value: s3ProcessedBedCap.bucket.bucketName,
    });
    new CfnOutput(this, 'BedCapProcessingTopic', {
      value: BedCapProcessingTopic.topicArn,
    });





  }
}
