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
from constructs import Construct
from aws_cdk import Stack, Aws, Fn, CfnOutput, aws_s3 as s3
from lib.blueprints.pipeline_definitions.deploy_actions import (
    create_baseline_job_lambda,
    sagemaker_layer,
    create_invoke_lambda_custom_resource,
)
from lib.blueprints.pipeline_definitions.templates_parameters import (
    ParameteresFactory as pf,
    ConditionsFactory as cf,
)

from lib.blueprints.pipeline_definitions.sagemaker_monitor_role import (
    create_sagemaker_monitor_role,
)
from lib.blueprints.pipeline_definitions.sagemaker_model_monitor_construct import (
    SageMakerModelMonitor,
)


class ModelMonitorStack(Stack):
    def __init__(
        self, scope: Construct, id: str, monitoring_type: str, **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # validate the provided monitoring_type
        if monitoring_type not in [
            "DataQuality",
            "ModelQuality",
            "ModelBias",
            "ModelExplainability",
        ]:
            raise ValueError(
                (
                    f"The {monitoring_type} is not valid. Supported Monitoring Types are: "
                    f"'DataQuality'|'ModelQuality'|'ModelBias'|'ModelExplainability'"
                )
            )

        # Baseline/Monitor attributes, this will be updated based on the monitoring_type
        self.baseline_attributes = dict()
        self.monitor_attributes = dict()

        # Parameteres #
        self.monitoring_type = monitoring_type
        self.blueprint_bucket_name = pf.create_blueprint_bucket_name_parameter(self)
        self.assets_bucket_name = pf.create_assets_bucket_name_parameter(self)
        self.endpoint_name = pf.create_endpoint_name_parameter(self)
        self.baseline_job_output_location = (
            pf.create_baseline_job_output_location_parameter(self)
        )
        self.baseline_data = pf.create_baseline_data_parameter(self)
        self.instance_type = pf.create_instance_type_parameter(self)
        self.instance_count = pf.create_instance_count_parameter(self)
        self.instance_volume_size = pf.create_instance_volume_size_parameter(self)
        self.baseline_max_runtime_seconds = (
            pf.create_baseline_max_runtime_seconds_parameter(self)
        )
        self.monitor_max_runtime_seconds = (
            pf.create_monitor_max_runtime_seconds_parameter(self, "ModelQuality")
        )
        self.kms_key_arn = pf.create_kms_key_arn_parameter(self)
        self.baseline_job_name = pf.create_baseline_job_name_parameter(self)
        self.monitoring_schedule_name = pf.create_monitoring_schedule_name_parameter(
            self
        )
        self.data_capture_bucket = pf.create_data_capture_bucket_name_parameter(self)
        self.baseline_output_bucket = pf.create_baseline_output_bucket_name_parameter(
            self
        )
        self.data_capture_s3_location = pf.create_data_capture_location_parameter(self)
        self.monitoring_output_location = (
            pf.create_monitoring_output_location_parameter(self)
        )
        self.schedule_expression = pf.create_schedule_expression_parameter(self)
        self.image_uri = pf.create_algorithm_image_uri_parameter(self)

        # common conditions
        self.kms_key_arn_provided = cf.create_kms_key_arn_provided_condition(
            self, self.kms_key_arn
        )

        # Resources #
        self.assets_bucket = s3.Bucket.from_bucket_name(
            self, "ImportedAssetsBucket", self.assets_bucket_name.value_as_string
        )
        # getting blueprint bucket object from its name - will be used later in the stack
        self.blueprint_bucket = s3.Bucket.from_bucket_name(
            self, "ImportedBlueprintBucket", self.blueprint_bucket_name.value_as_string
        )

        # update common Baseline attributes
        self._update_common_baseline_attributes()

        # add ModelQuality specific parameters/conditions, and update self.baseline_attributes/self.monitor_attributes
        if self.monitoring_type in ["ModelQuality", "ModelBias", "ModelExplainability"]:
            self._add_model_quality_resources()

        # add extra ModelBias/ModelExplainability
        if self.monitoring_type in ["ModelBias", "ModelExplainability"]:
            self._add_model_bias_explainability_extra_attributes()

        # create custom resource to invoke the baseline job lambda
        invoke_lambda_custom_resource = self._create_invoke_lambda_custom_resource()

        # creating SageMaker monitor role
        self.sagemaker_role = self._create_sagemaker_monitor_role()

        # update attributes
        self._update_common_monitor_attributes()

        # create SageMaker monitoring Schedule
        sagemaker_monitor = SageMakerModelMonitor(
            self, f"{monitoring_type}Monitor", **self.monitor_attributes
        )

        # add job definition dependency on sagemaker role and invoke_lambda_custom_resource
        # (so, the baseline job is created)
        sagemaker_monitor.job_definition.node.add_dependency(self.sagemaker_role)
        sagemaker_monitor.job_definition.node.add_dependency(
            invoke_lambda_custom_resource
        )

        # Outputs #
        self._create_stack_outputs()

    def _update_common_baseline_attributes(self):
        self.baseline_attributes.update(
            dict(
                monitoring_type=self.monitoring_type,
                baseline_job_name=self.baseline_job_name.value_as_string,
                baseline_data_location=self.baseline_data.value_as_string,
                baseline_output_bucket=self.baseline_output_bucket.value_as_string,
                baseline_job_output_location=self.baseline_job_output_location.value_as_string,
                endpoint_name=self.endpoint_name.value_as_string,
                instance_type=self.instance_type.value_as_string,
                instance_volume_size=self.instance_volume_size.value_as_string,
                max_runtime_seconds=self.baseline_max_runtime_seconds.value_as_string,
                kms_key_arn=Fn.condition_if(
                    self.kms_key_arn_provided.logical_id,
                    self.kms_key_arn.value_as_string,
                    Aws.NO_VALUE,
                ).to_string(),
                kms_key_arn_provided_condition=self.kms_key_arn_provided,
                stack_name=Aws.STACK_NAME,
            )
        )

    def _update_common_monitor_attributes(self):
        self.monitor_attributes.update(
            dict(
                monitoring_schedule_name=self.monitoring_schedule_name.value_as_string,
                endpoint_name=self.endpoint_name.value_as_string,
                baseline_job_output_location=f"s3://{self.baseline_job_output_location.value_as_string}",
                schedule_expression=self.schedule_expression.value_as_string,
                monitoring_output_location=f"s3://{self.monitoring_output_location.value_as_string}",
                instance_type=self.instance_type.value_as_string,
                instance_count=self.instance_count.value_as_string,
                instance_volume_size=self.instance_volume_size.value_as_string,
                max_runtime_seconds=self.monitor_max_runtime_seconds.value_as_string,
                kms_key_arn=Fn.condition_if(
                    self.kms_key_arn_provided.logical_id,
                    self.kms_key_arn.value_as_string,
                    Aws.NO_VALUE,
                ).to_string(),
                role_arn=self.sagemaker_role.role_arn,
                image_uri=self.image_uri.value_as_string,
                monitoring_type=self.monitoring_type,
                tags=[{"key": "stack-name", "value": Aws.STACK_NAME}],
            )
        )

    def _create_invoke_lambda_custom_resource(self):
        # create sagemaker layer
        sm_layer = sagemaker_layer(self, self.blueprint_bucket)

        # create baseline job lambda action
        baseline_job_lambda = create_baseline_job_lambda(
            self,
            blueprint_bucket=self.blueprint_bucket,
            assets_bucket=self.assets_bucket,
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
            blueprint_bucket=self.blueprint_bucket,
            # add baseline attributes to the invoke lambda custom resource, so any change to these attributes
            # (via template update) will re-invoke the baseline lambda and re-calculate the baseline
            custom_resource_properties={
                "Resource": "InvokeLambda",
                "function_name": baseline_job_lambda.function_name,
                "assets_bucket_name": self.assets_bucket_name.value_as_string,
                **self.baseline_attributes,
            },
        )

        # add dependency on baseline lambda
        invoke_lambda_custom_resource.node.add_dependency(baseline_job_lambda)

        return invoke_lambda_custom_resource

    def _create_sagemaker_monitor_role(self):
        return create_sagemaker_monitor_role(
            scope=self,
            id="MLOpsSagemakerMonitorRole",
            kms_key_arn=self.kms_key_arn.value_as_string,
            assets_bucket_name=self.assets_bucket_name.value_as_string,
            data_capture_bucket=self.data_capture_bucket.value_as_string,
            data_capture_s3_location=self.data_capture_s3_location.value_as_string,
            baseline_output_bucket=self.baseline_output_bucket.value_as_string,
            baseline_job_output_location=self.baseline_job_output_location.value_as_string,
            output_s3_location=self.monitoring_output_location.value_as_string,
            kms_key_arn_provided_condition=self.kms_key_arn_provided,
            baseline_job_name=self.baseline_job_name.value_as_string,
            monitoring_schedule_name=self.monitoring_schedule_name.value_as_string,
            endpoint_name=self.endpoint_name.value_as_string,
            model_monitor_ground_truth_bucket=self.ground_truth_s3_bucket.value_as_string
            if self.monitoring_type in ["ModelQuality", "ModelBias"]
            else None,
            model_monitor_ground_truth_input=self.ground_truth_s3_uri.value_as_string
            if self.monitoring_type in ["ModelQuality", "ModelBias"]
            else None,
            monitoring_type=self.monitoring_type,
        )

    def _add_model_quality_resources(self):
        """
        Adds ModelQuality specific parameters/conditions and updates
        self.baseline_attributes/self.monitor_attributes. Most of these attributes are reused
        by ModelBias and ModelExplainability monitors
        """
        # add baseline job attributes (they are different from Monitor attributes)
        if self.monitoring_type == "ModelQuality":
            self.baseline_inference_attribute = pf.create_inference_attribute_parameter(
                self, "Baseline"
            )
            self.baseline_probability_attribute = (
                pf.create_probability_attribute_parameter(self, "Baseline")
            )
            self.ground_truth_attribute = pf.create_ground_truth_attribute_parameter(
                self
            )
            # add ModelQuality Baseline attributes
            self.baseline_attributes.update(
                dict(
                    ground_truth_attribute=self.ground_truth_attribute.value_as_string,
                    inference_attribute=self.baseline_inference_attribute.value_as_string,
                    probability_attribute=self.baseline_probability_attribute.value_as_string,
                )
            )
        # add monitor attributes
        self.monitor_inference_attribute = pf.create_inference_attribute_parameter(
            self, "Monitor"
        )
        self.monitor_probability_attribute = pf.create_probability_attribute_parameter(
            self, "Monitor"
        )
        # only create ground_truth_s3_url parameter for ModelQuality/Bias
        if self.monitoring_type in ["ModelQuality", "ModelBias"]:
            # ground_truth_s3_uri is only for ModelQuality/ModelBias
            self.ground_truth_s3_bucket = pf.create_ground_truth_bucket_name_parameter(
                self
            )
            self.ground_truth_s3_uri = pf.create_ground_truth_s3_uri_parameter(self)
            self.monitor_attributes.update(
                dict(
                    ground_truth_s3_uri=f"s3://{self.ground_truth_s3_uri.value_as_string}"
                )
            )
        # problem_type and probability_threshold_attribute are the same for both
        self.problem_type = pf.create_problem_type_parameter(self)
        self.probability_threshold_attribute = (
            pf.create_probability_threshold_attribute_parameter(self)
        )

        # add conditions (used by monitor)
        self.inference_attribute_provided = cf.create_attribute_provided_condition(
            self, "InferenceAttributeProvided", self.monitor_inference_attribute
        )

        self.binary_classification_propability_attribute_provided = (
            cf.create_problem_type_binary_classification_attribute_provided_condition(
                self,
                self.problem_type,
                self.monitor_probability_attribute,
                "ProbabilityAttribute",
            )
        )
        self.binary_classification_propability_threshold_provided = (
            cf.create_problem_type_binary_classification_attribute_provided_condition(
                self,
                self.problem_type,
                self.probability_threshold_attribute,
                "ProbabilityThreshold",
            )
        )

        # add shared Baseline attributes
        self.baseline_attributes.update(
            dict(
                problem_type=self.problem_type.value_as_string,
                probability_threshold_attribute=self.probability_threshold_attribute.value_as_string,
            )
        )

        # add ModelQuality Monitor attributes
        self.monitor_attributes.update(
            dict(
                problem_type=self.problem_type.value_as_string,
                # pass inference_attribute if provided
                inference_attribute=Fn.condition_if(
                    self.inference_attribute_provided.logical_id,
                    self.monitor_inference_attribute.value_as_string,
                    Aws.NO_VALUE,
                ).to_string(),
                # pass probability_attribute if provided and ProblemType is BinaryClassification
                probability_attribute=Fn.condition_if(
                    self.binary_classification_propability_attribute_provided.logical_id,
                    self.monitor_probability_attribute.value_as_string,
                    Aws.NO_VALUE,
                ).to_string(),
                # pass probability_threshold_attribute if provided and ProblemType is BinaryClassification
                probability_threshold_attribute=Fn.condition_if(
                    self.binary_classification_propability_threshold_provided.logical_id,
                    self.probability_threshold_attribute.value_as_string,
                    Aws.NO_VALUE,
                ).to_string(),
            )
        )

    def _add_model_bias_explainability_extra_attributes(self):
        # create paramaters/conditions
        # create bias specific paramaters
        if self.monitoring_type == "ModelBias":
            self.base_config = pf.create_bias_config_parameter(self)
            self.model_predicted_label_config = (
                pf.create_model_predicted_label_config_parameter(self)
            )
            self.model_predicted_label_config_provided = (
                cf.create_attribute_provided_condition(
                    self,
                    "PredictedLabelConfigProvided",
                    self.model_predicted_label_config,
                )
            )
            # update baseline attributes
            self.baseline_attributes.update(
                dict(
                    model_predicted_label_config=Fn.condition_if(
                        self.model_predicted_label_config_provided.logical_id,
                        self.model_predicted_label_config.value_as_string,
                        Aws.NO_VALUE,
                    ).to_string(),
                    bias_config=self.base_config.value_as_string,
                )
            )

        if self.monitoring_type == "ModelExplainability":
            self.shap_config = pf.create_shap_config_parameter(self)
            self.model_scores = pf.create_model_scores_parameter(self)
            self.model_scores_provided = cf.create_attribute_provided_condition(
                self, "ModelScoresProvided", self.model_scores
            )
            # update baseline attributes
            self.baseline_attributes.update(
                dict(
                    shap_config=self.shap_config.value_as_string,
                    model_scores=Fn.condition_if(
                        self.model_scores_provided.logical_id,
                        self.model_scores.value_as_string,
                        Aws.NO_VALUE,
                    ).to_string(),
                )
            )
        # common parameters
        self.features_attribute = pf.create_features_attribute_parameter(self)
        self.features_attribute_provided = cf.create_attribute_provided_condition(
            self, "FeaturesAttributeProvided", self.features_attribute
        )

        # update monitor attributes
        self.monitor_attributes.update(
            dict(
                features_attribute=Fn.condition_if(
                    self.features_attribute_provided.logical_id,
                    self.features_attribute.value_as_string,
                    Aws.NO_VALUE,
                ).to_string(),
            )
        )

    def _create_stack_outputs(self):
        CfnOutput(
            self,
            id="BaselineName",
            value=self.baseline_job_name.value_as_string,
        )
        CfnOutput(
            self,
            id="MonitoringScheduleJobName",
            value=self.monitoring_schedule_name.value_as_string,
        )
        CfnOutput(
            self,
            id="MonitoringScheduleType",
            value=self.monitoring_type,
        )
        CfnOutput(
            self,
            id="BaselineJobOutput",
            value=f"https://s3.console.aws.amazon.com/s3/buckets/{self.baseline_job_output_location.value_as_string}/",
        )
        CfnOutput(
            self,
            id="MonitoringScheduleOutput",
            value=(
                f"https://s3.console.aws.amazon.com/s3/buckets/{self.monitoring_output_location.value_as_string}/"
                f"{self.endpoint_name.value_as_string}/{self.monitoring_schedule_name.value_as_string}/"
            ),
        )
        CfnOutput(
            self,
            id="MonitoredSagemakerEndpoint",
            value=self.endpoint_name.value_as_string,
        )
        CfnOutput(
            self,
            id="DataCaptureS3Location",
            value=(
                f"https://s3.console.aws.amazon.com/s3/buckets/{self.data_capture_s3_location.value_as_string}"
                f"/{self.endpoint_name.value_as_string}/"
            ),
        )
