# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.1] - 2021-03-19

### Updated

- AWS ECR image scan on push property's name from `scanOnPush` to `ScanOnPush` for image scanning based on the recently updated property name in AWS CloudFormation.
- AWS ECR repository's name in the IAM policy's resource name from `<repository-name>*` to `<pipeline_stack_name>*-<repository-name>*` to accommodate recent repository name being prefixed with AWS CloudFormation stack name.

## [1.1.0] - 2021-01-26

### Added

- Allows you to provision multiple model monitor pipelines to periodically monitor the quality of deployed Amazon SageMaker's ML models.
- Ability to use an existing S3 bucket as the model artifact and data bucket, or create a new one to store model artifact and data.

### Updated

- Updates AWS Cloud Development Kit (AWS CDK) and AWS Solutions Constructs to version 1.83.0.
- Updates request body of the Pipelines API's calls.

## [1.0.0] - 2020-11-05

### Added

- Initiates a pre-configured pipeline through an API call or a Git repository
- Automatically deploys a trained model and provides an inference endpoint
- Supports running your own integration tests to ensure that the deployed model meets expectations
- Allows to provision multiple environments to support ML model's life cycle
- Notifies users of the pipeline outcome though SMS or email
