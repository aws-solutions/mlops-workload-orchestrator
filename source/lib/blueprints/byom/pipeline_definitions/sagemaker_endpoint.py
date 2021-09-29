# #####################################################################################################################
#  Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                            #
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
from aws_cdk import (
    aws_sagemaker as sagemaker,
)


def create_sagemaker_endpoint(scope, id, endpoint_config_name, endpoint_name, model_name, **kwargs):
    # create Sagemaker endpoint
    sagemaker_endpoint = sagemaker.CfnEndpoint(
        scope,
        id,
        endpoint_config_name=endpoint_config_name,
        endpoint_name=endpoint_name,
        tags=[{"key": "endpoint-name", "value": f"{model_name}-endpoint"}],
        **kwargs,
    )

    return sagemaker_endpoint
