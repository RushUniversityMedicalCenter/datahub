# Rush Medical phase 2

This repo is to convert existing terraform code to cdk and add enhancements to the application

To test in your own account or in the rush poc account. 

* clone this repo
* Run 
`npm install`  
`cdk deploy` 

To make changes and validate the code

`cdk synth`

To verify the changes before deploy and compare with existing deployment

`cdk diff`

## Useful commands

 * `npm run build`   compile typescript to js
 * `npm run watch`   watch for changes and compile
 * `npm run test`    perform the jest unit tests
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk synth`       emits the synthesized CloudFormation template
