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
from typing import List, Dict, Union, Optional
from constructs import Construct
from aws_cdk import Token, Fn, aws_sagemaker as sagemaker


class SageMakerModelMonitor(Construct):
    """
    Creates Amazon SageMaker Model Monitor (DataQuality or ModelQuality)

    Attributes:
        scope (CDK Construct scope): that's needed to create CDK resources
        id (str): CDK resource's logical id
        monitoring_schedule_name (str): name of the monitoring job to be created
        endpoint_name (str): name of the deployed SageMaker endpoint to be monitored
        baseline_job_output_location (str): the baseline job's output location <bucket-name>/<prefix>
        schedule_expression (str): cron job expression
        monitoring_output_location (str): S3 location where the output will be stored
        instance_type (str): compute instance type for the baseline job, in the form of a CDK CfnParameter object
        instance_volume_size (str): volume size of the EC2 instance
        instance_count (str): number of EC2 instances
        max_runtime_seconds (str): max time the job is allowed to run
        kms_key_arn (str): optional arn of the kms key used to encrypt datacapture and
            to encrypt job's output
        role_arn (str): Sagemaker role's arn to be used to create the monitoring schedule
        image_uri (str): the Model Monitor's Docker image URI
        monitoring_type (str): type of SageMaker Model Monitor. Supported values ['DataQuality'|'ModelQuality']
        tags (list[dict[str, str]]): resource tags
        ground_truth_s3_uri (str): used with ModelQuality monitor. Location of the ground truth labels (default: None)
        problem_type (str): used with ModelQuality monitor. Type of Machine Learning problem. Valid values are
            ['Regression'|'BinaryClassification'|'MulticlassClassification'] (default: None).
        inference_attribute (str): used with ModelQuality monitor. Index or JSONpath to locate predicted label(s).
            Required for 'Regression'|'MulticlassClassification' problems,
            and not required for 'BinaryClassification' if 'probability_attribute' and
            'probability_threshold_attribute' are provided (default: None).
        probability_attribute (str): used with ModelQuality monitor. index or JSONpath to locate probabilities.
            Used only with 'BinaryClassification' problem if 'inference_attribute' is not provided (default: None).
        probability_threshold_attribute (str): used with ModelQuality monitor. Threshold to convert probabilities to
            binaries. Used only with 'BinaryClassification' problem if 'inference_attribute' is not provided (default: None).
    """

    def __init__(
        self,  # NOSONAR:S107 the class is designed to take many attributes
        scope: Construct,
        id: str,
        monitoring_schedule_name: str,
        endpoint_name: str,
        baseline_job_output_location: str,
        schedule_expression: str,
        monitoring_output_location: str,
        instance_type: str,
        instance_count: str,
        instance_volume_size: str,
        max_runtime_seconds: str,
        kms_key_arn: str,
        role_arn: str,
        image_uri: str,
        monitoring_type: str,
        tags: List[Dict[str, str]],
        ground_truth_s3_uri: Optional[str] = None,
        problem_type: Optional[str] = None,
        inference_attribute: Optional[str] = None,
        probability_attribute: Optional[str] = None,
        probability_threshold_attribute: Optional[str] = None,
        config_uri: Optional[str] = None,
        features_attribute: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)
        self.scope = scope
        self.id = id
        self.monitoring_schedule_name = monitoring_schedule_name
        self.endpoint_name = endpoint_name
        self.baseline_job_output_location = baseline_job_output_location
        self.schedule_expression = schedule_expression
        self.monitoring_output_location = monitoring_output_location
        self.instance_type = instance_type
        self.instance_count = instance_count
        self.instance_volume_size = instance_volume_size
        self.max_runtime_seconds = max_runtime_seconds
        self.kms_key_arn = kms_key_arn
        self.role_arn = role_arn
        self.image_uri = image_uri
        self.monitoring_type = monitoring_type
        self.tags = tags
        self.ground_truth_s3_uri = ground_truth_s3_uri
        self.problem_type = problem_type
        self.inference_attribute = inference_attribute
        self.probability_attribute = probability_attribute
        self.probability_threshold_attribute = probability_threshold_attribute
        self.features_attribute = features_attribute

        # validate the provided monitoring_type
        if monitoring_type not in [
            "DataQuality",
            "ModelQuality",
            "ModelBias",
            "ModelExplainability",
        ]:
            raise ValueError(
                (
                    f"The provided monitoring type: {monitoring_type} is not valid. "
                    + "It must be 'DataQuality'|'ModelQuality'|'ModelBias'|'ModelExplainability"
                )
            )

        # create the [DataQuality|ModelQuality]JobDefinition
        self.__job_definition = self._get_job_definition(
            monitoring_type=monitoring_type, id=f"{monitoring_type}JobDefinition"
        )

        # create the monitoring schedule
        self.__monitoring_schedule = self._create_sagemaker_monitoring_schedule(
            monitoring_schedule_name=self.monitoring_schedule_name,
            monitor_job_definition=self.__job_definition,
        )

    def _get_job_definition(
        self, monitoring_type: str, id: str
    ) -> Union[
        sagemaker.CfnDataQualityJobDefinition,
        sagemaker.CfnModelQualityJobDefinition,
        sagemaker.CfnModelBiasJobDefinition,
        sagemaker.CfnModelExplainabilityJobDefinition,
    ]:
        """
        Gets the *JobDefinition based on the monitoring_type

        Args:
            monitoring_type (str): possible values ['DataQuality'|'ModelQuality'|'ModelBias'|'ModelExplainability']
            id (str): CDK resource's logical id

        Returns:
            sagemaker.CfnDataQualityJobDefinition|sagemaker.CfnModelQualityJobDefinition object|
            sagemaker.CfnModelBiasJobDefinition|sagemaker.CfnModelExplainabilityJobDefinition
        """
        # create *JobDefinition MonitoringType->function_name map
        type_function_map = dict(
            DataQuality="_create_data_quality_job_definition",
            ModelQuality="_create_model_quality_job_definition",
            ModelBias="_create_model_bias_job_definition",
            ModelExplainability="_create_model_explainability_job_definition",
        )

        # call the right function to create the *JobDefinition
        job_definition = getattr(self, type_function_map[monitoring_type])(id)

        return job_definition

    def _create_data_quality_job_definition(
        self,
        id: str,
    ) -> sagemaker.CfnDataQualityJobDefinition:
        """
        Creates Amazon SageMaker's Data Quality Job Definition

        Args:
            id (str): CDK resource's logical id

        Returns:
            sagemaker.CfnDataQualityJobDefinition object
        """
        data_quality_job_definition = sagemaker.CfnDataQualityJobDefinition(
            self.scope,
            id,
            data_quality_app_specification=sagemaker.CfnDataQualityJobDefinition.DataQualityAppSpecificationProperty(
                image_uri=self.image_uri
            ),
            data_quality_baseline_config=sagemaker.CfnDataQualityJobDefinition.DataQualityBaselineConfigProperty(
                constraints_resource=sagemaker.CfnDataQualityJobDefinition.ConstraintsResourceProperty(
                    s3_uri=f"{self.baseline_job_output_location}/constraints.json"
                ),
                statistics_resource=sagemaker.CfnDataQualityJobDefinition.StatisticsResourceProperty(
                    s3_uri=f"{self.baseline_job_output_location}/statistics.json"
                ),
            ),
            data_quality_job_input=sagemaker.CfnDataQualityJobDefinition.DataQualityJobInputProperty(
                endpoint_input=sagemaker.CfnDataQualityJobDefinition.EndpointInputProperty(
                    endpoint_name=self.endpoint_name,
                    local_path="/opt/ml/processing/input/data_quality_input",
                )
            ),
            data_quality_job_output_config=sagemaker.CfnDataQualityJobDefinition.MonitoringOutputConfigProperty(
                monitoring_outputs=[
                    sagemaker.CfnDataQualityJobDefinition.MonitoringOutputProperty(
                        s3_output=sagemaker.CfnDataQualityJobDefinition.S3OutputProperty(
                            s3_uri=self.monitoring_output_location,
                            local_path="/opt/ml/processing/output/data_quality_output",
                            s3_upload_mode="EndOfJob",
                        )
                    )
                ],
                kms_key_id=self.kms_key_arn,
            ),
            job_resources=sagemaker.CfnDataQualityJobDefinition.MonitoringResourcesProperty(
                cluster_config=sagemaker.CfnDataQualityJobDefinition.ClusterConfigProperty(
                    instance_count=Token.as_number(self.instance_count),
                    instance_type=self.instance_type,
                    volume_size_in_gb=Token.as_number(self.instance_volume_size),
                    volume_kms_key_id=self.kms_key_arn,
                )
            ),
            stopping_condition=sagemaker.CfnDataQualityJobDefinition.StoppingConditionProperty(
                max_runtime_in_seconds=Token.as_number(self.max_runtime_seconds)
            ),
            role_arn=self.role_arn,
            tags=self.tags,
        )

        return data_quality_job_definition

    def _create_model_quality_job_definition(
        self,
        id: str,
    ) -> sagemaker.CfnModelQualityJobDefinition:
        """
        Creates Amazon SageMaker's Model Quality Job Definition

        Args:
            id (str): CDK resource's logical id

        Returns:
            sagemaker.CfnModelQualityJobDefinition object
        """

        # create the ModelQualityJobDefinition
        model_quality_job_definition = sagemaker.CfnModelQualityJobDefinition(
            self.scope,
            id,
            model_quality_app_specification=sagemaker.CfnModelQualityJobDefinition.ModelQualityAppSpecificationProperty(
                problem_type=self.problem_type, image_uri=self.image_uri
            ),
            model_quality_baseline_config=sagemaker.CfnModelQualityJobDefinition.ModelQualityBaselineConfigProperty(
                constraints_resource=sagemaker.CfnModelQualityJobDefinition.ConstraintsResourceProperty(
                    s3_uri=f"{self.baseline_job_output_location}/constraints.json"
                ),
            ),
            model_quality_job_input=sagemaker.CfnModelQualityJobDefinition.ModelQualityJobInputProperty(
                endpoint_input=sagemaker.CfnModelQualityJobDefinition.EndpointInputProperty(
                    endpoint_name=self.endpoint_name,
                    local_path="/opt/ml/processing/input/model_quality_input",
                    inference_attribute=self.inference_attribute,
                    probability_attribute=self.probability_attribute,
                    probability_threshold_attribute=Token.as_number(
                        self.probability_threshold_attribute
                    ),
                ),
                ground_truth_s3_input=sagemaker.CfnModelQualityJobDefinition.MonitoringGroundTruthS3InputProperty(
                    s3_uri=self.ground_truth_s3_uri
                ),
            ),
            model_quality_job_output_config=sagemaker.CfnModelQualityJobDefinition.MonitoringOutputConfigProperty(
                monitoring_outputs=[
                    sagemaker.CfnModelQualityJobDefinition.MonitoringOutputProperty(
                        s3_output=sagemaker.CfnModelQualityJobDefinition.S3OutputProperty(
                            s3_uri=self.monitoring_output_location,
                            local_path="/opt/ml/processing/output/model_quality_output",
                            s3_upload_mode="EndOfJob",
                        )
                    )
                ],
                kms_key_id=self.kms_key_arn,
            ),
            job_resources=sagemaker.CfnModelQualityJobDefinition.MonitoringResourcesProperty(
                cluster_config=sagemaker.CfnModelQualityJobDefinition.ClusterConfigProperty(
                    instance_count=Token.as_number(self.instance_count),
                    instance_type=self.instance_type,
                    volume_size_in_gb=Token.as_number(self.instance_volume_size),
                    volume_kms_key_id=self.kms_key_arn,
                )
            ),
            stopping_condition=sagemaker.CfnModelQualityJobDefinition.StoppingConditionProperty(
                max_runtime_in_seconds=Token.as_number(self.max_runtime_seconds)
            ),
            role_arn=self.role_arn,
            tags=self.tags,
        )

        return model_quality_job_definition

    def _create_model_bias_job_definition(
        self,
        id: str,
    ) -> sagemaker.CfnModelBiasJobDefinition:
        """
        Creates Amazon SageMaker's Model Bias Job Definition

        Args:
            id (str): CDK resource's logical id

        Returns:
            sagemaker.CfnModelBiasJobDefinition object
        """
        # create the ModelBiasJobDefinition
        model_bias_job_definition = sagemaker.CfnModelBiasJobDefinition(
            self.scope,
            id,
            model_bias_app_specification=sagemaker.CfnModelBiasJobDefinition.ModelBiasAppSpecificationProperty(
                config_uri=f"{self.baseline_job_output_location}/monitor/analysis_config.json",
                image_uri=self.image_uri,
            ),
            model_bias_baseline_config=sagemaker.CfnModelBiasJobDefinition.ModelBiasBaselineConfigProperty(
                constraints_resource=sagemaker.CfnModelBiasJobDefinition.ConstraintsResourceProperty(
                    s3_uri=f"{self.baseline_job_output_location}/analysis.json"
                ),
            ),
            model_bias_job_input=sagemaker.CfnModelBiasJobDefinition.ModelBiasJobInputProperty(
                endpoint_input=sagemaker.CfnModelBiasJobDefinition.EndpointInputProperty(
                    endpoint_name=self.endpoint_name,
                    local_path="/opt/ml/processing/input/model_bias_input",
                    features_attribute=self.features_attribute,
                    inference_attribute=self.inference_attribute,
                    probability_attribute=self.probability_attribute,
                    probability_threshold_attribute=Token.as_number(
                        self.probability_threshold_attribute
                    ),
                ),
                ground_truth_s3_input=sagemaker.CfnModelBiasJobDefinition.MonitoringGroundTruthS3InputProperty(
                    s3_uri=self.ground_truth_s3_uri
                ),
            ),
            model_bias_job_output_config=sagemaker.CfnModelBiasJobDefinition.MonitoringOutputConfigProperty(
                monitoring_outputs=[
                    sagemaker.CfnModelBiasJobDefinition.MonitoringOutputProperty(
                        s3_output=sagemaker.CfnModelBiasJobDefinition.S3OutputProperty(
                            s3_uri=self.monitoring_output_location,
                            local_path="/opt/ml/processing/output/model_bias_output",
                            s3_upload_mode="EndOfJob",
                        )
                    )
                ],
                kms_key_id=self.kms_key_arn,
            ),
            job_resources=sagemaker.CfnModelBiasJobDefinition.MonitoringResourcesProperty(
                cluster_config=sagemaker.CfnModelBiasJobDefinition.ClusterConfigProperty(
                    instance_count=Token.as_number(self.instance_count),
                    instance_type=self.instance_type,
                    volume_size_in_gb=Token.as_number(self.instance_volume_size),
                    volume_kms_key_id=self.kms_key_arn,
                )
            ),
            stopping_condition=sagemaker.CfnModelBiasJobDefinition.StoppingConditionProperty(
                max_runtime_in_seconds=Token.as_number(self.max_runtime_seconds)
            ),
            role_arn=self.role_arn,
            tags=self.tags,
        )

        return model_bias_job_definition

    def _create_model_explainability_job_definition(
        self,
        id: str,
    ) -> sagemaker.CfnModelExplainabilityJobDefinition:
        """
        Creates Amazon SageMaker's Model Explainability Job Definition

        Args:
            id (str): CDK resource's logical id

        Returns:
            sagemaker.CfnModelExplainabilityJobDefinition object
        """
        # create the ModelExplainabilityJobDefinition
        model_explainability_job_definition = sagemaker.CfnModelExplainabilityJobDefinition(
            self.scope,
            id,
            model_explainability_app_specification=sagemaker.CfnModelExplainabilityJobDefinition.ModelExplainabilityAppSpecificationProperty(
                config_uri=f"{self.baseline_job_output_location}/monitor/analysis_config.json",
                image_uri=self.image_uri,
            ),
            model_explainability_baseline_config=sagemaker.CfnModelExplainabilityJobDefinition.ModelExplainabilityBaselineConfigProperty(
                constraints_resource=sagemaker.CfnModelExplainabilityJobDefinition.ConstraintsResourceProperty(
                    s3_uri=f"{self.baseline_job_output_location}/analysis.json"
                ),
            ),
            model_explainability_job_input=sagemaker.CfnModelExplainabilityJobDefinition.ModelExplainabilityJobInputProperty(
                endpoint_input=sagemaker.CfnModelExplainabilityJobDefinition.EndpointInputProperty(
                    endpoint_name=self.endpoint_name,
                    local_path="/opt/ml/processing/input/model_explainability_input",
                    features_attribute=self.features_attribute,
                    inference_attribute=self.inference_attribute,
                    probability_attribute=self.probability_attribute,
                )
            ),
            model_explainability_job_output_config=sagemaker.CfnModelExplainabilityJobDefinition.MonitoringOutputConfigProperty(
                monitoring_outputs=[
                    sagemaker.CfnModelExplainabilityJobDefinition.MonitoringOutputProperty(
                        s3_output=sagemaker.CfnModelExplainabilityJobDefinition.S3OutputProperty(
                            s3_uri=self.monitoring_output_location,
                            local_path="/opt/ml/processing/output/model_explainability_output",
                            s3_upload_mode="EndOfJob",
                        )
                    )
                ],
                kms_key_id=self.kms_key_arn,
            ),
            job_resources=sagemaker.CfnModelExplainabilityJobDefinition.MonitoringResourcesProperty(
                cluster_config=sagemaker.CfnModelExplainabilityJobDefinition.ClusterConfigProperty(
                    instance_count=Token.as_number(self.instance_count),
                    instance_type=self.instance_type,
                    volume_size_in_gb=Token.as_number(self.instance_volume_size),
                    volume_kms_key_id=self.kms_key_arn,
                )
            ),
            stopping_condition=sagemaker.CfnModelExplainabilityJobDefinition.StoppingConditionProperty(
                max_runtime_in_seconds=Token.as_number(self.max_runtime_seconds)
            ),
            role_arn=self.role_arn,
            tags=self.tags,
        )

        return model_explainability_job_definition

    def _create_sagemaker_monitoring_schedule(
        self,
        monitoring_schedule_name: str,
        monitor_job_definition: Union[
            sagemaker.CfnDataQualityJobDefinition,
            sagemaker.CfnModelQualityJobDefinition,
            sagemaker.CfnModelBiasJobDefinition,
            sagemaker.CfnModelExplainabilityJobDefinition,
        ],
    ) -> sagemaker.CfnMonitoringSchedule:
        """
        Creates Amazon SageMaker's Monitoring Schedule object

        Args:
            monitoring_schedule_name (str): name of the monitoring job to be created
            monitor_job_definition (sagemaker.CfnDataQualityJobDefinition|sagemaker.CfnModelQualityJobDefinition object|
                sagemaker.CfnModelBiasJobDefinition|sagemaker.CfnModelExplainabilityJobDefinition):
                monitor job definition

        Returns:
            sagemaker.CfnMonitoringSchedule object
        """

        # create the monitoring schedule
        schedule = sagemaker.CfnMonitoringSchedule(
            self.scope,
            f"{self.id}Schedule",
            monitoring_schedule_name=monitoring_schedule_name,
            monitoring_schedule_config=sagemaker.CfnMonitoringSchedule.MonitoringScheduleConfigProperty(
                schedule_config=sagemaker.CfnMonitoringSchedule.ScheduleConfigProperty(
                    schedule_expression=self.schedule_expression
                ),
                # *JobDefinition's name is not specified, so stack updates won't fail
                # hence, "monitor_job_definition.job_definition_name" has no value.
                # The get_att is used to get the generated *JobDefinition's name
                monitoring_job_definition_name=Fn.get_att(
                    monitor_job_definition.logical_id, "JobDefinitionName"
                ).to_string(),
                monitoring_type=self.monitoring_type,
            ),
            tags=self.tags,
        )

        # add dependency on teh monitor job defintion
        schedule.add_dependency(monitor_job_definition)

        return schedule

    @property
    def job_definition(
        self,
    ) -> Union[
        sagemaker.CfnDataQualityJobDefinition,
        sagemaker.CfnModelQualityJobDefinition,
        sagemaker.CfnModelBiasJobDefinition,
        sagemaker.CfnModelExplainabilityJobDefinition,
    ]:
        return self.__job_definition

    @property
    def monitoring_schedule(self) -> sagemaker.CfnMonitoringSchedule:
        return self.__monitoring_schedule
