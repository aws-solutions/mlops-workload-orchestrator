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
from aws_cdk import (
    aws_s3 as s3,
    core,
)
from lib.blueprints.byom.pipeline_definitions.deploy_actions import (
    create_data_baseline_job,
    create_invoke_lambda_custom_resource,
)
from lib.blueprints.byom.pipeline_definitions.templates_parameters import (
    create_blueprint_bucket_name_parameter,
    create_assets_bucket_name_parameter,
    create_baseline_job_name_parameter,
    create_monitoring_schedule_name_parameter,
    create_endpoint_name_parameter,
    create_baseline_job_output_location_parameter,
    create_monitoring_output_location_parameter,
    create_instance_type_parameter,
    create_training_data_parameter,
    create_monitoring_type_parameter,
    create_instance_volume_size_parameter,
    create_max_runtime_seconds_parameter,
    create_kms_key_arn_parameter,
    create_kms_key_arn_provided_condition,
    create_data_capture_bucket_name_parameter,
    create_data_capture_location_parameter,
    create_schedule_expression_parameter,
    create_algorithm_image_uri_parameter,
    create_baseline_output_bucket_name_parameter,
)

from lib.blueprints.byom.pipeline_definitions.sagemaker_monitor_role import create_sagemaker_monitor_role
from lib.blueprints.byom.pipeline_definitions.sagemaker_monitoring_schedule import create_sagemaker_monitoring_scheduale


class ModelMonitorStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Parameteres #
        blueprint_bucket_name = create_blueprint_bucket_name_parameter(self)
        assets_bucket_name = create_assets_bucket_name_parameter(self)
        endpoint_name = create_endpoint_name_parameter(self)
        baseline_job_output_location = create_baseline_job_output_location_parameter(self)
        training_data = create_training_data_parameter(self)
        instance_type = create_instance_type_parameter(self)
        instance_volume_size = create_instance_volume_size_parameter(self)
        monitoring_type = create_monitoring_type_parameter(self)
        max_runtime_seconds = create_max_runtime_seconds_parameter(self)
        kms_key_arn = create_kms_key_arn_parameter(self)
        baseline_job_name = create_baseline_job_name_parameter(self)
        monitoring_schedule_name = create_monitoring_schedule_name_parameter(self)
        data_capture_bucket = create_data_capture_bucket_name_parameter(self)
        baseline_output_bucket = create_baseline_output_bucket_name_parameter(self)
        data_capture_s3_location = create_data_capture_location_parameter(self)
        monitoring_output_location = create_monitoring_output_location_parameter(self)
        schedule_expression = create_schedule_expression_parameter(self)
        image_uri = create_algorithm_image_uri_parameter(self)

        # conditions
        kms_key_arn_provided = create_kms_key_arn_provided_condition(self, kms_key_arn)

        # Resources #
        assets_bucket = s3.Bucket.from_bucket_name(self, "AssetsBucket", assets_bucket_name.value_as_string)
        # getting blueprint bucket object from its name - will be used later in the stack
        blueprint_bucket = s3.Bucket.from_bucket_name(self, "BlueprintBucket", blueprint_bucket_name.value_as_string)

        # creating data baseline job
        baseline_job_lambda = create_data_baseline_job(
            self,
            blueprint_bucket,
            assets_bucket,
            baseline_job_name.value_as_string,
            training_data.value_as_string,
            baseline_job_output_location.value_as_string,
            endpoint_name.value_as_string,
            instance_type.value_as_string,
            instance_volume_size.value_as_string,
            max_runtime_seconds.value_as_string,
            core.Fn.condition_if(
                kms_key_arn_provided.logical_id, kms_key_arn.value_as_string, core.Aws.NO_VALUE
            ).to_string(),
            kms_key_arn_provided,
            core.Aws.STACK_NAME,
        )

        # create custom resource to invoke the batch transform lambda
        invoke_lambda_custom_resource = create_invoke_lambda_custom_resource(
            self,
            "InvokeBaselineLambda",
            baseline_job_lambda.function_arn,
            baseline_job_lambda.function_name,
            blueprint_bucket,
            {
                "Resource": "InvokeLambda",
                "function_name": baseline_job_lambda.function_name,
                "assets_bucket_name": assets_bucket_name.value_as_string,
                "endpoint_name": endpoint_name.value_as_string,
                "instance_type": instance_type.value_as_string,
                "baseline_job_output_location": baseline_job_output_location.value_as_string,
                "training_data": training_data.value_as_string,
                "instance_volume_size": instance_volume_size.value_as_string,
                "monitoring_schedule_name": monitoring_schedule_name.value_as_string,
                "baseline_job_name": baseline_job_name.value_as_string,
                "max_runtime_seconds": max_runtime_seconds.value_as_string,
                "data_capture_s3_location": data_capture_s3_location.value_as_string,
                "monitoring_output_location": monitoring_output_location.value_as_string,
                "schedule_expression": schedule_expression.value_as_string,
                "image_uri": image_uri.value_as_string,
                "kms_key_arn": kms_key_arn.value_as_string,
            },
        )

        # add dependency on baseline lambda
        invoke_lambda_custom_resource.node.add_dependency(baseline_job_lambda)

        # creating monitoring schedule
        sagemaker_role = create_sagemaker_monitor_role(
            self,
            "MLOpsSagemakerMonitorRole",
            kms_key_arn=kms_key_arn.value_as_string,
            assets_bucket_name=assets_bucket_name.value_as_string,
            data_capture_bucket=data_capture_bucket.value_as_string,
            data_capture_s3_location=data_capture_s3_location.value_as_string,
            baseline_output_bucket=baseline_output_bucket.value_as_string,
            baseline_job_output_location=baseline_job_output_location.value_as_string,
            output_s3_location=monitoring_output_location.value_as_string,
            kms_key_arn_provided_condition=kms_key_arn_provided,
            baseline_job_name=baseline_job_name.value_as_string,
            monitoring_schedual_name=monitoring_schedule_name.value_as_string,
        )

        # create Sagemaker monitoring Schedule
        sagemaker_monitoring_scheduale = create_sagemaker_monitoring_scheduale(
            self,
            "MonitoringSchedule",
            monitoring_schedule_name.value_as_string,
            endpoint_name.value_as_string,
            baseline_job_name.value_as_string,
            baseline_job_output_location.value_as_string,
            schedule_expression.value_as_string,
            monitoring_output_location.value_as_string,
            instance_type.value_as_string,
            instance_volume_size.value_as_number,
            max_runtime_seconds.value_as_number,
            core.Fn.condition_if(
                kms_key_arn_provided.logical_id, kms_key_arn.value_as_string, core.Aws.NO_VALUE
            ).to_string(),
            sagemaker_role.role_arn,
            image_uri.value_as_string,
            core.Aws.STACK_NAME,
        )

        # add dependency on invoke_lambda_custom_resource
        sagemaker_monitoring_scheduale.node.add_dependency(invoke_lambda_custom_resource)

        # Outputs #
        core.CfnOutput(
            self,
            id="DataBaselineJobName",
            value=baseline_job_name.value_as_string,
        )
        core.CfnOutput(
            self,
            id="MonitoringScheduleJobName",
            value=monitoring_schedule_name.value_as_string,
        )
        core.CfnOutput(
            self,
            id="MonitoringScheduleType",
            value=monitoring_type.value_as_string,
        )
        core.CfnOutput(
            self,
            id="BaselineJobOutputLocation",
            value=(
                f"https://s3.console.aws.amazon.com/s3/buckets/{baseline_job_output_location.value_as_string}"
                f"/{baseline_job_name.value_as_string}/"
            ),
        )
        core.CfnOutput(
            self,
            id="MonitoringScheduleOutputLocation",
            value=(
                f"https://s3.console.aws.amazon.com/s3/buckets/{monitoring_output_location.value_as_string}/"
                f"{endpoint_name.value_as_string}/{monitoring_schedule_name.value_as_string}/"
            ),
        )
        core.CfnOutput(
            self,
            id="MonitoredSagemakerEndpoint",
            value=endpoint_name.value_as_string,
        )
        core.CfnOutput(
            self,
            id="DataCaptureLocation",
            value=(
                f"https://s3.console.aws.amazon.com/s3/buckets/{data_capture_s3_location.value_as_string}"
                f"/{endpoint_name.value_as_string}/"
            ),
        )
