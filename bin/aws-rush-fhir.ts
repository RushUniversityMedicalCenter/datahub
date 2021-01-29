/**
 File: aws-rush-fhir.ts
 Project: aws-rush-fhir
 File Created: Wednesday, 6th January 2021 2:12:57 pm
 Author: Pandre, Lakshmikanth (pandrel@amazon.com)
 -----
 Last Modified: Friday, 29th January 2021 2:10:06 pm
 Modified By: Pandre, Lakshmikanth (pandrel@amazon.com)
 -----
 © 2020 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.

 This AWS Content is provided subject to the terms of the AWS Customer Agreement
 available at http://aws.amazon.com/agreement or other written agreement between
 Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
 **/


//#!/usr/bin/env node
import 'source-map-support/register';
import {infraStack} from '../lib/infra-stack';
import {App} from "@aws-cdk/core";
import {fhirStack} from "../lib/fhir-stack";
import {fhirConvStack} from "../lib/fhir-conv-stack";
import {bedcapStack} from "../lib/bedcap-stack";


const app = new App();
const envName = app.node.tryGetContext('envName') || process.env.envName || 'dev'
const vpcCidr = app.node.tryGetContext('vpcCidr') || process.env.vpcCidr || '10.0.0.0/16'
const healthLakeEndpoint = app.node.tryGetContext('vpcCidr') || process.env.healthLakeEndpoint || 'UNDEFINED'

const InfraStack = new infraStack(app, envName+'Infra',{
  envName: envName,
  vpcCidr: vpcCidr,
});

const FhirConv =  new fhirConvStack(app, envName+'FhirConv',{
  envName: envName,
});
FhirConv.addDependency(InfraStack,'DeployAfterInfra');

const FhirStack = new fhirStack(app, envName+'Fhir',{
  envName: envName,
  healthLakeEndpoint: healthLakeEndpoint,
});
FhirStack.addDependency(InfraStack,'DeployAfterInfra')
FhirStack.addDependency(FhirConv,'DeployAfterFhirConv')  // fhir stack needs fhir conv url

const BedCapStack =  new bedcapStack(app, envName+'BedCap',{
  envName: envName,
});

