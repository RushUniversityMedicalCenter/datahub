import ecs = require('@aws-cdk/aws-ecs');
import ec2 = require('@aws-cdk/aws-ec2');
import ecs_patterns = require('@aws-cdk/aws-ecs-patterns');
import elbv2 = require('@aws-cdk/aws-elasticloadbalancingv2');
import { AutoScalingGroup } from '@aws-cdk/aws-autoscaling';
import {App, Stack, StackProps, CfnParameter, Fn} from "@aws-cdk/core";
import {SubnetType} from "@aws-cdk/aws-ec2";


export interface ecsStackProps extends StackProps {
  readonly environment: string;
  readonly vpc: ec2.Vpc;
}

export class ecsStack extends Stack {
  constructor(app: App, id: string, props: ecsStackProps) {
    super(app, id, props);

    const ecsCluster = new ecs.Cluster(this, 'fhir-cluster', {
      clusterName: props.environment + '-fhir-cluster',
      vpc: props.vpc,
    })

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

  }
}
