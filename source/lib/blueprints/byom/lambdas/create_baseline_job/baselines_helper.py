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
from typing import Callable, Any, Dict, List, Optional
import logging
import sagemaker
from sagemaker.model_monitor import DefaultModelMonitor
from sagemaker.model_monitor import ModelQualityMonitor
from sagemaker.model_monitor.dataset_format import DatasetFormat

logger = logging.getLogger(__name__)


def exception_handler(func: Callable[..., Any]) -> Any:
    """
    Docorator function to handle exceptions

    Args:
        func (object): function to be decorated

    Returns:
        func's return value

    Raises:
        Exception thrown by the decorated function
    """

    def wrapper_function(*args, **kwargs):
        try:
            return func(*args, **kwargs)

        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            raise e

    return wrapper_function


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
        sagemaker_session: (sagemaker.session.Session): Session object which manages interactions with Amazon SageMaker
            APIs and any other AWS services needed. If not specified, one is created using the default AWS configuration
            chain (default: None).
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
        tags: Optional[List[Dict[str, str]]] = None,
    ) -> None:
        # validate the provided monitoring_type
        if monitoring_type not in ["DataQuality", "ModelQuality"]:
            raise ValueError(
                (
                    f"The provided monitoring type: {monitoring_type} is not valid. "
                    + "It must be 'DataQuality'|'ModelQuality'"
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
            DataQuality="_create_data_quality_baseline", ModelQuality="_create_model_quality_baseline"
        )

        # get the formated baseline job arguments
        baseline_job_args = self._get_baseline_job_args()

        # call the right function to create the *Baseline Job
        baseline_processing_job = getattr(self, type_function_map[self.monitoring_type])(baseline_job_args)

        return baseline_processing_job

    @exception_handler
    def _get_baseline_job_args(
        self,
    ) -> Dict[str, Dict[str, str]]:
        """
        Gets the baseline job arguments to create the *baseline job

        Returns:
            dict[str, dict[str, str]]: the arguments to create the *baseline job
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
                dataset_format=DatasetFormat.csv(header=True),
                baseline_dataset=self.baseline_dataset,
                output_s3_uri=self.output_s3_uri,
            ),
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

        return baseline_args

    @exception_handler
    def _add_model_quality_args(
        self,
        baseline_args: Dict[str, Dict[str, str]],
    ) -> Dict[str, Dict[str, str]]:
        """
        Adds ModelQuality's specific arguments to the passed baseline_args

        Args:
            baseline_args (dict[str, dict[str, str]]): arguments to create the baseline job

        Returns:
            dict[str, dict[str, str]]: The combined arguments to create the baseline job
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
    def _create_data_quality_baseline(
        self, data_quality_baseline_job_args: Dict[str, Dict[str, str]]
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

        # create DefaultModelMonitor
        data_quality_monitor = DefaultModelMonitor(**data_quality_baseline_job_args["class_args"])

        # create the DataQuality baseline job
        data_baseline_job = data_quality_monitor.suggest_baseline(
            **data_quality_baseline_job_args["suggest_args"],
        )

        return data_baseline_job

    @exception_handler
    def _create_model_quality_baseline(
        self,
        model_quality_baseline_job_args: Dict[str, Dict[str, str]],
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

        # create ModelQualityMonitor
        model_quality_monitor = ModelQualityMonitor(**model_quality_baseline_job_args["class_args"])

        # create the DataQuality baseline job
        model_baseline_job = model_quality_monitor.suggest_baseline(
            **model_quality_baseline_job_args["suggest_args"],
        )

        return model_baseline_job

    def _is_valid_argument_value(self, value: str) -> bool:
        # validate the argument's value is not None or empty string
        return True if value else False
