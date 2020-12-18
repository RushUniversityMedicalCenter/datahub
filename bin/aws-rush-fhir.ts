#!/usr/bin/env node
import 'source-map-support/register';
import {infraStack} from '../lib/infraStack';
import {App} from "@aws-cdk/core";
import {appStack} from "../lib/aws-rush-fhir-stack";
import {ecsStack} from "../lib/ecsStack";

const app = new App();
const environment = app.node.tryGetContext('ENVIRONMENT') || process.env.ENVIRONMENT


const infra = new infraStack(app, 'infraStack',{
  environment: environment,
});

new appStack(app, 'appStack',{
  environment: environment,
});

new ecsStack(app, 'ecsStack',{
  environment: environment,
  vpc: infra.vpc,
});
