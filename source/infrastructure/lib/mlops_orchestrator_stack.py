# #####################################################################################################################
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.                                                 #
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
from constructs import Construct
from aws_cdk import (
    Stack,
    Aws,
    Aspects,
    Fn,
    CustomResource,
    Duration,
    CfnMapping,
    CfnCondition,
    CfnOutput,
)
from aws_cdk import (
    aws_iam as iam,
    aws_s3 as s3,
    aws_ecr as ecr,
    aws_lambda as lambda_,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_codecommit as codecommit,
    aws_codebuild as codebuild,
    aws_kms as kms,
    aws_apigateway as apigw,
    aws_sns_subscriptions as subscriptions,
    aws_sns as sns,
)
from aws_solutions_constructs import aws_apigateway_lambda
from lib.blueprints.aspects.conditional_resource import ConditionalResources
from lib.blueprints.pipeline_definitions.helpers import (
    suppress_s3_access_policy,
    suppress_lambda_policies,
    suppress_sns,
)
from lib.blueprints.pipeline_definitions.templates_parameters import (
    ParameteresFactory as pf,
    ConditionsFactory as cf,
)
from lib.blueprints.pipeline_definitions.deploy_actions import (
    sagemaker_layer,
    create_solution_helper,
    create_uuid_custom_resource,
    create_send_data_custom_resource,
    create_copy_assets_lambda,
)
from lib.blueprints.pipeline_definitions.iam_policies import (
    create_invoke_lambda_policy,
    create_orchestrator_policy,
)
from lib.blueprints.pipeline_definitions.configure_multi_account import (
    configure_multi_account_parameters_permissions,
)
from lib.blueprints.pipeline_definitions.sagemaker_model_registry import (
    create_sagemaker_model_registry,
)
from lib.blueprints.pipeline_definitions.cdk_context_value import (
    get_cdk_context_value,
)
from lib.blueprints.pipeline_definitions.sagemaker_model_registry import (
    create_sagemaker_model_registry,
)
from lib.blueprints.pipeline_definitions.cdk_context_value import (
    get_cdk_context_value,
)


class MLOpsStack(Stack):
    def __init__(
        self, scope: Construct, id: str, *, multi_account=False, **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Get stack parameters:
        notification_email = pf.create_notification_email_parameter(self)
        git_address = pf.create_git_address_parameter(self)
        # Get the optional S3 assets bucket to use
        existing_bucket = pf.create_existing_bucket_parameter(self)
        # Get the optional S3 assets bucket to use
        existing_ecr_repo = pf.create_existing_ecr_repo_parameter(self)
        # Will SageMaker's Model Registry be used to provision models
        use_model_registry = pf.create_use_model_registry_parameter(self)
        # Does the user want the solution to create model registry
        create_model_registry = pf.create_model_registry_parameter(self)
        # Enable detailed error message in the API response
        allow_detailed_error_message = pf.create_detailed_error_message_parameter(self)

        # Conditions
        git_address_provided = cf.create_git_address_provided_condition(
            self, git_address
        )

        # client provided an existing S3 bucket name, to be used for assets
        existing_bucket_provided = cf.create_existing_bucket_provided_condition(
            self, existing_bucket
        )

        # client provided an existing Amazon ECR name
        existing_ecr_provided = cf.create_existing_ecr_provided_condition(
            self, existing_ecr_repo
        )

        # client wants the solution to create model registry
        model_registry_condition = cf.create_model_registry_condition(
            self, create_model_registry
        )

        # S3 bucket needs to be created for assets
        create_new_bucket = cf.create_new_bucket_condition(self, existing_bucket)

        # Amazon ECR repo needs too be created for custom Algorithms
        create_new_ecr_repo = cf.create_new_ecr_repo_condition(self, existing_ecr_repo)

        # Constants
        pipeline_stack_name = "mlops-pipeline"

        # CDK Resources setup
        access_logs_bucket = s3.Bucket(
            self,
            "accessLogs",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            enforce_ssl=True,
        )

        # remove ACL to add bucket policy instead
        access_logs_bucket.node.default_child.add_deletion_override(
            "Properties.AccessControl"
        )

        # This is a logging bucket.
        access_logs_bucket.node.default_child.cfn_options.metadata = (
            suppress_s3_access_policy()
        )

        # Import user provide S3 bucket, if any. s3.Bucket.from_bucket_arn is used instead of
        # s3.Bucket.from_bucket_name to allow cross account bucket.
        client_existing_bucket = s3.Bucket.from_bucket_arn(
            self,
            "ClientExistingBucket",
            f"arn:{Aws.PARTITION}:s3:::{existing_bucket.value_as_string.strip()}",
        )

        # Create the resource if existing_bucket_provided condition is True
        Aspects.of(client_existing_bucket).add(
            ConditionalResources(existing_bucket_provided)
        )

        # Import user provided Amazon ECR repository

        client_erc_repo = ecr.Repository.from_repository_name(
            self, "ClientExistingECRReo", existing_ecr_repo.value_as_string
        )
        # Create the resource if existing_ecr_provided condition is True
        Aspects.of(client_erc_repo).add(ConditionalResources(existing_ecr_provided))

        # Creating assets bucket so that users can upload ML Models to it.
        assets_bucket = s3.Bucket(
            self,
            "pipeline-assets-" + str(uuid.uuid4()),
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            server_access_logs_bucket=access_logs_bucket,
            server_access_logs_prefix="assets_bucket_access_logs",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
        )

        # Create the resource if create_new_bucket condition is True
        Aspects.of(assets_bucket).add(ConditionalResources(create_new_bucket))

        # Get assets S3 bucket's name/arn, based on the condition
        assets_s3_bucket_name = Fn.condition_if(
            existing_bucket_provided.logical_id,
            client_existing_bucket.bucket_name,
            assets_bucket.bucket_name,
        ).to_string()

        blueprints_bucket_name = "blueprint-repository-" + str(uuid.uuid4())
        blueprint_repository_bucket = s3.Bucket(
            self,
            blueprints_bucket_name,
            encryption=s3.BucketEncryption.S3_MANAGED,
            server_access_logs_bucket=access_logs_bucket,
            server_access_logs_prefix=blueprints_bucket_name,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            enforce_ssl=True,
        )

        # add override for access logs bucket
        access_logs_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:PutObject"],
                principals=[iam.ServicePrincipal("logging.s3.amazonaws.com")],
                resources=[
                    f"{access_logs_bucket.bucket_arn}/*",
                ],
                conditions={
                    "ArnLike": {
                        "aws:SourceArn": [
                            f"arn:{Aws.PARTITION}:s3:::{assets_s3_bucket_name}",
                            blueprint_repository_bucket.bucket_arn,
                        ]
                    },
                    "StringEquals": {"aws:SourceAccount": Aws.ACCOUNT_ID},
                },
            )
        )

        # Creating Amazon ECR repository
        ecr_repo = ecr.Repository(self, "ECRRepo", image_scan_on_push=True)

        # Create the resource if create_new_ecr condition is True
        Aspects.of(ecr_repo).add(ConditionalResources(create_new_ecr_repo))

        # Get ECR repo's name based on the condition
        ecr_repo_name = Fn.condition_if(
            existing_ecr_provided.logical_id,
            client_erc_repo.repository_name,
            ecr_repo.repository_name,
        ).to_string()

        # Get ECR repo's arn based on the condition
        ecr_repo_arn = Fn.condition_if(
            existing_ecr_provided.logical_id,
            client_erc_repo.repository_arn,
            ecr_repo.repository_arn,
        ).to_string()

        # create sns topic and subscription
        mlops_notifications_topic = (
            sns.Topic(  # NOSONAR: the sns topic does not contain sensitive data
                self,
                "MLOpsNotificationsTopic",
            )
        )
        mlops_notifications_topic.node.default_child.cfn_options.metadata = (
            suppress_sns()
        )

        mlops_notifications_topic.add_subscription(
            subscriptions.EmailSubscription(
                email_address=notification_email.value_as_string
            )
        )

        # grant EventBridge permissions to publish messages
        # (via EventBridge Rules used to monitor SageMaker resources)
        mlops_notifications_topic.add_to_resource_policy(
            iam.PolicyStatement(
                actions=["sns:Publish"],
                effect=iam.Effect.ALLOW,
                resources=[mlops_notifications_topic.topic_arn],
                principals=[iam.ServicePrincipal("events.amazonaws.com")],
            )
        )

        # solution helper function
        helper_function = create_solution_helper(self)

        # custom resource to generate UUID
        create_id_function = create_uuid_custom_resource(
            self, create_model_registry.value_as_string, helper_function.function_arn
        )

        # creating SageMaker Model registry
        # use the first 8 characters as a unique_id to be appended to the model_package_group_name
        unique_id = Fn.select(
            0, Fn.split("-", create_id_function.get_att_string("UUID"))
        )
        model_package_group_name = f"mlops-model-registry-{unique_id}"
        model_registry = create_sagemaker_model_registry(
            self, "SageMakerModelRegistry", model_package_group_name
        )

        # only create based on the condition
        model_registry.cfn_options.condition = model_registry_condition

        # add dependency on the create_id_function custom resource
        model_registry.node.add_dependency(create_id_function)

        # Custom resource to copy source bucket content to blueprints bucket
        custom_resource_lambda_fn = create_copy_assets_lambda(
            self, blueprint_repository_bucket.bucket_name
        )

        # grant permission to upload file to the blueprints bucket
        blueprint_repository_bucket.grant_write(custom_resource_lambda_fn)
        custom_resource = CustomResource(
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

        # Cloudformation policy setup
        orchestrator_policy = create_orchestrator_policy(
            self,
            pipeline_stack_name,
            ecr_repo_name,
            blueprint_repository_bucket,
            assets_s3_bucket_name,
        )
        orchestrator_policy.attach_to_role(cloudformation_role)

        # Lambda function IAM setup
        lambda_passrole_policy = iam.PolicyStatement(
            actions=["iam:passrole"], resources=[cloudformation_role.role_arn]
        )

        # create sagemaker layer
        sm_layer = sagemaker_layer(self, blueprint_repository_bucket)
        # make sure the sagemaker code is uploaded first to the blueprints bucket
        sm_layer.node.add_dependency(custom_resource)
        # API Gateway and lambda setup to enable provisioning pipelines through API calls
        provisioner_apigw_lambda = aws_apigateway_lambda.ApiGatewayToLambda(
            self,
            "PipelineOrchestration",
            lambda_function_props={
                "runtime": lambda_.Runtime.PYTHON_3_10,
                "handler": "index.handler",
                "code": lambda_.Code.from_asset("../lambdas/pipeline_orchestration"),
                "layers": [sm_layer],
                "timeout": Duration.minutes(10),
            },
            api_gateway_props={
                "defaultMethodOptions": {
                    "authorizationType": apigw.AuthorizationType.IAM,
                },
                "restApiName": f"{Aws.STACK_NAME}-orchestrator",
                "proxy": False,
                "dataTraceEnabled": True,
            },
        )

        # add lambda suppressions
        provisioner_apigw_lambda.lambda_function.node.default_child.cfn_options.metadata = (
            suppress_lambda_policies()
        )
        provisioner_apigw_lambda.lambda_function.node.default_child.cfn_options.metadata = (
            suppress_lambda_policies()
        )

        provision_resource = provisioner_apigw_lambda.api_gateway.root.add_resource(
            "provisionpipeline"
        )

        provision_resource.add_method("POST")
        status_resource = provisioner_apigw_lambda.api_gateway.root.add_resource(
            "pipelinestatus"
        )

        status_resource.add_method("POST")
        blueprint_repository_bucket.grant_read(provisioner_apigw_lambda.lambda_function)
        provisioner_apigw_lambda.lambda_function.add_to_role_policy(
            lambda_passrole_policy
        )
        orchestrator_policy.attach_to_role(
            provisioner_apigw_lambda.lambda_function.role
        )

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
            key="ASSETS_BUCKET", value=str(assets_s3_bucket_name)
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
            key="REGION", value=Aws.REGION
        )
        provisioner_apigw_lambda.lambda_function.add_environment(
            key="IS_MULTI_ACCOUNT", value=str(multi_account)
        )
        provisioner_apigw_lambda.lambda_function.add_environment(
            key="USE_MODEL_REGISTRY", value=use_model_registry.value_as_string
        )
        provisioner_apigw_lambda.lambda_function.add_environment(
            key="ALLOW_DETAILED_ERROR_MESSAGE",
            value=allow_detailed_error_message.value_as_string,
        )

        provisioner_apigw_lambda.lambda_function.add_environment(
            key="MLOPS_NOTIFICATIONS_SNS_TOPIC",
            value=mlops_notifications_topic.topic_arn,
        )
        provisioner_apigw_lambda.lambda_function.add_environment(
            key="ECR_REPO_NAME", value=ecr_repo_name
        )

        provisioner_apigw_lambda.lambda_function.add_environment(
            key="ECR_REPO_ARN", value=ecr_repo_arn
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
                    },
                    {
                        "id": "W12",
                        "reason": "sagemaker:ListModelCards and sagemaker:Search can not have a restricted resource.",
                    },
                ]
            }
        }

        # Codepipeline with Git source definitions ###
        source_output = codepipeline.Artifact()
        # processing git_address to retrieve repo name
        repo_name_split = Fn.split("/", git_address.value_as_string)
        repo_name = Fn.select(5, repo_name_split)
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
            create_invoke_lambda_policy(
                [provisioner_apigw_lambda.lambda_function.function_arn]
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
        metrics_mapping = CfnMapping(
            self,
            "AnonymizedData",
            mapping={"SendAnonymizedData": {"Data": "Yes"}},
            lazy=False,
        )
        metrics_condition = CfnCondition(
            self,
            "AnonymizedDatatoAWS",
            expression=Fn.condition_equals(
                metrics_mapping.find_in_map("SendAnonymizedData", "Data"), "Yes"
            ),
        )

        # If user chooses Git as pipeline provision type, create codepipeline with Git repo as source
        Aspects.of(repo).add(ConditionalResources(git_address_provided))
        Aspects.of(codecommit_pipeline).add(ConditionalResources(git_address_provided))
        Aspects.of(codebuild_project).add(ConditionalResources(git_address_provided))

        # Create Template Interface
        paramaters_list = [
            notification_email.logical_id,
            git_address.logical_id,
            existing_bucket.logical_id,
            existing_ecr_repo.logical_id,
            use_model_registry.logical_id,
            create_model_registry.logical_id,
            allow_detailed_error_message.logical_id,
        ]

        paramaters_labels = {
            f"{notification_email.logical_id}": {
                "default": "Notification Email (Required)"
            },
            f"{git_address.logical_id}": {
                "default": "CodeCommit Repo URL Address (Optional)"
            },
            f"{existing_bucket.logical_id}": {
                "default": "Name of an Existing S3 Bucket (Optional)"
            },
            f"{existing_ecr_repo.logical_id}": {
                "default": "Name of an Existing Amazon ECR repository (Optional)"
            },
            f"{use_model_registry.logical_id}": {
                "default": "Do you want to use SageMaker Model Registry?"
            },
            f"{create_model_registry.logical_id}": {
                "default": "Do you want the solution to create a SageMaker's model package group?"
            },
            f"{allow_detailed_error_message.logical_id}": {
                "default": "Do you want to allow detailed error messages in the APIs response?"
            },
        }

        # configure mutli-account parameters and permissions
        is_delegated_admin = None
        if multi_account:
            (
                paramaters_list,
                paramaters_labels,
                is_delegated_admin,
            ) = configure_multi_account_parameters_permissions(
                self,
                assets_bucket,
                blueprint_repository_bucket,
                ecr_repo,
                model_registry,
                provisioner_apigw_lambda.lambda_function,
                paramaters_list,
                paramaters_labels,
            )

        # properties of send data custom resource
        # if you add new metrics to the cr properties, make sure to updated the allowed keys
        # to send in the "_sanitize_data" function in source/lambdas/solution_helper/lambda_function.py
        send_data_cr_properties = {
            "Resource": "AnonymizedMetric",
            "UUID": create_id_function.get_att_string("UUID"),
            "bucketSelected": Fn.condition_if(
                existing_bucket_provided.logical_id,
                "True",
                "False",
            ).to_string(),
            "gitSelected": Fn.condition_if(
                git_address_provided.logical_id,
                "True",
                "False",
            ).to_string(),
            "Region": Aws.REGION,
            "IsMultiAccount": str(multi_account),
            "IsDelegatedAccount": is_delegated_admin if multi_account else Aws.NO_VALUE,
            "UseModelRegistry": use_model_registry.value_as_string,
            "SolutionId": get_cdk_context_value(self, "SolutionId"),
            "Version": get_cdk_context_value(self, "Version"),
        }

        # create send data custom resource
        send_data_function = create_send_data_custom_resource(
            self, helper_function.function_arn, send_data_cr_properties
        )

        # create send_data_function based on metrics_condition condition
        Aspects.of(send_data_function).add(ConditionalResources(metrics_condition))

        # create template metadata
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
        CfnOutput(
            self,
            id="BlueprintsBucket",
            value=f"https://s3.console.aws.amazon.com/s3/buckets/{blueprint_repository_bucket.bucket_name}",
            description="S3 Bucket to upload MLOps Framework Blueprints",
        )
        CfnOutput(
            self,
            id="AssetsBucket",
            value=f"https://s3.console.aws.amazon.com/s3/buckets/{assets_s3_bucket_name}",
            description="S3 Bucket to upload model artifact",
        )
        CfnOutput(
            self,
            id="ECRRepoName",
            value=ecr_repo_name,
            description="Amazon ECR repository's name",
        )
        CfnOutput(
            self,
            id="ECRRepoArn",
            value=ecr_repo_arn,
            description="Amazon ECR repository's arn",
        )

        CfnOutput(
            self,
            id="ModelRegistryArn",
            value=Fn.condition_if(
                model_registry_condition.logical_id,
                model_registry.attr_model_package_group_arn,
                "[No Model Package Group was created]",
            ).to_string(),
            description="SageMaker model package group arn",
        )

        CfnOutput(
            self,
            id="MLOpsNotificationsTopicArn",
            value=mlops_notifications_topic.topic_arn,
            description="MLOps notifications SNS topic arn.",
        )
