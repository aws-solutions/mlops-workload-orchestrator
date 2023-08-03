# #####################################################################################################################
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.                                            #
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
from constructs import IConstruct, Construct
from aws_cdk import IAspect
from aws_cdk.aws_lambda import Function


@jsii.implements(IAspect)
class ProtobufConfigAspect(Construct):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)

    def visit(self, node: IConstruct):
        if isinstance(node, Function):
            # this is to handle the protobuf package breaking changes.
            node.add_environment(
                key="PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", value="python"
            )
