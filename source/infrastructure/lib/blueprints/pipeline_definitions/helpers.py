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
from aws_cdk import Aws, aws_iam as iam

logs_str = ":logs:"


def pipeline_permissions(pipeline, assets_bucket):
    """
    pipeline_permissions adds necessary permissions for a codepipeline to operate. A helper function to attach
    permissions to different types of pipeline created based on user parameters.

    :pipeline: Codepipeilne instsance in a form of a CDK object
    :assets_bucket: the bucket cdk object where pipeline assets are stored
    :return: nothing
    """
    pipeline.add_to_role_policy(
        iam.PolicyStatement(
            actions=[
                "s3:GetObject",
                "lambda:GetFunctionConfiguration",
                "logs:DescribeLogGroups",
            ],
            resources=[
                assets_bucket.arn_for_objects("*"),
                "arn:"
                + Aws.PARTITION
                + ":lambda:"
                + Aws.REGION
                + ":"
                + Aws.ACCOUNT_ID
                + ":function:*",
                "arn:"
                + Aws.PARTITION
                + logs_str
                + Aws.REGION
                + ":"
                + Aws.ACCOUNT_ID
                + ":log-group:*",
            ],
        )
    )


def add_logs_policy(function_role):
    function_role.add_to_policy(
        iam.PolicyStatement(
            actions=[
                "logs:CreateLogStream",
                "logs:PutLogEvents",
            ],
            resources=[
                "arn:"
                + Aws.PARTITION
                + logs_str
                + Aws.REGION
                + ":"
                + Aws.ACCOUNT_ID
                + ":log-group:/aws/lambda/*",
                "arn:"
                + Aws.PARTITION
                + logs_str
                + Aws.REGION
                + ":"
                + Aws.ACCOUNT_ID
                + ":log-group:*:log-stream:*",
            ],
        )
    )
    function_role.add_to_policy(
        iam.PolicyStatement(
            actions=["logs:CreateLogGroup"],
            resources=[
                "arn:"
                + Aws.PARTITION
                + logs_str
                + Aws.REGION
                + ":"
                + Aws.ACCOUNT_ID
                + ":*"
            ],
        )
    )


def suppress_pipeline_policy():
    return {
        "cfn_nag": {
            "rules_to_suppress": [
                {
                    "id": "W12",
                    "reason": (
                        "The codepipeline permissions PutJobSuccessResult and PutJobFailureResult "
                        "are not able to be bound to resources."
                    ),
                }
            ]
        }
    }


def suppress_list_function_policy():
    return {
        "cfn_nag": {
            "rules_to_suppress": [
                {
                    "id": "W12",
                    "reason": "The lambda permission ListFunctions is not able to be bound to resources.",
                }
            ]
        }
    }


def suppress_s3_access_policy():
    return {
        "cfn_nag": {
            "rules_to_suppress": [
                {"id": "W35", "reason": "This is the access bucket"},
            ]
        }
    }


def suppress_pipeline_bucket():
    return {
        "cfn_nag": {
            "rules_to_suppress": [
                {
                    "id": "W51",
                    "reason": (
                        "This bucket does not need bucket policy. Permissions write to this bucket are set with IAM."
                    ),
                },
                {
                    "id": "W35",
                    "reason": (
                        "This bucket is auto generated by CDK's codepipeline construct to handle its assets."
                        " It does not need access logging"
                    ),
                },
            ]
        }
    }


def suppress_iam_complex():
    return {
        "cfn_nag": {
            "rules_to_suppress": [
                {
                    "id": "W76",
                    "reason": "Complex iam policy is required for this functionality",
                }
            ]
        }
    }


def suppress_sns():
    return {
        "cfn_nag": {
            "rules_to_suppress": [
                {
                    "id": "W47",
                    "reason": "This SNS topic does not contain any sensitive information.",
                }
            ]
        }
    }


def suppress_ecr_policy():
    return {
        "cfn_nag": {
            "rules_to_suppress": [
                {
                    "id": "W12",
                    "reason": "This ECR Policy (ecr:GetAuthorizationToken) can not have a restricted resource.",
                }
            ]
        }
    }


def suppress_cloudwatch_policy():
    return {
        "cfn_nag": {
            "rules_to_suppress": [
                {
                    "id": "W12",
                    "reason": "The cloudwatch:PutMetricData can not have a restricted resource.",
                }
            ]
        }
    }


def suppress_cloudformation_action():
    return {
        "cfn_nag": {
            "rules_to_suppress": [
                {
                    "id": "F4",
                    "reason": (
                        "The cloudformation action is granted PassRole action with * resources to deploy "
                        "different resources by different MLOps pipelines."
                    ),
                },
                {
                    "id": "F39",
                    "reason": (
                        "The cloudformation action is granted admin permissions to deploy different resources by "
                        "different MLOps pipelines. Roles are defined by the pipelines' cloudformation templates."
                    ),
                },
                {
                    "id": "W12",
                    "reason": (
                        "This cloudformation action's deployement roel needs * resource to deploy different resources"
                        " by MLOps pipelines. Specific resources are declared in the roles defined by each pipeline."
                    ),
                },
            ]
        }
    }


def suppress_lambda_policies():
    return {
        "cfn_nag": {
            "rules_to_suppress": [
                {
                    "id": "W89",
                    "reason": "The lambda function does not need to be attached to a vpc.",
                },
                {
                    "id": "W58",
                    "reason": "The lambda functions role already has permissions to write cloudwatch logs",
                },
                {
                    "id": "W92",
                    "reason": "The lambda function does need to define ReservedConcurrentExecutions",
                },
            ]
        }
    }


def suppress_delegated_admin_policy():
    return {
        "cfn_nag": {
            "rules_to_suppress": [
                {
                    "id": "W12",
                    "reason": "organizations:ListDelegatedAdministrators can not have a restricted resource.",
                }
            ]
        }
    }
