#!/usr/bin/env python3
# #####################################################################################################################
#  Copyright 2020-2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                       #
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
from aws_cdk import core
from lib.aws_mlops_stack import MLOpsStack
from lib.blueprints.byom.model_monitor import ModelMonitorStack
from lib.blueprints.byom.realtime_inference_pipeline import BYOMRealtimePipelineStack
from lib.blueprints.byom.byom_batch_pipeline import BYOMBatchStack
from lib.blueprints.byom.single_account_codepipeline import SingleAccountCodePipelineStack
from lib.blueprints.byom.multi_account_codepipeline import MultiAccountCodePipelineStack
from lib.blueprints.byom.byom_custom_algorithm_image_builder import BYOMCustomAlgorithmImageBuilderStack
from lib.aws_sdk_config_aspect import AwsSDKConfigAspect

solution_id = "SO0136"
app = core.App()

mlops_stack_single = MLOpsStack(
    app, "aws-mlops-single-account-framework", description=f"({solution_id}) - AWS MLOps Framework. Version %%VERSION%%"
)

# add AWS_SDK_USER_AGENT env variable to Lambda functions
core.Aspects.of(mlops_stack_single).add(AwsSDKConfigAspect(app, "SDKUserAgentSingle", solution_id))

mlops_stack_multi = MLOpsStack(
    app,
    "aws-mlops-multi-account-framework",
    multi_account=True,
    description=f"({solution_id}) - AWS MLOps Framework. Version %%VERSION%%",
)

core.Aspects.of(mlops_stack_multi).add(AwsSDKConfigAspect(app, "SDKUserAgentMulti", solution_id))

BYOMCustomAlgorithmImageBuilderStack(
    app,
    "BYOMCustomAlgorithmImageBuilderStack",
    description=(
        f"({solution_id}byom-caib) - Bring Your Own Model pipeline to build custom algorithm docker images"
        f"in AWS MLOps Framework. Version %%VERSION%%"
    ),
)

batch_stack = BYOMBatchStack(
    app,
    "BYOMBatchStack",
    description=(
        f"({solution_id}byom-bt) - BYOM Batch Transform pipeline" f"in AWS MLOps Framework. Version %%VERSION%%"
    ),
)

core.Aspects.of(batch_stack).add(AwsSDKConfigAspect(app, "SDKUserAgentBatch", solution_id))

model_monitor_stack = ModelMonitorStack(
    app,
    "ModelMonitorStack",
    description=(f"({solution_id}byom-mm) - Model Monitor pipeline. Version %%VERSION%%"),
)

core.Aspects.of(model_monitor_stack).add(AwsSDKConfigAspect(app, "SDKUserAgentMonitor", solution_id))


realtime_stack = BYOMRealtimePipelineStack(
    app,
    "BYOMRealtimePipelineStack",
    description=(f"({solution_id}byom-rip) - BYOM Realtime Inference Pipleline. Version %%VERSION%%"),
)

core.Aspects.of(realtime_stack).add(AwsSDKConfigAspect(app, "SDKUserAgentRealtime", solution_id))

SingleAccountCodePipelineStack(
    app,
    "SingleAccountCodePipelineStack",
    description=(f"({solution_id}byom-sac) - Single-account codepipeline. Version %%VERSION%%"),
)

MultiAccountCodePipelineStack(
    app,
    "MultiAccountCodePipelineStack",
    description=(f"({solution_id}byom-mac) - Multi-account codepipeline. Version %%VERSION%%"),
)


app.synth()
