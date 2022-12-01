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
from typing import Any, Dict, List, Optional, Union
import logging
import json
import sagemaker
from botocore.client import BaseClient
from sagemaker.model_monitor import DefaultModelMonitor
from sagemaker.model_monitor import ModelQualityMonitor
from sagemaker.model_monitor import ModelBiasMonitor
from sagemaker.model_monitor import ModelExplainabilityMonitor
from sagemaker.model_monitor.dataset_format import DatasetFormat
from sagemaker.clarify import (
    DataConfig,
    BiasConfig,
    ModelConfig,
    ModelPredictedLabelConfig,
    SHAPConfig,
)
from shared.wrappers import exception_handler

logger = logging.getLogger(__name__)


class SolutionSageMakerBaselines:
    """
    Creates Amazon SageMaker (DataQuality or ModelQuality) Baselines Jobs

    Attributes:
        monitoring_type (str): type of SageMaker Model Monitor. Supported values ['DataQuality'|'ModelQuality']
        instance_type (str): compute instance type for the baseline job, in the form of a CDK CfnParameter object
        instance_count (int): number of EC2 instances
        instance_volume_size (int): volume size of the EC2 instance
        role_arn (str): Sagemaker role's arn to be used to create the baseline job
        baseline_job_name (str): name of the baseline job to be created
        baseline_dataset (str): S3 URI location of the baseline data (file's format: csv)
        output_s3_uri (str): S3 prefix of the baseline job's output
        max_runtime_seconds (int): optional max time the job is allowed to run
        kms_key_arn (str): optional arn of the kms key used to encrypt datacapture and
            to encrypt job's output
        problem_type (str): used with ModelQuality baseline. Type of Machine Learning problem. Valid values are
            ['Regression'|'BinaryClassification'|'MulticlassClassification'] (default: None).
        ground_truth_attribute (str): index or JSONpath to locate actual label(s) (used with ModelQuality baseline).
            (default: None).
        inference_attribute (str): index or JSONpath to locate predicted label(s) (used with ModelQuality baseline).
            Required for 'Regression'|'MulticlassClassification' problems,
            and not required for 'BinaryClassification' if 'probability_attribute' and
            'probability_threshold_attribute' are provided (default: None).
        probability_attribute (str): index or JSONpath to locate probabilities(used with ModelQuality baseline).
            Used only with 'BinaryClassification' problem if 'inference_attribute' is not provided (default: None).
        probability_threshold_attribute (float): threshold to convert probabilities to binaries (used with ModelQuality baseline).
            Used only with 'BinaryClassification' problem if 'inference_attribute' is not provided (default: None).
        sagemaker_session (sagemaker.session.Session): Session object which manages interactions with Amazon SageMaker
            APIs and any other AWS services needed. If not specified, one is created using the default AWS configuration
            chain (default: None).
        data_config (sagemaker.clarify.DataConfig): Config of the input/output data used by ModelBias/ModelExplainability baselines
            refer to https://sagemaker.readthedocs.io/en/stable/api/training/processing.html#sagemaker.clarify.DataConfig
        bias_config (sagemaker.clarify.BiasConfig): Config of sensitive groups
            refer to https://sagemaker.readthedocs.io/en/stable/api/training/processing.html#sagemaker.clarify.BiasConfig
        model_config (sagemaker.clarify.ModelConfig): Config of the model and its endpoint to be created.
            Used by ModelBias/ModelExplainability baselines.
            refer to https://sagemaker.readthedocs.io/en/stable/api/training/processing.html#sagemaker.clarify.ModelConfig
        model_predicted_label_config (sagemaker.clarify.ModelPredictedLabelConfig): Config of how to extract the predicted label
            from the model output.Used by ModelBias baseline.
            refer to https://sagemaker.readthedocs.io/en/stable/api/training/processing.html#sagemaker.clarify.ModelPredictedLabelConfig
        explainability_config (sagemaker.clarify.SHAPConfig): Config of the specific explainability method. Currently, only SHAP is supported.
            Used by ModelExplainability baseline.
            refer to https://sagemaker.readthedocs.io/en/stable/api/training/processing.html#sagemaker.clarify.ExplainabilityConfig
        model_scores: (str or int): Index or JSONPath location in the model output for the predicted scores to be explained.
            This is not required if the model output is a single score. Used by ModelExplainability baseline.
        tags (list[dict[str, str]]): resource tags (default: None).
    """

    @exception_handler
    def __init__(
        self,  # NOSONAR:S107 the class is designed to take many attributes
        monitoring_type: str,
        instance_type: str,
        instance_count: int,
        instance_volume_size: int,
        role_arn: str,
        baseline_job_name: str,
        baseline_dataset: str,
        output_s3_uri: str,
        max_runtime_in_seconds: Optional[int] = None,
        kms_key_arn: Optional[str] = None,
        problem_type: Optional[str] = None,
        ground_truth_attribute: Optional[str] = None,
        inference_attribute: Optional[str] = None,
        probability_attribute: Optional[str] = None,
        probability_threshold_attribute: Optional[float] = None,
        sagemaker_session: Optional[sagemaker.session.Session] = None,
        data_config: Optional[DataConfig] = None,
        bias_config: Optional[BiasConfig] = None,
        model_config: Optional[ModelConfig] = None,
        model_predicted_label_config: Optional[ModelPredictedLabelConfig] = None,
        explainability_config: Optional[SHAPConfig] = None,
        model_scores: Optional[Union[str, int]] = None,
        tags: Optional[List[Dict[str, str]]] = None,
    ) -> None:
        # validate the provided monitoring_type
        if monitoring_type not in ["DataQuality", "ModelQuality", "ModelBias", "ModelExplainability"]:
            raise ValueError(
                (
                    f"The provided monitoring type: {monitoring_type} is not valid. "
                    + "It must be 'DataQuality'|'ModelQuality'|'ModelBias'|'ModelExplainability'"
                )
            )
        self.monitoring_type = monitoring_type
        self.instance_type = instance_type
        self.instance_count = instance_count
        self.instance_volume_size = instance_volume_size
        self.role_arn = role_arn
        self.baseline_job_name = baseline_job_name
        self.baseline_dataset = baseline_dataset
        self.output_s3_uri = output_s3_uri
        self.max_runtime_in_seconds = max_runtime_in_seconds
        self.kms_key_arn = kms_key_arn
        self.problem_type = problem_type
        self.ground_truth_attribute = ground_truth_attribute
        self.inference_attribute = inference_attribute
        self.probability_attribute = probability_attribute
        self.probability_threshold_attribute = probability_threshold_attribute
        self.sagemaker_session = sagemaker_session
        self.data_config = data_config
        self.bias_config = bias_config
        self.model_config = model_config
        self.model_predicted_label_config = model_predicted_label_config
        self.explainability_config = explainability_config
        self.model_scores = model_scores
        self.tags = tags

    @exception_handler
    def create_baseline_job(self) -> sagemaker.processing.ProcessingJob:
        """
        Gets the *BaselineJob based on the monitoring_type

        Returns:
            sagemaker.processing.ProcessingJob object
        """
        # create *Baseline Job MonitoringType->function_name map
        type_function_map = dict(
            DataQuality="_create_data_quality_baseline",
            ModelQuality="_create_model_quality_baseline",
            ModelBias="_create_model_bias_baseline",
            ModelExplainability="_create_model_explainability_baseline",
        )

        # get the formated baseline job arguments
        baseline_job_args = self._get_baseline_job_args()

        # call the right function to create the *Baseline Job
        baseline_processing_job = getattr(self, type_function_map[self.monitoring_type])(baseline_job_args)

        return baseline_processing_job

    @exception_handler
    def _get_baseline_job_args(
        self,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Gets the baseline job arguments to create the *baseline job

        Returns:
            dict[str, dict[str, Any]]: the arguments to create the *baseline job
        """
        # validate baseline_dataset
        if not self._is_valid_argument_value(self.baseline_dataset):
            raise ValueError(
                f"BaselineDataset S3Uri must be provided to create the {self.monitoring_type} baseline job"
            )

        baseline_args = dict(
            # args passed to the Monitor class's construct
            class_args=dict(
                instance_type=self.instance_type,
                instance_count=self.instance_count,
                volume_size_in_gb=self.instance_volume_size,
                role=self.role_arn,
            ),
            # args passed to the Monitor class's suggest_baseline function
            suggest_args=dict(
                job_name=self.baseline_job_name,
            ),
        )

        # add args valid only for DataQuality or ModelQuality
        if self.monitoring_type in ["DataQuality", "ModelQuality"]:
            baseline_args["suggest_args"].update(
                {
                    "dataset_format": DatasetFormat.csv(header=True),
                    "baseline_dataset": self.baseline_dataset,
                    "output_s3_uri": self.output_s3_uri,
                }
            )

        # add max_runtime_in_seconds if provided
        if self.max_runtime_in_seconds:
            baseline_args["class_args"].update({"max_runtime_in_seconds": self.max_runtime_in_seconds})

        # add sagemaker session if provided
        if self.sagemaker_session:
            baseline_args["class_args"].update({"sagemaker_session": self.sagemaker_session})

        # add tags if provided
        if self.tags:
            baseline_args["class_args"].update({"tags": self.tags})

        # add kms key if provided
        if self.kms_key_arn:
            baseline_args["class_args"].update({"output_kms_key": self.kms_key_arn})
            baseline_args["class_args"].update({"volume_kms_key": self.kms_key_arn})

        # add ModelQuality args
        if self.monitoring_type == "ModelQuality":
            baseline_args = self._add_model_quality_args(baseline_args)

        # add ModelBias args
        if self.monitoring_type == "ModelBias":
            baseline_args = self._add_model_bias_args(baseline_args)

        # add ModelQuality args
        if self.monitoring_type == "ModelExplainability":
            baseline_args = self._add_model_explainability_args(baseline_args)

        return baseline_args

    @exception_handler
    def _add_model_quality_args(
        self,
        baseline_args: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Adds ModelQuality's specific arguments to the passed baseline_args

        Args:
            baseline_args (dict[str, dict[str, Any]]): arguments to create the baseline job

        Returns:
            dict[str, dict[str, Any]]: The combined arguments to create the baseline job
        """
        # validate the problem_type
        if self.problem_type not in ["Regression", "BinaryClassification", "MulticlassClassification"]:
            raise ValueError(
                (
                    f"The {self.problem_type} is not valid. ProblemType must be "
                    + "['Regression'|'BinaryClassification'|'MulticlassClassification']"
                )
            )
        baseline_args["suggest_args"].update({"problem_type": self.problem_type})

        # For Regression or MulticlassClassification, inference_attribute is required
        if self.problem_type in ["Regression", "MulticlassClassification"]:
            # validate InferenceAttribute value
            if not self._is_valid_argument_value(self.inference_attribute):
                raise ValueError(
                    "InferenceAttribute must not be provided for ProblemType: Regression or MulticlassClassification"
                )
            # add to args dict
            baseline_args["suggest_args"].update({"inference_attribute": self.inference_attribute})
        # For BinaryClassification, use probability_attribute and probability_threshold_attribute or inference_attribute
        else:
            if self._is_valid_argument_value(self.probability_attribute) and self._is_valid_argument_value(
                self.probability_threshold_attribute
            ):
                baseline_args["suggest_args"].update({"probability_attribute": self.probability_attribute})
                baseline_args["suggest_args"].update(
                    {"probability_threshold_attribute": self.probability_threshold_attribute}
                )

            elif self._is_valid_argument_value(self.inference_attribute):
                baseline_args["suggest_args"].update({"inference_attribute": self.inference_attribute})
            else:
                raise ValueError(
                    (
                        "InferenceAttribute or (ProbabilityAttribute/ProbabilityThresholdAttribute) must be provided "
                        + "for ProblemType: BinaryClassification"
                    )
                )

        # validate ground_truth_attribute
        if not self._is_valid_argument_value(self.ground_truth_attribute):
            raise ValueError("GroundTruthAttribute must be provided")

        baseline_args["suggest_args"].update({"ground_truth_attribute": self.ground_truth_attribute})

        return baseline_args

    @exception_handler
    def _add_model_bias_args(
        self,
        baseline_args: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        baseline_args["suggest_args"].update(
            {
                "data_config": self.data_config,
                "bias_config": self.bias_config,
                "model_config": self.model_config,
                "model_predicted_label_config": self.model_predicted_label_config,
            }
        )

        # add kms_key, if provided, to encrypt the user code file
        if self.kms_key_arn:
            baseline_args["suggest_args"].update({"kms_key": self.kms_key_arn})

        return baseline_args

    @exception_handler
    def _add_model_explainability_args(
        self,
        baseline_args: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        baseline_args["suggest_args"].update(
            {
                "data_config": self.data_config,
                "explainability_config": self.explainability_config,
                "model_config": self.model_config,
                "model_scores": self.model_scores,
            }
        )

        # add kms_key, if provided, to encrypt the user code file
        if self.kms_key_arn:
            baseline_args["suggest_args"].update({"kms_key": self.kms_key_arn})

        return baseline_args

    @exception_handler
    def _create_data_quality_baseline(
        self, data_quality_baseline_job_args: Dict[str, Dict[str, Any]]
    ) -> sagemaker.processing.ProcessingJob:
        """
        Creates SageMaker DataQuality baseline job

        Args:
            data_quality_baseline_job_args (dict[str, dict[str, str]]): The DataQuality baseline job arguments

        Returns:
            sagemaker.processing.ProcessingJob object
        """
        logger.info(
            f"Creating DataQuality baseline job {data_quality_baseline_job_args['suggest_args']['job_name']} ..."
        )

        # create DefaultModel Monitor
        data_quality_monitor = DefaultModelMonitor(**data_quality_baseline_job_args["class_args"])

        # create the DataQuality baseline job
        data_quality_baseline_job = data_quality_monitor.suggest_baseline(
            **data_quality_baseline_job_args["suggest_args"],
        )

        return data_quality_baseline_job

    @exception_handler
    def _create_model_quality_baseline(
        self,
        model_quality_baseline_job_args: Dict[str, Dict[str, Any]],
    ) -> sagemaker.processing.ProcessingJob:
        """
        Creates SageMaker ModelQuality baseline job

        Args:
            model_quality_baseline_job_config (dict[str, dict[str, str]]): The ModelQuality baseline job arguments

        Returns:
            sagemaker.processing.ProcessingJob object
        """
        logger.info(
            f"Creating ModelQuality baseline job {model_quality_baseline_job_args['suggest_args']['job_name']} ..."
        )

        # create ModelQuality Monitor
        model_quality_monitor = ModelQualityMonitor(**model_quality_baseline_job_args["class_args"])

        # create the ModelQuality baseline job
        model_quality_baseline_job = model_quality_monitor.suggest_baseline(
            **model_quality_baseline_job_args["suggest_args"],
        )

        return model_quality_baseline_job

    @exception_handler
    def _create_model_bias_baseline(
        self,
        model_bias_baseline_job_args: Dict[str, Dict[str, Any]],
    ) -> sagemaker.processing.ProcessingJob:
        """
        Creates SageMaker ModelBias baseline job

        Args:
            model_bias_baseline_job_config (dict[str, dict[str, Any]]): The ModelBias baseline job arguments

        Returns:
            sagemaker.processing.ProcessingJob object
        """
        logger.info(f"Creating ModelBias baseline job {model_bias_baseline_job_args['suggest_args']['job_name']} ...")

        # create ModelBias Monitor
        model_bias_monitor = ModelBiasMonitor(**model_bias_baseline_job_args["class_args"])

        # create the ModelBias baseline job
        model_bias_baseline_job = model_bias_monitor.suggest_baseline(
            **model_bias_baseline_job_args["suggest_args"],
        )

        # get the analysis_config.json for Model Bias monitor
        analysis_config = model_bias_monitor.latest_baselining_job_config.analysis_config._to_dict()
        logger.info(f"Model Bias analysis config: {json.dumps(analysis_config)}")

        # upload ModelBias analysis_config.json file to S3
        self._upload_analysis_config(
            output_s3_uri=f"{self.output_s3_uri}/monitor/analysis_config.json", analysis_config=analysis_config
        )

        return model_bias_baseline_job

    @exception_handler
    def _create_model_explainability_baseline(
        self,
        model_explainability_baseline_job_args: Dict[str, Dict[str, Any]],
    ) -> sagemaker.processing.ProcessingJob:
        """
        Creates SageMaker ModelExplainability baseline job

        Args:
            model_explainability_baseline_job_config (dict[str, dict[str, Any]]): The ModelExplainability baseline job arguments

        Returns:
            sagemaker.processing.ProcessingJob object
        """
        logger.info(
            f"Creating ModelExplainability baseline job {model_explainability_baseline_job_args['suggest_args']['job_name']} ..."
        )

        # create ModelExplainability Monitor
        model_explainability_monitor = ModelExplainabilityMonitor(
            **model_explainability_baseline_job_args["class_args"]
        )

        # create the ModelExplainability baseline job
        model_explainability_baseline_job = model_explainability_monitor.suggest_baseline(
            **model_explainability_baseline_job_args["suggest_args"],
        )

        # get the analysis_config.json for Explainability monitor
        analysis_config = model_explainability_monitor.latest_baselining_job_config.analysis_config._to_dict()
        logger.info(f"model_explainability analysis config: {json.dumps(analysis_config)}")

        # upload Explainability analysis_config.json file to S3
        self._upload_analysis_config(
            output_s3_uri=f"{self.output_s3_uri}/monitor/analysis_config.json", analysis_config=analysis_config
        )

        return model_explainability_baseline_job

    def _is_valid_argument_value(self, value: str) -> bool:
        # validate the argument's value is not None or empty string
        return True if value else False

    @staticmethod
    @exception_handler
    def get_model_name(endpoint_name: str, sm_client: BaseClient) -> str:
        """
        Gets Baselines from Model Registry and Model Name from the deployed endpoint

        Args:
            endpoint_name (str): SageMaker Endpoint name to be monitored
            sm_client (Boto3 SageMaker client): Amazon SageMaker boto3 client

        Returns:
            str: SageMaker model name
        """
        # get the EndpointConfigName using the Endpoint Name
        endpoint_config_name = sm_client.describe_endpoint(EndpointName=endpoint_name)["EndpointConfigName"]

        # get the ModelName using EndpointConfigName
        model_name = sm_client.describe_endpoint_config(EndpointConfigName=endpoint_config_name)["ProductionVariants"][
            0
        ]["ModelName"]

        return model_name

    @staticmethod
    @exception_handler
    def get_baseline_dataset_header(bucket_name: str, file_key: str, s3_client: BaseClient) -> List[str]:
        """
        Get the baseline dataset's header (columns names) from teh baseline dataset csv
        file stored in the S3 Assets bucket

        Args:
            bucket_name (str): the bucket name where the json config file is stored
            file_key (str): baseline dataset csv file S3 key
            s3_client (BaseClient): S3 boto3 client

        Returns:
            header [column names] as List[str]
        """
        # read the baseline dataset csv  file from S3
        dataset = s3_client.get_object(Bucket=bucket_name, Key=file_key)["Body"].read().decode("utf-8")
        # Extract features names (row 1). Note the label is expected to be the first column
        header = dataset.split("\n")[0].split(",")

        return header

    @exception_handler
    def _upload_analysis_config(self, output_s3_uri: str, analysis_config: Dict[str, Any]):
        logger.info(f"uploading analysis_confg.json to {output_s3_uri}")
        analysis_config_uri = sagemaker.s3.S3Uploader.upload_string_as_file_body(
            json.dumps(analysis_config), desired_s3_uri=output_s3_uri, sagemaker_session=self.sagemaker_session
        )

        logger.info(f"analysis_confg.json uri is: {analysis_config_uri}")
