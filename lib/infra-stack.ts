/*
 * File: infra-stack.ts
 * Project: aws-rush-fhir
 * File Created: Monday, 18th January 2021 5:02:20 pm
 * Author: Lakshmikanth Pandre (pandrel@amazon.com)
 * -----
 * Last Modified: Friday, 29th January 2021 9:03:16 am
 * Modified By: Canivel, Danilo (dccanive@amazon.com>)
 * -----
 * (c) 2020 - 2021 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
 * This AWS Content is provided subject to the terms of the AWS Customer Agreement available at
 * http://aws.amazon.com/agreement or other written agreement between Customer and either
 * Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
 */

import ec2 = require("@aws-cdk/aws-ec2");
import { App, CfnOutput, Stack, StackProps } from "@aws-cdk/core";
import { GatewayVpcEndpointAwsService, SubnetType } from "@aws-cdk/aws-ec2";

export interface infraStackProps extends StackProps {
  readonly envName: string;
  readonly vpcCidr: string;
}

export class infraStack extends Stack {
  constructor(app: App, id: string, props: infraStackProps) {
    super(app, id, props);

    const envName = props.envName;
    const vpcCidr = props.vpcCidr;

    const vpc = new ec2.Vpc(this, envName + "-vpc", {
      cidr: vpcCidr,
      maxAzs: 2,
      enableDnsHostnames: true,
      enableDnsSupport: true,
      subnetConfiguration: [
        {
          subnetType: ec2.SubnetType.PUBLIC,
          name: "public-",
          cidrMask: 24,
        },
        {
          subnetType: ec2.SubnetType.PRIVATE,
          name: "private-",
          cidrMask: 24,
        },
      ],
    });

    vpc.addGatewayEndpoint("s3vpce", {
      service: GatewayVpcEndpointAwsService.S3,
    });

    vpc.addGatewayEndpoint("ddbvpce", {
      service: GatewayVpcEndpointAwsService.DYNAMODB,
    });

    const fhirConvSg = new ec2.SecurityGroup(this, "fhir-sg", {
      vpc: vpc,
      allowAllOutbound: true,
      description: "Lambda Private Security Group",
    });

    fhirConvSg.addIngressRule(
      ec2.Peer.ipv4(vpc.vpcCidrBlock),
      ec2.Port.tcp(80),
      "Access to Fhir Convertor via ALB"
    );

    new CfnOutput(this, "vpcId", {
      value: vpc.vpcId.toString(),
      exportName: envName + "-vpcId",
    });

    new CfnOutput(this, "privateSubnets", {
      value: vpc.selectSubnets({ subnetType: SubnetType.PRIVATE }).subnetIds.toString(),
      exportName: envName + "-privateSubnets",
    });

    new CfnOutput(this, "fhirConvSg", {
      value: fhirConvSg.securityGroupId.toString(),
      exportName: envName + "-fhirConvSg",
    });

    new CfnOutput(this, "azs", {
      value: vpc.availabilityZones.toString(),
      exportName: envName + "-azs",
    });
  }
}
