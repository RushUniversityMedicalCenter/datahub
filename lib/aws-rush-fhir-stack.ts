import s3 = require('@aws-cdk/aws-s3');
import kms = require('@aws-cdk/aws-kms');
import iam = require('@aws-cdk/aws-iam');
import {Duration, App, Stack, StackProps, CfnParameter, Fn} from "@aws-cdk/core";


export interface appStackProps extends StackProps {
  readonly environment: string;
}

export class appStack extends Stack {
  constructor(app: App, id: string, props: appStackProps) {
    super(app, id, props);



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
      roleName: "AWSGlueServiceRole"+props.environment
    })
    roleGlueService.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSGlueServiceRole'))


    // ecs role
    const roleEcsExecution = new iam.Role(this, 'roleEcsExecution',{
      assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com")
    })
    roleEcsExecution.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AmazonECSTaskExecutionRolePolicy'))


    //
    // KMS keys
    //

    const kmsLandingKey = new kms.Key(this, 'kmsLandingKey',{
      alias: props.environment+'-landing-key'
    })
    kmsLandingKey.grantEncryptDecrypt(roleProcessLambda)
    // kmsLandingKey.grantEncryptDecrypt(roleGlueService)


    const kmsProcessedKey = new kms.Key(this, 'kmsProcessedKey',{
      alias: props.environment+'-processed-key'
    })
    kmsProcessedKey.grantEncryptDecrypt(roleProcessLambda)
    kmsProcessedKey.grantEncryptDecrypt(roleGlueService)

    const kmsDatabaseKey = new kms.Key(this, 'kmsDatabaseKey',{
      alias: props.environment+'-database-key'
    })
    kmsDatabaseKey.grantEncryptDecrypt(roleProcessLambda)


    //
    // S3 buckets
    //

    // Landing Buckets - Direct, Api, SFTP
    const s3LandingDirect = new s3.Bucket(this, props.environment+'landing-direct',{
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

    const s3LandingApi = new s3.Bucket(this, props.environment+'landing-api',{
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

    const s3LandingSftp = new s3.Bucket(this, props.environment+'landing-sftp',{
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


    const s3LandingJuvare = new s3.Bucket(this, props.environment+'landing-juvare',{
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


    //
    // ECS
    //

    // const ecsCluster = new ecs.Cluster(this,'fhir-cluster',{
    //   clusterName: props.environment+'-fhir-cluster',
    //   vpc: thisvpc,
    // })
    //
    // const ecsTaskDef = new ecs.Ec2TaskDefinition(this, 'fhir',{
    //   networkMode: ecs.NetworkMode.AWS_VPC,
    // })
    // ecsTaskDef.addContainer('fhir',{
    //   cpu: 512,
    //   memoryLimitMiB: 1024,
    //   image: 'healthplatformregistry.azurecr.io/fhirconverter:v2.0.0'
    //
    // })


    //
    // Lambda functions
    //

    // const processCCDA = new lambda.Function(this,'processCCDA',{
    //   runtime: lambda.Runtime.PYTHON_3_8,
    //   code: lambda.Code.fromAsset("lambda"),
    //   handler: 'processCCDA.lambda_handler',
    //   environment: {
    //     REGION: this.region,
    //     DYNAMODB_CONVERSION_TABLE_LOG: "",
    //     BUCKET_PREPROCESSED_CCDS: "",
    //     FHIR_CONVERTER_ENDPOINT: "/api/convert/cda/",
    //     FHIR_CONVERTER_TEMPLATENAME: "ccd.hbs",
    //     FHIR_CONVERTER_URL: ""
    //   }
    // })







  }
}
