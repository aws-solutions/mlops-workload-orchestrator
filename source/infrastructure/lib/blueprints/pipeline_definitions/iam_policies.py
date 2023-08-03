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
from aws_cdk import aws_iam as iam, Fn, Aws
from lib.blueprints.pipeline_definitions.helpers import (
    suppress_ecr_policy,
    suppress_cloudwatch_policy,
    suppress_delegated_admin_policy,
)

sagemaker_arn_prefix = Fn.sub(
    "arn:${PARTITION}:sagemaker:${REGION}:${ACCOUNT_ID}",
    {"PARTITION": Aws.PARTITION, "REGION": Aws.REGION, "ACCOUNT_ID": Aws.ACCOUNT_ID},
)


def sagemaker_policy_statement(
    is_realtime_pipeline, endpoint_name, endpoint_name_provided
):
    actions = [
        "sagemaker:CreateModel",
        "sagemaker:DescribeModel",  # NOSONAR: permission needs to be repeated for clarity
        "sagemaker:DeleteModel",
    ]
    resources = [
        f"{sagemaker_arn_prefix}:model/mlopssagemakermodel*"  # NOSONAR: permission needs to be repeated for clarity
    ]

    if is_realtime_pipeline:
        # extend actions
        actions.extend(
            [
                "sagemaker:CreateEndpointConfig",  # NOSONAR: permission needs to be repeated for clarity
                "sagemaker:DescribeEndpointConfig",  # NOSONAR: permission needs to be repeated for clarity
                "sagemaker:DeleteEndpointConfig",  # NOSONAR: permission needs to be repeated for clarity
                "sagemaker:CreateEndpoint",  # NOSONAR: permission needs to be repeated for clarity
                "sagemaker:DescribeEndpoint",  # NOSONAR: permission needs to be repeated for clarity
                "sagemaker:DeleteEndpoint",  # NOSONAR: permission needs to be repeated for clarity
            ]
        )

        # if a custom endpoint_name is provided, use it. Otherwise, use the generated name
        endpoint = Fn.condition_if(
            endpoint_name_provided.logical_id,
            endpoint_name.value_as_string,
            "mlopssagemakerendpoint*",
        ).to_string()

        # extend resources and add
        resources.extend(
            [
                f"{sagemaker_arn_prefix}:endpoint-config/mlopssagemakerendpointconfig*",
                f"{sagemaker_arn_prefix}:endpoint/{endpoint}",
            ]
        )
    return iam.PolicyStatement(
        effect=iam.Effect.ALLOW,  # NOSONAR: effect is repeated for readability
        actions=actions,
        resources=resources,
    )


def baseline_lambda_get_model_name_policy(endpoint_name):
    # these permissions are required to get the ModelName used by the monitored endpoint
    return iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        actions=[
            "sagemaker:DescribeModel",
            "sagemaker:DescribeEndpointConfig",
            "sagemaker:DescribeEndpoint",
        ],
        resources=[
            f"{sagemaker_arn_prefix}:model/mlopssagemakermodel*",
            f"{sagemaker_arn_prefix}:endpoint-config/mlopssagemakerendpointconfig*",
            f"{sagemaker_arn_prefix}:endpoint/{endpoint_name}",
        ],
    )


def sagemaker_model_bias_explainability_baseline_job_policy():
    # required to create/delete a Shadow endpointConfig/Endpoint created by the sagemaker clarify
    return iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        actions=[
            "sagemaker:DescribeModel",
            "sagemaker:DescribeEndpointConfig",
            "sagemaker:DescribeEndpoint",
            "sagemaker:CreateEndpointConfig",
            "sagemaker:CreateEndpoint",
            "sagemaker:DeleteEndpointConfig",
            "sagemaker:DeleteEndpoint",
            "sagemaker:InvokeEndpoint",  # NOSONAR: permission needs to be repeated for clarity
        ],
        resources=[
            f"{sagemaker_arn_prefix}:model/mlopssagemakermodel*",
            f"{sagemaker_arn_prefix}:endpoint-config/sm-clarify-config*",
            f"{sagemaker_arn_prefix}:endpoint/sm-clarify-*",
        ],
    )


def sagemaker_baseline_job_policy(baseline_job_name):
    return iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        actions=[
            "sagemaker:CreateProcessingJob",
            "sagemaker:DescribeProcessingJob",
            "sagemaker:StopProcessingJob",
        ],
        resources=[
            f"{sagemaker_arn_prefix}:processing-job/{baseline_job_name}",
        ],
    )


def batch_transform_policy():
    return iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        actions=[
            "sagemaker:CreateTransformJob",
        ],
        resources=[
            f"{sagemaker_arn_prefix}:transform-job/mlopssagemakermodel-*-batch-transform-*"
        ],
    )


def autopilot_job_policy(job_name):
    return iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        actions=["sagemaker:CreateAutoMLJob"],
        resources=[f"{sagemaker_arn_prefix}:automl-job/{job_name}"],
    )


def training_job_policy(job_name, job_type):
    actions_map = {
        "TrainingJob": "sagemaker:CreateTrainingJob",
        "HyperparameterTuningJob": "sagemaker:CreateHyperParameterTuningJob",
    }
    resources_map = {
        "TrainingJob": f"{sagemaker_arn_prefix}:training-job/{job_name}",
        "HyperparameterTuningJob": f"{sagemaker_arn_prefix}:hyper-parameter-tuning-job/{job_name}",
    }
    return iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        actions=[actions_map[job_type]],
        resources=[resources_map[job_type]],
    )


def autopilot_job_endpoint_policy(job_name):
    return iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        actions=[
            "sagemaker:DescribeModel",
            "sagemaker:DescribeEndpointConfig",
            "sagemaker:DescribeEndpoint",
            "sagemaker:InvokeEndpoint",
        ],
        resources=[
            f"{sagemaker_arn_prefix}:model/{job_name}*",
            f"{sagemaker_arn_prefix}:endpoint-config/{job_name}*",
            f"{sagemaker_arn_prefix}:endpoint/{job_name}*",
        ],
    )


def create_service_role(scope, id, service, description):
    return iam.Role(
        scope,
        id,
        assumed_by=iam.ServicePrincipal(service),
        description=description,
    )


def sagemaker_monitor_policy_statement(
    baseline_job_name, monitoring_schedule_name, endpoint_name, monitoring_type
):
    # common permissions
    actions = [
        "sagemaker:DescribeModel",
        "sagemaker:DescribeEndpointConfig",
        "sagemaker:DescribeEndpoint",
        "sagemaker:CreateEndpointConfig",
        "sagemaker:CreateEndpoint",
        "sagemaker:CreateMonitoringSchedule",
        "sagemaker:DescribeMonitoringSchedule",
        "sagemaker:StopMonitoringSchedule",
        "sagemaker:DeleteMonitoringSchedule",
        "sagemaker:DescribeProcessingJob",
        "sagemaker:DeleteEndpointConfig",
        "sagemaker:DeleteEndpoint",
        "sagemaker:InvokeEndpoint",
    ]
    # common resources
    resources = [
        f"{sagemaker_arn_prefix}:model/mlopssagemakermodel*",
        f"{sagemaker_arn_prefix}:endpoint-config/mlopssagemakerendpointconfig*",
        f"{sagemaker_arn_prefix}:endpoint/{endpoint_name}",
        f"{sagemaker_arn_prefix}:monitoring-schedule/{monitoring_schedule_name}",
        f"{sagemaker_arn_prefix}:processing-job/{baseline_job_name}",
        f"{sagemaker_arn_prefix}:endpoint-config/sm-clarify-config*",
        f"{sagemaker_arn_prefix}:endpoint/sm-clarify-*",
    ]

    # create a map of monitoring type -> required permissions/resources
    type_permissions = {
        "DataQuality": {
            "permissions": [
                "sagemaker:CreateDataQualityJobDefinition",
                "sagemaker:DescribeDataQualityJobDefinition",
                "sagemaker:DeleteDataQualityJobDefinition",
            ],
            "resources": [f"{sagemaker_arn_prefix}:data-quality-job-definition/*"],
        },
        "ModelQuality": {
            "permissions": [
                "sagemaker:CreateModelQualityJobDefinition",
                "sagemaker:DescribeModelQualityJobDefinition",
                "sagemaker:DeleteModelQualityJobDefinition",
            ],
            "resources": [f"{sagemaker_arn_prefix}:model-quality-job-definition/*"],
        },
        "ModelBias": {
            "permissions": [
                "sagemaker:CreateModelBiasJobDefinition",
                "sagemaker:DescribeModelBiasJobDefinition",
                "sagemaker:DeleteModelBiasJobDefinition",
            ],
            "resources": [f"{sagemaker_arn_prefix}:model-bias-job-definition/*"],
        },
        "ModelExplainability": {
            "permissions": [
                "sagemaker:CreateModelExplainabilityJobDefinition",
                "sagemaker:DescribeModelExplainabilityJobDefinition",
                "sagemaker:DeleteModelExplainabilityJobDefinition",
            ],
            "resources": [
                f"{sagemaker_arn_prefix}:model-explainability-job-definition/*"
            ],
        },
    }
    # add monitoring type's specific permissions
    actions.extend(type_permissions[monitoring_type]["permissions"])

    # add monitoring type's specific resources
    resources.extend(type_permissions[monitoring_type]["resources"])

    # create the policy statement
    return iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        actions=actions,
        resources=resources,
    )


def sagemaker_tags_policy_statement():
    return iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        actions=[
            "sagemaker:AddTags",
            "sagemaker:DeleteTags",
        ],
        resources=[f"{sagemaker_arn_prefix}:*"],
    )


def sagemaker_logs_metrics_policy_document(scope, id):
    policy = iam.Policy(
        scope,
        id,
        statements=[
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:DescribeLogStreams",
                    "logs:GetLogEvents",
                    "logs:PutLogEvents",
                ],
                resources=[
                    f"arn:{Aws.PARTITION}:logs:{Aws.REGION}:{Aws.ACCOUNT_ID}:log-group:/aws/sagemaker/*"
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "cloudwatch:PutMetricData",
                ],
                resources=["*"],
            ),
        ],
    )
    policy.node.default_child.cfn_options.metadata = suppress_cloudwatch_policy()

    return policy


def s3_policy_read(resources_list, principals=None):
    return iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        principals=principals,
        actions=["s3:GetObject", "s3:ListBucket"],
        resources=resources_list,
    )


def create_ecr_repo_policy(principals):
    return iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        actions=[
            "ecr:DescribeImages",
            "ecr:DescribeRepositories",  # NOSONAR: permission needs to be repeated for clarity
            "ecr:GetDownloadUrlForLayer",
            "ecr:BatchGetImage",
            "ecr:BatchCheckLayerAvailability",
        ],
        principals=principals,
    )


def s3_policy_write(resources_list):
    return iam.PolicyStatement(
        actions=[
            "s3:PutObject",  # NOSONAR: permission needs to be repeated for clarity
        ],
        resources=resources_list,
    )


def pass_role_policy_statement(role):
    return iam.PolicyStatement(
        actions=["iam:PassRole"],
        resources=[
            role.role_arn,
        ],
        conditions={
            "StringLike": {"iam:PassedToService": "sagemaker.amazonaws.com"},
        },
    )


def get_role_policy_statement(role):
    return iam.PolicyStatement(
        actions=["iam:GetRole"],
        resources=[
            role.role_arn,
        ],
    )


def ecr_policy_document(scope, id, repo_arn):
    ecr_policy = iam.Policy(
        scope,
        id,
        statements=[
            iam.PolicyStatement(
                actions=[
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:DescribeRepositories",  # NOSONAR: permission needs to be repeated for clarity
                    "ecr:DescribeImages",
                    "ecr:BatchGetImage",
                ],
                resources=[repo_arn],
            ),
            iam.PolicyStatement(
                actions=[
                    "ecr:GetAuthorizationToken",
                ],
                # it can not be bound to resources other than *
                resources=["*"],
            ),
        ],
    )
    # add supression for *
    ecr_policy.node.default_child.cfn_options.metadata = suppress_ecr_policy()

    return ecr_policy


def kms_policy_document(scope, id, kms_key_arn):
    return iam.Policy(
        scope,
        id,
        statements=[
            iam.PolicyStatement(
                actions=[
                    "kms:Encrypt",
                    "kms:Decrypt",
                    "kms:CreateGrant",
                    "kms:ReEncrypt*",
                    "kms:GenerateDataKey*",
                    "kms:DescribeKey",
                ],
                resources=[kms_key_arn],
            )
        ],
    )


def get_model_registry_actions_resources(model_package_group_name):
    actions = [
        "sagemaker:DescribeModelPackageGroup",
        "sagemaker:DescribeModelPackage",
        "sagemaker:ListModelPackages",
        "sagemaker:UpdateModelPackage",
        "sagemaker:CreateModel",  # NOSONAR: permission needs to be repeated for clarity
    ]

    resources = [
        f"{sagemaker_arn_prefix}:model-package-group/{model_package_group_name}",
        f"{sagemaker_arn_prefix}:model-package/{model_package_group_name}/*",
    ]

    return (actions, resources)


def model_registry_policy_statement(model_package_group_name):
    actions, resources = get_model_registry_actions_resources(model_package_group_name)
    return iam.PolicyStatement(
        actions=actions,
        resources=resources,
    )


def model_registry_policy_document(scope, id, model_package_group_name):
    return iam.Policy(
        scope,
        id,
        statements=[model_registry_policy_statement(model_package_group_name)],
    )


def model_package_group_policy(model_package_group_name, accounts_list):
    actions, resources = get_model_registry_actions_resources(model_package_group_name)
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AddPermModelPackageGroup",
                "Effect": "Allow",
                "Principal": {
                    "AWS": [
                        f"arn:{Aws.PARTITION}:iam::{account_id}:root"
                        for account_id in accounts_list
                    ]
                },
                "Action": actions,
                "Resource": resources,
            }
        ],
    }


def cloudformation_stackset_policy(stack_name, account_id):
    return iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        actions=[
            "cloudformation:DescribeStackSet",
            "cloudformation:DescribeStackInstance",
            "cloudformation:CreateStackSet",
        ],
        resources=[
            # Stack sets with service-managed permissions are created in the management account,
            # including stack sets created by delegated administrators.
            # the "*" is used here for "ACCOUNT_ID" when a delegated administrator account
            # is used by the solution (default). Otherwise, Aws.ACCOUNT_ID used.
            # more info on CF StackSets with delegated admin account can be found here:
            # https://docs.amazonaws.cn/en_us/AWSCloudFormation/latest/UserGuide/stacksets-orgs-delegated-admin.html
            f"arn:{Aws.PARTITION}:cloudformation:{Aws.REGION}:{account_id}:stackset/{stack_name}:*",
            f"arn:{Aws.PARTITION}:cloudformation:*::type/resource/*",
        ],
    )


def cloudformation_stackset_instances_policy(stack_name, account_id):
    return iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        actions=[
            "cloudformation:CreateStackInstances",
            "cloudformation:DeleteStackInstances",
            "cloudformation:UpdateStackSet",
            "lambda:TagResource",
        ],
        resources=[
            f"arn:{Aws.PARTITION}:cloudformation::{account_id}:stackset-target/{stack_name}:*",
            f"arn:{Aws.PARTITION}:cloudformation:{Aws.REGION}::type/resource/*",
            f"arn:{Aws.PARTITION}:cloudformation:{Aws.REGION}:{account_id}:stackset/{stack_name}:*",
            f"arn:{Aws.PARTITION}:lambda:{Aws.REGION}:{Aws.ACCOUNT_ID}:function:*",
        ],
    )


def delegated_admin_policy_document(scope, id):
    delegated_admin_policy = iam.Policy(
        scope,
        id,
        statements=[
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["organizations:ListDelegatedAdministrators"],
                resources=["*"],
            )
        ],
    )
    # add supression for *
    delegated_admin_policy.node.default_child.cfn_options.metadata = (
        suppress_delegated_admin_policy()
    )

    return delegated_admin_policy


def create_orchestrator_policy(
    scope,
    pipeline_stack_name,
    ecr_repo_name,
    blueprint_repository_bucket,
    assets_s3_bucket_name,
):
    orchestrator_policy = iam.Policy(
        scope,
        "lambdaOrchestratorPolicy",
        statements=[
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "cloudformation:CreateStack",
                    "cloudformation:DeleteStack",
                    "cloudformation:UpdateStack",
                    "cloudformation:DescribeStacks",
                    "cloudformation:ListStackResources",
                ],
                resources=[
                    (
                        f"arn:{Aws.PARTITION}:cloudformation:{Aws.REGION}:"
                        f"{Aws.ACCOUNT_ID}:stack/{pipeline_stack_name}*/*"
                    ),
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
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
                    "iam:UntagRole",
                    "iam:TagRole",
                ],
                resources=[
                    f"arn:{Aws.PARTITION}:iam::{Aws.ACCOUNT_ID}:role/{pipeline_stack_name}*"
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ecr:CreateRepository",
                    "ecr:DescribeRepositories",  # NOSONAR: permission needs to be repeated for clarity
                ],
                resources=[
                    (
                        f"arn:{Aws.PARTITION}:ecr:{Aws.REGION}:"
                        f"{Aws.ACCOUNT_ID}:repository/{ecr_repo_name}"
                    )
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "codebuild:CreateProject",
                    "codebuild:DeleteProject",
                    "codebuild:BatchGetProjects",
                ],
                resources=[
                    (
                        f"arn:{Aws.PARTITION}:codebuild:{Aws.REGION}:"
                        f"{Aws.ACCOUNT_ID}:project/ContainerFactory*"
                    ),
                    (
                        f"arn:{Aws.PARTITION}:codebuild:{Aws.REGION}:"
                        f"{Aws.ACCOUNT_ID}:project/VerifySagemaker*"
                    ),
                    f"arn:{Aws.PARTITION}:codebuild:{Aws.REGION}:{Aws.ACCOUNT_ID}:report-group/*",
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
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
                    "lambda:TagResource",
                ],
                resources=[
                    f"arn:{Aws.PARTITION}:lambda:{Aws.REGION}:{Aws.ACCOUNT_ID}:layer:*",
                    f"arn:{Aws.PARTITION}:lambda:{Aws.REGION}:{Aws.ACCOUNT_ID}:function:*",
                ],
            ),
            s3_policy_read(
                [
                    blueprint_repository_bucket.bucket_arn,
                    f"arn:{Aws.PARTITION}:s3:::{assets_s3_bucket_name}",
                    blueprint_repository_bucket.arn_for_objects("*"),
                    f"arn:{Aws.PARTITION}:s3:::{assets_s3_bucket_name}/*",
                ]
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "servicecatalog:CreateApplication",
                    "servicecatalog:GetApplication",
                    "servicecatalog:UpdateApplication",
                    "servicecatalog:DeleteApplication",
                    "servicecatalog:CreateAttributeGroup",
                    "servicecatalog:GetAttributeGroup",
                    "servicecatalog:UpdateAttributeGroup",
                    "servicecatalog:DeleteAttributeGroup",
                    "servicecatalog:AssociateResource",
                    "servicecatalog:DisassociateResource",
                    "servicecatalog:AssociateAttributeGroup",
                    "servicecatalog:DisassociateAttributeGroup",
                    "servicecatalog:TagResource",
                ],
                resources=[
                    f"arn:{Aws.PARTITION}:servicecatalog:{Aws.REGION}:{Aws.ACCOUNT_ID}:/applications/*",
                    f"arn:{Aws.PARTITION}:servicecatalog:{Aws.REGION}:{Aws.ACCOUNT_ID}:/attribute-groups/*",
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "codepipeline:CreatePipeline",
                    "codepipeline:UpdatePipeline",
                    "codepipeline:DeletePipeline",
                    "codepipeline:GetPipeline",
                    "codepipeline:GetPipelineState",
                    "codepipeline:TagResource",
                    "codepipeline:UntagResource",
                ],
                resources=[
                    (
                        f"arn:{Aws.PARTITION}:codepipeline:{Aws.REGION}:"
                        f"{Aws.ACCOUNT_ID}:{pipeline_stack_name}*"
                    )
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "apigateway:POST",
                    "apigateway:PATCH",
                    "apigateway:DELETE",
                    "apigateway:GET",
                    "apigateway:PUT",
                ],
                resources=[
                    f"arn:{Aws.PARTITION}:apigateway:{Aws.REGION}::/restapis/*",
                    f"arn:{Aws.PARTITION}:apigateway:{Aws.REGION}::/restapis",
                    f"arn:{Aws.PARTITION}:apigateway:{Aws.REGION}::/account",
                    f"arn:{Aws.PARTITION}:apigateway:{Aws.REGION}::/usageplans",
                    f"arn:{Aws.PARTITION}:apigateway:{Aws.REGION}::/usageplans/*",
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogGroup",
                    "logs:DescribeLogGroups",
                ],
                resources=[
                    f"arn:{Aws.PARTITION}:logs:{Aws.REGION}:{Aws.ACCOUNT_ID}:log-group:*",
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:CreateBucket",
                    "s3:PutEncryptionConfiguration",
                    "s3:PutBucketVersioning",
                    "s3:PutBucketPublicAccessBlock",
                    "s3:PutBucketLogging",
                    "s3:GetBucketPolicy",
                    "s3:PutBucketPolicy",
                    "s3:DeleteBucketPolicy",
                ],
                resources=[f"arn:{Aws.PARTITION}:s3:::*"],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:PutObject",  # NOSONAR: permission needs to be repeated for clarity
                ],
                resources=[f"arn:{Aws.PARTITION}:s3:::{assets_s3_bucket_name}/*"],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
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
                        f"arn:{Aws.PARTITION}:sns:{Aws.REGION}:{Aws.ACCOUNT_ID}:"
                        f"{pipeline_stack_name}*-*PipelineNotification*"
                    )
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "events:PutRule",
                    "events:DescribeRule",
                    "events:PutTargets",
                    "events:RemoveTargets",
                    "events:DeleteRule",
                    "events:PutEvents",
                ],
                resources=[
                    f"arn:{Aws.PARTITION}:events:{Aws.REGION}:{Aws.ACCOUNT_ID}:rule/*",
                    f"arn:{Aws.PARTITION}:events:{Aws.REGION}:{Aws.ACCOUNT_ID}:event-bus/*",
                ],
            ),
            # SageMaker Model Card permissions
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    # to perform model card operations
                    "sagemaker:CreateModelCard",
                    "sagemaker:DescribeModelCard",
                    "sagemaker:UpdateModelCard",
                    "sagemaker:DeleteModelCard",
                    "sagemaker:CreateModelCardExportJob",
                    "sagemaker:DescribeModelCardExportJob",
                    "sagemaker:DescribeModel",
                    # to extract training details information
                    "sagemaker:DescribeTrainingJob",
                ],
                resources=[
                    f"arn:{Aws.PARTITION}:sagemaker:{Aws.REGION}:{Aws.ACCOUNT_ID}:model-card/*",
                    f"arn:{Aws.PARTITION}:sagemaker:{Aws.REGION}:{Aws.ACCOUNT_ID}:model/*",
                    f"arn:{Aws.PARTITION}:sagemaker:{Aws.REGION}:{Aws.ACCOUNT_ID}:training-job/*",
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["sagemaker:ListModelCards", "sagemaker:Search"],
                # ListModelCards/sagemaker:Search do not have a scoped-down resource
                resources=[
                    "*",
                ],
            ),
        ],
    )

    return orchestrator_policy


def create_invoke_lambda_policy(lambda_functions_list):
    return iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        actions=[
            "lambda:InvokeFunction"
        ],  # NOSONAR: permission needs to be repeated for clarity
        resources=lambda_functions_list,
    )
