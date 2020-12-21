#!/usr/bin/env node
import 'source-map-support/register';
import {infraStack} from '../lib/infraStack';
import {App} from "@aws-cdk/core";
import {appStack} from "../lib/aws-rush-fhir-stack";
import {ecsStack} from "../lib/ecsStack";

const app = new App();
const envName = app.node.tryGetContext('envName') || process.env.envName || 'dev'
const vpcCidr = app.node.tryGetContext('vpcCidr') || process.env.vpcCidr || '10.0.0.0/16'

new infraStack(app, 'infraStack',{
  envName: envName,
  vpcCidr: vpcCidr,
});

// new appStack(app, 'appStack',{
//   envName: envName,
// });
//
new ecsStack(app, 'ecsStack',{
  envName: envName,
});
