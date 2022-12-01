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
from typing import Optional, Union, List, Dict, Any
import json
import boto3
from sagemaker.session import Session
from sagemaker.model_card import (
    Environment,
    ModelOverview,
    IntendedUses,
    ObjectiveFunction,
    Metric,
    TrainingDetails,
    MetricGroup,
    EvaluationJob,
    AdditionalInformation,
    ModelCard,
    Function,
    TrainingJobDetails,
    RiskRatingEnum,
    ObjectiveFunctionEnum,
    FacetEnum,
    MetricTypeEnum,
    ModelCardStatusEnum,
    EvaluationMetricTypeEnum,
)

from sagemaker.model_card.model_card import TrainingMetric
from shared.helper import DateTimeEncoder
from shared.logger import get_logger
from shared.wrappers import exception_handler

logger = get_logger(__name__)


class SolutionModelCardHelpers:
    @classmethod
    @exception_handler
    def get_environment(cls, container_image: List[str]) -> Union[Environment, None]:
        """Initialize an Environment object.

        Args:
            container_image (list[str]): A list of SageMaker training/inference image URIs. The maximum list length is 15.
        """
        return Environment(container_image=container_image) if container_image else None

    @classmethod
    @exception_handler
    def list_model_cards(cls, sagemaker_session: Session) -> Dict[str, Any]:
        """List all model cards in the SageMaker service.

        Args:
            sagemaker_session (sagemaker.session.Session): SageMaker session.
        Returns:
            a Python dictionary with all model cards
        """
        return sagemaker_session.sagemaker_client.list_model_cards()

    @classmethod
    @exception_handler
    def get_model_overview(
        cls, model_name: Optional[str] = None, sagemaker_session: Session = None, **kwargs
    ) -> ModelOverview:
        """Initialize a Model Overview object.

        Args:
            model_name (str, optional): A unique name for the model (default: None).
            sagemaker_session (sagemaker.session.Session): SageMaker session (default: None).
            model_id (str, optional): A SageMaker Model ARN or non-SageMaker Model ID (default: None).
            kwargs: possible values:
                model_description (str, optional): A description of the model (default: None).
                model_version (int or float, optional): The version of the model (default: None).
                problem_type (str, optional): The type of problem that the model solves. For example, "Binary Classification", "Multiclass Classification", "Linear Regression", "Computer Vision", or "Natural Language Processing" (default: None).
                algorithm_type (str, optional): The algorithm used to solve the problem type (default: None).
                model_creator (str, optional): The organization, research group, or authors that created the model (default: None).
                model_owner (str, optional): The individual or group that maintains the model in your organization (default: None).
                model_artifact (List[str], optional): A list of model artifact location URIs. The maximum list size is 15. (default: None).
                inference_environment (Environment, optional): An overview of the model's inference environment (default: None).
        Returns:
            sagemaker.model_card.ModelOverview
        """
        # automatically get ModelOverview from model name is provided
        if model_name:
            return ModelOverview.from_model_name(model_name=model_name, sagemaker_session=sagemaker_session, **kwargs)
        else:
            # update inference_environment if provided
            inference_environment = kwargs.get("inference_environment")
            kwargs.update(
                {"inference_environment": cls.get_environment(inference_environment) if inference_environment else None}
            )
            return ModelOverview(**kwargs)

    @classmethod
    @exception_handler
    def get_intended_uses(
        cls,
        purpose_of_model: Optional[str] = None,
        intended_uses: Optional[str] = None,
        factors_affecting_model_efficiency: Optional[str] = None,
        risk_rating: Optional[Union[RiskRatingEnum, str]] = RiskRatingEnum.UNKNOWN,
        explanations_for_risk_rating: Optional[str] = None,
    ) -> IntendedUses:
        """Initialize an Intended Uses object.

        Args:
            purpose_of_model (str, optional): The general purpose of this model (default: None).
            intended_uses (str, optional): The intended use cases for this model (default: None).
            factors_affecting_model_efficiency (str, optional): Factors affecting model efficacy (default: None).
            risk_rating (RiskRatingEnum or str, optional): Your organization's risk rating for this model. It is highly recommended to use sagemaker.model_card.RiskRatingEnum. Possible values include: ``RiskRatingEnum.HIGH`` ("High"), ``RiskRatingEnum.LOW`` ("Low"), ``RiskRatingEnum.MEDIUM`` ("Medium"), or ``RiskRatingEnum.UNKNOWN`` ("Unknown"). Defaults to ``RiskRatingEnum.UNKNOWN``.
            explanations_for_risk_rating (str, optional): An explanation of why your organization categorizes this model with this risk rating (default: None).
        Returns:
            sagemaker.model_card.IntendedUses
        """
        return IntendedUses(
            purpose_of_model=purpose_of_model,
            intended_uses=intended_uses,
            factors_affecting_model_efficiency=factors_affecting_model_efficiency,
            risk_rating=risk_rating,
            explanations_for_risk_rating=explanations_for_risk_rating,
        )

    @classmethod
    @exception_handler
    def get_objective_function(
        cls,
        function: Optional[Union[ObjectiveFunctionEnum, str]] = None,
        facet: Optional[Union[FacetEnum, str]] = None,
        condition: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> ObjectiveFunction:
        """Initialize an Objective Function object.

        Args:
            function (ObjectiveFunctionEnum or str, optional): The optimization direction of the model's objective function. It is highly recommended to use sagemaker.model_card.ObjectiveFunctionEnum. Possible values include: ``ObjectiveFunctionEnum.MAXIMIZE`` ("Maximize") or ``ObjectiveFunctionEnum.MINIMIZE`` ("Minimize") (default: None).
            facet (FacetEnum or str, optional): The metric of the model's objective function. For example, `loss` or `rmse`. It is highly recommended to use sagemaker.model_card.FacetEnum. Possible values include:, ``FacetEnum.ACCURACY`` ("Accuracy"), ``FacetEnum.AUC`` ("AUC"), ``FacetEnum.LOSS`` ("Loss"), ``FacetEnum.MAE`` ("MAE"), or ``FacetEnum.RMSE`` ("RMSE") (default: None).
            condition (str, optional): An optional description of any conditions of your objective function metric (default: None).
            notes (str, optional): Notes about the objective function, including other considerations for possible objective functions (default: None).
        Returns:
            sagemaker.model_card.ObjectiveFunction
        """
        return ObjectiveFunction(function=Function(function=function, facet=facet, condition=condition), notes=notes)

    @classmethod
    @exception_handler
    def get_metric(
        cls,
        name: str,
        type: Union[MetricTypeEnum, str],
        value: Union[int, float, str, bool, List],
        notes: Optional[str] = None,
        x_axis_name: Optional[Union[str, list]] = None,
        y_axis_name: Optional[Union[str, list]] = None,
    ) -> Metric:
        """Initialize a Metric object.

        Args:
            name (str): The name of the metric.
            type (str or MetricTypeEnum): It is highly recommended to use sagemaker.model_card.MetricTypeEnum. Possible values include:
            ``MetricTypeEnum.BAR_CHART`` ("bar_char"), ``MetricTypeEnum.BOOLEAN`` ("boolean"),
            ``MetricTypeEnum.LINEAR_GRAPH`` ("linear_graph"), ``MetricTypeEnum.MATRIX`` ("matrix"), ``MetricTypeEnum.NUMBER``
            ("number"), or ``MetricTypeEnum.STRING`` ("string").
            value (int or float or str or bool or List): The datatype of the metric. The metric's `value` must be compatible with the metric's `type`.
            notes (str, optional): Any notes to add to the metric (default: None).
            x_axis_name (str, optional): The name of the x axis (default: None).
            y_axis_name (str, optional): The name of the y axis (default: None).
        Returns:
            sagemaker.model_card.Metric
        """
        return Metric(name=name, type=type, value=value, notes=notes, x_axis_name=x_axis_name, y_axis_name=y_axis_name)

    @classmethod
    @exception_handler
    def get_metric_group(cls, name: str, metric_data: Optional[List[Dict[str, Any]]] = None) -> MetricGroup:
        """Initialize a Metric Group object.

        Args:
            name (str): The metric group name.
            metric_data (List[Dict[str, Any]]): A list of dictionaries representing metrics.
        Returns:
            sagemaker.model_card.MetricGroup
        """
        return MetricGroup(
            name=name, metric_data=[cls.get_metric(**metric) for metric in metric_data] if metric_data else None
        )

    @classmethod
    @exception_handler
    def get_training_metric(
        cls,
        name: str,
        value: Union[int, float],
        notes: Optional[str] = None,
    ) -> TrainingMetric:
        """Initialize a TrainingMetric object.

        Args:
            name (str): The metric name.
            value (int or float): The metric value.
            notes (str, optional): Notes on the metric (default: None).
        Returns:
            sagemaker.model_card.TrainingMetric
        """
        return TrainingMetric(name=name, value=value, notes=notes)

    @classmethod
    @exception_handler
    def get_training_job_details(
        cls,
        training_arn: Optional[str] = None,
        training_datasets: Optional[List[str]] = None,
        training_environment: Optional[List[str]] = None,
        training_metrics: Optional[List[Dict[str, Any]]] = None,
        user_provided_training_metrics: Optional[List[Dict[str, Any]]] = None,
    ) -> TrainingJobDetails:
        """Initialize a Training Job Details object.

        Args:
            training_arn (str, optional): The SageMaker training job Amazon Resource Name (ARN) (default: None).
            training_datasets (List[str], optional): The location of the datasets used to train the model. The maximum list size is 15. (default: None).
            training_environment (Environment, optional): The SageMaker training image URI. (default: None).
            training_metrics (List[Dict[str, Any]], optional): SageMaker training job results. The maximum `training_metrics` list length is 50 (default: None).
            user_provided_training_metrics (List[Dict[str, Any]], optional): Custom training job results. The maximum `user_provided_training_metrics` list length is 50 (default: None).
        Returns:
            sagemaker.model_card.TrainingJobDetails
        """
        return TrainingJobDetails(
            training_arn=training_arn,
            training_datasets=training_datasets,
            training_environment=cls.get_environment(training_environment),
            training_metrics=[cls.get_training_metric(**metric) for metric in training_metrics]
            if training_metrics
            else None,
            user_provided_training_metrics=[
                cls.get_training_metric(**metric) for metric in user_provided_training_metrics
            ]
            if user_provided_training_metrics
            else None,
        )

    @classmethod
    @exception_handler
    def get_training_details(
        cls,
        model_name: Optional[str] = None,
        training_job_name: Optional[str] = None,
        objective_function: Optional[Dict[str, Any]] = None,
        training_observations: Optional[str] = None,
        training_job_details: Optional[Dict[str, Any]] = None,
        sagemaker_session: Session = None,
    ) -> TrainingDetails:
        """Initialize a TrainingDetails object.

        Args:
            model_name (str, optional): existing model name, to be used to auto-discover training details.
            training_job_name (str, optional): training job name, to be used to auto-discover training details.
            objective_function (Dict[str, Any], optional): The objective function that is optimized during training (default: None).
            training_observations (str, optional): Any observations about training (default: None).
            training_job_details (Dict[str, Any], optional): Details about any associated training jobs (default: None).
            sagemaker_session (Session): sagemaker session (default: None).
        Returns:
            sagemaker.model_card.TrainingDetails
        """
        # if model_name was provided, auto-discover training details from model_overview
        if model_name:
            return TrainingDetails.from_model_overview(
                model_overview=ModelOverview.from_model_name(
                    model_name=model_name, sagemaker_session=sagemaker_session
                ),
                sagemaker_session=sagemaker_session,
            )
        # else, if training_job_name was provided, aut-discover training details from job name
        elif training_job_name:
            return TrainingDetails.from_training_job_name(
                training_job_name=training_job_name, sagemaker_session=sagemaker_session
            )
        # else create TrainingDetails using other provided params
        else:
            return TrainingDetails(
                objective_function=cls.get_objective_function(**objective_function) if objective_function else None,
                training_observations=training_observations,
                training_job_details=cls.get_training_job_details(**training_job_details)
                if training_job_details
                else None,
            )

    @classmethod
    @exception_handler
    def get_evaluation_job(
        cls,
        name: str,
        metric_file_s3_url: Optional[str] = None,
        metric_type: Optional[Union[EvaluationMetricTypeEnum, str]] = None,
        evaluation_observation: Optional[str] = None,
        evaluation_job_arn: Optional[str] = None,
        datasets: Optional[List[str]] = None,
        metadata: Optional[dict] = None,
        metric_groups: Optional[List[Dict[str, Any]]] = None,
    ) -> EvaluationJob:
        """Initialize an Evaluation Job object.

        Args:
            name (str): The evaluation job name.
            metric_file_s3_url (str. optional): metric file's s3 bucket url, to be used to auto-discover evaluation metrics (default: None).
            metric_type (str, optional): one of model_card_metric_schema|clarify_bias|clarify_explainability|regression|binary_classification|multiclass_classification.
                Required  if metric_file_s3_url is provide (default: None).
            evaluation_observation (str, optional): Any observations made during model evaluation (default: None).
            evaluation_job_arn (str, optional): The Amazon Resource Name (ARN) of the evaluation job (default: None).
            datasets (List[str], optional): Evaluation dataset locations. Maximum list length is 10 (default: None).
            metadata (Optional[dict], optional): Additional attributes associated with the evaluation results (default: None).
            metric_groups (List[Dict[str, Any], optional): An evaluation Metric Group object (default: None).
        Returns:
            sagemaker.model_card.EvaluationJob
        """
        # define a map for metric_type
        metric_type_map = {
            "model_card_metric_schema": EvaluationMetricTypeEnum.MODEL_CARD_METRIC_SCHEMA,
            "clarify_bias": EvaluationMetricTypeEnum.CLARIFY_BIAS,
            "clarify_explainability": EvaluationMetricTypeEnum.CLARIFY_EXPLAINABILITY,
            "regression": EvaluationMetricTypeEnum.REGRESSION,
            "binary_classification": EvaluationMetricTypeEnum.BINARY_CLASSIFICATION,
            "multiclass_classification": EvaluationMetricTypeEnum.MULTICLASS_CLASSIFICATION,
        }
        # if metric_file_s3_url provided, add metric group from json file in s3
        if metric_file_s3_url:
            # check metric_type is provided
            if not metric_type:
                raise ValueError("metric_type type is required if evaluation metrics are to be loaded from s3 url")
            if metric_type not in metric_type_map.keys():
                raise ValueError(
                    "metric_type must be one of model_card_metric_schema|clarify_bias|clarify_explainability|regression|binary_classification|multiclass_classification"
                )
            # create EvaluationJob
            evaluation_job = EvaluationJob(name=name)
            # add metric group from s3 url
            evaluation_job.add_metric_group_from_s3(
                session=boto3.session.Session(),
                s3_url=metric_file_s3_url,
                metric_type=metric_type_map.get(metric_type),
            )
            return evaluation_job
        # else construct EvaluationJob from user provided params
        else:
            return EvaluationJob(
                name=name,
                evaluation_observation=evaluation_observation,
                evaluation_job_arn=evaluation_job_arn,
                datasets=datasets,
                metadata=metadata,
                metric_groups=[cls.get_metric_group(**metric_group) for metric_group in metric_groups]
                if metric_groups
                else None,
            )

    @classmethod
    @exception_handler
    def get_additional_information(
        cls,
        ethical_considerations: Optional[str] = None,
        caveats_and_recommendations: Optional[str] = None,
        custom_details: Optional[dict] = None,
    ) -> AdditionalInformation:
        """Initialize an Additional Information object.

        Args:
            ethical_considerations (str, optional): Any ethical considerations to document about the model (default: None).
            caveats_and_recommendations (str, optional): Caveats and recommendations for those who might use this model in their applications (default: None).
            custom_details (dict, optional): Any additional custom information to document about the model (default: None).
        Returns:
            sagemaker.model_card.AdditionalInformation
        """
        return AdditionalInformation(
            ethical_considerations=ethical_considerations,
            caveats_and_recommendations=caveats_and_recommendations,
            custom_details=custom_details,
        )


class SolutionModelCard:
    def __init__(
        self,  # NOSONAR:S107 this function is designed to take many arguments
        name: str,
        status: Optional[Union[ModelCardStatusEnum, str]] = ModelCardStatusEnum.DRAFT,
        arn: Optional[str] = None,
        version: Optional[int] = None,
        created_by: Optional[dict] = None,
        last_modified_by: Optional[dict] = None,
        model_overview: Optional[ModelOverview] = None,
        intended_uses: Optional[IntendedUses] = None,
        training_details: Optional[TrainingDetails] = None,
        evaluation_details: Optional[List[EvaluationJob]] = None,
        additional_information: Optional[AdditionalInformation] = None,
        sagemaker_session: Optional[Session] = None,
    ):
        self.name = name
        self.arn = arn
        self.status = status
        self.version = version
        self.created_by = created_by
        self.last_modified_by = last_modified_by
        self.model_overview = model_overview
        self.intended_uses = intended_uses
        self.training_details = training_details
        self.evaluation_details = evaluation_details
        self.additional_information = additional_information
        self.sagemaker_session = sagemaker_session

    @exception_handler
    def create_model_card(self):
        # constructing ModelCard object
        model_card = ModelCard(
            name=self.name,
            status=self.status,
            arn=self.arn,
            version=self.version,
            created_by=self.created_by,
            last_modified_by=self.last_modified_by,
            model_overview=self.model_overview,
            intended_uses=self.intended_uses,
            training_details=self.training_details,
            evaluation_details=self.evaluation_details,
            additional_information=self.additional_information,
            sagemaker_session=self.sagemaker_session,
        )
        # create model card
        model_card.create()
        logger.info(f"Model Card with the name: {self.name} has been created...")

    @exception_handler
    def delete_model_card(self):
        # create ModelCard object for the card to be deleted
        model_card = ModelCard(name=self.name)
        # delete the model card
        model_card.delete()
        logger.info(f"Model Card with the name: {self.name} has been deleted...")

    @exception_handler
    def describe_model_card(self) -> Dict[str, Any]:
        model_card_info = self.sagemaker_session.sagemaker_client.describe_model_card(ModelCardName=self.name)
        return model_card_info

    @classmethod
    @exception_handler
    def load_model_card(cls, name: str, version: Optional[int] = None, sagemaker_session: Session = None) -> ModelCard:
        model_card = ModelCard.load(
            name=name,
            version=version,
            sagemaker_session=sagemaker_session,
        )
        logger.info(f"Model Card with the name: {name} has been loaded...")
        return model_card

    @exception_handler
    def update_model_card(self):
        # load model card
        model_card = self.load_model_card(
            name=self.name, version=self.version, sagemaker_session=self.sagemaker_session
        )
        # only include provided params (non-None vales), and exclude name, arn, and sagemaker_session
        keywords = dict(
            filter(
                lambda elem: elem[1] is not None and elem[0] not in ["name", "arn", "sagemaker_session"],
                self.__dict__.items(),
            )
        )
        # update model card
        model_card.update(**keywords)
        logger.info(f"Model Card with the name: {self.name} has been updated...")

    @staticmethod
    @exception_handler
    def export_model_card(
        model_card: ModelCard,
        s3_output_path: str,
        export_job_name: Optional[str] = None,
        model_card_version: Optional[int] = None,
    ):

        model_card.export_pdf(
            s3_output_path=s3_output_path, export_job_name=export_job_name, model_card_version=model_card_version
        )
        logger.info(f"Model Card with the name: {model_card.name} has been exported...")


class SolutionModelCardAPIs:
    def __init__(self, event: Dict[str, Any], sagemaker_session: Session):
        self.event = event
        self.name = event.get("name")
        self.status = event.get("status", "Draft")
        self.arn = event.get("arn")
        self.version = event.get("version")
        self.created_by = event.get("created_by")
        self.last_modified_by = event.get("last_modified_by")
        self.expected_model_overview_params = [
            "model_id",
            "model_name",
            "model_description",
            "model_version",
            "problem_type",
            "algorithm_type",
            "model_creator",
            "model_owner",
            "model_artifact",
            "inference_environment",
        ]
        self.expected_intended_uses_params = [
            "purpose_of_model",
            "intended_uses",
            "factors_affecting_model_efficiency",
            "risk_rating",
            "explanations_for_risk_rating",
        ]
        self.expected_training_details_params = [
            "model_name",
            "training_job_name",
            "objective_function",
            "training_observations",
            "training_job_details",
        ]

        self.expected_evaluation_details_params = [
            "name",
            "metric_file_s3_url",
            "metric_type",
            "evaluation_observation",
            "evaluation_job_arn",
            "datasets",
            "metadata",
            "metric_groups",
        ]
        self.expected_additional_information_params = [
            "ethical_considerations",
            "caveats_and_recommendations",
            "custom_details",
        ]
        self.model_overview = self._filter_expected_params(
            event.get("model_overview", {}), self.expected_model_overview_params
        )
        self.intended_uses = self._filter_expected_params(
            event.get("intended_uses", {}), self.expected_intended_uses_params
        )
        self.training_details = self._filter_expected_params(
            event.get("training_details", {}), self.expected_training_details_params
        )
        self.evaluation_details = [
            self._filter_expected_params(evaluation_details, self.expected_evaluation_details_params)
            for evaluation_details in event.get("evaluation_details", [])
        ]
        self.additional_information = self._filter_expected_params(
            event.get("additional_information", {}), self.expected_additional_information_params
        )
        self.sagemaker_session = sagemaker_session

    @classmethod
    @exception_handler
    def _filter_expected_params(cls, params: Dict[str, Any], expected_params: List[str]) -> Dict[str, Any]:
        return {key: params[key] for key in params.keys() if key in expected_params}

    @classmethod
    @exception_handler
    def _api_response(cls, message: str):
        return {
            "statusCode": 200,
            "isBase64Encoded": False,
            "body": json.dumps(
                {
                    "message": message,
                },
                indent=4,
                cls=DateTimeEncoder,
            ),
            "headers": {"Content-Type": "plain/text"},
        }

    @exception_handler
    def _create_solutions_card_object(self):
        # create solution model card object
        solutions_card_object = SolutionModelCard(
            name=self.name,
            status=self.status,
            arn=self.arn,
            version=self.version,
            created_by=self.created_by,
            last_modified_by=self.last_modified_by,
            # create objects if some params are provided. Otherwise, pass None
            model_overview=SolutionModelCardHelpers.get_model_overview(**self.model_overview)
            if self.model_overview
            else None,
            intended_uses=SolutionModelCardHelpers.get_intended_uses(**self.intended_uses)
            if self.intended_uses
            else None,
            training_details=SolutionModelCardHelpers.get_training_details(**self.training_details)
            if self.training_details
            else None,
            evaluation_details=[
                SolutionModelCardHelpers.get_evaluation_job(**evaluation_details)
                for evaluation_details in self.evaluation_details
            ]
            if self.evaluation_details
            else None,
            additional_information=SolutionModelCardHelpers.get_additional_information(**self.additional_information)
            if self.additional_information
            else None,
            sagemaker_session=self.sagemaker_session,
        )
        return solutions_card_object

    @exception_handler
    def create(self):
        # create model card
        self._create_solutions_card_object().create_model_card()
        # describe the create model card to return in the API call's response
        return self._api_response(
            SolutionModelCard(name=self.name, sagemaker_session=self.sagemaker_session).describe_model_card()
        )

    @exception_handler
    def update(self):
        # update model card
        self._create_solutions_card_object().update_model_card()
        # describe the updated model card to return in the API call's response
        return self._api_response(
            SolutionModelCard(name=self.name, sagemaker_session=self.sagemaker_session).describe_model_card()
        )

    @exception_handler
    def delete(self):
        SolutionModelCard(name=self.name, sagemaker_session=self.sagemaker_session).delete_model_card()
        return self._api_response(f"Model card with the name: {self.name} has been deleted")

    @exception_handler
    def describe(self):
        # describe the model card
        response = SolutionModelCard(name=self.name, sagemaker_session=self.sagemaker_session).describe_model_card()
        logger.info(response)
        return self._api_response(response)

    @exception_handler
    def list_model_cards(self):
        response = SolutionModelCardHelpers.list_model_cards(sagemaker_session=self.sagemaker_session)
        logger.info(response)
        return self._api_response(response)

    @exception_handler
    def export_to_pdf(self, s3_output_path: str):
        # load model card first
        model_card = SolutionModelCard.load_model_card(name=self.name, sagemaker_session=self.sagemaker_session)
        # export model card to s3 as a pdf file
        SolutionModelCard.export_model_card(
            model_card=model_card,
            s3_output_path=s3_output_path,
            export_job_name=self.event.get("export_job_name"),
            model_card_version=int(self.event.get("model_card_version"))
            if self.event.get("model_card_version")
            else None,
        )
        return self._api_response(f"Model card with the name: {self.name} has been exported to {s3_output_path}")
