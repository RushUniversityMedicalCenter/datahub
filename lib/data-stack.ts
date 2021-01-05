import s3 = require('@aws-cdk/aws-s3');
import s3n = require('@aws-cdk/aws-s3-notifications')
import kms = require('@aws-cdk/aws-kms');
import iam = require('@aws-cdk/aws-iam');
import ec2 = require('@aws-cdk/aws-ec2');
import dynamodb = require('@aws-cdk/aws-dynamodb');
import sqs = require('@aws-cdk/aws-sqs');
import sns = require('@aws-cdk/aws-sns');
import lambda = require('@aws-cdk/aws-lambda');
import sfn = require('@aws-cdk/aws-stepfunctions');
import tasks = require('@aws-cdk/aws-stepfunctions-tasks')
import {App, CfnOutput, Duration, Fn, Stack, StackProps} from "@aws-cdk/core";
import {createLambda, creates3bucket} from "./helpers";
import {SubnetType} from "@aws-cdk/aws-ec2";
import {InvokeFunction} from "@aws-cdk/aws-stepfunctions-tasks";
import {ifError} from "assert";


export interface dataStackProps extends StackProps {
  readonly envName: string;
}

export class dataStack extends Stack {
  constructor(app: App, id: string, props: dataStackProps) {
    super(app, id, props);

    const envName = props.envName
    // VPC imports
    const privateSubnetIds = Fn.split(",", Fn.importValue(envName+"-privateSubnets"));
    const fhirConvSgId = Fn.importValue(envName+"-fhirConvSg");

    const vpc = ec2.Vpc.fromVpcAttributes(this, "importedVpc", {
      vpcId: Fn.importValue(envName+"-vpcId"),
      availabilityZones: Fn.split(",",Fn.importValue(envName+"-azs")),
      privateSubnetIds: [ Fn.select(0,privateSubnetIds), Fn.select(1,privateSubnetIds)],
    });

    //
    // IAM roles
    //

    // IAM role for processCCDA, .. add more tbd

    const roleLambdaProcessCCD = new iam.Role(this, 'roleLambdaProcessCCD',{
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com")
    });
    roleLambdaProcessCCD.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaVPCAccessExecutionRole'))
    roleLambdaProcessCCD.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaRole'))
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
    const ccds_hash_table_log = new dynamodb.Table(this, 'ccds_hash_table_log', {
      tableName: envName+'-ccds_hash_table_log',
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: kmsDatabaseKey,
      partitionKey: {name: 'id', type: dynamodb.AttributeType.STRING},
    })
    ccds_hash_table_log.grantFullAccess(roleLambdaProcessCCD)

    const ccds_sqs_messages_log = new dynamodb.Table(this, 'ccds_sqs_messages_log', {
      tableName: envName+'-ccds_sqs_messages_log',
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: kmsDatabaseKey,
      partitionKey: {name: 'id', type: dynamodb.AttributeType.STRING},
    })
    ccds_sqs_messages_log.grantFullAccess(roleLambdaProcessCCD)

    const ccd_fhir_conversion_log = new dynamodb.Table(this, 'ddb', {
      tableName: envName+'-ccd_fhir_conversion_log',
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: kmsDatabaseKey,
      partitionKey: {name: 'id', type: dynamodb.AttributeType.STRING},
    })
    ccd_fhir_conversion_log.grantFullAccess(roleLambdaProcessCCD)

    const ccds_sfn_exceptions_log = new dynamodb.Table(this, 'ccds_sfn_exceptions_log', {
      tableName: envName+'-ccds_sfn_exceptions_log',
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: kmsDatabaseKey,
      partitionKey: {name: 'id', type: dynamodb.AttributeType.STRING},
    })
    ccds_sfn_exceptions_log.grantFullAccess(roleLambdaProcessCCD)

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

    //
    // SNS
    //

    const snsCCDConversionStatusTopic = new sns.Topic(this, 'snsCCDConversionStatusTopic', {
      displayName: envName+'CCDConversionStatusTopic'
    })


    // S3 Triggers/Notifications

    s3LandingDirect.bucket.addEventNotification(s3.EventType.OBJECT_CREATED, new s3n.SqsDestination(ccdQueue))
    s3LandingApi.bucket.addEventNotification(s3.EventType.OBJECT_CREATED, new s3n.SqsDestination(ccdQueue))
    s3LandingSftp.bucket.addEventNotification(s3.EventType.OBJECT_CREATED, new s3n.SqsDestination(ccdQueue))
    s3LandingJuvare.bucket.addEventNotification(s3.EventType.OBJECT_CREATED, new s3n.SqsDestination(ccdQueue))




    //
    // app stack elements
    //
    //

    const ccda_step0_start_state_machine = new createLambda(this, envName, roleLambdaProcessCCD, 'ccda_step0_start_state_machine',
      {
        CCDS_SQSMESSAGE_TABLE_LOG: ccds_sqs_messages_log.tableName,
        SFN_ARN: ccdQueue.queueArn,
      });

    const ccda_step1_new_files = new createLambda(this, envName, roleLambdaProcessCCD, 'ccda_step1_new_files',
      {
        BUCKET_PROCESSED_CCDS: s3Processed.bucket.bucketName,
        CCDS_SQSMESSAGE_TABLE_LOG: ccds_sqs_messages_log.tableName,
        FOLDER_PROCESSED_CCDS: 'converted',
      });

    const ccda_step1a_batch_processing = new createLambda(this, envName, roleLambdaProcessCCD, 'ccda_step1a_batch_processing',
      {}
      );

    const ccda_step2_validation = new createLambda(this, envName, roleLambdaProcessCCD, 'ccda_step2_validation',
      {}
      );

    const ccda_step3_deduplication = new createLambda(this, envName, roleLambdaProcessCCD, 'ccda_step3_deduplication',
      {
        CCDS_HASH_TABLE_LOG: ccds_hash_table_log.tableName,
      });

    const ccda_step4_converter = new lambda.Function(this, 'ccda_step4_converter', {
      functionName: envName + '-' + 'ccda_step4_converter',
      runtime: lambda.Runtime.PYTHON_3_8,
      handler: 'ccda_step4_converter/lambda_function.lambda_handler',
      code: lambda.Code.fromAsset('lambda/'),
      role: roleLambdaProcessCCD,
      environment: {
        BUCKET_PROCESSED_CCDS: s3Processed.bucket.bucketName,
        CCDS_SQSMESSAGE_TABLE_LOG: ccds_sqs_messages_log.tableName,
        FHIR_CONVERTER_ENDPOINT: '/api/convert/cda/',
        FHIR_CONVERTER_TEMPLATENAME: 'ccd.hbs',
        FHIR_CONVERTER_URL: 'http://34.205.75.147',
        FOLDER_PROCESSED_CCDS: 'converted',
        },
      vpc: vpc,
      vpcSubnets: {subnetType: SubnetType.PRIVATE},
      securityGroups: [ec2.SecurityGroup.fromSecurityGroupId(this,'fhir-sg',fhirConvSgId)],
      }


    );
    // todo parameterize fhir convertor url

    const ccda_step5_dataset_builder = new createLambda(this, envName, roleLambdaProcessCCD, 'ccda_step5_dataset_builder',
      {
        BUCKET_PROCESSED_FHIR_DATASETS: s3Processed.bucket.bucketName,
        CCDS_SQSMESSAGE_TABLE_LOG: ccds_sqs_messages_log.tableName,
        FOLDER_PROCESSED_FHIRS_DATASETS: 'fhir_datasets'
      });

    const ccda_step6_fhir_resource_split = new createLambda(this, envName, roleLambdaProcessCCD, 'ccda_step6_fhir_resource_split',
      {
        BUCKET_PROCESSED_FHIR_RESOURCES: s3Processed.bucket.bucketName,
        CCDS_SQSMESSAGE_TABLE_LOG: ccds_sqs_messages_log.tableName,
        FOLDER_PROCESSED_FHIR_RESOURCES: 'fhir_resources',
        HEALTHLAKE_ENDPOINT:'https://healthlake.us-east-1.amazonaws.com/datastore/c93bb7da51d252aac7f77e831d5ca29f/r4/',
      });

    // todo parameterize healthlake endpoint.

    const ccda_exception_handler = new createLambda(this, envName, roleLambdaProcessCCD, 'ccda_exception_handler',
      {
        CCDS_HASH_TABLE_LOG: ccds_hash_table_log.tableName,
        CCDS_SFN_EXCEPTIONS_LOG: ccds_sfn_exceptions_log.tableName,
    })

    const ccda_finish_stepfunction = new createLambda(this, envName, roleLambdaProcessCCD, 'ccda_finish_stepfunction',
      {}
    );

    // step function

    // // Tasks

    const ExceptionHandler = new tasks.LambdaInvoke(this, 'ExceptionHandler',{
      lambdaFunction: ccda_exception_handler.lambdaFunction
    })
    const NotifyFailure = new tasks.SnsPublish(this, 'NotifyFailure',{
        topic: snsCCDConversionStatusTopic,
        message: sfn.TaskInput.fromJsonPathAt('$')
      })
    const Fail = new sfn.Fail(this,'Fail')

    const exceptionHandler = sfn.Chain
      .start(ExceptionHandler)
      .next(NotifyFailure)
      .next(Fail)

    const ValidateFile = new tasks.LambdaInvoke(this, 'ValidateFile',{
      lambdaFunction: ccda_step2_validation.lambdaFunction
    }).addCatch(exceptionHandler)

    const Deduplication = new tasks.LambdaInvoke(this, 'Deduplication',{
      lambdaFunction: ccda_step3_deduplication.lambdaFunction
    }).addCatch(exceptionHandler)

    const ConvertToFHIR = new tasks.LambdaInvoke(this, 'ConvertToFHIR',{
      lambdaFunction: ccda_step4_converter
    }).addCatch(exceptionHandler)

    const BuildFHIRDatasets = new tasks.LambdaInvoke(this, 'BuildFHIRDatasets',{
      lambdaFunction: ccda_step5_dataset_builder.lambdaFunction
    }).addCatch(exceptionHandler)

    const WaitTryAgain = new sfn.Wait(this, 'WaitTryAgain',{
      time: sfn.WaitTime.duration(Duration.seconds(10))
    })
    const SaveFHIRResources = new tasks.LambdaInvoke(this, 'SaveFHIRResources',{
      lambdaFunction: ccda_step6_fhir_resource_split.lambdaFunction
    })
      .addCatch(WaitTryAgain,{
        resultPath: '$.error',
        errors:['HealthLakePostTooManyRequestsError']
      })
      .addRetry({
        maxAttempts: 5,
        errors: ['HealthLakePostTooManyRequestsError']
      })
      .addCatch(exceptionHandler)



    const ProcessSQSMessage = new tasks.LambdaInvoke(this, 'ProcessSQSMessage', {
      lambdaFunction: ccda_step1_new_files.lambdaFunction,
      outputPath: '$.Payload',
    })





    const validateMapChain = sfn.Chain
      .start(ValidateFile)
      .next(Deduplication)
      .next(ConvertToFHIR)
      .next(BuildFHIRDatasets)
      .next(SaveFHIRResources)
      .next(new sfn.Pass(this,'Complete'))

    const validateMap = new sfn.Map(this,'ValidateAll',{
      itemsPath: '$.Records',
      maxConcurrency: 0,
    })
    validateMap.iterator(validateMapChain)


    const definition = sfn.Chain
      .start(ProcessSQSMessage)
      .next(validateMap)
      .next(new tasks.LambdaInvoke(this, 'FinalizeProcess',{
        lambdaFunction: ccda_finish_stepfunction.lambdaFunction,
      }))

    const stateMachine = new sfn.StateMachine(this, envName+'CCDAtoFHIRStateMachine',{
      definition,
    })
    snsCCDConversionStatusTopic.grantPublish(stateMachine.role)




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
