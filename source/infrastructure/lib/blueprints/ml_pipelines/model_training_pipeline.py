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
from aws_cdk import (
    Stack,
    Aws,
    Fn,
    CfnOutput,
    aws_s3 as s3,
    aws_events as events,
    aws_sns as sns,
)
from lib.blueprints.pipeline_definitions.deploy_actions import (
    model_training_job,
    sagemaker_layer,
    create_invoke_lambda_custom_resource,
    eventbridge_rule_to_sns,
)

from lib.blueprints.pipeline_definitions.templates_parameters import (
    ParameteresFactory as pf,
    ConditionsFactory as cf,
)


class TrainingJobStack(Stack):
    def __init__(self, scope: Construct, id: str, training_type: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.training_type = training_type
        # Parameteres #
        self.blueprint_bucket_name = pf.create_blueprint_bucket_name_parameter(self)
        self.assets_bucket_name = pf.create_assets_bucket_name_parameter(self)
        self.job_name = pf.create_autopilot_job_name_parameter(self)
        self.algorithm_image_uri = pf.create_algorithm_image_uri_parameter(self)
        self.instance_type = pf.create_instance_type_parameter(self)
        self.instance_count = pf.create_instance_count_parameter(self)
        self.instance_volume_size = pf.create_instance_volume_size_parameter(self)
        self.job_output_location = pf.create_job_output_location_parameter(self)
        self.kms_key_arn = pf.create_kms_key_arn_parameter(self)
        self.training_data = pf.create_training_data_parameter(self)
        self.validation_data = pf.create_validation_data_parameter(self)
        self.encrypt_inter_container_traffic = (
            pf.create_encrypt_inner_traffic_parameter(self)
        )
        self.max_runtime_per_training_job_in_seconds = (
            pf.create_max_runtime_per_job_parameter(self)
        )
        self.use_spot_instances = pf.create_use_spot_instances_parameter(self)
        self.max_wait_time_for_spot = pf.create_max_wait_time_for_spot_parameter(self)
        self.content_type = pf.create_content_type_parameter(self)
        self.s3_data_type = pf.create_s3_data_type_parameter(self)
        self.data_distribution = pf.create_data_distribution_parameter(self)
        self.compression_type = pf.create_compression_type_parameter(self)
        self.data_input_mode = pf.create_data_input_mode_parameter(self)
        self.data_record_wrapping = pf.create_data_record_wrapping_parameter(self)
        self.attribute_names = pf.create_attribute_names_parameter(self)
        self.hyperparameters = pf.create_hyperparameters_parameter(self)
        self.mlops_sns_topic_arn = pf.create_sns_topic_arn_parameter(self)

        # Resources #
        self.assets_bucket = s3.Bucket.from_bucket_name(
            self, "ImportedAssetsBucket", self.assets_bucket_name.value_as_string
        )
        # getting blueprint bucket object from its name - will be used later in the stack
        self.blueprint_bucket = s3.Bucket.from_bucket_name(
            self, "ImportedBlueprintBucket", self.blueprint_bucket_name.value_as_string
        )

        # import the sns Topic
        self.job_notification_topic = sns.Topic.from_topic_arn(
            self, "JobNotification", self.mlops_sns_topic_arn.value_as_string
        )

        # Conditions
        self.validation_data_provided = cf.create_attribute_provided_condition(
            self, "ValidationDataProvided", self.validation_data
        )
        self.data_record_wrapping_provided = cf.create_attribute_provided_condition(
            self, "RecordWrappingProvided", self.data_record_wrapping
        )
        self.compression_type_provided = cf.create_attribute_provided_condition(
            self, "CompressionTypeProvided", self.compression_type
        )
        self.kms_key_arn_provided = cf.create_attribute_provided_condition(
            self, "KMSProvided", self.kms_key_arn
        )

        self.attribute_names_provided = cf.create_attribute_provided_condition(
            self, "AttributeNamesProvided", self.attribute_names
        )

        # create a dict to hold attributes for the training lambda
        self.training_attributes = dict(
            blueprint_bucket=self.blueprint_bucket,
            assets_bucket=self.assets_bucket,
            job_type=training_type,
            job_name=self.job_name.value_as_string,
            training_data=self.training_data.value_as_string,
            validation_data=Fn.condition_if(
                self.validation_data_provided.logical_id,
                self.validation_data.value_as_string,
                Aws.NO_VALUE,
            ).to_string(),
            s3_data_type=self.s3_data_type.value_as_string,
            content_type=self.content_type.value_as_string,
            data_distribution=self.data_distribution.value_as_string,
            compression_type=Fn.condition_if(
                self.compression_type_provided.logical_id,
                self.compression_type.value_as_string,
                Aws.NO_VALUE,
            ).to_string(),
            data_input_mode=self.data_input_mode.value_as_string,
            data_record_wrapping=Fn.condition_if(
                self.data_record_wrapping_provided.logical_id,
                self.data_record_wrapping.value_as_string,
                Aws.NO_VALUE,
            ).to_string(),
            attribute_names=Fn.condition_if(
                self.attribute_names_provided.logical_id,
                self.attribute_names.value_as_string,
                Aws.NO_VALUE,
            ).to_string(),
            hyperparameters=self.hyperparameters.value_as_string,
            job_output_location=self.job_output_location.value_as_string,
            image_uri=self.algorithm_image_uri.value_as_string,
            instance_type=self.instance_type.value_as_string,
            instance_count=self.instance_count.value_as_string,
            instance_volume_size=self.instance_volume_size.value_as_string,
            kms_key_arn=Fn.condition_if(
                self.kms_key_arn_provided.logical_id,
                self.kms_key_arn.value_as_string,
                Aws.NO_VALUE,
            ).to_string(),
            encrypt_inter_container_traffic=self.encrypt_inter_container_traffic.value_as_string,
            max_runtime_per_training_job_in_seconds=self.max_runtime_per_training_job_in_seconds.value_as_string,
            use_spot_instances=self.use_spot_instances.value_as_string,
            max_wait_time_for_spot=self.max_wait_time_for_spot.value_as_string,
        )

        # add HyperparameterTuningJob specific parameters
        if training_type == "HyperparameterTuningJob":
            self.tuner_config = pf.create_tuner_config_parameter(self)
            self.hyperparameters_ranges = pf.create_hyperparameters_range_parameter(
                self
            )
            # update the training attributes
            self.training_attributes.update(
                {
                    "tuner_config": self.tuner_config.value_as_string,
                    "hyperparameter_ranges": self.hyperparameters_ranges.value_as_string,
                }
            )

        # create Training job lambda
        training_lambda = self._create_model_training_lambda()

        # create custom resource to invoke the training job lambda
        invoke_lambda_custom_resource = self._create_invoke_lambda_custom_resource(
            function_name=training_lambda.function_name,
            function_arn=training_lambda.function_arn,
        )

        # create dependency on the training lambda
        invoke_lambda_custom_resource.node.add_dependency(training_lambda)

        # create the EventBridge Rule to notify admin about the status of the job
        self._create_job_notification_rule()

        # create stack outputs
        self._create_stack_outputs()

    def _create_model_training_lambda(self):
        # create SageMaker SDK layer
        sm_layer = sagemaker_layer(self, self.blueprint_bucket)

        # update the training attributes
        self.training_attributes.update(
            {
                "sm_layer": sm_layer,
                "kms_key_arn_provided_condition": self.kms_key_arn_provided,
            }
        )

        # create training job lambda
        training_lambda = model_training_job(
            scope=self, id="ModelTrainingLambda", **self.training_attributes
        )

        return training_lambda

    def _create_invoke_lambda_custom_resource(self, function_name, function_arn):
        # remove unnecessary training attributes to add to custom resource properties
        self.training_attributes.pop("sm_layer", None)
        self.training_attributes.pop("kms_key_arn_provided_condition", None)
        self.training_attributes.pop("blueprint_bucket", None)
        self.training_attributes.pop("assets_bucket", None)

        # create the custom resource
        invoke_lambda_custom_resource = create_invoke_lambda_custom_resource(
            scope=self,
            id="InvokeTrainingLambda",
            lambda_function_arn=function_arn,
            lambda_function_name=function_name,
            blueprint_bucket=self.blueprint_bucket,
            # add the main training attributes to the invoke lambda custom resource,
            # so any change in one attribute will re-invoke the model training lambda
            custom_resource_properties={
                "Resource": "InvokeLambda",
                "function_name": function_name,
                "assets_bucket": self.assets_bucket.bucket_name,
                **self.training_attributes,
            },
        )

        return invoke_lambda_custom_resource

    def _create_job_notification_rule(
        self,
    ):
        values_map = {
            "TrainingJob": {
                "detail_type": ["SageMaker Training Job State Change"],
                "detail": {
                    "TrainingJobName": [self.job_name.value_as_string],
                    "TrainingJobStatus": ["Completed", "Failed", "Stopped"],
                },
                "sns_message": events.RuleTargetInput.from_text(
                    (
                        f"The training job {events.EventField.from_path('$.detail.TrainingJobName')} status is: "
                        f"{events.EventField.from_path('$.detail.TrainingJobStatus')}."
                    )
                ),
            },
            "HyperparameterTuningJob": {
                "detail_type": ["SageMaker HyperParameter Tuning Job State Change"],
                "detail": {
                    "HyperParameterTuningJobName": [self.job_name.value_as_string],
                    "HyperParameterTuningJobStatus": ["Completed", "Failed", "Stopped"],
                },
                "sns_message": events.RuleTargetInput.from_text(
                    (
                        f"The hyperparameter training job {events.EventField.from_path('$.detail.HyperParameterTuningJobName')} status is: "
                        f"{events.EventField.from_path('$.detail.HyperParameterTuningJobStatus')}."
                    )
                ),
            },
        }

        eventbridge_rule_to_sns(
            scope=self,
            logical_id="JobNotificationRule",
            description="EventBridge rule to notify the admin on the status change of the job",
            source=["aws.sagemaker"],
            detail_type=values_map[self.training_type]["detail_type"],
            detail=values_map[self.training_type]["detail"],
            target_sns_topic=self.job_notification_topic,
            sns_message=values_map[self.training_type]["sns_message"],
        )

    def _create_stack_outputs(self):
        CfnOutput(
            self,
            id="TrainingJobName",
            value=self.job_name.value_as_string,
            description="The training job's name",
        )
        CfnOutput(
            self,
            id="TrainingJobOutputLocation",
            value=f"https://s3.console.aws.amazon.com/s3/buckets/{self.assets_bucket_name.value_as_string}/{self.job_output_location.value_as_string}/",
            description="Output location of the training job",
        )
        CfnOutput(
            self,
            id="TrainingDataLocation",
            value=f"https://s3.console.aws.amazon.com/s3/buckets/{self.assets_bucket_name.value_as_string}/{self.training_data.value_as_string}",
            description="Training data used by the training job",
        )

        CfnOutput(
            self,
            id="ValidationDataLocation",
            value=f"https://s3.console.aws.amazon.com/s3/buckets/{self.assets_bucket_name.value_as_string}/{self.training_data.value_as_string}",
            description="Training data used by the training job",
        ).node.condition = self.validation_data_provided
