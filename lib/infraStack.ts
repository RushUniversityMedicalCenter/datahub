import ec2 = require('@aws-cdk/aws-ec2');
import {App, CfnOutput, Stack, StackProps} from "@aws-cdk/core";
import {GatewayVpcEndpointAwsService, SubnetType} from "@aws-cdk/aws-ec2";

export interface infraStackProps extends StackProps {
  readonly envName: string;
  readonly vpcCidr: string;
}

export class infraStack extends Stack {
  constructor(app: App, id: string, props: infraStackProps) {
    super(app,id,props);

    const envName = props.envName;
    const vpcCidr = props.vpcCidr;

    const vpc = new ec2.Vpc(this, envName+'-vpc',{
      cidr: vpcCidr,
      maxAzs: 2,
      enableDnsHostnames: true,
      enableDnsSupport: true,
      subnetConfiguration: [
        {
          subnetType: ec2.SubnetType.PUBLIC,
          name: 'public-',
          cidrMask: 24,
        },
        {
          subnetType: ec2.SubnetType.PRIVATE,
          name: 'private-',
          cidrMask: 24,
        },
      ],
    });

    vpc.addGatewayEndpoint('s3vpce', {
      service: GatewayVpcEndpointAwsService.S3
    })

    vpc.addGatewayEndpoint('ddbvpce', {
      service: GatewayVpcEndpointAwsService.DYNAMODB
    })

    const ecsSG = new ec2.SecurityGroup(this, 'ecs-sg',{
      vpc: vpc,
      allowAllOutbound: true,
      description: 'Lambda Private Security Group'
    })

    ecsSG.addIngressRule(ec2.Peer.ipv4(vpc.vpcCidrBlock), ec2.Port.tcp(2019), 'Fhir Convertor ECS sg');

    new CfnOutput(this, 'vpcIdExport', {
      value: vpc.vpcId.toString(),
      exportName: envName+'-vpcId'
    });

    new CfnOutput(this, 'privateSubnetsExport', {
      value: vpc.selectSubnets({subnetType: SubnetType.PRIVATE}).subnetIds.toString(),
      exportName: envName+'-privateSubnets'
    });

    new CfnOutput(this, 'ecsSGExport', {
      value: ecsSG.securityGroupId.toString(),
      exportName: envName+'-ecsSG'
    });

    new CfnOutput(this, 'azs',{
      value: vpc.availabilityZones.toString(),
      exportName: envName+'-azs'
    })

  }
}
