# #####################################################################################################################
#  Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                            #
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
from aws_cdk import aws_iam as iam, core
from lib.blueprints.byom.pipeline_definitions.helpers import suppress_ecr_policy, suppress_cloudwatch_policy


def sagemaker_policiy_statement():
    return iam.PolicyStatement(
        actions=[
            "sagemaker:CreateModel",
            "sagemaker:DescribeModel",
            "sagemaker:DeleteModel",
            "sagemaker:CreateModel",
            "sagemaker:CreateEndpointConfig",
            "sagemaker:DescribeEndpointConfig",
            "sagemaker:DeleteEndpointConfig",
            "sagemaker:CreateEndpoint",
            "sagemaker:DescribeEndpoint",
            "sagemaker:DeleteEndpoint",
        ],
        resources=[
            (
                f"arn:{core.Aws.PARTITION}:sagemaker:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:model/"
                f"mlopssagemakermodel*"
            ),
            (
                f"arn:{core.Aws.PARTITION}:sagemaker:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:endpoint-config/"
                f"mlopssagemakerendpointconfig*"
            ),
            (
                f"arn:{core.Aws.PARTITION}:sagemaker:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:endpoint/"
                f"mlopssagemakerendpoint*"
            ),
        ],
    )


def sagemaker_baseline_job_policy(baseline_job_name):
    return iam.PolicyStatement(
        actions=[
            "sagemaker:CreateProcessingJob",
            "sagemaker:DescribeProcessingJob",
            "sagemaker:StopProcessingJob",
            "sagemaker:DeleteProcessingJob",
        ],
        resources=[
            (
                f"arn:{core.Aws.PARTITION}:sagemaker:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:"
                f"processing-job/{baseline_job_name}"
            ),
        ],
    )


def batch_transform_policy():
    return iam.PolicyStatement(
        actions=[
            "sagemaker:CreateTransformJob",
        ],
        resources=[
            (
                f"arn:{core.Aws.PARTITION}:sagemaker:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:"
                f"transform-job/mlopssagemakermodel-*-batch-transform-*"
            ),
        ],
    )


def create_service_role(scope, id, service, description):
    return iam.Role(
        scope,
        id,
        assumed_by=iam.ServicePrincipal(service),
        description=description,
    )


def sagemaker_monitor_policiy_statement(baseline_job_name, monitoring_schedual_name):
    return iam.PolicyStatement(
        actions=[
            "sagemaker:DescribeEndpointConfig",
            "sagemaker:DescribeEndpoint",
            "sagemaker:CreateMonitoringSchedule",
            "sagemaker:DescribeMonitoringSchedule",
            "sagemaker:StopMonitoringSchedule",
            "sagemaker:DeleteMonitoringSchedule",
            "sagemaker:DescribeProcessingJob",
        ],
        resources=[
            (
                f"arn:{core.Aws.PARTITION}:sagemaker:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:endpoint-config/"
                f"mlopssagemakerendpointconfig*"
            ),
            (
                f"arn:{core.Aws.PARTITION}:sagemaker:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:endpoint/"
                f"mlopssagemakerendpoint*"
            ),
            (
                f"arn:{core.Aws.PARTITION}:sagemaker:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:"
                f"monitoring-schedule/{monitoring_schedual_name}"
            ),
            (
                f"arn:{core.Aws.PARTITION}:sagemaker:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:"
                f"processing-job/{baseline_job_name}"
            ),
        ],
    )


def sagemaker_tags_policy_statement():
    return iam.PolicyStatement(
        actions=[
            "sagemaker:AddTags",
            "sagemaker:DeleteTags",
        ],
        resources=[f"arn:{core.Aws.PARTITION}:sagemaker:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:*"],
    )


def sagemaker_logs_metrics_policy_document(scope, id):
    policy = iam.Policy(
        scope,
        id,
        statements=[
            iam.PolicyStatement(
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:DescribeLogStreams",
                    "logs:GetLogEvents",
                    "logs:PutLogEvents",
                ],
                resources=[
                    f"arn:{core.Aws.PARTITION}:logs:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:log-group:/aws/sagemaker/*"
                ],
            ),
            iam.PolicyStatement(
                actions=[
                    "cloudwatch:PutMetricData",
                ],
                resources=["*"],
            ),
        ],
    )
    policy.node.default_child.cfn_options.metadata = suppress_cloudwatch_policy()

    return policy


def s3_policy_read_write(resources_list):
    return iam.PolicyStatement(
        actions=["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
        resources=resources_list,
    )


def s3_policy_read(resources_list):
    return iam.PolicyStatement(
        actions=["s3:GetObject", "s3:ListBucket"],
        resources=resources_list,
    )


def s3_policy_write(resources_list):
    return iam.PolicyStatement(
        actions=["s3:PutObject"],
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
                    "ecr:DescribeRepositories",
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


def cloudformation_stackset_policy(stack_name):
    return iam.PolicyStatement(
        actions=[
            "cloudformation:DescribeStackSet",
            "cloudformation:DescribeStackInstance",
            "cloudformation:CreateStackSet",
        ],
        resources=[
            f"arn:aws:cloudformation:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:stackset/{stack_name}:*",
            "arn:aws:cloudformation:*::type/resource/*",
        ],
    )


def cloudformation_stackset_instances_policy(stack_name):
    return iam.PolicyStatement(
        actions=[
            "cloudformation:CreateStackInstances",
            "cloudformation:DeleteStackInstances",
            "cloudformation:UpdateStackSet",
        ],
        resources=[
            f"arn:aws:cloudformation::{core.Aws.ACCOUNT_ID}:stackset-target/{stack_name}:*",
            f"arn:aws:cloudformation:{core.Aws.REGION}::type/resource/*",
            f"arn:aws:cloudformation:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:stackset/{stack_name}:*",
        ],
    )