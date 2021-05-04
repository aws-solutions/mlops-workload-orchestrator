# aws-mlops-framework

The machine learning (ML) lifecycle is an iterative and repetitive process that involves
changing models over time and learning from new data. As ML applications gain popularity,
organizations are building new and better applications for a wide range of use cases including
optimized email campaigns, forecasting tools, recommendation engines, self-driving vehicles,
virtual personal assistants, and more. While operational and pipelining processes vary greatly
across projects and organizations, the processes contain commonalities across use cases.

The solution helps you streamline and enforce architecture best practices by providing an extendable
framework for managing ML pipelines for Amazon Machine Learning (Amazon ML) services and third-party
services. The solution’s template allows you to upload trained models, configure the orchestration of
the pipeline, initiate the start of the deployment process, move models through different stages of
deployment, and monitor the successes and failures of the operations. The solution also provides a
pipeline for building and registering Docker images for custom algorithms that can be used for model
deployment on an [Amazon SageMaker](https://aws.amazon.com/sagemaker/) endpoint.

You can use batch and real-time data inferences to configure the pipeline for your business context.
You can also provision multiple Model Monitor pipelines to periodically monitor the quality of deployed
Amazon SageMaker ML models. This solution increases your team’s agility and efficiency by allowing them
to repeat successful processes at scale.

#### Benefits

- **Leverage a pre-configured machine learning pipeline:** Use the solution's reference architecture to initiate a pre-configured pipeline through an API call or a Git repository.
- **Automatically deploy a trained model and inference endpoint:** Use the solution's framework to automate the model monitor pipeline or the Amazon SageMaker BYOM pipeline. Deliver an inference endpoint with model drift detection packaged as a serverless microservice.

---

## Architecture

This solution is built with two primary components: 1) the orchestrator component, created by deploying the solution’s AWS CloudFormation template, and 2) the AWS CodePipeline instance deployed from either calling the solution’s API Gateway, or by committing a configuration file into an AWS CodeCommit repository. The solution’s pipelines are implemented as AWS CloudFormation templates, which allows you to extend the solution and add custom pipelines.

To support multiple use cases and business needs, the solution provides two AWS CloudFormation templates: **option 1** for single account deployment, and **option 2** for multi-account deployment.

### Template option 1: Single account deployment

The solution’s single account architecture allows you to provision ML pipelines in a single AWS account.

![architecture-option-1](source/architecture-option-1.png)

### Template option 2: Multi-account deployment

The solution uses [AWS Organizations](https://aws.amazon.com/organizations/) and [AWS CloudFormation StackSets](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/what-is-cfnstacksets.html) to allow you to provision or update ML pipelines across AWS accounts. Using an administrator account (also referred to as the orchestrator account) allows you to deploy ML pipelines implemented as AWS CloudFormation templates into selected target accounts (for example, development, staging, and production accounts).

![architecture-option-2](source/architecture-option-2.png)

---

## File Structure

Upon successfully cloning the repository into your local development environment but **prior** to running the initialization script, you will see the following file structure in your editor:

```
├── deployment                            [folder containing build scripts]
│   ├── cdk-solution-helper               [A helper function to help deploy lambda function code through S3 buckets]
│   ├── build-s3-dist.sh                  [A script to prepare the solution for deploying from source code]
├── source                                [source code containing CDK App and lambda functions]
│   ├── lambdas                           [folder containing source code the lambda functions]
│   │   ├── custom_resource               [lambda function to copy necessary resources from aws solutions bucket]
│   │   ├── pipeline_orchestration        [lambda function to provision ML pipelines]
│   └── lib
│       ├── blueprints                    [folder containing implementations of different types of ML pipelines supported by this solution]
│       │   ├── byom                      [implementation of bring-your-own-model ML pipeline]
│       │   │   ├── lambdas               [folder containing source code the lambda functions]
│       │   │   └── pipeline_definitions  [folder containing CDK implementation of pipeline stages in BYOM]
│       ├── aws_mlops_stack.py            [CDK implementation of the main framework ]
│       └── conditional_resource.py       [a helper file to enable conditional resource provisioning in CDK]
├── .gitignore
├── CHANGELOG.md                          [required for every solution to include changes based on version to auto[uild release notes]
├── CODE_OF_CONDUCT.md                    [standardized open source file for all solutions]
├── CONTRIBUTING.md                       [standardized open source file for all solutions]
├── LICENSE.txt                           [required open source file for all solutions - should contain the Apache 2.0 license]
├── NOTICE.txt                            [required open source file for all solutions - should contain references to all 3rd party libraries]
└── README.md                             [required file for all solutions]

* Note: Not all languages are supported at this time. Actual appearance may vary depending on release.
```

## Building the solution

### 1. Get source code

Clone this git repository.

`git clone https://github.com/awslabs/<repository_name>`

---

### 2. Running Unit Tests

The `/source/run-all-tests.sh` script is the centralized script for running all unit, integration, and snapshot tests for both the CDK project as well as any associated Lambda functions or other source code packages.

- Note: It is the developer's responsibility to ensure that all test commands are called in this script, and that it is kept up to date.

This script is called from the solution build scripts to ensure that specified tests are passing while performing build, validation and publishing tasks via the pipeline.

---

### 3. Building Project Distributable

- Configure the bucket name of your target Amazon S3 distribution bucket

```
export DIST_OUTPUT_BUCKET=my-bucket-name # bucket where customized code will reside
export SOLUTION_NAME=my-solution-name
export VERSION=my-version # version number for the customized code
```

_Note:_ You would have to create an S3 bucket with the prefix 'my-bucket-name-<aws_region>'; aws_region is where you are testing the customized solution. Also, the assets in bucket should be publicly accessible.

- Now build the distributable:

```
cd deployment && chmod +x ./build-s3-dist.sh \n
./build-s3-dist.sh $DIST_OUTPUT_BUCKET $SOLUTION_NAME $VERSION \n
```

- Deploy the distributable to an Amazon S3 bucket in your account. _Note:_ You must have the AWS Command Line Interface installed.

```
aws s3 cp ./dist/ s3://my-bucket-name-<aws_region>/$SOLUTION_NAME/$VERSION/ --recursive --acl bucket-owner-full-control --profile aws-cred-profile-name \n
```

- Get the link for the solution template uploaded to your Amazon S3 bucket.
- Deploy the solution to your account by launching a new AWS CloudFormation stack using the link of the solution template in Amazon S3.

## Known Issues

### Image Builder Pipeline may fail due to Docker Hub rate limits

When building custom model container that pulls public docker images from Docker Hub in short time period, you may occasionally face throttling errors with an error message such as:
` toomanyrequests You have reached your pull rate limit. You may increase the limit by authenticating and upgrading: https://www.docker.com/increase-rate-limit`

This is due to Docker Inc. [limiting the rate at which images are pulled under Docker Hub anonymous and free plans](https://docs.docker.com/docker-hub/download-rate-limit/). Under the new limits of Dockerhub, free plan anonymous use is limited to 100 pulls per six hours, free plan authenticated accounts limited to 200 pulls per six hours, and Pro and Team accounts do not see any rate limits.

For more information regarding this issue and short-term and long-term fixes, refer to this AWS blog post: [Advice for customers dealing with Docker Hub rate limits, and a Coming Soon announcement](https://aws.amazon.com/blogs/containers/advice-for-customers-dealing-with-docker-hub-rate-limits-and-a-coming-soon-announcement/)

### Model Monitor Blueprint may fail in multi-account deployment option

When using the blueprint for Model Monitor pipeline in multi-account deployment option, the deployment of the stack in the staging ("DeployStaging") account may fail with an error message:

```
Resource handler returned message: "Error occurred during operation 'CREATE'." (RequestToken:<token-id>, HandlerErrorCode: GeneralServiceException)
```

Workaround: there is no known workaround for this issue for the multi-account Model Monitor blueprint.

---

Copyright 2020-2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.

Licensed under the Apache License Version 2.0 (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at

    http://www.apache.org/licenses/

or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions and limitations under the License.
