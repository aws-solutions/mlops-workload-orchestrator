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
import jsii
import json
from aws_cdk.core import IAspect, IConstruct, Construct
from aws_cdk.aws_lambda import Function


@jsii.implements(IAspect)
class AwsSDKConfigAspect(Construct):
    def __init__(self, scope: Construct, id: str, solution_id: str):
        super().__init__(scope, id)
        self.solution_id = solution_id

    def visit(self, node: IConstruct):
        if isinstance(node, Function):
            user_agent = json.dumps({"user_agent_extra": f"AwsSolution/{self.solution_id}/%%VERSION%%"})
            node.add_environment(key="AWS_SDK_USER_AGENT", value=user_agent)
