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
from aws_cdk import (
    aws_s3 as s3,
    core,
)
from lib.blueprints.byom.pipeline_definitions.deploy_actions import (
    create_baseline_job_lambda,
    sagemaker_layer,
    create_invoke_lambda_custom_resource,
)
from lib.blueprints.byom.pipeline_definitions.templates_parameters import (
    ParameteresFactory as pf,
    ConditionsFactory as cf,
)

from lib.blueprints.byom.pipeline_definitions.sagemaker_monitor_role import create_sagemaker_monitor_role
from lib.blueprints.byom.pipeline_definitions.sagemaker_model_monitor_construct import SageMakerModelMonitor


class ModelMonitorStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, monitoring_type: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # validate the provided monitoring_type
        if monitoring_type not in ["DataQuality", "ModelQuality"]:
            raise ValueError(
                (
                    f"The {monitoring_type} is not valid. Currently supported Monitoring Types are: "
                    f"['DataQuality'|'ModelQuality']"
                )
            )

        # Baseline/Monitor attributes, this will be updated based on the monitoring_type
        self.baseline_attributes = dict()
        self.monitor_attributes = dict()

        # Parameteres #
        blueprint_bucket_name = pf.create_blueprint_bucket_name_parameter(self)
        assets_bucket_name = pf.create_assets_bucket_name_parameter(self)
        endpoint_name = pf.create_endpoint_name_parameter(self)
        baseline_job_output_location = pf.create_baseline_job_output_location_parameter(self)
        baseline_data = pf.create_baseline_data_parameter(self)
        instance_type = pf.create_instance_type_parameter(self)
        instance_count = pf.create_instance_count_parameter(self)
        instance_volume_size = pf.create_instance_volume_size_parameter(self)
        baseline_max_runtime_seconds = pf.create_baseline_max_runtime_seconds_parameter(self)
        monitor_max_runtime_seconds = pf.create_monitor_max_runtime_seconds_parameter(self, "ModelQuality")
        kms_key_arn = pf.create_kms_key_arn_parameter(self)
        baseline_job_name = pf.create_baseline_job_name_parameter(self)
        monitoring_schedule_name = pf.create_monitoring_schedule_name_parameter(self)
        data_capture_bucket = pf.create_data_capture_bucket_name_parameter(self)
        baseline_output_bucket = pf.create_baseline_output_bucket_name_parameter(self)
        data_capture_s3_location = pf.create_data_capture_location_parameter(self)
        monitoring_output_location = pf.create_monitoring_output_location_parameter(self)
        schedule_expression = pf.create_schedule_expression_parameter(self)
        image_uri = pf.create_algorithm_image_uri_parameter(self)

        # add ModelQuality specific parameters/conditions, and update self.baseline_attributes/self.monitor_attributes
        if monitoring_type == "ModelQuality":
            self._add_model_quality_resources()

        # conditions
        kms_key_arn_provided = cf.create_kms_key_arn_provided_condition(self, kms_key_arn)

        # Resources #
        assets_bucket = s3.Bucket.from_bucket_name(self, "ImportedAssetsBucket", assets_bucket_name.value_as_string)
        # getting blueprint bucket object from its name - will be used later in the stack
        blueprint_bucket = s3.Bucket.from_bucket_name(
            self, "ImportedBlueprintBucket", blueprint_bucket_name.value_as_string
        )

        # create sagemaker layer
        sm_layer = sagemaker_layer(self, blueprint_bucket)

        # update Baseline attributes
        self.baseline_attributes.update(
            dict(
                monitoring_type=monitoring_type,
                baseline_job_name=baseline_job_name.value_as_string,
                baseline_data_location=baseline_data.value_as_string,
                baseline_job_output_location=baseline_job_output_location.value_as_string,
                endpoint_name=endpoint_name.value_as_string,
                instance_type=instance_type.value_as_string,
                instance_volume_size=instance_volume_size.value_as_string,
                max_runtime_seconds=baseline_max_runtime_seconds.value_as_string,
                kms_key_arn=core.Fn.condition_if(
                    kms_key_arn_provided.logical_id, kms_key_arn.value_as_string, core.Aws.NO_VALUE
                ).to_string(),
                kms_key_arn_provided_condition=kms_key_arn_provided,
                stack_name=core.Aws.STACK_NAME,
            )
        )
        # create baseline job lambda action
        baseline_job_lambda = create_baseline_job_lambda(
            self,
            blueprint_bucket=blueprint_bucket,
            assets_bucket=assets_bucket,
            sm_layer=sm_layer,
            **self.baseline_attributes,
        )

        # create custom resource to invoke the baseline job lambda
        # remove the condition from the custom resource properties. Otherwise, CFN will give an error
        del self.baseline_attributes["kms_key_arn_provided_condition"]
        invoke_lambda_custom_resource = create_invoke_lambda_custom_resource(
            scope=self,
            id="InvokeBaselineLambda",
            lambda_function_arn=baseline_job_lambda.function_arn,
            lambda_function_name=baseline_job_lambda.function_name,
            blueprint_bucket=blueprint_bucket,
            # add baseline attributes to the invoke lambda custom resource, so any change to these attributes
            # (via template update) will re-invoke the baseline lambda and re-calculate the baseline
            custom_resource_properties={
                "Resource": "InvokeLambda",
                "function_name": baseline_job_lambda.function_name,
                "assets_bucket_name": assets_bucket_name.value_as_string,
                **self.baseline_attributes,
            },
        )

        # add dependency on baseline lambda
        invoke_lambda_custom_resource.node.add_dependency(baseline_job_lambda)

        # creating monitoring schedule
        sagemaker_role = create_sagemaker_monitor_role(
            scope=self,
            id="MLOpsSagemakerMonitorRole",
            kms_key_arn=kms_key_arn.value_as_string,
            assets_bucket_name=assets_bucket_name.value_as_string,
            data_capture_bucket=data_capture_bucket.value_as_string,
            data_capture_s3_location=data_capture_s3_location.value_as_string,
            baseline_output_bucket=baseline_output_bucket.value_as_string,
            baseline_job_output_location=baseline_job_output_location.value_as_string,
            output_s3_location=monitoring_output_location.value_as_string,
            kms_key_arn_provided_condition=kms_key_arn_provided,
            baseline_job_name=baseline_job_name.value_as_string,
            monitoring_schedule_name=monitoring_schedule_name.value_as_string,
            endpoint_name=endpoint_name.value_as_string,
            model_monitor_ground_truth_input=None
            if monitoring_type == "DataQuality"
            else self.monitor_attributes["ground_truth_s3_uri"],
        )

        # resource tags
        resource_tags = [{"key": "stack-name", "value": core.Aws.STACK_NAME}]

        # update attributes
        self.monitor_attributes.update(
            dict(
                monitoring_schedule_name=monitoring_schedule_name.value_as_string,
                endpoint_name=endpoint_name.value_as_string,
                baseline_job_name=baseline_job_name.value_as_string,
                baseline_job_output_location=baseline_job_output_location.value_as_string,
                schedule_expression=schedule_expression.value_as_string,
                monitoring_output_location=monitoring_output_location.value_as_string,
                instance_type=instance_type.value_as_string,
                instance_count=instance_count.value_as_string,
                instance_volume_size=instance_volume_size.value_as_string,
                max_runtime_seconds=monitor_max_runtime_seconds.value_as_string,
                kms_key_arn=core.Fn.condition_if(
                    kms_key_arn_provided.logical_id, kms_key_arn.value_as_string, core.Aws.NO_VALUE
                ).to_string(),
                role_arn=sagemaker_role.role_arn,
                image_uri=image_uri.value_as_string,
                monitoring_type=monitoring_type,
                tags=resource_tags,
            )
        )
        # create Sagemaker monitoring Schedule
        sagemaker_monitor = SageMakerModelMonitor(self, f"{monitoring_type}Monitor", **self.monitor_attributes)

        # add job definition dependency on sagemaker role and invoke_lambda_custom_resource (so, the baseline job is created)
        sagemaker_monitor.job_definition.node.add_dependency(sagemaker_role)
        sagemaker_monitor.job_definition.node.add_dependency(invoke_lambda_custom_resource)

        # Outputs #
        core.CfnOutput(
            self,
            id="BaselineName",
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
            value=monitoring_type,
        )
        core.CfnOutput(
            self,
            id="BaselineJobOutput",
            value=f"https://s3.console.aws.amazon.com/s3/buckets/{baseline_job_output_location.value_as_string}/",
        )
        core.CfnOutput(
            self,
            id="MonitoringScheduleOutput",
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
            id="DataCaptureS3Location",
            value=(
                f"https://s3.console.aws.amazon.com/s3/buckets/{data_capture_s3_location.value_as_string}"
                f"/{endpoint_name.value_as_string}/"
            ),
        )

    def _add_model_quality_resources(self):
        """
        Adds ModelQuality specific parameters/conditions and updates self.baseline_attributes/self.monitor_attributes
        """
        # add baseline job attributes (they are different from Monitor attributes)
        baseline_inference_attribute = pf.create_inference_attribute_parameter(self, "Baseline")
        baseline_probability_attribute = pf.create_probability_attribute_parameter(self, "Baseline")
        ground_truth_attribute = pf.create_ground_truth_attribute_parameter(self)
        # add monitor attributes
        monitor_inference_attribute = pf.create_inference_attribute_parameter(self, "Monitor")
        monitor_probability_attribute = pf.create_probability_attribute_parameter(self, "Monitor")
        ground_truth_s3_uri = pf.create_ground_truth_s3_uri_parameter(self)
        # problem_type and probability_threshold_attribute are the same for both
        problem_type = pf.create_problem_type_parameter(self)
        probability_threshold_attribute = pf.create_probability_threshold_attribute_parameter(self)

        # add conditions (used by monitor)
        is_regression_or_multiclass_classification_problem = (
            cf.create_problem_type_regression_or_multiclass_classification_condition(self, problem_type)
        )
        is_binary_classification_problem = cf.create_problem_type_binary_classification_condition(self, problem_type)

        # add ModelQuality Baseline attributes
        self.baseline_attributes.update(
            dict(
                problem_type=problem_type.value_as_string,
                ground_truth_attribute=ground_truth_attribute.value_as_string,
                inference_attribute=baseline_inference_attribute.value_as_string,
                probability_attribute=baseline_probability_attribute.value_as_string,
                probability_threshold_attribute=probability_threshold_attribute.value_as_string,
            )
        )

        # add ModelQuality Monitor attributes
        self.monitor_attributes.update(
            dict(
                problem_type=problem_type.value_as_string,
                ground_truth_s3_uri=ground_truth_s3_uri.value_as_string,
                # inference_attribute is required for Regression/Multiclass Classification problems
                # probability_attribute/probability_threshold_attribute are not used
                inference_attribute=core.Fn.condition_if(
                    is_regression_or_multiclass_classification_problem.logical_id,
                    monitor_inference_attribute.value_as_string,
                    core.Aws.NO_VALUE,
                ).to_string(),
                # for a Binary Classification problem, we use probability_attribute and probability_threshold_attribute.
                # note: probability_attribute is the index of the predicted probability in the captured data by the
                # SageMaker endpoint. Tepically, probability_attribute="0" and probability_threshold_attribute="0.5"
                probability_attribute=core.Fn.condition_if(
                    is_binary_classification_problem.logical_id,
                    monitor_probability_attribute.value_as_string,
                    core.Aws.NO_VALUE,
                ).to_string(),
                probability_threshold_attribute=core.Fn.condition_if(
                    is_binary_classification_problem.logical_id,
                    probability_threshold_attribute.value_as_string,
                    core.Aws.NO_VALUE,
                ).to_string(),
            )
        )
