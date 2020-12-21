#!/usr/bin/env node
import 'source-map-support/register';
import {infraStack} from '../lib/infra-stack';
import {App} from "@aws-cdk/core";
import {securityStack} from "../lib/security-stack";
import {fhirConvStack} from "../lib/fhir-conv-stack";


const app = new App();
const envName = app.node.tryGetContext('envName') || process.env.envName || 'dev'
const vpcCidr = app.node.tryGetContext('vpcCidr') || process.env.vpcCidr || '10.0.0.0/16'

new infraStack(app, envName+'Infra',{
  envName: envName,
  vpcCidr: vpcCidr,
});

new securityStack (app, envName+'SecurityStack',{
  envName: envName,
});

new fhirConvStack(app, envName+'FhirConv',{
  envName: envName,
});
