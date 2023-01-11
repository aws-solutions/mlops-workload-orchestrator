# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [2.1.1] - 2023-01-11

### Updated

- Python runtime 3.10.
- Python libraries. 

## [2.1.0] - 2022-11-30

### Added

- Integration with Amazon SageMaker Model Card and Model Dashboard features to allow customers to perform model card operations. All Amazon SageMaker resources (models, endpoints, training jobs, and model monitors) created by the solution will show up on the SageMaker Model Dashboard.

### Fixed

- Missing AWS IAM Role permissions used by the Amazon SageMaker Clarify Model Bias Monitor and Amazon SageMaker Clarify Model Explainability Monitor scheduling jobs.

## [2.0.1] - 2022-08-12

### Updated

- The AWS IAM Role permissions with the new naming convention for the temporary Amazon SageMaker endpoints used by the Amazon SageMaker Clarify Model Bias Monitor and Amazon SageMaker Clarify Model Explainability Monitor pipelines.

### Fixed

- Environment variables of lambda functions by adding `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python` to handle `protobuf` library breaking changes in versions greater than `3.20.1`.

- Empty string image url for the model training pipelines when using Amazon SageMaker Model Registry option.

## [2.0.0] - 2022-05-31

### Added

- A new pipeline to train Machine Learning (ML) models using [Amazon SageMaker built-in algorithms](https://docs.aws.amazon.com/sagemaker/latest/dg/algos.html) and [Amazon SageMaker Training Job](https://docs.aws.amazon.com/sagemaker/latest/dg/how-it-works-training.html).
- A new pipeline to train ML models using Amazon SageMaker built-in algorithms and [Amazon Hyperparameter Tuning Job](https://docs.aws.amazon.com/sagemaker/latest/dg/automatic-model-tuning-how-it-works.html).
- A new pipeline to train ML models using Amazon SageMaker built-in algorithms and
  [Amazon SageMaker Autopilot Job](https://docs.aws.amazon.com/sagemaker/latest/dg/autopilot-automate-model-development.html).
- [Amazon EventBridge Rules](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-rules.html)
  to notify the solution's administrator(s) about the status of the training jobs.

### Updated

- The [Amazon Simple Notification Service (SNS)](https://aws.amazon.com/sns/?whats-new-cards.sort-by=item.additionalFields.postDateTime&whats-new-cards.sort-order=desc)
  Topic, used for pipelines notifications, was moved to the solution's main template.

## [1.5.0] - 2022-01-24

### Added

- A new pipeline to deploy [Amazon SageMaker Clarify Model Bias Monitor](https://docs.aws.amazon.com/sagemaker/latest/dg/clarify-model-monitor-bias-drift.html). The new pipeline monitors predictions for bias on a regular basis, and generates
  alerts if bias beyond a certain threshold is detected.
- A new pipeline to deploy [Amazon SageMaker Clarify Explainability (Feature Attribution Drift) Monitor](https://docs.aws.amazon.com/sagemaker/latest/dg/clarify-model-monitor-feature-attribution-drift.html). The new pipeline helps data scientists and ML engineers
  monitor predictions for feature attribution drift on a regular basis.

### Updated

- The solution's name was changed from "AWS MLOps Framework" to "MLOps Workload Orchestrator".

## [1.4.1] - 2021-12-20

### Added

- Developer section in the Implementation Guide (IG) to explain how customers can integrate
  their own custom blueprints with the solution.
- Configurable server-side error propagation to allow/disallow detailed error messages
  in the solution's APIs responses.

### Updated

- The format of the solution's APIs responses.
- AWS Cloud Development Kit (AWS CDK) and AWS Solutions Constructs to version 1.126.0.

## [1.4.0] - 2021-09-28

### Added

- A new pipeline to deploy [Amazon SageMaker Model Quality Monitor](https://docs.aws.amazon.com/sagemaker/latest/dg/model-monitor-model-quality.html). The new pipeline monitors the performance of a deployed model by comparing the
  predictions that the model makes with the actual ground truth labels that the model attempts to predict.

### Updated

- The Model Monitor pipeline's API call. Now, the Model Monitor pipeline is split into two pipelines, Data Quality Monitor pipeline, and Model Quality Monitor pipeline.
- The format of CloudFormation templates parameters' names from `PARAMETERNAME` to `ParameterName`.
- The APIs of the Realtime Inference pipeline to support passing an optional custom endpoint name.
- The data quality baseline's Lambda to use AWS SageMaker SDK to create the baseline, instead of using Boto3.
- AWS Cloud Development Kit (AWS CDK) and AWS Solutions Constructs to version 1.117.0.

## [1.3.0] - 2021-06-24

### Added

- The option to use [Amazon SageMaker Model Registry](https://docs.aws.amazon.com/sagemaker/latest/dg/model-registry.html) to deploy versioned models. The model registry allows you to catalog models for production, manage model versions, associate metadata with models, manage the approval status of a model, deploy models to production, and automate model deployment with CI/CD.
- The option to use an [AWS Organizations delegated administrator account](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-orgs-delegated-admin.html) to orchestrate the deployment of Machine Learning (ML) workloads across the AWS Organizations accounts using AWS CloudFormation StackSets.

### Updated

- The build of the AWS Lambda layer for Amazon SageMaker SDK using the lambda:build-python3.8 Docker image.

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
