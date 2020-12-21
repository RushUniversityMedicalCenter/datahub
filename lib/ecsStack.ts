import ecs = require('@aws-cdk/aws-ecs');
import ec2 = require('@aws-cdk/aws-ec2');
import ecs_patterns = require('@aws-cdk/aws-ecs-patterns');
import elbv2 = require('@aws-cdk/aws-elasticloadbalancingv2');
import { AutoScalingGroup } from '@aws-cdk/aws-autoscaling';
import {App, Stack, StackProps, CfnParameter, Fn, CfnOutput} from "@aws-cdk/core";
import {SubnetType} from "@aws-cdk/aws-ec2";


export interface ecsStackProps extends StackProps {
  readonly envName: string;
}

export class ecsStack extends Stack {
  constructor(app: App, id: string, props: ecsStackProps) {
    super(app, id, props);

    const envName = props.envName;
    const vpcId = Fn.importValue(envName+"-vpcId");
    const availabilityZones = Fn.split(",",Fn.importValue(envName+"-azs"));
    const privateSubnetIds = Fn.split(",", Fn.importValue(envName+"-privateSubnets"));
    //
    // const availabilityZones = Fn.importValue(envName+"-azs").split("," );
    // const privateSubnetIds = Fn.importValue(envName+"-privateSubnets").split(",");

    // const azs = Fn.importValue(envName+"-azs").split("," );
    // const privSubs = Fn.importValue(envName+"-privateSubnets").split(",");


    // const availabilityZones = ('us-east-1a,us-east-1b').split("," );
    // const privateSubnetIds = ('subnet-0cc9e25f9d4bb31de,subnet-08a6e5e6c5de38d37').split(",")

    console.log(vpcId);
    console.log(availabilityZones)
    console.log(privateSubnetIds)

    const vpc = ec2.Vpc.fromVpcAttributes(this, "importedVpc", {
      // vpcId: 'vpc-035c861aaefdaab86',
      // availabilityZones: ['us-east-1a','us-east-1b'],
      // privateSubnetIds: ['subnet-0cc9e25f9d4bb31de','subnet-08a6e5e6c5de38d37'],
      vpcId: vpcId,
      availabilityZones: availabilityZones,
      privateSubnetIds: [ Fn.select(0,privateSubnetIds), Fn.select(1,privateSubnetIds)],
    });


    const ecsCluster = new ecs.Cluster(this, 'fhir-cluster', {
      clusterName: envName+'-fhir-cluster',
      vpc: vpc,
    })

    new ecs_patterns.ApplicationLoadBalancedFargateService(this, "FhirConverter", {
      cluster: ecsCluster, // Required
      assignPublicIp: false,
      cpu: 512, // Default is 256
      desiredCount: 2, // Default is 1
      taskImageOptions: {
        image: ecs.ContainerImage.fromRegistry("healthplatformregistry.azurecr.io/fhirconverter:v2.0.0"),
        containerPort: 2019,
      },
      memoryLimitMiB: 2048, // Default is 512
      publicLoadBalancer: false // Default is false
    });

  }
}

// availabilityZones: Fn.split(',',Fn.importValue(envName+'-azs')),
//   privateSubnetIds: Fn.split(',',Fn.importValue(envName+'-privateSubnets')),

// const ecsTaskDef = new ecs.Ec2TaskDefinition(this, 'fhir', {
//   networkMode: ecs.NetworkMode.AWS_VPC,
// })
// const ecsContainer = ecsTaskDef.addContainer('fhir', {
//   cpu: 512,
//   memoryLimitMiB: 1024,
//   // using image: 'healthplatformregistry.azurecr.io/fhirconverter:v2.0.0'
//   image: ecs.ContainerImage.fromRegistry('healthplatformregistry.azurecr.io/fhirconverter:v2.0.0'),
//   hostname: 'fhirconverter',
// })
// ecsContainer.addPortMappings({
//   containerPort: 2019,
//   hostPort: 2019,
//   protocol: ecs.Protocol.TCP
// })
//
// const ecsService = new ecs.Ec2Service(this, 'fhir',{
//   cluster: ecsCluster,
//   taskDefinition: ecsTaskDef,
//   desiredCount: 2,
// })
//
// // ALB
//
// const alb = new elbv2.ApplicationLoadBalancer(this, 'fhirconverter'{
//   thisVpc,
//   internetfa
// })

// Create a load-balanced Fargate service and make it private
// new ecs_patterns.ApplicationLoadBalancedFargateService(this, "MyFargateService", {
//   cluster: ecsCluster, // Required
//   assignPublicIp: false,
//   cpu: 512, // Default is 256
//   desiredCount: 2, // Default is 1
//   taskImageOptions: { image: ecs.ContainerImage.fromRegistry("healthplatformregistry.azurecr.io/fhirconverter:v2.0.0") },
//   memoryLimitMiB: 2048, // Default is 512
//   publicLoadBalancer: false // Default is false
// });
