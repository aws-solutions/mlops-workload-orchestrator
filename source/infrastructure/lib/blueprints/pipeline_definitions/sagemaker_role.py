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
from aws_cdk import Aspects, Aws, aws_iam as iam
from lib.blueprints.aspects.conditional_resource import ConditionalResources

from lib.blueprints.pipeline_definitions.iam_policies import (
    ecr_policy_document,
    kms_policy_document,
    sagemaker_policy_statement,
    sagemaker_monitor_policy_statement,
    sagemaker_tags_policy_statement,
    sagemaker_logs_metrics_policy_document,
    s3_policy_read,
    s3_policy_write,
    pass_role_policy_statement,
    get_role_policy_statement,
    model_registry_policy_document,
)


def create_sagemaker_role(
    scope,  # NOSONAR:S107 this function is designed to take many arguments
    id,
    custom_algorithms_ecr_arn,
    kms_key_arn,
    model_package_group_name,
    assets_bucket_name,
    input_bucket_name,
    input_s3_location,
    output_s3_location,
    ecr_repo_arn_provided_condition,
    kms_key_arn_provided_condition,
    model_registry_provided_condition,
    is_realtime_pipeline=False,
    endpoint_name=None,
    endpoint_name_provided=None,
):
    # create optional policies
    ecr_policy = ecr_policy_document(scope, "MLOpsECRPolicy", custom_algorithms_ecr_arn)
    kms_policy = kms_policy_document(scope, "MLOpsKmsPolicy", kms_key_arn)
    model_registry = model_registry_policy_document(
        scope, "ModelRegistryPolicy", model_package_group_name
    )

    # add conditions to KMS and ECR policies
    Aspects.of(kms_policy).add(ConditionalResources(kms_key_arn_provided_condition))
    Aspects.of(ecr_policy).add(ConditionalResources(ecr_repo_arn_provided_condition))
    Aspects.of(model_registry).add(
        ConditionalResources(model_registry_provided_condition)
    )

    # create sagemaker role
    role = iam.Role(
        scope, id, assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com")
    )

    # permissions to create sagemaker resources
    sagemaker_policy = sagemaker_policy_statement(
        is_realtime_pipeline, endpoint_name, endpoint_name_provided
    )

    # sagemaker tags permissions
    sagemaker_tags_policy = sagemaker_tags_policy_statement()
    # logs permissions
    logs_policy = sagemaker_logs_metrics_policy_document(scope, "LogsMetricsPolicy")
    # S3 permissions
    s3_read = s3_policy_read(
        list(
            set(
                [
                    f"arn:{Aws.PARTITION}:s3:::{assets_bucket_name}",
                    f"arn:{Aws.PARTITION}:s3:::{assets_bucket_name}/*",
                    f"arn:{Aws.PARTITION}:s3:::{input_bucket_name}",
                    f"arn:{Aws.PARTITION}:s3:::{input_s3_location}",
                ]
            )
        )
    )
    s3_write = s3_policy_write(
        [
            f"arn:{Aws.PARTITION}:s3:::{output_s3_location}/*",
        ]
    )
    # IAM PassRole permission
    pass_role_policy = pass_role_policy_statement(role)
    # IAM GetRole permission
    get_role_policy = get_role_policy_statement(role)

    # add policy statements
    role.add_to_policy(sagemaker_policy)
    role.add_to_policy(sagemaker_tags_policy)
    logs_policy.attach_to_role(role)
    role.add_to_policy(s3_read)
    role.add_to_policy(s3_write)
    role.add_to_policy(pass_role_policy)
    role.add_to_policy(get_role_policy)

    # attach the conditional policies
    kms_policy.attach_to_role(role)
    ecr_policy.attach_to_role(role)
    model_registry.attach_to_role(role)

    return role
