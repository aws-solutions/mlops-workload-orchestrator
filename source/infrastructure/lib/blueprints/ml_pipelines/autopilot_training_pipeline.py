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
    autopilot_training_job,
    sagemaker_layer,
    create_invoke_lambda_custom_resource,
    eventbridge_rule_to_sns,
)

from lib.blueprints.pipeline_definitions.templates_parameters import (
    ParameteresFactory as pf,
    ConditionsFactory as cf,
)


class AutopilotJobStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Parameteres #
        self.blueprint_bucket_name = pf.create_blueprint_bucket_name_parameter(self)
        self.assets_bucket_name = pf.create_assets_bucket_name_parameter(self)
        self.job_name = pf.create_autopilot_job_name_parameter(self)
        self.problem_type = pf.create_autopilot_problem_type_parameter(self)
        self.job_objective = pf.create_job_objective_parameter(self)
        self.training_data = pf.create_training_data_parameter(self)
        self.target_attribute_name = pf.create_target_attribute_name_parameter(self)
        self.job_output_location = pf.create_job_output_location_parameter(self)
        self.compression_type = pf.create_compression_type_parameter(self)
        self.max_candidates = pf.create_max_candidates_parameter(self)
        self.encrypt_inter_container_traffic = (
            pf.create_encrypt_inner_traffic_parameter(self)
        )
        self.max_runtime_per_training_job_in_seconds = (
            pf.create_max_runtime_per_job_parameter(self)
        )
        self.total_job_runtime_in_seconds = pf.create_total_job_runtime_parameter(self)
        self.generate_candidate_definitions_only = (
            pf.create_generate_definitions_only_parameter(self)
        )
        self.kms_key_arn = pf.create_kms_key_arn_parameter(self)
        self.mlops_sns_topic_arn = pf.create_sns_topic_arn_parameter(self)

        # Conditions
        self.problem_type_provided = cf.create_attribute_provided_condition(
            self, "ProblemTypeProvided", self.problem_type
        )
        self.job_objective_provided = cf.create_attribute_provided_condition(
            self, "JobObjectiveProvided", self.job_objective
        )
        self.compression_type_provided = cf.create_attribute_provided_condition(
            self, "CompressionTypeProvided", self.compression_type
        )
        self.kms_key_arn_provided = cf.create_attribute_provided_condition(
            self, "KMSProvided", self.kms_key_arn
        )

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
            self, "AutopilotJobNotification", self.mlops_sns_topic_arn.value_as_string
        )

        # create Autopilot job lambda
        autopilot_lambda = self._create_autoplot_lambda()

        # create custom resource to invoke the autopilot job lambda
        invoke_lambda_custom_resource = self._create_invoke_lambda_custom_resource(
            function_name=autopilot_lambda.function_name,
            function_arn=autopilot_lambda.function_arn,
        )

        # create dependency on the autopilot lambda
        invoke_lambda_custom_resource.node.add_dependency(autopilot_lambda)

        # create EventBride notification rules
        self._create_job_notification_rules()

        # create stack outputs
        self._create_stack_outputs()

    def _create_autoplot_lambda(self):
        # create SageMaker SDK layer
        sm_layer = sagemaker_layer(self, self.blueprint_bucket)

        # create Autopilot job lambda
        autopilot_lambda = autopilot_training_job(
            scope=self,
            id="AutopilotLambda",
            blueprint_bucket=self.blueprint_bucket,
            assets_bucket=self.assets_bucket,
            job_name=self.job_name.value_as_string,
            training_data=self.training_data.value_as_string,
            target_attribute_name=self.target_attribute_name.value_as_string,
            job_output_location=self.job_output_location.value_as_string,
            problem_type=Fn.condition_if(
                self.problem_type_provided.logical_id,
                self.problem_type.value_as_string,
                Aws.NO_VALUE,
            ).to_string(),
            job_objective=Fn.condition_if(
                self.job_objective_provided.logical_id,
                self.job_objective.value_as_string,
                Aws.NO_VALUE,
            ).to_string(),
            compression_type=Fn.condition_if(
                self.compression_type_provided.logical_id,
                self.compression_type.value_as_string,
                Aws.NO_VALUE,
            ).to_string(),
            max_candidates=self.max_candidates.value_as_string,
            kms_key_arn=Fn.condition_if(
                self.kms_key_arn_provided.logical_id,
                self.kms_key_arn.value_as_string,
                Aws.NO_VALUE,
            ).to_string(),
            encrypt_inter_container_traffic=self.encrypt_inter_container_traffic.value_as_string,
            max_runtime_per_training_job_in_seconds=self.max_runtime_per_training_job_in_seconds.value_as_string,
            total_job_runtime_in_seconds=self.total_job_runtime_in_seconds.value_as_string,
            generate_candidate_definitions_only=self.generate_candidate_definitions_only.value_as_string,
            sm_layer=sm_layer,
            kms_key_arn_provided_condition=self.kms_key_arn_provided,
        )

        return autopilot_lambda

    def _create_invoke_lambda_custom_resource(self, function_name, function_arn):
        invoke_lambda_custom_resource = create_invoke_lambda_custom_resource(
            scope=self,
            id="InvokeAutopilotLambda",
            lambda_function_arn=function_arn,
            lambda_function_name=function_name,
            blueprint_bucket=self.blueprint_bucket,
            # add the main Autopilot attributes to the invoke lambda custom resource,
            # so any change in one attribute will re-invoke the autopilot lambda
            custom_resource_properties={
                "Resource": "InvokeLambda",
                "function_name": function_name,
                "assets_bucket": self.assets_bucket.bucket_name,
                "kms_key_arn": self.kms_key_arn.value_as_string,
                "job_name": self.job_name.value_as_string,
                "training_data": self.training_data.value_as_string,
                "target_attribute_name": self.target_attribute_name.value_as_string,
                "job_output_location": self.job_output_location.value_as_string,
                "problem_type": self.problem_type.value_as_string,
                "objective_type": self.job_objective.value_as_string,
                "compression_type": self.compression_type.value_as_string,
                "max_candidates": self.max_candidates.value_as_string,
                "total_runtime": self.total_job_runtime_in_seconds.value_as_string,
                "generate_candidate_definitions_only": self.generate_candidate_definitions_only.value_as_string,
            },
        )

        return invoke_lambda_custom_resource

    def _create_job_notification_rules(self):
        event_source = ["aws.sagemaker"]
        # Currently, SageMaker Autopilot job does not emit status change events to EventBridge
        # The autopilot creates several types of sub-jobs (processing, transform, training)
        # in addition to a hyperparameter tuning job (which produces the final model).
        # All the sub-jobs names start of the the autopilot job's name.

        # This rule monitors the status change of hyperparameter tuning using
        # the prefix (autopilot job name)
        eventbridge_rule_to_sns(
            scope=self,
            logical_id="AutopilotJobTunerRule",
            description="EventBridge rule to notify the admin on the status change of the hyperparameter job used by the autopilot job",
            source=event_source,
            detail_type=["SageMaker HyperParameter Tuning Job State Change"],
            detail={
                "HyperParameterTuningJobName": [
                    {"prefix": self.job_name.value_as_string}
                ],
                "HyperParameterTuningJobStatus": ["Completed", "Failed", "Stopped"],
            },
            target_sns_topic=self.job_notification_topic,
            sns_message=events.RuleTargetInput.from_text(
                (
                    f"The hyperparameter training job {events.EventField.from_path('$.detail.HyperParameterTuningJobName')} "
                    f"(used by the Autopilot job: {self.job_name.value_as_string}) status is: "
                    f"{events.EventField.from_path('$.detail.HyperParameterTuningJobStatus')}."
                )
            ),
        )

        # The Autopilot job runs processing jobs (after the hyperparameter job is done)
        # to generate reports about model explainability.
        # The last two processing jobs names start with "<autopilot-job-name>-documentation" and "<autopilot-job-name>-dpp"
        eventbridge_rule_to_sns(
            scope=self,
            logical_id="AutopilotJobProcessingRule",
            description="EventBridge rule to notify the admin on the status change of the last two processing jobs used the autopilot job",
            source=event_source,
            detail_type=["SageMaker Processing Job State Change"],
            detail={
                "ProcessingJobName": [
                    {"prefix": f"{self.job_name.value_as_string}-dpp"},
                    {"prefix": f"{self.job_name.value_as_string}-documentation"},
                ],
                "ProcessingJobStatus": ["Completed", "Failed", "Stopped"],
            },
            target_sns_topic=self.job_notification_topic,
            sns_message=events.RuleTargetInput.from_text(
                (
                    f"The processing job {events.EventField.from_path('$.detail.ProcessingJobName')} "
                    f"(used by the Autopilot job: {self.job_name.value_as_string}) status is: "
                    f"{events.EventField.from_path('$.detail.ProcessingJobStatus')}."
                )
            ),
        )

        # The autopilot uses intermidate processing jobs to pre-process data. This rules notify the admin only
        # if their status is Failed|Stopped. If these jobs failed/stopped, the next jobs won't be executed.
        # The processing jobs names start with "<autopilot-job-name>-db" and "<autopilot-job-name>-pr"
        eventbridge_rule_to_sns(
            scope=self,
            logical_id="AutopilotJobInterProcessingRule",
            description="EventBridge rule to notify the admin on the status change of the intermidate processing jobs used the autopilot job",
            source=event_source,
            detail_type=["SageMaker Processing Job State Change"],
            detail={
                "ProcessingJobName": [
                    {"prefix": f"{self.job_name.value_as_string}-dp"},
                    {"prefix": f"{self.job_name.value_as_string}-pr"},
                ],
                "ProcessingJobStatus": ["Failed", "Stopped"],
            },
            target_sns_topic=self.job_notification_topic,
            sns_message=events.RuleTargetInput.from_text(
                (
                    f"The processing job {events.EventField.from_path('$.detail.ProcessingJobName')} "
                    f"(used by the Autopilot job: {self.job_name.value_as_string}) status is: "
                    f"{events.EventField.from_path('$.detail.ProcessingJobStatus')}."
                )
            ),
        )

        # Before running the Hyperparameter job, the autopilot runs few intermidate training jobs,
        # and then transform jobs to evaluate models.
        # This rule is used notify the admin if any training job is failed/stopped.
        eventbridge_rule_to_sns(
            scope=self,
            logical_id="AutopilotJobTrainingRule",
            description="EventBridge rule to notify the admin on the status change of the intermidate training jobs used the autopilot job",
            source=event_source,
            detail_type=["SageMaker Training Job State Change"],
            detail={
                "TrainingJobName": [
                    {"prefix": f"{self.job_name.value_as_string}-dpp"},
                ],
                "TrainingJobStatus": ["Failed", "Stopped"],
            },
            target_sns_topic=self.job_notification_topic,
            sns_message=events.RuleTargetInput.from_text(
                (
                    f"The training job {events.EventField.from_path('$.detail.TrainingJobName')} "
                    f"(used by the Autopilot job: {self.job_name.value_as_string}) status is: "
                    f"{events.EventField.from_path('$.detail.TrainingJobStatus')}."
                )
            ),
        )

        # The autopilot also creates several transform jobs to evaluate the models created by
        # the intermidate training jobs.
        # This rule is used notify the admin if any transform job is failed/stopped.
        eventbridge_rule_to_sns(
            scope=self,
            logical_id="AutopilotJobTransformRule",
            description="EventBridge rule to notify the admin on the status change of the intermidate transform jobs used the autopilot job",
            source=event_source,
            detail_type=["SageMaker Transform Job State Change"],
            detail={
                "TransformJobName": [
                    {"prefix": f"{self.job_name.value_as_string}-dpp"},
                ],
                "TransformJobStatus": ["Failed", "Stopped"],
            },
            target_sns_topic=self.job_notification_topic,
            sns_message=events.RuleTargetInput.from_text(
                (
                    f"The transform job {events.EventField.from_path('$.detail.TransformJobName')} "
                    f"(used by the Autopilot job: {self.job_name.value_as_string}) status is: "
                    f"{events.EventField.from_path('$.detail.TransformJobStatus')}."
                )
            ),
        )

    def _create_stack_outputs(self):
        CfnOutput(
            self,
            id="AutopilotJobName",
            value=self.job_name.value_as_string,
            description="The autopilot training job's name",
        )
        CfnOutput(
            self,
            id="AutopilotJobOutputLocation",
            value=f"https://s3.console.aws.amazon.com/s3/buckets/{self.assets_bucket_name.value_as_string}/{self.job_output_location.value_as_string}/",
            description="Output location of the autopilot training job",
        )
        CfnOutput(
            self,
            id="TrainingDataLocation",
            value=f"https://s3.console.aws.amazon.com/s3/buckets/{self.assets_bucket_name.value_as_string}/{self.training_data.value_as_string}",
            description="Training data used by the autopilot training job",
        )
