# #####################################################################################################################
#  Copyright 2020-2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                       #
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
from aws_cdk import (
    aws_iam as iam,
    aws_s3 as s3,
    aws_ecr as ecr,
    aws_lambda as lambda_,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_codecommit as codecommit,
    aws_codebuild as codebuild,
    aws_apigateway as apigw,
    core,
)
from aws_solutions_constructs import aws_apigateway_lambda
from lib.conditional_resource import ConditionalResources
from lib.blueprints.byom.pipeline_definitions.helpers import (
    suppress_s3_access_policy,
    apply_secure_bucket_policy,
    suppress_lambda_policies,
)
from lib.blueprints.byom.pipeline_definitions.templates_parameters import (
    create_notification_email_parameter,
    create_git_address_parameter,
    create_existing_bucket_parameter,
    create_existing_ecr_repo_parameter,
    create_account_id_parameter,
    create_org_id_parameter,
    create_git_address_provided_condition,
    create_existing_bucket_provided_condition,
    create_existing_ecr_provided_condition,
    create_new_bucket_condition,
    create_new_ecr_repo_condition,
)
from lib.blueprints.byom.pipeline_definitions.deploy_actions import sagemaker_layer


class MLOpsStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, *, multi_account=False, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Get stack parameters:
        notification_email = create_notification_email_parameter(self)
        git_address = create_git_address_parameter(self)
        # Get the optional S3 assets bucket to use
        existing_bucket = create_existing_bucket_parameter(self)
        # Get the optional S3 assets bucket to use
        existing_ecr_repo = create_existing_ecr_repo_parameter(self)
        # create only if multi_account template
        if multi_account:
            # create development parameters
            account_type = "development"
            dev_account_id = create_account_id_parameter(self, "DEV_ACCOUNT_ID", account_type)
            dev_org_id = create_org_id_parameter(self, "DEV_ORG_ID", account_type)
            # create staging parameters
            account_type = "staging"
            staging_account_id = create_account_id_parameter(self, "STAGING_ACCOUNT_ID", account_type)
            staging_org_id = create_org_id_parameter(self, "STAGING_ORG_ID", account_type)
            # create production parameters
            account_type = "production"
            prod_account_id = create_account_id_parameter(self, "PROD_ACCOUNT_ID", account_type)
            prod_org_id = create_org_id_parameter(self, "PROD_ORG_ID", account_type)

        # Conditions
        git_address_provided = create_git_address_provided_condition(self, git_address)

        # client provided an existing S3 bucket name, to be used for assets
        existing_bucket_provided = create_existing_bucket_provided_condition(self, existing_bucket)

        # client provided an existing Amazon ECR name
        existing_ecr_provided = create_existing_ecr_provided_condition(self, existing_ecr_repo)

        # S3 bucket needs to be created for assets
        create_new_bucket = create_new_bucket_condition(self, existing_bucket)

        # Amazon ECR repo needs too be created for custom Algorithms
        create_new_ecr_repo = create_new_ecr_repo_condition(self, existing_ecr_repo)

        # Constants
        pipeline_stack_name = "mlops-pipeline"

        # CDK Resources setup
        access_logs_bucket = s3.Bucket(
            self,
            "accessLogs",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        # Apply secure transfer bucket policy
        apply_secure_bucket_policy(access_logs_bucket)

        # This is a logging bucket.
        access_logs_bucket.node.default_child.cfn_options.metadata = suppress_s3_access_policy()

        # Import user provide S3 bucket, if any. s3.Bucket.from_bucket_arn is used instead of
        # s3.Bucket.from_bucket_name to allow cross account bucket.
        client_existing_bucket = s3.Bucket.from_bucket_arn(
            self,
            "ClientExistingBucket",
            f"arn:aws:s3:::{existing_bucket.value_as_string.strip()}",
        )

        # Create the resource if existing_bucket_provided condition is True
        core.Aspects.of(client_existing_bucket).add(ConditionalResources(existing_bucket_provided))

        # Import user provided Amazon ECR repository

        client_erc_repo = ecr.Repository.from_repository_name(
            self, "ClientExistingECRReo", existing_ecr_repo.value_as_string
        )
        # Create the resource if existing_ecr_provided condition is True
        core.Aspects.of(client_erc_repo).add(ConditionalResources(existing_ecr_provided))

        # Creating assets bucket so that users can upload ML Models to it.
        assets_bucket = s3.Bucket(
            self,
            "pipeline-assets-" + str(uuid.uuid4()),
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            server_access_logs_bucket=access_logs_bucket,
            server_access_logs_prefix="assets_bucket_access_logs",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        # Apply secure transport bucket policy
        apply_secure_bucket_policy(assets_bucket)
        s3_actions = ["s3:GetObject", "s3:ListBucket"]
        # if multi account
        if multi_account:
            # add permissions for other accounts to access the assets bucket

            assets_bucket.add_to_resource_policy(
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=s3_actions,
                    principals=[
                        iam.AccountPrincipal(dev_account_id.value_as_string),
                        iam.AccountPrincipal(staging_account_id.value_as_string),
                        iam.AccountPrincipal(prod_account_id.value_as_string),
                    ],
                    resources=[assets_bucket.bucket_arn, f"{assets_bucket.bucket_arn}/*"],
                )
            )

        # Create the resource if create_new_bucket condition is True
        core.Aspects.of(assets_bucket).add(ConditionalResources(create_new_bucket))

        # Get assets S3 bucket's name/arn, based on the condition
        assets_s3_bucket_name = core.Fn.condition_if(
            existing_bucket_provided.logical_id,
            client_existing_bucket.bucket_name,
            assets_bucket.bucket_name,
        ).to_string()

        # Creating Amazon ECR repository
        ecr_repo = ecr.Repository(self, "ECRRepo", image_scan_on_push=True)

        # if multi account
        if multi_account:
            # add permissios to other account to pull images
            ecr_repo.add_to_resource_policy(
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "ecr:DescribeImages",
                        "ecr:DescribeRepositories",
                        "ecr:GetDownloadUrlForLayer",
                        "ecr:BatchGetImage",
                        "ecr:BatchCheckLayerAvailability",
                    ],
                    principals=[
                        iam.AccountPrincipal(dev_account_id.value_as_string),
                        iam.AccountPrincipal(staging_account_id.value_as_string),
                        iam.AccountPrincipal(prod_account_id.value_as_string),
                    ],
                )
            )
        # Create the resource if create_new_ecr condition is True
        core.Aspects.of(ecr_repo).add(ConditionalResources(create_new_ecr_repo))

        # Get ECR repo's name based on the condition
        ecr_repo_name = core.Fn.condition_if(
            existing_ecr_provided.logical_id,
            client_erc_repo.repository_name,
            ecr_repo.repository_name,
        ).to_string()

        # Get ECR repo's arn based on the condition
        ecr_repo_arn = core.Fn.condition_if(
            existing_ecr_provided.logical_id,
            client_erc_repo.repository_arn,
            ecr_repo.repository_arn,
        ).to_string()

        blueprints_bucket_name = "blueprint-repository-" + str(uuid.uuid4())
        blueprint_repository_bucket = s3.Bucket(
            self,
            blueprints_bucket_name,
            encryption=s3.BucketEncryption.S3_MANAGED,
            server_access_logs_bucket=access_logs_bucket,
            server_access_logs_prefix=blueprints_bucket_name,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )
        # Apply secure transport bucket policy
        apply_secure_bucket_policy(blueprint_repository_bucket)

        # if multi account
        if multi_account:
            # add permissions for other accounts to access the blueprint bucket
            blueprint_repository_bucket.add_to_resource_policy(
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=s3_actions,
                    principals=[
                        iam.AccountPrincipal(dev_account_id.value_as_string),
                        iam.AccountPrincipal(staging_account_id.value_as_string),
                        iam.AccountPrincipal(prod_account_id.value_as_string),
                    ],
                    resources=[blueprint_repository_bucket.bucket_arn, f"{blueprint_repository_bucket.bucket_arn}/*"],
                )
            )

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

        custom_resource_lambda_fn.node.default_child.cfn_options.metadata = suppress_lambda_policies()
        blueprint_repository_bucket.grant_write(custom_resource_lambda_fn)
        custom_resource = core.CustomResource(
            self,
            "CustomResourceCopyAssets",
            service_token=custom_resource_lambda_fn.function_arn,
        )
        custom_resource.node.add_dependency(blueprint_repository_bucket)
        # IAM policies setup ###
        cloudformation_role = iam.Role(
            self,
            "mlopscloudformationrole",
            assumed_by=iam.ServicePrincipal("cloudformation.amazonaws.com"),
        )
        lambda_invoke_action = "lambda:InvokeFunction"
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
                        (
                            f"arn:{core.Aws.PARTITION}:cloudformation:{core.Aws.REGION}:"
                            f"{core.Aws.ACCOUNT_ID}:stack/{pipeline_stack_name}*/*"
                        ),
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
                    resources=[f"arn:{core.Aws.PARTITION}:iam::{core.Aws.ACCOUNT_ID}:role/{pipeline_stack_name}*"],
                ),
                iam.PolicyStatement(
                    actions=[
                        "ecr:CreateRepository",
                        "ecr:DescribeRepositories",
                    ],
                    resources=[
                        (
                            f"arn:{core.Aws.PARTITION}:ecr:{core.Aws.REGION}:"
                            f"{core.Aws.ACCOUNT_ID}:repository/{ecr_repo_name}"
                        )
                    ],
                ),
                iam.PolicyStatement(
                    actions=[
                        "codebuild:CreateProject",
                        "codebuild:DeleteProject",
                        "codebuild:BatchGetProjects",
                    ],
                    resources=[
                        (
                            f"arn:{core.Aws.PARTITION}:codebuild:{core.Aws.REGION}:"
                            f"{core.Aws.ACCOUNT_ID}:project/ContainerFactory*"
                        ),
                        (
                            f"arn:{core.Aws.PARTITION}:codebuild:{core.Aws.REGION}:"
                            f"{core.Aws.ACCOUNT_ID}:project/VerifySagemaker*"
                        ),
                        (
                            f"arn:{core.Aws.PARTITION}:codebuild:{core.Aws.REGION}:"
                            f"{core.Aws.ACCOUNT_ID}:report-group/*"
                        ),
                    ],
                ),
                iam.PolicyStatement(
                    actions=[
                        "lambda:CreateFunction",
                        "lambda:DeleteFunction",
                        lambda_invoke_action,
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
                    actions=s3_actions,
                    resources=[
                        blueprint_repository_bucket.bucket_arn,
                        blueprint_repository_bucket.arn_for_objects("*"),
                        f"arn:{core.Aws.PARTITION}:s3:::{assets_s3_bucket_name}/*",
                    ],
                ),
                iam.PolicyStatement(
                    actions=[
                        "codepipeline:CreatePipeline",
                        "codepipeline:UpdatePipeline",
                        "codepipeline:DeletePipeline",
                        "codepipeline:GetPipeline",
                        "codepipeline:GetPipelineState",
                    ],
                    resources=[
                        (
                            f"arn:{core.Aws.PARTITION}:codepipeline:{core.Aws.REGION}:"
                            f"{core.Aws.ACCOUNT_ID}:{pipeline_stack_name}*"
                        )
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
                    resources=[f"arn:{core.Aws.PARTITION}:s3:::*"],
                ),
                iam.PolicyStatement(
                    actions=[
                        "s3:PutObject",
                    ],
                    resources=[f"arn:{core.Aws.PARTITION}:s3:::{assets_s3_bucket_name}/*"],
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
                        (
                            f"arn:{core.Aws.PARTITION}:sns:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:"
                            f"{pipeline_stack_name}*-*PipelineNotification*"
                        )
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
        lambda_passrole_policy = iam.PolicyStatement(actions=["iam:passrole"], resources=[cloudformation_role.role_arn])
        # create sagemaker layer
        sm_layer = sagemaker_layer(self, blueprint_repository_bucket)
        # make sure the sagemaker code is uploaded first to the blueprints bucket
        sm_layer.node.add_dependency(custom_resource)
        # API Gateway and lambda setup to enable provisioning pipelines through API calls
        provisioner_apigw_lambda = aws_apigateway_lambda.ApiGatewayToLambda(
            self,
            "PipelineOrchestration",
            lambda_function_props={
                "runtime": lambda_.Runtime.PYTHON_3_8,
                "handler": "index.handler",
                "code": lambda_.Code.from_asset("lambdas/pipeline_orchestration"),
                "layers": [sm_layer],
                "timeout": core.Duration.minutes(10),
            },
            api_gateway_props={
                "defaultMethodOptions": {
                    "authorizationType": apigw.AuthorizationType.IAM,
                },
                "restApiName": f"{core.Aws.STACK_NAME}-orchestrator",
                "proxy": False,
                "dataTraceEnabled": True,
            },
        )

        # add lambda supressions
        provisioner_apigw_lambda.lambda_function.node.default_child.cfn_options.metadata = suppress_lambda_policies()

        provision_resource = provisioner_apigw_lambda.api_gateway.root.add_resource("provisionpipeline")
        provision_resource.add_method("POST")
        status_resource = provisioner_apigw_lambda.api_gateway.root.add_resource("pipelinestatus")
        status_resource.add_method("POST")
        blueprint_repository_bucket.grant_read(provisioner_apigw_lambda.lambda_function)
        provisioner_apigw_lambda.lambda_function.add_to_role_policy(lambda_passrole_policy)
        orchestrator_policy.attach_to_role(provisioner_apigw_lambda.lambda_function.role)

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
        provisioner_apigw_lambda.lambda_function.add_environment(key="ASSETS_BUCKET", value=str(assets_s3_bucket_name))
        provisioner_apigw_lambda.lambda_function.add_environment(
            key="CFN_ROLE_ARN", value=str(cloudformation_role.role_arn)
        )
        provisioner_apigw_lambda.lambda_function.add_environment(key="PIPELINE_STACK_NAME", value=pipeline_stack_name)
        provisioner_apigw_lambda.lambda_function.add_environment(
            key="NOTIFICATION_EMAIL", value=notification_email.value_as_string
        )
        provisioner_apigw_lambda.lambda_function.add_environment(key="REGION", value=core.Aws.REGION)
        provisioner_apigw_lambda.lambda_function.add_environment(key="IS_MULTI_ACCOUNT", value=str(multi_account))

        # if multi account
        if multi_account:
            provisioner_apigw_lambda.lambda_function.add_environment(
                key="DEV_ACCOUNT_ID", value=dev_account_id.value_as_string
            )
            provisioner_apigw_lambda.lambda_function.add_environment(key="DEV_ORG_ID", value=dev_org_id.value_as_string)

            provisioner_apigw_lambda.lambda_function.add_environment(
                key="STAGING_ACCOUNT_ID", value=staging_account_id.value_as_string
            )
            provisioner_apigw_lambda.lambda_function.add_environment(
                key="STAGING_ORG_ID", value=staging_org_id.value_as_string
            )

            provisioner_apigw_lambda.lambda_function.add_environment(
                key="PROD_ACCOUNT_ID", value=prod_account_id.value_as_string
            )
            provisioner_apigw_lambda.lambda_function.add_environment(
                key="PROD_ORG_ID", value=prod_org_id.value_as_string
            )

        provisioner_apigw_lambda.lambda_function.add_environment(key="ECR_REPO_NAME", value=ecr_repo_name)

        provisioner_apigw_lambda.lambda_function.add_environment(key="ECR_REPO_ARN", value=ecr_repo_arn)

        provisioner_apigw_lambda.lambda_function.add_environment(key="LOG_LEVEL", value="DEBUG")
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

        # Codepipeline with Git source definitions ###
        source_output = codepipeline.Artifact()
        # processing git_address to retrieve repo name
        repo_name_split = core.Fn.split("/", git_address.value_as_string)
        repo_name = core.Fn.select(5, repo_name_split)
        # getting codecommit repo cdk object using 'from_repository_name'
        repo = codecommit.Repository.from_repository_name(self, "AWSMLOpsFrameworkRepository", repo_name)
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
                            branch="main",
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
                actions=[lambda_invoke_action],
                resources=[provisioner_apigw_lambda.lambda_function.function_arn],
            )
        )
        codebuild_project.add_to_role_policy(
            iam.PolicyStatement(
                actions=[lambda_invoke_action],
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

        # custom resource for operational metrics###
        metrics_mapping = core.CfnMapping(self, "AnonymousData", mapping={"SendAnonymousData": {"Data": "Yes"}})
        metrics_condition = core.CfnCondition(
            self,
            "AnonymousDatatoAWS",
            expression=core.Fn.condition_equals(metrics_mapping.find_in_map("SendAnonymousData", "Data"), "Yes"),
        )

        helper_function = lambda_.Function(
            self,
            "SolutionHelper",
            code=lambda_.Code.from_asset("lambdas/solution_helper"),
            handler="lambda_function.handler",
            runtime=lambda_.Runtime.PYTHON_3_8,
            timeout=core.Duration.seconds(60),
        )

        helper_function.node.default_child.cfn_options.metadata = suppress_lambda_policies()
        create_id_function = core.CustomResource(
            self,
            "CreateUniqueID",
            service_token=helper_function.function_arn,
            properties={"Resource": "UUID"},
            resource_type="Custom::CreateUUID",
        )

        send_data_function = core.CustomResource(
            self,
            "SendAnonymousData",
            service_token=helper_function.function_arn,
            properties={
                "Resource": "AnonymousMetric",
                "UUID": create_id_function.get_att_string("UUID"),
                "gitSelected": git_address.value_as_string,
                "Region": core.Aws.REGION,
                "SolutionId": "SO0136",
                "Version": "%%VERSION%%",
            },
            resource_type="Custom::AnonymousData",
        )

        core.Aspects.of(helper_function).add(ConditionalResources(metrics_condition))
        core.Aspects.of(create_id_function).add(ConditionalResources(metrics_condition))
        core.Aspects.of(send_data_function).add(ConditionalResources(metrics_condition))

        # If user chooses Git as pipeline provision type, create codepipeline with Git repo as source
        core.Aspects.of(repo).add(ConditionalResources(git_address_provided))
        core.Aspects.of(codecommit_pipeline).add(ConditionalResources(git_address_provided))
        core.Aspects.of(codebuild_project).add(ConditionalResources(git_address_provided))

        # Create Template Interface
        paramaters_list = [
            notification_email.logical_id,
            git_address.logical_id,
            existing_bucket.logical_id,
            existing_ecr_repo.logical_id,
        ]

        # if multi account
        if multi_account:
            paramaters_list.extend(
                [
                    dev_account_id.logical_id,
                    dev_org_id.logical_id,
                    staging_account_id.logical_id,
                    staging_org_id.logical_id,
                    prod_account_id.logical_id,
                    prod_org_id.logical_id,
                ]
            )

        paramaters_labels = {
            f"{notification_email.logical_id}": {"default": "Notification Email (Required)"},
            f"{git_address.logical_id}": {"default": "CodeCommit Repo URL Address (Optional)"},
            f"{existing_bucket.logical_id}": {"default": "Name of an Existing S3 Bucket (Optional)"},
            f"{existing_ecr_repo.logical_id}": {"default": "Name of an Existing Amazon ECR repository (Optional)"},
        }

        if multi_account:
            paramaters_labels.update(
                {
                    f"{dev_account_id.logical_id}": {"default": "Development Account ID (Required)"},
                    f"{dev_org_id.logical_id}": {"default": "Development Account Organizational Unit ID (Required)"},
                    f"{staging_account_id.logical_id}": {"default": "Staging Account ID (Required)"},
                    f"{staging_org_id.logical_id}": {"default": "Staging Account Organizational Unit ID (Required)"},
                    f"{prod_account_id.logical_id}": {"default": "Production Account ID (Required)"},
                    f"{prod_org_id.logical_id}": {"default": "Production Account Organizational Unit ID (Required)"},
                }
            )
        self.template_options.metadata = {
            "AWS::CloudFormation::Interface": {
                "ParameterGroups": [
                    {
                        "Label": {"default": "MLOps Framework Settings"},
                        "Parameters": paramaters_list,
                    }
                ],
                "ParameterLabels": paramaters_labels,
            }
        }
        # Outputs #
        core.CfnOutput(
            self,
            id="BlueprintsBucket",
            value=f"https://s3.console.aws.amazon.com/s3/buckets/{blueprint_repository_bucket.bucket_name}",
            description="S3 Bucket to upload MLOps Framework Blueprints",
        )
        core.CfnOutput(
            self,
            id="AssetsBucket",
            value=f"https://s3.console.aws.amazon.com/s3/buckets/{assets_s3_bucket_name}",
            description="S3 Bucket to upload model artifact",
        )
        core.CfnOutput(
            self,
            id="ECRRepoName",
            value=ecr_repo_name,
            description="Amazon ECR repository's name",
        )
        core.CfnOutput(
            self,
            id="ECRRepoArn",
            value=ecr_repo_arn,
            description="Amazon ECR repository's arn",
        )