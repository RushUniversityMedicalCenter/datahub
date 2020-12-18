import ec2 = require('@aws-cdk/aws-ec2');
import {App, CfnOutput, Stack, StackProps} from "@aws-cdk/core";
import {GatewayVpcEndpointAwsService, SubnetType} from "@aws-cdk/aws-ec2";

export interface infraStackProps extends StackProps {
  readonly environment: string;
}

export class infraStack extends Stack {
  constructor(app: App, id: string, props: infraStackProps) {
    super(app,id,props);

    const vpc = new ec2.Vpc(this, props.environment+'-vpc',{
      cidr: '10.1.0.0/21',
      maxAzs: 2,
      subnetConfiguration: [
        {
          subnetType: ec2.SubnetType.PUBLIC,
          name: 'pub-app-',
          cidrMask: 24,
        },
        {
          subnetType: ec2.SubnetType.PRIVATE,
          name: 'priv-app-',
          cidrMask: 24,
        },
        {
          subnetType: ec2.SubnetType.ISOLATED,
          name: 'priv-db-',
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

    const lambdaSg = new ec2.SecurityGroup(this, 'lambda-sg',{
      vpc: vpc,
      allowAllOutbound: true,
      description: 'Lambda Private Security Group'
    })

    lambdaSg.addIngressRule(ec2.Peer.ipv4(vpc.vpcCidrBlock), ec2.Port.tcp(5432), 'Aurora Internal Ingress');

    new CfnOutput(this, 'vpcIdExport', {
      value: vpc.vpcId.toString(),
      exportName: 'vpcIdExport'
    });

    new CfnOutput(this, 'privateSubnetsExport', {
      value: vpc.selectSubnets({subnetType: SubnetType.PRIVATE}).subnetIds.toString(),
      exportName: 'privateSubnetsExport'
    });

    new CfnOutput(this, 'lambdaSGExport', {
      value: lambdaSg.securityGroupId.toString(),
      exportName: 'lambdaSGExport'
    });

  }
}
