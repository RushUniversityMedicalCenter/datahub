import ecs = require('@aws-cdk/aws-ecs');
import ec2 = require('@aws-cdk/aws-ec2');
import alb = require('@aws-cdk/aws-elasticloadbalancingv2');
import * as route53 from '@aws-cdk/aws-route53';
import * as acm from '@aws-cdk/aws-certificatemanager';
import ecs_patterns = require('@aws-cdk/aws-ecs-patterns');
import ssm = require('@aws-cdk/aws-ssm')
import {App, CfnOutput, Fn, Stack, StackProps} from "@aws-cdk/core";


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

    const dummyRoute53Zone = new route53.PrivateHostedZone(this, 'dummyRoute53Zone', {
      zoneName: envName+'.dummydomain-'+this.account+'.com',
      vpc,
    })

    const ssm_base_path = '/'+envName+'/fhirConv/'

    // create_import_acm_cert.sh will create cert and this parameter value. If running manually run the script before running cdk deploy
    const acm_arn = ssm.StringParameter.valueForStringParameter(this, ssm_base_path+'self_signed_acm_arn')
    const fhirCertificate = acm.Certificate.fromCertificateArn(this, 'fhirCertificate', acm_arn)

    const ecsCluster = new ecs.Cluster(this, 'fhir-cluster', {
      clusterName: envName+'-fhir-cluster',
      vpc: vpc,
    })

    const fhirConvertor = new ecs_patterns.ApplicationLoadBalancedFargateService(this, "FhirConverter", {
      cluster: ecsCluster, // Required
      assignPublicIp: false,
      cpu: 1024, // Default is 256
      desiredCount: 2, // Default is 1
      taskImageOptions: {
        image: ecs.ContainerImage.fromRegistry("healthplatformregistry.azurecr.io/fhirconverter:v2.0.0"),
        containerPort: 2019,
        enableLogging: true,
      },
      memoryLimitMiB: 4096, // Default is 512
      publicLoadBalancer: false, // Default is false
      openListener: false,
      protocol: alb.ApplicationProtocol.HTTPS,
      certificate: fhirCertificate,
      domainName: 'fhirconv.'+dummyRoute53Zone.zoneName,
      domainZone: dummyRoute53Zone,
    });

    fhirConvertor.loadBalancer.addSecurityGroup(fhirConvSg)

    new ssm.StringParameter(this,'fhirConvertorUrl',{
      stringValue: 'https://'+fhirConvertor.loadBalancer.loadBalancerDnsName,
      parameterName: ssm_base_path+'fhirConvertorUrl'
    })


    new CfnOutput(this, 'fhirConvertorExport', {
      value: 'http://'+fhirConvertor.loadBalancer.loadBalancerDnsName,
      //exportName: envName+'-fhir-convertor-url'
    });

  }
}
