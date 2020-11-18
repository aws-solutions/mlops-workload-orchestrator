# #####################################################################################################################
#  Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                            #
#                                                                                                                     #
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance     #
#  with the License. A copy of the License is located at                                                              #
#                                                                                                                     #
#  http://www.apache.org/licenses/LICENSE-2.0                                                                         #
#                                                                                                                     #
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES  #
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions     #
#  and limitations under the License.                                                                                 #
# #####################################################################################################################
import uuid
import os
from aws_cdk import (
    aws_iam as iam,
    aws_s3 as s3,
    aws_s3_assets as assets,
    aws_s3_deployment as s3deploy,
    aws_lambda as lambda_,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_codecommit as codecommit,
    aws_codebuild as codebuild,
    aws_apigateway as apigw,
    aws_logs as logs,
    custom_resources as cr,
    core,
)
from aws_solutions_constructs import aws_apigateway_lambda
from lib.conditional_resource import ConditionalResources


class MLOpsStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Get stack parameters: email and repo address
        notification_email = core.CfnParameter(
            self,
            "Email Address",
            type="String",
            description="Specify an email to receive notifications about pipeline outcomes.",
            allowed_pattern='^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$',
            min_length=5,
            max_length=320,
            constraint_description="Please enter an email address with correct format (example@exmaple.com)"
        )
        git_address = core.CfnParameter(
            self,
            "CodeCommit Repo Address",
            type="String",
            description="AWS CodeCommit repository clone URL to connect to the framework.",
            allowed_pattern='^(((https:\/\/|ssh:\/\/)(git\-codecommit)\.[a-zA-Z0-9_.+-]+(amazonaws\.com\/)[a-zA-Z0-9-.]+(\/)[a-zA-Z0-9-.]+(\/)[a-zA-Z0-9-.]+$)|)',
            min_length=0,
            max_length=320,
            constraint_description="CodeCommit address must follow the pattern: ssh or https://git-codecommit.REGION.amazonaws.com/version/repos/REPONAME"
        )

        # Conditions
        git_address_provided = core.CfnCondition(
            self,
            "GitAddressProvided",
            expression=core.Fn.condition_not(core.Fn.condition_equals(git_address, "")),
        )

        # Constants
        pipeline_stack_name = "MLOps-pipeline"

        # CDK Resources setup
        access_logs_bucket = s3.Bucket(self, "accessLogs", encryption=s3.BucketEncryption.S3_MANAGED, block_public_access=s3.BlockPublicAccess.BLOCK_ALL)
        access_logs_bucket.node.default_child.cfn_options.metadata = {
            "cfn_nag": {
                "rules_to_suppress": [
                    {"id": "W35", "reason": "This is the access bucket."},
                    {
                        "id": "W51",
                        "reason": "This S3 bucket does not need a bucket policy.",
                    },
                ]
            }
        }
        source_bucket = s3.Bucket.from_bucket_name(
            self, "BucketByName", "%%BUCKET_NAME%%"
        )

        blueprints_bucket_name = "blueprint-repository-" + str(uuid.uuid4())
        blueprint_repository_bucket = s3.Bucket(
            self,
            blueprints_bucket_name,
            encryption=s3.BucketEncryption.S3_MANAGED,
            server_access_logs_bucket=access_logs_bucket,
            server_access_logs_prefix=blueprints_bucket_name,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL
        )
        blueprint_repository_bucket.node.default_child.cfn_options.metadata = {
            "cfn_nag": {
                "rules_to_suppress": [
                    {
                        "id": "W51",
                        "reason": "This S3 bucket does not need a bucket policy. All access to this bucket is restricted by IAM (CDK grant_read method)",
                    }
                ]
            }
        }

        # Custom resource to copy source bucket content to blueprints bucket
        custom_resource_lambda_fn = lambda_.Function(
            self,
            "CustomResourceLambda",
            code=lambda_.Code.from_asset("lambdas/custom_resource"),
            handler="index.on_event",
            runtime=lambda_.Runtime.PYTHON_3_8,
            environment={
                "source_bucket": "https://%%BUCKET_NAME%%-"
                + core.Aws.REGION
                + ".s3.amazonaws.com/%%SOLUTION_NAME%%/%%VERSION%%",
                "destination_bucket": blueprint_repository_bucket.bucket_name,
                "LOG_LEVEL": "INFO",
            },
            timeout=core.Duration.seconds(60),
        )
        custom_resource_lambda_fn.node.default_child.cfn_options.metadata = {
            "cfn_nag": {
                "rules_to_suppress": [
                    {
                        "id": "W58",
                        "reason": "The lambda functions role already has permissions to write cloudwatch logs",
                    }
                ]
            }
        }
        blueprint_repository_bucket.grant_write(custom_resource_lambda_fn)
        custom_resource = core.CustomResource(
            self,
            "CustomResourceCopyAssets",
            service_token=custom_resource_lambda_fn.function_arn,
        )
        custom_resource.node.add_dependency(blueprint_repository_bucket)
        ### IAM policies setup ###
        cloudformation_role = iam.Role(
            self,
            "mlopscloudformationrole",
            assumed_by=iam.ServicePrincipal("cloudformation.amazonaws.com"),
        )
        # Cloudformation policy setup
        orchestrator_policy = iam.Policy(
            self,
            "lambdaOrchestratorPolicy",
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "cloudformation:CreateStack",
                        "cloudformation:DeleteStack",
                        "cloudformation:UpdateStack",
                        "cloudformation:ListStackResources",
                    ],
                    resources=[
                        f"arn:{core.Aws.PARTITION}:cloudformation:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:stack/{pipeline_stack_name}*/*",
                    ],
                ),
                iam.PolicyStatement(
                    actions=[
                        "iam:CreateRole",
                        "iam:DeleteRole",
                        "iam:DeleteRolePolicy",
                        "iam:GetRole",
                        "iam:GetRolePolicy",
                        "iam:PassRole",
                        "iam:PutRolePolicy",
                        "iam:AttachRolePolicy",
                        "iam:DetachRolePolicy",
                    ],
                    resources=[
                        f"arn:{core.Aws.PARTITION}:iam::{core.Aws.ACCOUNT_ID}:role/{pipeline_stack_name}*"
                    ],
                ),
                iam.PolicyStatement(
                    actions=[
                        "ecr:CreateRepository",
                        "ecr:DeleteRepository",
                        "ecr:DescribeRepositories",
                    ],
                    resources=[
                        f"arn:{core.Aws.PARTITION}:ecr:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:repository/awsmlopsmodels*"
                    ],
                ),
                iam.PolicyStatement(
                    actions=[
                        "codebuild:CreateProject",
                        "codebuild:DeleteProject",
                        "codebuild:BatchGetProjects",
                    ],
                    resources=[
                        f"arn:{core.Aws.PARTITION}:codebuild:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:project/ContainerFactory*",
                        f"arn:{core.Aws.PARTITION}:codebuild:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:project/VerifySagemaker*",
                        f"arn:{core.Aws.PARTITION}:codebuild:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:report-group/*",
                    ],
                ),
                iam.PolicyStatement(
                    actions=[
                        "lambda:CreateFunction",
                        "lambda:DeleteFunction",
                        "lambda:InvokeFunction",
                        "lambda:PublishLayerVersion",
                        "lambda:DeleteLayerVersion",
                        "lambda:GetLayerVersion",
                        "lambda:GetFunctionConfiguration",
                        "lambda:GetFunction",
                        "lambda:AddPermission",
                        "lambda:RemovePermission",
                        "lambda:UpdateFunctionConfiguration",
                    ],
                    resources=[
                        f"arn:{core.Aws.PARTITION}:lambda:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:layer:*",
                        f"arn:{core.Aws.PARTITION}:lambda:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:function:*",
                    ],
                ),
                iam.PolicyStatement(
                    actions=["s3:GetObject"],
                    resources=[
                        blueprint_repository_bucket.bucket_arn,
                        blueprint_repository_bucket.arn_for_objects("*"),
                        f"arn:{core.Aws.PARTITION}:s3:::pipeline-assets-*",
                    ],
                ),
                iam.PolicyStatement(
                    actions=[
                        "codepipeline:CreatePipeline",
                        "codepipeline:DeletePipeline",
                        "codepipeline:GetPipeline",
                        "codepipeline:GetPipelineState",
                    ],
                    resources=[
                        f"arn:{core.Aws.PARTITION}:codepipeline:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:{pipeline_stack_name}*"
                    ],
                ),
                iam.PolicyStatement(
                    actions=[
                        "apigateway:POST",
                        "apigateway:PATCH",
                        "apigateway:DELETE",
                        "apigateway:GET",
                        "apigateway:PUT",
                    ],
                    resources=[
                        f"arn:{core.Aws.PARTITION}:apigateway:{core.Aws.REGION}::/restapis/*",
                        f"arn:{core.Aws.PARTITION}:apigateway:{core.Aws.REGION}::/restapis",
                        f"arn:{core.Aws.PARTITION}:apigateway:{core.Aws.REGION}::/account",
                        f"arn:{core.Aws.PARTITION}:apigateway:{core.Aws.REGION}::/usageplans",
                        f"arn:{core.Aws.PARTITION}:apigateway:{core.Aws.REGION}::/usageplans/*",
                    ],
                ),
                iam.PolicyStatement(
                    actions=[
                        "logs:CreateLogGroup",
                        "logs:DescribeLogGroups",
                    ],
                    resources=[
                        f"arn:{core.Aws.PARTITION}:logs:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:log-group:*",
                    ],
                ),
                iam.PolicyStatement(
                    actions=[
                        "s3:CreateBucket",
                        "s3:PutEncryptionConfiguration",
                        "s3:PutBucketVersioning",
                        "s3:PutBucketPublicAccessBlock",
                        "s3:PutBucketLogging",
                    ],
                    resources=["arn:" + core.Aws.PARTITION + ":s3:::*"],
                ),
                iam.PolicyStatement(
                    actions=[
                        "sns:CreateTopic",
                        "sns:DeleteTopic",
                        "sns:Subscribe",
                        "sns:Unsubscribe",
                        "sns:GetTopicAttributes",
                        "sns:SetTopicAttributes",
                    ],
                    resources=[
                        f"arn:{core.Aws.PARTITION}:sns:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:{pipeline_stack_name}*-PipelineNotification*",
                    ],
                ),
                iam.PolicyStatement(
                    actions=[
                        "events:PutRule",
                        "events:DescribeRule",
                        "events:PutTargets",
                        "events:RemoveTargets",
                        "events:DeleteRule",
                        "events:PutEvents",
                    ],
                    resources=[
                        f"arn:{core.Aws.PARTITION}:events:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:rule/*",
                        f"arn:{core.Aws.PARTITION}:events:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:event-bus/*",
                    ],
                ),
            ],
        )
        orchestrator_policy.attach_to_role(cloudformation_role)

        # Lambda function IAM setup
        lambda_passrole_policy = iam.PolicyStatement(
            actions=["iam:passrole"], resources=[cloudformation_role.role_arn]
        )
        # API Gateway and lambda setup to enable provisioning pipelines through API calls
        provisioner_apigw_lambda = aws_apigateway_lambda.ApiGatewayToLambda(
            self,
            "PipelineOrchestration",
            lambda_function_props={
                "runtime": lambda_.Runtime.PYTHON_3_8,
                "handler": "index.handler",
                "code": lambda_.Code.from_asset("lambdas/pipeline_orchestration"),
            },
            api_gateway_props={
                "defaultMethodOptions": {
                    "authorizationType": apigw.AuthorizationType.IAM,
                },
                "restApiName": f"{core.Aws.STACK_NAME}-orchestrator",
                "proxy": False
            },
        )
        provision_resource = provisioner_apigw_lambda.api_gateway.root.add_resource('provisionpipeline')
        provision_resource.add_method('POST')
        status_resource = provisioner_apigw_lambda.api_gateway.root.add_resource('pipelinestatus')
        status_resource.add_method('POST')
        blueprint_repository_bucket.grant_read(provisioner_apigw_lambda.lambda_function)
        provisioner_apigw_lambda.lambda_function.add_to_role_policy(
            lambda_passrole_policy
        )
        orchestrator_policy.attach_to_role(
            provisioner_apigw_lambda.lambda_function.role
        )
        provisioner_apigw_lambda.lambda_function.add_to_role_policy(
            iam.PolicyStatement(actions=["xray:PutTraceSegments"], resources=["*"])
        )
        lambda_node = provisioner_apigw_lambda.lambda_function.node.default_child
        lambda_node.cfn_options.metadata = {
            "cfn_nag": {
                "rules_to_suppress": [
                    {
                        "id": "W12",
                        "reason": "The xray permissions PutTraceSegments is not able to be bound to resources.",
                    }
                ]
            }
        }
        # Environment variables setup
        provisioner_apigw_lambda.lambda_function.add_environment(
            key="BLUEPRINT_BUCKET_URL",
            value=str(blueprint_repository_bucket.bucket_regional_domain_name),
        )
        provisioner_apigw_lambda.lambda_function.add_environment(
            key="BLUEPRINT_BUCKET", value=str(blueprint_repository_bucket.bucket_name)
        )
        provisioner_apigw_lambda.lambda_function.add_environment(
            key="ACCESS_BUCKET", value=str(access_logs_bucket.bucket_name)
        )
        provisioner_apigw_lambda.lambda_function.add_environment(
            key="CFN_ROLE_ARN", value=str(cloudformation_role.role_arn)
        )
        provisioner_apigw_lambda.lambda_function.add_environment(
            key="PIPELINE_STACK_NAME", value=pipeline_stack_name
        )
        provisioner_apigw_lambda.lambda_function.add_environment(
            key="NOTIFICATION_EMAIL", value=notification_email.value_as_string
        )
        provisioner_apigw_lambda.lambda_function.add_environment(
            key="LOG_LEVEL", value="DEBUG"
        )
        cfn_policy_for_lambda = orchestrator_policy.node.default_child
        cfn_policy_for_lambda.cfn_options.metadata = {
            "cfn_nag": {
                "rules_to_suppress": [
                    {
                        "id": "W76",
                        "reason": "A complex IAM policy is required for this resource.",
                    }
                ]
            }
        }

        ### Codepipeline with Git source definitions ###
        source_output = codepipeline.Artifact()
        # processing git_address to retrieve repo name
        repo_name_split = core.Fn.split("/", git_address.value_as_string)
        repo_name = core.Fn.select(5, repo_name_split)
        # getting codecommit repo cdk object using 'from_repository_name'
        repo = codecommit.Repository.from_repository_name(
            self, "AWSMLOpsFrameworkRepository", repo_name
        )
        codebuild_project = codebuild.PipelineProject(
            self,
            "Take config file",
            build_spec=codebuild.BuildSpec.from_object(
                {
                    "version": "0.2",
                    "phases": {
                        "build": {
                            "commands": [
                                "ls -a",
                                "aws lambda invoke --function-name "
                                + provisioner_apigw_lambda.lambda_function.function_name
                                + " --payload fileb://mlops-config.json response.json"
                                + " --invocation-type RequestResponse",
                            ]
                        }
                    },
                }
            ),
        )
        # Defining a Codepipeline project with CodeCommit as source
        codecommit_pipeline = codepipeline.Pipeline(
            self,
            "MLOpsCodeCommitPipeline",
            stages=[
                codepipeline.StageProps(
                    stage_name="Source",
                    actions=[
                        codepipeline_actions.CodeCommitSourceAction(
                            action_name="CodeCommit",
                            repository=repo,
                            output=source_output,
                        )
                    ],
                ),
                codepipeline.StageProps(
                    stage_name="TakeConfig",
                    actions=[
                        codepipeline_actions.CodeBuildAction(
                            action_name="provision_pipeline",
                            input=source_output,
                            outputs=[],
                            project=codebuild_project,
                        )
                    ],
                ),
            ],
            cross_account_keys=False,
        )
        codecommit_pipeline.add_to_role_policy(
            iam.PolicyStatement(
                actions=["lambda:InvokeFunction"],
                resources=[provisioner_apigw_lambda.lambda_function.function_arn],
            )
        )
        codebuild_project.add_to_role_policy(
            iam.PolicyStatement(
                actions=["lambda:InvokeFunction"],
                resources=[provisioner_apigw_lambda.lambda_function.function_arn],
            )
        )
        pipeline_child_nodes = codecommit_pipeline.node.find_all()
        pipeline_child_nodes[1].node.default_child.cfn_options.metadata = {
            "cfn_nag": {
                "rules_to_suppress": [
                    {
                        "id": "W35",
                        "reason": "This is a managed bucket generated by CDK for codepipeline.",
                    },
                    {
                        "id": "W51",
                        "reason": "This is a managed bucket generated by CDK for codepipeline.",
                    },
                ]
            }
        }

        ###custom resource for operational metrics###
        metricsMapping = core.CfnMapping(self, 'AnonymousData',
            mapping={
                'SendAnonymousData': {
                    'Data': 'Yes'
                }
            }
        )
        metrics_condition = core.CfnCondition(self, 'AnonymousDatatoAWS',
            expression=core.Fn.condition_equals(metricsMapping.find_in_map('SendAnonymousData', 'Data'), 'Yes')
        )

        helper_function = lambda_.Function(
            self,
            "SolutionHelper",
            code=lambda_.Code.from_asset("lambdas/solution_helper"),
            handler="lambda_function.handler",
            runtime=lambda_.Runtime.PYTHON_3_8,
            timeout=core.Duration.seconds(60),
        )

        createIdFunction = core.CustomResource(self, 'CreateUniqueID',
            service_token=helper_function.function_arn,
            properties={
                'Resource': 'UUID'
            },
            resource_type='Custom::CreateUUID'
        )

        sendDataFunction = core.CustomResource(self, 'SendAnonymousData',
            service_token=helper_function.function_arn,
            properties={
                'Resource': 'AnonymousMetric',
                'UUID': createIdFunction.get_att_string('UUID'),
                'gitSelected': git_address.value_as_string,
                'Region': core.Aws.REGION,
                'SolutionId': 'SO0136',
                'Version': '%%VERSION%%',
            },
            resource_type='Custom::AnonymousData'
        )

        core.Aspects.of(helper_function).add(ConditionalResources(metrics_condition))
        core.Aspects.of(createIdFunction).add(ConditionalResources(metrics_condition))
        core.Aspects.of(sendDataFunction).add(ConditionalResources(metrics_condition))
        helper_function.node.default_child.cfn_options.metadata = {
            "cfn_nag": {
                "rules_to_suppress": [
                    {
                        "id": "W58",
                        "reason": "The lambda functions role already has permissions to write cloudwatch logs",
                    }
                ]
            }
        }

        # If user chooses Git as pipeline provision type, create codepipeline with Git repo as source
        core.Aspects.of(repo).add(ConditionalResources(git_address_provided))
        core.Aspects.of(codecommit_pipeline).add(
            ConditionalResources(git_address_provided)
        )
        core.Aspects.of(codebuild_project).add(
            ConditionalResources(git_address_provided)
        )
