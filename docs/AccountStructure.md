# Rush AWS Account Structure

AWS Accounts in RUSH environment are managed via Control Tower. Below is the current Account structure deployed by AWS ProServe Team

AWS Control Tower creates an abstraction or orchestration layer that combines and integrates the capabilities of several other AWS services, including AWS Organizations, AWS Single Sign-on, and AWS Service Catalog. AWS Control Tower provides the easiest way to set up and govern a secure, compliant, multi-account AWS environment based on best practices established by working with thousands of enterprises.

**Features**

AWS Control Tower has the following features:

**Landing zone** – A landing zone is a well-architected, multi-account AWS environment that's based on security and compliance best practices. It is the enterprise-wide container that holds all of your organizational units (OUs), accounts, users, and other resources that you want to be subject to compliance regulation. A landing zone can scale to fit the needs of an enterprise of any size.

**Guardrails** – A guardrail is a high-level rule that provides ongoing governance for your overall AWS environment. It's expressed in plain language. Two kinds of guardrails exist: preventive and detective. Three categories of guidance apply to the two kinds of guardrails: mandatory, strongly recommended, or elective. For more information about guardrails, see How Guardrails Work.

**Account Factory** – An Account Factory is a configurable account template that helps to standardize the provisioning of new accounts with pre-approved account configurations. AWS Control Tower offers a built-in Account Factory that helps automate the account provisioning workflow in your organization. For more information, see Provision and manage accounts with Account Factory.

**Dashboard** – The dashboard offers continuous oversight of your landing zone to your team of central cloud administrators. Use the dashboard to see provisioned accounts across your enterprise, guardrails enabled for policy enforcement, guardrails enabled for continuous detection of policy non-conformance, and noncompliant resources organized by accounts and OUs.

![AccountStructure](../images/RushAccountStructure.png)


## Account Descriptions

**AWS SSO Login Page to access all accounts:** https://rushedu.awsapps.com/start#/


| AccountID | Account Email | AccountAlias  | Purpose  |
|---|---|---|---|
| 199592724270 | anil_j_saldanha@rush.edu  | RushAWS  | Control Tower Master: Central Account to manage AWS Organizations, AWS SSO - Users, IDP integrations, PermissionSets, Account Factory - create new accounts, Manage Guardrails  |
| 744154405456 | aws-rush-log@rush.edu | Log Archive | Log archive account – This account is for your team of users that need access to all the logging information for all of your managed accounts within managed OUs in your landing zone.  |
| 027869397375 | aws-rush-audit@rush.edu | Audit  | Audit account – This account is for your team of users that need access to the audit information made available by AWS Control Tower. You can also use this account as the access point for third-party tools that will perform programmatic auditing of your environment to help you audit for compliance purposes  |
| 074115082420 | aws-rush-tools@rush.edu | ToolsAccount  | Central account used to deploy the FHIR, Juvare stacks into target account via CodeBuild. This account can be used by Rush to further deploy any DevOps Tools in the future  |
| 095405523388 | aws-rush-dev01@rush.edu | Dev01  | Dev account - to deploy Development instances of Healthlake, Fhir stack and Juvare stack  |
| 473322558963 | aws-rush-stage01@rush.edu | Stage01 | Stage account - to deploy Stage instances of Healthlake, Fhir stack and Juvare stack  |
| TBD | aws-rush-prod01@rush.edu | Prod01 | Production account - to deploy Production instances of Healthlake, Fhir stack and Juvare stack  |




Refer following documentation to understand more about Control Tower and its Administration
https://docs.aws.amazon.com/controltower/latest/userguide/what-is-control-tower.html

As part of this engagement ProServe team has configured Control Tower, created ToolsAccount and Dev01 accounts. Will have Rush deploy Stage and Prod accounts during a walkthrough session.


**Gaurdrails:** Proserve team has enabled Mandatory and most of the Strongly Recommended Gaurdrails. Rush Team can enable/disable any further Elective guardrails as requried.

**Detailed Guardrails reference:**  
https://docs.aws.amazon.com/controltower/latest/userguide/guardrails.html
https://docs.aws.amazon.com/controltower/latest/userguide/guardrails-reference.html

## Security Alerts and Guardrail deviations

Please subscribe to the following SNS Topics in the Audit account to get notified on Security Alerts and Guardrail deviations via Email/SMS

**SNS Topics**

| Name | Arn|
|---|---|
| aws-controltower-AggregateSecurityNotifications | arn:aws:sns:us-east-1:027869397375:aws-controltower-AggregateSecurityNotifications |
| aws-controltower-AllConfigNotifications	|	arn:aws:sns:us-east-1:027869397375:aws-controltower-AllConfigNotifications |
| aws-controltower-SecurityNotifications	|	arn:aws:sns:us-east-1:027869397375:aws-controltower-SecurityNotifications |
