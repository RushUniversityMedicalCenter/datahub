import ec2 = require('@aws-cdk/aws-ec2');
import {App, CfnOutput, Stack, StackProps} from "@aws-cdk/core";
import {GatewayVpcEndpointAwsService, SubnetType} from "@aws-cdk/aws-ec2";

export interface infraStackProps extends StackProps {
  readonly environment: string;
}

export class infraStack extends Stack {
  public readonly vpc: ec2.Vpc;
  public readonly lambdaSg: ec2.SecurityGroup;

  constructor(app: App, id: string, props: infraStackProps) {
    super(app,id,props);

    this.vpc = new ec2.Vpc(this, props.environment+'-vpc',{
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

    this.vpc.addGatewayEndpoint('s3vpce', {
      service: GatewayVpcEndpointAwsService.S3
    })

    this.vpc.addGatewayEndpoint('ddbvpce', {
      service: GatewayVpcEndpointAwsService.DYNAMODB
    })

    this.lambdaSg = new ec2.SecurityGroup(this, 'lambda-sg',{
      vpc: this.vpc,
      allowAllOutbound: true,
      description: 'Lambda Private Security Group'
    })

    this.lambdaSg.addIngressRule(ec2.Peer.ipv4(this.vpc.vpcCidrBlock), ec2.Port.tcp(5432), 'Aurora Internal Ingress');

    new CfnOutput(this, 'vpcIdExport', {
      value: this.vpc.vpcId.toString(),
      exportName: 'vpcIdExport'
    });

    new CfnOutput(this, 'privateSubnetsExport', {
      value: this.vpc.selectSubnets({subnetType: SubnetType.PRIVATE}).subnetIds.toString(),
      exportName: 'privateSubnetsExport'
    });

    new CfnOutput(this, 'lambdaSGExport', {
      value: this.lambdaSg.securityGroupId.toString(),
      exportName: 'lambdaSGExport'
    });

  }
  public getVpc = () => {
    return this.vpc
  }
}
