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
def get_cdk_context_value(scope, key):
    """
    get_cdk_context_value gets the cdk context value for a provided key

    :scope: CDK Construct scope

    :returns: context value
    :Raises: Exception: The context key: {key} is undefined.
    """
    value = scope.node.try_get_context(key)
    if value is None:
        raise ValueError(f"The CDK context key: {key} is undefined.")
    else:
        return value
