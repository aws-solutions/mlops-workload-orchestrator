######################################################################################################################
#  Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           #
#                                                                                                                    #
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance    #
#  with the License. A copy of the License is located at                                                             #
#                                                                                                                    #
#      http://www.apache.org/licenses/LICENSE-2.0                                                                    #
#                                                                                                                    #
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES #
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    #
#  and limitations under the License.                                                                                #
######################################################################################################################

import unittest
import requests
from unittest import mock
from lambda_function import handler


def mocked_requests_post(*args, **kwargs):
    class MockResponse:
        def __init__(self, status_code, reason):
            self.status_code = status_code
            self.reason = reason

        def raise_for_status(self):
            pass  # NOSONAR this is just used as a mocked response object

    return MockResponse(200, "OK")


class LambdaTest(unittest.TestCase):
    exception_message = "Exception should not be raised when metrics cannot be sent"

    def test_custom_resource(self):
        import lambda_function

        # test resource == "UUID"
        event = {"RequestType": "Create", "ResourceProperties": {"Resource": "UUID"}}

        lambda_function.custom_resource(event, None)
        self.assertIsNotNone(lambda_function.helper.Data.get("UUID"))

        # test resource == "AnonymousMetric"
        with mock.patch("requests.post", side_effect=mocked_requests_post) as mock_post:
            event = {
                "RequestType": "Create",
                "ResourceProperties": {
                    "Resource": "AnonymousMetric",
                    "SolutionId": "SO1234",
                    "gitSelected": "True",
                    "bucketSelected": "False",
                    "IsMultiAccount": "True",
                    "IsDelegatedAccount": "True",
                    "UUID": "some-uuid",
                },
            }
            lambda_function.custom_resource(event, None)
            actual_payload = mock_post.call_args.kwargs["json"]
            self.assertEqual(
                actual_payload["Data"],
                {
                    "RequestType": "Create",
                    "gitSelected": "True",
                    "bucketSelected": "False",
                    "IsMultiAccount": "True",
                    "IsDelegatedAccount": "True",
                },
            )

    @mock.patch("requests.post", side_effect=mocked_requests_post)
    def test_send_anonymous_metrics_successful(self, mock_post):
        event = {
            "RequestType": "Create",
            "ResourceProperties": {
                "Resource": "AnonymousMetric",
                "SolutionId": "SO1234",
                "gitSelected": "True",
                "bucketSelected": "False",
                "UUID": "some-uuid",
                "Foo": "Bar",
            },
        }

        from lambda_function import _send_anonymous_metrics

        response = _send_anonymous_metrics(event["RequestType"], event["ResourceProperties"])

        self.assertIsNotNone(response)

        expected_metrics_endpoint = "https://metrics.awssolutionsbuilder.com/generic"
        actual_metrics_endpoint = mock_post.call_args.args[0]
        self.assertEqual(expected_metrics_endpoint, actual_metrics_endpoint)

        expected_headers = {"Content-Type": "application/json"}
        actual_headers = mock_post.call_args.kwargs["headers"]
        self.assertEqual(expected_headers, actual_headers)

        actual_payload = mock_post.call_args.kwargs["json"]
        self.assertIn("Solution", actual_payload)
        self.assertIn("UUID", actual_payload)
        self.assertIn("TimeStamp", actual_payload)

        self.assertIn("Data", actual_payload)
        self.assertEqual(
            actual_payload["Data"],
            {"RequestType": "Create", "gitSelected": "True", "bucketSelected": "False"},
        )

        # delete a key from the resource properties. It should send data with no errors
        del event["ResourceProperties"]["bucketSelected"]
        response = _send_anonymous_metrics(event["RequestType"], event["ResourceProperties"])
        self.assertIsNotNone(response)
        actual_payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(
            actual_payload["Data"],
            {"RequestType": "Create", "gitSelected": "True"},
        )

    @mock.patch("requests.post", side_effect=mocked_requests_post(404, "HTTPError"))
    def test_send_anonymous_metrics_http_error(self, mock_post):
        event = {
            "RequestType": "Create",
            "ResourceProperties": {"Resource": "AnonymousMetric", "SolutionId": "SO1234", "UUID": "some-uuid"},
        }

        try:
            from lambda_function import _send_anonymous_metrics

            response = _send_anonymous_metrics(event["RequestType"], event["ResourceProperties"])
            # the function shouldn't throw an exception, and return None
            self.assertIsNone(response)

        except AssertionError as e:
            self.fail(str(e))

    @mock.patch("requests.post", side_effect=mocked_requests_post)
    def test_send_anonymous_metrics_connection_error(self, mock_post):
        mock_post.side_effect = requests.exceptions.ConnectionError()
        event = {
            "RequestType": "Update",
            "ResourceProperties": {"Resource": "AnonymousMetric", "SolutionId": "SO1234", "UUID": "some-uuid"},
        }

        try:
            from lambda_function import _send_anonymous_metrics

            response = _send_anonymous_metrics(event["RequestType"], event["ResourceProperties"])
            # the function shouldn't throw an exception, and return None
            self.assertIsNone(response)

        except AssertionError as e:
            self.fail(str(e))

    @mock.patch("requests.post")
    def test_send_anonymous_metrics_other_error(self, mock_post):
        try:
            invalid_event = {
                "RequestType": "Delete",
                "ResourceProperties": {"Resource": "AnonymousMetric", "UUID": "some-uuid"},
            }

            from lambda_function import _send_anonymous_metrics

            response = _send_anonymous_metrics(invalid_event["RequestType"], invalid_event["ResourceProperties"])
            # the function shouldn't throw an exception, and return None
            assert response is None
        except AssertionError as e:
            self.fail(str(e))

    def test_sanitize_data(self):
        from lambda_function import _sanitize_data

        resource_properties = {
            "ServiceToken": "lambda-fn-arn",
            "Resource": "AnonymousMetric",
            "SolutionId": "SO1234",
            "UUID": "some-uuid",
            "Region": "us-east-1",
            "gitSelected": "True",
            "bucketSelected": "False",
            "Foo": "Bar",
        }

        expected_response = {
            "Region": "us-east-1",
            "gitSelected": "True",
            "bucketSelected": "False",
        }

        actual_response = _sanitize_data(resource_properties)
        self.assertCountEqual(expected_response, actual_response)

    @mock.patch("lambda_function.helper")
    def test_helper(self, mocked_helper):
        handler({}, {})
        mocked_helper.assert_called()
