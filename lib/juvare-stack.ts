/*
 * File: juvare-stack.ts
 * Project: aws-rush-fhir
 * File Created: Monday, 18th January 2021 5:02:20 pm
 * Author: Lakshmikanth Pandre (pandrel@amazon.com)
 * -----
 * Last Modified: Friday, 29th January 2021 9:02:57 am
 * Modified By: Canivel, Danilo (dccanive@amazon.com>)
 * -----
 * (c) 2020 - 2021 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
 * This AWS Content is provided subject to the terms of the AWS Customer Agreement available at
 * http://aws.amazon.com/agreement or other written agreement between Customer and either
 * Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
 */

import s3 = require("@aws-cdk/aws-s3");
import s3n = require("@aws-cdk/aws-s3-notifications");
import s3deploy = require("@aws-cdk/aws-s3-deployment");
import kms = require("@aws-cdk/aws-kms");
import iam = require("@aws-cdk/aws-iam");
import dynamodb = require("@aws-cdk/aws-dynamodb");
import glue = require("@aws-cdk/aws-glue");
import sns = require("@aws-cdk/aws-sns");
import lambda = require("@aws-cdk/aws-lambda");
import { App, CfnOutput, Duration, RemovalPolicy, Stack, StackProps } from "@aws-cdk/core";
import { createLambda, createLambdaWithLayer, creates3bucket } from "./helpers";

export interface juvareStackProps extends StackProps {
  readonly envName: string;
}

export class juvareStack extends Stack {
  constructor(app: App, id: string, props: juvareStackProps) {
    super(app, id, props);

    const envName = props.envName;

    // IAM role for processCCDA, .. add more tbd

    const roleLambdaProcessJuvare = new iam.Role(this, "roleLambdaProcessJuvare", {
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
      roleName: envName + "LambdaProcessJuvare",
    });
    roleLambdaProcessJuvare.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSLambdaVPCAccessExecutionRole")
    );
    roleLambdaProcessJuvare.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSLambdaRole")
    );
    roleLambdaProcessJuvare.addToPolicy(
      new iam.PolicyStatement({
        resources: ["*"],
        actions: ["glue:StartCrawler"],
      })
    );

    // glue service role
    //const roleGlueService = iam.Role.fromRoleArn(this, 'roleGlueService','arn:aws:iam::'+this.account+':role/AWSGlueServiceRole-'+envName)
    const roleGlueService = new iam.Role(this, "roleGlueService", {
      assumedBy: new iam.CompositePrincipal(
        new iam.ServicePrincipal("glue.amazonaws.com"),
        new iam.ServicePrincipal("lambda.amazonaws.com")
      ),
      // Glue role name must follow the below syntax. AWSGlueServiceRole Prefix is required for Glue to work properly.
      roleName: "AWSGlueServiceRole-" + envName + "Juvare",
    });
    roleGlueService.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSGlueServiceRole")
    );

    // KMS

    const kmsJuvareKey = new kms.Key(this, "kmsJuvareKey", {
      alias: envName + "-juvare-key",
      enableKeyRotation: true,
    });
    kmsJuvareKey.grantEncryptDecrypt(roleLambdaProcessJuvare);

    // S3 Buckets - Juvare

    const s3LandingJuvare = new creates3bucket(this, "landing-juvare", kmsJuvareKey);
    s3LandingJuvare.bucket.grantReadWrite(roleLambdaProcessJuvare);

    // Create folder structure in Juvare Landing bucket
    new s3deploy.BucketDeployment(this, "cdph_idph", {
      sources: [s3deploy.Source.asset("./juvare_folder_structure/juvare")],
      destinationBucket: s3LandingJuvare.bucket,
      //destinationKeyPrefix: '',
    });

    const s3ProcessedJuvare = new creates3bucket(this, "processed-juvare", kmsJuvareKey);
    s3ProcessedJuvare.bucket.grantReadWrite(roleLambdaProcessJuvare);
    s3ProcessedJuvare.bucket.grantReadWrite(roleGlueService);

    // Athena Queries bucket. AES256 encrypted to allow users to use the bucket for athena queries
    const s3AthenaQueries = new s3.Bucket(this, "athena-queries", {
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: RemovalPolicy.RETAIN,
      versioned: true,
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
    s3AthenaQueries.grantReadWrite(roleGlueService);

    // S3 Buckets - HHS

    const s3LandingHHS = new creates3bucket(this, "landing-hhs", kmsJuvareKey);
    s3LandingHHS.bucket.grantReadWrite(roleLambdaProcessJuvare);

    // Create folder structure in HHS Landing bucket
    new s3deploy.BucketDeployment(this, "hhs", {
      sources: [s3deploy.Source.asset("./hhs_folder_structure")],
      destinationBucket: s3LandingHHS.bucket,
      //destinationKeyPrefix: '',
    });

    const s3ProcessedHHS = new creates3bucket(this, "processed-hhs", kmsJuvareKey);
    s3ProcessedJuvare.bucket.grantReadWrite(roleLambdaProcessJuvare);
    s3ProcessedJuvare.bucket.grantReadWrite(roleGlueService);

    // dynamodb - juvare
    const juvare_hash_table_log = new dynamodb.Table(this, "juvare_hash_table_log", {
      tableName: envName + "-juvare_hash_table_log",
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: kmsJuvareKey,
      partitionKey: { name: "md5Digest", type: dynamodb.AttributeType.STRING },
      removalPolicy: RemovalPolicy.DESTROY,
    });
    juvare_hash_table_log.grantFullAccess(roleLambdaProcessJuvare);

    const juvare_execution_log = new dynamodb.Table(this, "juvare_execution_log", {
      tableName: envName + "-juvare_execution_log",
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: kmsJuvareKey,
      partitionKey: { name: "lambdaId", type: dynamodb.AttributeType.STRING },
      removalPolicy: RemovalPolicy.DESTROY,
    });
    juvare_execution_log.grantFullAccess(roleLambdaProcessJuvare);

    // dynamodb - hhs

    const hhs_hash_table_log = new dynamodb.Table(this, "hhs_hash_table_log", {
      tableName: envName + "-hhs_hash_table_log",
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: kmsJuvareKey,
      partitionKey: { name: "md5Digest", type: dynamodb.AttributeType.STRING },
      removalPolicy: RemovalPolicy.DESTROY,
    });
    hhs_hash_table_log.grantFullAccess(roleLambdaProcessJuvare);

    const hhs_execution_log = new dynamodb.Table(this, "hhs_execution_log", {
      tableName: envName + "-hhs_execution_log",
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: kmsJuvareKey,
      partitionKey: { name: "lambdaId", type: dynamodb.AttributeType.STRING },
      removalPolicy: RemovalPolicy.DESTROY,
    });
    hhs_execution_log.grantFullAccess(roleLambdaProcessJuvare);

    //
    // SNS - Juvare
    //

    const JuvareProcessingTopic = new sns.Topic(this, "snsJuvareProcessingTopic", {
      displayName: envName + "JuvareProcessingTopic",
    });

    //
    // SNS - HHS
    //

    const HHSProcessingTopic = new sns.Topic(this, "snsHHSProcessingTopic", {
      displayName: envName + "HHSProcessingTopic",
    });

    //
    // Glue - Juvare
    //

    const glueDbJuvare = new glue.Database(this, envName + "juvare", {
      databaseName: envName + "-juvare",
    });

    const JuvareDailyCDPHIDPHCrawler = new glue.CfnCrawler(this, "JuvareDailyCDPHIDPHCrawler", {
      name: envName + "JuvareDailyCDPHIDPHCrawler",
      role: roleGlueService.roleArn,
      databaseName: glueDbJuvare.databaseName,
      schedule: { scheduleExpression: "cron(0 0 * * ? *)" },
      tablePrefix: "daily_cpdh_idph_",
      targets: {
        s3Targets: [
          {
            path: "s3://" + s3ProcessedJuvare.bucket.bucketName + "/juvare/cdph_idph/",
          },
        ],
      },
    });

    const JuvareDailyHaveBedCrawler = new glue.CfnCrawler(this, "JuvareDailyHaveBedCrawler", {
      name: envName + "JuvareDailyHaveBedCrawler",
      role: roleGlueService.roleArn,
      databaseName: glueDbJuvare.databaseName,
      tablePrefix: "daily_have_bed_",
      schedule: { scheduleExpression: "cron(0 0 * * ? *)" },
      targets: {
        s3Targets: [
          {
            path: "s3://" + s3ProcessedJuvare.bucket.bucketName + "/juvare/daily_havbed/",
          },
        ],
      },
    });

    //
    // Glue - HHS
    //

    const glueDbHHS = new glue.Database(this, envName + "hhs", {
      databaseName: envName + "-hhs",
    });

    const HHSDailyCDPHIDPHCrawler = new glue.CfnCrawler(this, "HHSCrawler", {
      name: envName + "HHSCrawler",
      role: roleGlueService.roleArn,
      databaseName: glueDbJuvare.databaseName,
      schedule: { scheduleExpression: "cron(0 0 * * ? *)" },
      tablePrefix: "hhs_",
      targets: {
        s3Targets: [
          {
            path: "s3://" + s3ProcessedHHS.bucket.bucketName,
          },
        ],
      },
    });

    // lambda layers
    const layerXlrd = new lambda.LayerVersion(this, "xlrd", {
      code: lambda.Code.fromAsset("lambda_layer/xlrd.zip"),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_8],
      layerVersionName: envName + "-xlrd",
    });

    // lambda - Juvare

    const juvare_cdph_idph_process = new createLambdaWithLayer(
      this,
      envName,
      roleLambdaProcessJuvare,
      "juvare_cdph_idph_process",
      layerXlrd,
      {
        BUCKET_PROCESSED_JUVARE: s3ProcessedJuvare.bucket.bucketName,
        BUCKET_PROCESSED_JUVARE_FOLDER: "cdph_idph",
        BUCKET_RAW_JUVARE_FOLDER: "raw_cdph_idph",
        DYNAMODB_JUVARE_EXECUTION_LOG: juvare_execution_log.tableName,
        DYNAMODB_JUVARE_HASH_TABLE_LOG: juvare_hash_table_log.tableName,
        GLUE_CRAWLER_JUVARE_CDPH_IDPH: envName + "JuvareDailyCDPHIDPHCrawler",
        SNS_TOPIC_ARN: JuvareProcessingTopic.topicArn,
      }
    );

    // todo add crawler, glue db

    const juvare_have_bed_process = new createLambdaWithLayer(
      this,
      envName,
      roleLambdaProcessJuvare,
      "juvare_have_bed_process",
      layerXlrd,
      {
        BUCKET_PROCESSED_JUVARE: s3ProcessedJuvare.bucket.bucketName,
        BUCKET_PROCESSED_JUVARE_FOLDER: "daily_havbed",
        BUCKET_RAW_JUVARE_FOLDER: "raw_daily_havbed",
        DYNAMODB_JUVARE_EXECUTION_LOG: juvare_execution_log.tableName,
        DYNAMODB_JUVARE_HASH_TABLE_LOG: juvare_hash_table_log.tableName,
        GLUE_CRAWLER_JUVARE_HAVE_BED: envName + "JuvareDailyHaveBedCrawler",
        SNS_TOPIC_ARN: JuvareProcessingTopic.topicArn,
      }
    );

    // lambda - HHS

    const hhs_bed_capacity = new createLambda(
      this,
      envName,
      roleLambdaProcessJuvare,
      "hhs_bed_capacity",
      {
        BUCKET_PROCESSED_HHS: s3ProcessedHHS.bucket.bucketName,
        DYNAMODB_HHS_EXECUTION_LOG: hhs_execution_log.tableName,
        DYNAMODB_HHS_HASH_TABLE_LOG: hhs_hash_table_log.tableName,
        GLUE_CRAWLER_HHS: envName + "HHSCrawler",
        SNS_TOPIC_ARN: HHSProcessingTopic.topicArn,
      }
    );

    // S3 Triggers/Notifications - Juvare

    s3LandingJuvare.bucket.addEventNotification(
      s3.EventType.OBJECT_CREATED,
      new s3n.LambdaDestination(juvare_cdph_idph_process.lambdaFunction),
      {
        prefix: "cdph_idph/",
      }
    );

    s3LandingJuvare.bucket.addEventNotification(
      s3.EventType.OBJECT_CREATED,
      new s3n.LambdaDestination(juvare_have_bed_process.lambdaFunction),
      {
        prefix: "daily_havbed/",
      }
    );

    // S3 Triggers/Notifications - HHS

    s3LandingHHS.bucket.addEventNotification(
      s3.EventType.OBJECT_CREATED,
      new s3n.LambdaDestination(hhs_bed_capacity.lambdaFunction)
    );

    // CFN Outputs

    new CfnOutput(this, "roleGlueServiceExport", {
      value: roleGlueService.roleArn,
      exportName: envName + "-roleGlueService",
    });
  }
}
