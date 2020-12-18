import s3 = require('@aws-cdk/aws-s3');
import kms = require('@aws-cdk/aws-kms');
import iam = require('@aws-cdk/aws-iam');
import ecs = require('@aws-cdk/aws-ecs');
import ec2 = require('@aws-cdk/aws-ec2');
import {Duration, App, Stack, StackProps, CfnParameter, Fn} from "@aws-cdk/core";


export interface ecsStackProps extends StackProps {
  readonly environment: string;
}

export class ecsStack extends Stack {
  constructor(app: App, id: string, props: ecsStackProps) {
    super(app, id, props);

    // Network params imports
    const vpcID = new CfnParameter(this, 'vpcId', {
      type: 'AWS::EC2::VPC::Id',
      description: 'vpcId',
    })

    const privSubnets = new CfnParameter(this, 'privSubnets', {
      type: 'List<AWS::EC2::Subnet::Id>',
      description: 'Private Subnets'
    })


    const thisvpc = ec2.Vpc.fromVpcAttributes(this, 'vpc', {
      availabilityZones: Fn.getAzs(),
      vpcId: vpcID.valueAsString,
//      privateSubnetIds: Fn.split(',',Fn.join(',',privSubnets.valueAsList)),
    });


    const ecsCluster = new ecs.Cluster(this, 'fhir-cluster', {
      clusterName: props.environment + '-fhir-cluster',
      vpc: thisvpc,
    })

    const ecsTaskDef = new ecs.Ec2TaskDefinition(this, 'fhir', {
      networkMode: ecs.NetworkMode.AWS_VPC,
    })
    ecsTaskDef.addContainer('fhir', {
      cpu: 512,
      memoryLimitMiB: 1024,
      image: 'healthplatformregistry.azurecr.io/fhirconverter:v2.0.0'

    })
  }
}
