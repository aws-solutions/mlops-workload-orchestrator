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
    kms_policy_document,
    sagemaker_monitor_policy_statement,
    sagemaker_tags_policy_statement,
    sagemaker_logs_metrics_policy_document,
    s3_policy_read,
    s3_policy_write,
    pass_role_policy_statement,
    get_role_policy_statement,
)


def create_sagemaker_monitor_role(
    scope,  # NOSONAR:S107 this function is designed to take many arguments
    id,
    kms_key_arn,
    assets_bucket_name,
    data_capture_bucket,
    data_capture_s3_location,
    baseline_output_bucket,
    baseline_job_output_location,
    output_s3_location,
    kms_key_arn_provided_condition,
    baseline_job_name,
    monitoring_schedule_name,
    endpoint_name,
    model_monitor_ground_truth_bucket,
    model_monitor_ground_truth_input,
    monitoring_type,
):
    # create optional policies
    kms_policy = kms_policy_document(scope, "MLOpsKmsPolicy", kms_key_arn)

    # add conditions to KMS and ECR policies
    Aspects.of(kms_policy).add(ConditionalResources(kms_key_arn_provided_condition))

    # create sagemaker role
    role = iam.Role(
        scope, id, assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com")
    )

    # permissions to create sagemaker resources
    sagemaker_policy = sagemaker_monitor_policy_statement(
        baseline_job_name, monitoring_schedule_name, endpoint_name, monitoring_type
    )

    # sagemaker tags permissions
    sagemaker_tags_policy = sagemaker_tags_policy_statement()
    # logs/metrics permissions
    logs_metrics_policy = sagemaker_logs_metrics_policy_document(
        scope, "SagemakerLogsMetricsPolicy"
    )
    # S3 permissions
    s3_read_resources = list(
        set(  # set is used since a same bucket can be used more than once
            [
                f"arn:{Aws.PARTITION}:s3:::{assets_bucket_name}",
                f"arn:{Aws.PARTITION}:s3:::{assets_bucket_name}/*",
                f"arn:{Aws.PARTITION}:s3:::{data_capture_bucket}",
                f"arn:{Aws.PARTITION}:s3:::{data_capture_s3_location}/*",
                f"arn:{Aws.PARTITION}:s3:::{baseline_output_bucket}",
                f"arn:{Aws.PARTITION}:s3:::{baseline_job_output_location}/*",
            ]
        )
    )

    # add permissions to read ground truth data (only for ModelQuality monitor)
    if model_monitor_ground_truth_bucket:
        s3_read_resources.extend(
            [
                f"arn:{Aws.PARTITION}:s3:::{model_monitor_ground_truth_bucket}",
                f"arn:{Aws.PARTITION}:s3:::{model_monitor_ground_truth_input}/*",
            ]
        )
    s3_read = s3_policy_read(s3_read_resources)
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
    role.add_to_policy(s3_read)
    role.add_to_policy(s3_write)
    role.add_to_policy(pass_role_policy)
    role.add_to_policy(get_role_policy)

    # attach he logs/metrics policy document
    logs_metrics_policy.attach_to_role(role)
    # attach the conditional policies
    kms_policy.attach_to_role(role)

    return role
