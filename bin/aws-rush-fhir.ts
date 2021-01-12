#!/usr/bin/env node
import 'source-map-support/register';
import {infraStack} from '../lib/infra-stack';
import {App} from "@aws-cdk/core";
import {ccdStack} from "../lib/ccd-stack";
import {fhirConvStack} from "../lib/fhir-conv-stack";
import {juvareStack} from "../lib/juvare-stack";


const app = new App();
const envName = app.node.tryGetContext('envName') || process.env.envName || 'dev'
const vpcCidr = app.node.tryGetContext('vpcCidr') || process.env.vpcCidr || '10.0.0.0/16'

const InfraStack = new infraStack(app, envName+'InfraStack',{
  envName: envName,
  vpcCidr: vpcCidr,
});

const DataStack = new ccdStack (app, envName+'DataStack',{
  envName: envName,
});

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

