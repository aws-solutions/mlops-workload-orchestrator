import unittest
import pytest
import json
from unittest import TestCase
from unittest.mock import patch, Mock
from sagemaker.model_card import (
    Environment,
    ModelOverview,
    RiskRatingEnum,
    TrainingJobDetails,
    TrainingDetails,
    ModelCard,
)
from solution_model_card import SolutionModelCardHelpers, SolutionModelCard, SolutionModelCardAPIs


class TestSolutionModelCardHelpers(unittest.TestCase):
    def setUp(self):
        self.model_name = "test-model"
        self.model_id = "arn:model-name"
        self.container_image = ["<account-id>.dkr.ecr.us-east-2.amazonaws.com/sagemaker-sklearn-automl:2.5-1-cpu-py3"]
        # intended uses
        self.intended_uses = dict(
            purpose_of_model="customer churn",
            intended_uses="marketing allocation",
            factors_affecting_model_efficiency="data quality",
            risk_rating=RiskRatingEnum.MEDIUM,
        )
        # objective function
        self.objective_function = dict(function="Maximize", facet="AUC")
        # metric
        self.metric = dict(name="metric", type="linear_graph", value=[1.4, 1.5, 1.6])

        # metric group
        self._metric_group_name = "metric-group"
        # additional information
        self.additional_information = dict(
            ethical_considerations="evaluate model regularly", custom_details={"department": "marketing"}
        )

        # training job details
        self.training_job_details = dict(
            training_arn="training-job-arn",
            training_datasets=["s3://test-bucket/data/csv"],
            training_environment=self.container_image,
        )

        # training details
        self.training_details = dict(
            training_arn="training-jon-arn",
            training_metrics=[
                SolutionModelCardHelpers.get_training_metric(name=self.metric["name"], value=self.metric["value"])
            ],
        )
        self.training_job_name = "test-job-name"
        self.list_model_cards_response = {
            "ModelCardSummaries": [
                {
                    "ModelCardName": "TestModelCard",
                    "ModelCardArn": "arn:aws:sagemaker:<region>:account-id:model-card/TestModelCard",
                    "ModelCardStatus": "Draft",
                }
            ]
        }

    def test_get_environment(self):
        environment = SolutionModelCardHelpers.get_environment(self.container_image)
        assert environment.container_image == self.container_image

    @patch("sagemaker.model_card.ModelOverview.from_model_name")
    def test_get_model_overview(self, patched_model_overview):
        patched_model_overview.return_value = ModelOverview(
            model_name=self.model_name,
            model_id=self.model_id,
            inference_environment=Environment(container_image=self.container_image),
        )
        model_overview = SolutionModelCardHelpers.get_model_overview(model_name=self.model_name)
        assert model_overview.model_name == self.model_name
        assert model_overview.model_id == self.model_id
        assert model_overview.inference_environment.container_image == self.container_image

    def test_get_intended_uses(self):
        intended_uses = SolutionModelCardHelpers.get_intended_uses(**self.intended_uses)
        assert intended_uses.purpose_of_model == self.intended_uses["purpose_of_model"]
        assert intended_uses.risk_rating == RiskRatingEnum.MEDIUM
        assert intended_uses.explanations_for_risk_rating is None

    def test_get_objective_function(self):
        objective_function = SolutionModelCardHelpers.get_objective_function(**self.objective_function)
        assert objective_function.function.function == self.objective_function["function"]
        assert objective_function.function.facet == self.objective_function["facet"]
        assert objective_function.function.condition is None
        assert objective_function.notes is None

    def test_get_metric(self):
        metric = SolutionModelCardHelpers.get_metric(**self.metric)
        assert metric.name == self.metric["name"]
        assert metric.type == self.metric["type"]
        TestCase().assertEqual(metric.value, self.metric["value"])
        assert metric.notes is None
        assert metric.x_axis_name is None

    def test_get_metric_group(self):
        metric_group = SolutionModelCardHelpers.get_metric_group(
            name=self._metric_group_name,
        )
        assert metric_group.name == self._metric_group_name
        assert len(metric_group.metric_data) == 0
        # add metric
        metric_group.add_metric(SolutionModelCardHelpers.get_metric(**self.metric))
        assert metric_group.metric_data[0].name == self.metric["name"]

    def test_get_training_metric(self):
        training_metric = SolutionModelCardHelpers.get_training_metric(
            name=self.metric["name"], value=self.metric["value"]
        )
        assert training_metric.name == self.metric["name"]
        assert training_metric.value == self.metric["value"]
        assert training_metric.notes is None

    def test_get_training_job_details(self):
        training_job_details = SolutionModelCardHelpers.get_training_job_details(**self.training_job_details)
        assert training_job_details.training_arn == self.training_job_details["training_arn"]
        assert len(training_job_details.user_provided_training_metrics) == 0

    @patch("sagemaker.model_card.TrainingDetails.from_training_job_name")
    @patch("sagemaker.model_card.TrainingDetails.from_model_overview")
    @patch("sagemaker.model_card.ModelOverview.from_model_name")
    def test_get_training_details(
        self, patched_from_model_name, patched_from_model_overview, patched_from_training_job_name
    ):
        # create the return value
        returned_training_details = TrainingDetails(training_job_details=TrainingJobDetails(**self.training_details))
        # 1 - assert when model_name is provided
        # set the return vale for ModelOverview.from_model_name
        patched_from_model_name.return_value = ModelOverview(
            model_name=self.model_name,
            model_id=self.model_id,
            inference_environment=Environment(container_image=self.container_image),
        )
        # set the return vale for TrainingDetails.from_model_overview
        patched_from_model_overview.return_value = returned_training_details
        training_details_from_model_overview = SolutionModelCardHelpers.get_training_details(model_name=self.model_name)
        assert (
            training_details_from_model_overview.training_job_details.training_arn
            == self.training_details["training_arn"]
        )
        TestCase().assertEqual(
            training_details_from_model_overview.training_job_details.training_metrics,
            self.training_details["training_metrics"],
        )
        # 2 - assert when training_job_name is provided
        patched_from_training_job_name.return_value = returned_training_details
        training_details_from_job_name = SolutionModelCardHelpers.get_training_details(
            training_job_name=self.training_job_name
        )
        assert training_details_from_job_name.training_job_details.training_arn == self.training_details["training_arn"]

        # 3 - assert when other params are provided
        training_details = SolutionModelCardHelpers.get_training_details(training_job_details=self.training_job_details)

        assert training_details.training_job_details.training_arn == self.training_job_details["training_arn"]
        assert len(training_details.training_job_details.user_provided_training_metrics) == 0
        assert training_details.training_observations is None

    def test_get_additional_information(self):
        additional_information = SolutionModelCardHelpers.get_additional_information(**self.additional_information)
        assert additional_information.ethical_considerations == self.additional_information["ethical_considerations"]
        assert additional_information.caveats_and_recommendations is None
        TestCase().assertEqual(additional_information.custom_details, self.additional_information["custom_details"])

    @patch("sagemaker.Session")
    def test_list_model_cards(self, patched_session):
        patched_session.sagemaker_client.list_model_cards = Mock(return_value=self.list_model_cards_response)
        response = SolutionModelCardHelpers.list_model_cards(patched_session)
        assert response["ModelCardSummaries"][0]["ModelCardName"] == "TestModelCard"

    @patch("sagemaker.model_card.EvaluationJob.add_metric_group_from_s3")
    def test_get_evaluation_job(self, patched_add_metric_group_from_s3):
        job_name = "test-job"
        evaluation_job_arn = f"arn:evaluation-job/{job_name}"
        metric_file_s3_url = "s3://bucket/clarify.json"
        # test for error when metric_file_s3_url but metric_type is not provided
        with pytest.raises(ValueError) as error_info:
            SolutionModelCardHelpers.get_evaluation_job(name=job_name, metric_file_s3_url=metric_file_s3_url)
        assert (
            str(error_info.value) == "metric_type type is required if evaluation metrics are to be loaded from s3 url"
        )
        # test for error when metric_file_s3_url but metric_type has a wrong value
        with pytest.raises(ValueError) as error_info:
            SolutionModelCardHelpers.get_evaluation_job(
                name=job_name, metric_file_s3_url=metric_file_s3_url, metric_type="wrong-value"
            )
        assert (
            str(error_info.value)
            == "metric_type must be one of model_card_metric_schema|clarify_bias|clarify_explainability|regression|binary_classification|multiclass_classification"
        )
        # test when metric_file_s3_url and metric_type are provided
        evaluation_job = SolutionModelCardHelpers.get_evaluation_job(
            name=job_name, metric_file_s3_url=metric_file_s3_url, metric_type="clarify_bias"
        )
        assert evaluation_job.name == job_name

        # test with metric_file_s3_url and metric_type not provided
        evaluation_job = SolutionModelCardHelpers.get_evaluation_job(
            name=job_name, evaluation_job_arn=evaluation_job_arn
        )
        assert evaluation_job.evaluation_job_arn == evaluation_job_arn

    def test_get_additional_information(self):
        ethical_considerations = "no ethical concerns"
        caveats_and_recommendations = "some recommendations"
        additional_information = SolutionModelCardHelpers.get_additional_information(
            ethical_considerations=ethical_considerations, caveats_and_recommendations=caveats_and_recommendations
        )
        assert additional_information.ethical_considerations == ethical_considerations
        assert additional_information.caveats_and_recommendations == caveats_and_recommendations
        assert additional_information.custom_details is None


class TestSolutionModelCard(unittest.TestCase):
    def setUp(self):
        self.name = "test-card"
        self.status = "Draft"
        self.example_card = ModelCard(name=self.name, status=self.status)
        self.s3_output_path = "s3://bucket/exports"

    @patch("sagemaker.model_card.ModelCard.create")
    def test_create_model_card(self, patched_card_create):
        SolutionModelCard(name=self.name, status=self.status).create_model_card()
        assert patched_card_create.called is True

    @patch("sagemaker.model_card.ModelCard.delete")
    def test_delete_model_card(self, patched_card_delete):
        SolutionModelCard(name=self.name).delete_model_card()
        assert patched_card_delete.called is True

    @patch("sagemaker.Session")
    def test_describe_model_cards(self, patched_session):
        patched_session.sagemaker_client.describe_model_card = Mock(
            return_value={"name": self.name, "status": self.status}
        )
        response = SolutionModelCard(name=self.name, sagemaker_session=patched_session).describe_model_card()
        assert response["name"] == self.name
        assert response["status"] == self.status

    @patch("sagemaker.model_card.ModelCard.load")
    def test_load_model_card(self, patched_card_load):
        patched_card_load.return_value = self.example_card
        response = SolutionModelCard.load_model_card(name=self.name)
        assert response.name == self.name
        assert response.status == self.status

    @patch("sagemaker.model_card.ModelCard.update")
    @patch("solution_model_card.SolutionModelCard.load_model_card")
    def test_update_model_card(self, patched_load_model_card, patched_card_update):
        patched_load_model_card.return_value = self.example_card
        card = SolutionModelCard(name=self.name, status="Approved")
        card.update_model_card()
        patched_card_update.assert_called_with(status="Approved")

    @patch("sagemaker.model_card.ModelCard.export_pdf")
    @patch("solution_model_card.SolutionModelCard.load_model_card")
    def test_export_model_card(self, patched_load_model_card, patched_card_export_pdf):
        patched_load_model_card.return_value = self.example_card
        card = SolutionModelCard.load_model_card(name=self.name)
        SolutionModelCard.export_model_card(model_card=card, s3_output_path=self.s3_output_path)
        patched_card_export_pdf.assert_called_with(
            s3_output_path=self.s3_output_path, export_job_name=None, model_card_version=None
        )


class TestSolutionModelCardAPIs(unittest.TestCase):
    def setUp(self):
        self.event = dict(
            name="test-card",
            version=1,
            created_by="DS",
            model_overview=dict(model_description="model-description", unexpected="random-value"),
        )
        self.s3_url = "s3://test-bucket"
        self.message = "model card has been deleted"
        self.api_response = {
            "statusCode": 200,
            "isBase64Encoded": False,
            "body": json.dumps(
                {
                    "message": self.message,
                },
                indent=4,
            ),
            "headers": {"Content-Type": "plain/text"},
        }

    @patch("sagemaker.Session")
    def test__filter_expected_params(self, patched_session):
        card_api = SolutionModelCardAPIs(event=self.event, sagemaker_session=patched_session)
        TestCase().assertEqual(
            SolutionModelCardAPIs._filter_expected_params(
                self.event["model_overview"], expected_params=card_api.expected_model_overview_params
            ),
            {"model_description": "model-description"},
        )

    def test__api_response(self):
        TestCase().assertEqual(SolutionModelCardAPIs._api_response(message=self.message), self.api_response)

    @patch("sagemaker.Session")
    def test__create_solutions_card_object(self, patched_session):
        solutions_card_object = SolutionModelCardAPIs(
            event=self.event, sagemaker_session=patched_session
        )._create_solutions_card_object()
        assert solutions_card_object.name == self.event["name"]
        assert (
            solutions_card_object.model_overview.model_description == self.event["model_overview"]["model_description"]
        )
        assert solutions_card_object.additional_information is None

    @patch("sagemaker.Session")
    @patch("solution_model_card.SolutionModelCard.describe_model_card")
    @patch("solution_model_card.SolutionModelCard.create_model_card")
    def test_create(self, patched_create_model_card, patched_describe_model_card, patched_session):
        solutions_card_object = SolutionModelCardAPIs(event=self.event, sagemaker_session=patched_session)
        solutions_card_object.create()
        assert patched_create_model_card.called is True
        assert patched_describe_model_card.called is True

    @patch("sagemaker.Session")
    @patch("solution_model_card.SolutionModelCard.describe_model_card")
    @patch("solution_model_card.SolutionModelCard.update_model_card")
    def test_update(self, patched_update_model_card, patched_describe_model_card, patched_session):
        solutions_card_object = SolutionModelCardAPIs(event=self.event, sagemaker_session=patched_session)
        solutions_card_object.update()
        assert patched_update_model_card.called is True
        assert patched_describe_model_card.called is True

    @patch("sagemaker.Session")
    @patch("solution_model_card.SolutionModelCard.delete_model_card")
    def test_delete(self, patched_delete_model_card, patched_session):
        solutions_card_object = SolutionModelCardAPIs(event=self.event, sagemaker_session=patched_session)
        solutions_card_object.delete()
        assert patched_delete_model_card.called is True

    @patch("sagemaker.Session")
    @patch("solution_model_card.SolutionModelCard.describe_model_card")
    def test_describe(self, patched_describe_model_card, patched_session):
        solutions_card_object = SolutionModelCardAPIs(event=self.event, sagemaker_session=patched_session)
        solutions_card_object.describe()
        assert patched_describe_model_card.called is True

    @patch("sagemaker.Session")
    @patch("solution_model_card.SolutionModelCardHelpers.list_model_cards")
    def test_list_model_cards(self, patched_list_model_cards, patched_session):
        solutions_card_object = SolutionModelCardAPIs(event=self.event, sagemaker_session=patched_session)
        solutions_card_object.list_model_cards()
        assert patched_list_model_cards.called is True

    @patch("sagemaker.Session")
    @patch("solution_model_card.SolutionModelCard.export_model_card")
    @patch("solution_model_card.SolutionModelCard.load_model_card")
    def test_export_to_pdf(self, patched_load_model_card, patched_export_model_card, patched_session):
        solutions_card_object = SolutionModelCardAPIs(event=self.event, sagemaker_session=patched_session)
        solutions_card_object.export_to_pdf(s3_output_path=self.s3_url)
        assert patched_load_model_card.called is True
        assert patched_export_model_card.called is True
