import ecs = require('@aws-cdk/aws-ecs');
import ec2 = require('@aws-cdk/aws-ec2');
import ecs_patterns = require('@aws-cdk/aws-ecs-patterns');
import elbv2 = require('@aws-cdk/aws-elasticloadbalancingv2');
import { AutoScalingGroup } from '@aws-cdk/aws-autoscaling';
import {App, Stack, StackProps, CfnParameter, Fn, CfnOutput} from "@aws-cdk/core";
import {SubnetType} from "@aws-cdk/aws-ec2";


export interface fhirConvStackProps extends StackProps {
  readonly envName: string;
}

export class fhirConvStack extends Stack {
  constructor(app: App, id: string, props: fhirConvStackProps) {
    super(app, id, props);

    const envName = props.envName;
    const vpcId = Fn.importValue(envName+"-vpcId");
    const availabilityZones = Fn.split(",",Fn.importValue(envName+"-azs"));
    const privateSubnetIds = Fn.split(",", Fn.importValue(envName+"-privateSubnets"));
    const fhirConvSgId = Fn.importValue(envName+"-fhirConvSg");

    const vpc = ec2.Vpc.fromVpcAttributes(this, "importedVpc", {
      vpcId: vpcId,
      availabilityZones: availabilityZones,
      privateSubnetIds: [ Fn.select(0,privateSubnetIds), Fn.select(1,privateSubnetIds)],
    });

    const fhirConvSg = ec2.SecurityGroup.fromSecurityGroupId(this, 'fhirConvSg',fhirConvSgId);


    const ecsCluster = new ecs.Cluster(this, 'fhir-cluster', {
      clusterName: envName+'-fhir-cluster',
      vpc: vpc,
    })

    const fhirConvertor = new ecs_patterns.ApplicationLoadBalancedFargateService(this, "FhirConverter", {
      cluster: ecsCluster, // Required
      assignPublicIp: false,
      cpu: 512, // Default is 256
      desiredCount: 2, // Default is 1
      taskImageOptions: {
        image: ecs.ContainerImage.fromRegistry("healthplatformregistry.azurecr.io/fhirconverter:v2.0.0"),
        containerPort: 2019,
      },
      memoryLimitMiB: 2048, // Default is 512
      publicLoadBalancer: false, // Default is false
      openListener: false
    });

    fhirConvertor.loadBalancer.addSecurityGroup(fhirConvSg)

    new CfnOutput(this, 'fhirConvertorExport', {
      value: 'http://'+fhirConvertor.loadBalancer.loadBalancerDnsName,
      exportName: envName+'-fhir-convertor-url'
    });

  }
}
