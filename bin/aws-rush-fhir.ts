#!/usr/bin/env node
import 'source-map-support/register';
import {infraStack} from '../lib/infra-stack';
import {App} from "@aws-cdk/core";
import {fhirStack} from "../lib/fhir-stack";
import {fhirConvStack} from "../lib/fhir-conv-stack";
import {juvareStack} from "../lib/juvare-stack";


const app = new App();
const envName = app.node.tryGetContext('envName') || process.env.envName || 'dev'
const vpcCidr = app.node.tryGetContext('vpcCidr') || process.env.vpcCidr || '10.0.0.0/16'
const healthLakeEndpoint = app.node.tryGetContext('vpcCidr') || process.env.healthLakeEndpoint || 'UNDEFINED'

const InfraStack = new infraStack(app, envName+'Infra',{
  envName: envName,
  vpcCidr: vpcCidr,
});

const FhirStack = new fhirStack(app, envName+'Fhir',{
  envName: envName,
  healthLakeEndpoint: healthLakeEndpoint,
});
FhirStack.addDependency(InfraStack,'DeployAfterInfra')

const FhirConv =  new fhirConvStack(app, envName+'FhirConv',{
  envName: envName,
});
FhirConv.addDependency(InfraStack,'DeployAfterInfra');

const JuvareStack =  new juvareStack(app, envName+'Juvare',{
  envName: envName,
});

// const AppStack = new appStack(app, envName+'AppStack',{
//   envName: envName,
// });
// AppStack.addDependency(InfraStack,'DeployAfterInfra')
// AppStack.addDependency(DataStack,'DeployAfterDataStack')
// AppStack.addDependency(FhirConv,'DeployAfterFhirConv')

