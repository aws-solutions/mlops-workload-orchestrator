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
import pytest
from shared.helper import get_client, reset_client


_helpers_service_clients = dict()


@pytest.mark.parametrize("service,enpoint_url", [("s3", "https://s3"), ("cloudformation", "https://cloudformation")])
def test_get_client(service, enpoint_url):
    client = get_client(service)
    assert enpoint_url in client.meta.endpoint_url


@pytest.mark.parametrize("service", ["s3", "cloudformation"])
def test_reset_client(service):
    get_client(service)
    reset_client()
    assert _helpers_service_clients == dict()