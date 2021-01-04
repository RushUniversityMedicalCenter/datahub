// import s3 = require('@aws-cdk/aws-s3');
// import ec2 = require('@aws-cdk/aws-ec2');
// import iam = require('@aws-cdk/aws-iam');
// import lambda = require('@aws-cdk/aws-lambda');
// import sqs = require('@aws-cdk/aws-sqs');
// import {Duration, App, Stack, StackProps, CfnParameter, Fn} from "@aws-cdk/core";
// import {SubnetType} from "@aws-cdk/aws-ec2";
// import {createLambda} from "./helpers";
//
//
// export interface appStackProps extends StackProps {
//   readonly envName: string;
// }
//
// export class appStack extends Stack {
//   constructor(app: App, id: string, props: appStackProps) {
//     super(app, id, props);
//
//     const envName = props.envName
//
//     // IAM imports
//     const roleProcessLambda = iam.Role.fromRoleArn(this, 'roleProcessLambda', Fn.importValue(envName+'-roleProcessLambda'));
//     const roleGlueService = iam.Role.fromRoleArn(this, 'roleGlueService', Fn.importValue(envName+'-roleGlueService'));
//
//     // VPC imports
//     const privateSubnetIds = Fn.split(",", Fn.importValue(envName+"-privateSubnets"));
//     const fhirConvSgId = Fn.importValue(envName+"-fhirConvSg");
//
//     const vpc = ec2.Vpc.fromVpcAttributes(this, "importedVpc", {
//       vpcId: Fn.importValue(envName+"-vpcId"),
//       availabilityZones: Fn.split(",",Fn.importValue(envName+"-azs")),
//       privateSubnetIds: [ Fn.select(0,privateSubnetIds), Fn.select(1,privateSubnetIds)],
//     });
//
//     // Start state machine / Step function trigger
//
//     const ccda_step0_start_state_machine = new createLambda(this, envName, roleProcessLambda, 'ccda_step0_start_state_machine',
//       {
//         CCDS_SQSMESSAGE_TABLE_LOG: 'ccds_sqs_messages_log',
//         SFN_ARN: 'SQS Arn',
//             });
//
//     const ccda_step1_new_files = new createLambda(this, envName, roleProcessLambda, 'ccda_step1_new_files',
//       {
//         BUCKET_PROCESSED_CCDS: 'ccds_sqs_messages_log',
//         CCDS_SQSMESSAGE_TABLE_LOG: 'ccds_sqs_messages_log',
//         FOLDER_PROCESSED_CCDS: 'converted',
//       });
//
//     const ccda_step1a_batch_processing = new createLambda(this, envName, roleProcessLambda, 'ccda_step1a_batch_processing',
//       {
//         CCDS_SQSMESSAGE_TABLE_LOG: 'ccds_sqs_messages_log',
//         SFN_ARN: 'SQS Arn',
//       });
//
//     const ccda_step2_validation = new createLambda(this, envName, roleProcessLambda, 'ccda_step2_validation',
//       {
//         CCDS_SQSMESSAGE_TABLE_LOG:'ccds_sqs_messages_log',
//         SFN_ARN: 'SQS Arn',
//       });
//
//     const ccda_step3_deduplication = new createLambda(this, envName, roleProcessLambda, 'ccda_step3_deduplication',
//       {
//         CCDS_SQSMESSAGE_TABLE_LOG:'ccds_sqs_messages_log',
//         SFN_ARN: 'SQS Arn',
//       });
//
//     const ccda_step4_converter = new createLambda(this, envName, roleProcessLambda, 'ccda_step4_converter',
//       {
//         CCDS_SQSMESSAGE_TABLE_LOG:'ccds_sqs_messages_log',
//         SFN_ARN: 'SQS Arn',
//       });
//
//     const ccda_step5_dataset_builder = new createLambda(this, envName, roleProcessLambda, 'ccda_step5_dataset_builder',
//       {
//         CCDS_SQSMESSAGE_TABLE_LOG:'ccds_sqs_messages_log',
//         SFN_ARN: 'SQS Arn',
//       });
//
//     const ccda_step6_fhir_resource_split = new createLambda(this, envName, roleProcessLambda, 'ccda_step6_fhir_resource_split',
//       {
//         CCDS_SQSMESSAGE_TABLE_LOG:'ccds_sqs_messages_log',
//         SFN_ARN: 'SQS Arn',
//       });
//
//
//   }
// }
