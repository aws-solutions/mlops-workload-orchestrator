# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2021-05-04

### Added

- Two stack deployment options that provision machine learning (ML) pipelines either in a single AWS account, or across multiple AWS accounts for development, staging/test, and production environments.
- Ability to provide an optional AWS Key Management Service (KMS) key to encrypt captured data from the real-time Amazon SageMaker endpoint, output of batch transform and data baseline jobs, output of model monitor, and Amazon Elastic Compute Cloud (EC2) instance's volume used by Amazon SageMaker to run the solution's pipelines.
- New pipeline to build and register Docker images for custom ML algorithms.
- Ability to use an existing Amazon Elastic Container Registry (Amazon ECR) repository, or create a new one, to store Docker images for custom ML algorithms.
- Ability to provide different input/output Amazon Simple Storage Service (Amazon S3) buckets per pipeline deployment.

### Updated

- The creation of Amazon SageMaker resources using AWS CloudFormation.
- The request body of the solution's API calls to provision pipelines.
- AWS SDK to use the solution's identifier to track requests made by the solution to AWS services.
- AWS Cloud Development Kit (AWS CDK) and AWS Solutions Constructs to version 1.96.0.

## [1.1.1] - 2021-03-19

### Updated

- AWS ECR image scan on push property's name from `scanOnPush` to `ScanOnPush` for image scanning based on the recently updated property name in AWS CloudFormation.
- AWS ECR repository's name in the IAM policy's resource name from `<repository-name>*` to `*<repository-name>*` to accommodate recent repository name being prefixed with AWS CloudFormation stack name.

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
