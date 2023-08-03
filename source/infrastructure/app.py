#!/usr/bin/env python3
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
from aws_cdk import App, Aspects, DefaultStackSynthesizer
from lib.mlops_orchestrator_stack import MLOpsStack
from lib.blueprints.ml_pipelines.model_monitor import ModelMonitorStack
from lib.blueprints.ml_pipelines.realtime_inference_pipeline import (
    BYOMRealtimePipelineStack,
)
from lib.blueprints.ml_pipelines.byom_batch_pipeline import BYOMBatchStack
from lib.blueprints.ml_pipelines.single_account_codepipeline import (
    SingleAccountCodePipelineStack,
)
from lib.blueprints.ml_pipelines.multi_account_codepipeline import (
    MultiAccountCodePipelineStack,
)
from lib.blueprints.ml_pipelines.byom_custom_algorithm_image_builder import (
    BYOMCustomAlgorithmImageBuilderStack,
)
from lib.blueprints.ml_pipelines.autopilot_training_pipeline import (
    AutopilotJobStack,
)
from lib.blueprints.ml_pipelines.model_training_pipeline import (
    TrainingJobStack,
)
from lib.blueprints.aspects.aws_sdk_config_aspect import AwsSDKConfigAspect
from lib.blueprints.aspects.protobuf_config_aspect import ProtobufConfigAspect
from lib.blueprints.aspects.app_registry_aspect import AppRegistry
from lib.blueprints.pipeline_definitions.cdk_context_value import (
    get_cdk_context_value,
)

app = App()
solution_id = get_cdk_context_value(app, "SolutionId")
solution_name = get_cdk_context_value(app, "SolutionName")
version = get_cdk_context_value(app, "Version")
app_registry_name = get_cdk_context_value(app, "AppRegistryName")
application_type = get_cdk_context_value(app, "ApplicationType")

mlops_stack_single = MLOpsStack(
    app,
    "mlops-workload-orchestrator-single-account",
    description=f"({solution_id}-sa) - MLOps Workload Orchestrator (Single Account Option). Version {version}",
    synthesizer=DefaultStackSynthesizer(generate_bootstrap_version_rule=False),
)

# add app registry to single account stack
Aspects.of(mlops_stack_single).add(
    AppRegistry(
        mlops_stack_single,
        "AppRegistrySingleAccount",
        solution_id=solution_id,
        solution_name=solution_name,
        solution_version=version,
        app_registry_name=app_registry_name,
        application_type=application_type,
    )
)

# add AWS_SDK_USER_AGENT env variable to Lambda functions
Aspects.of(mlops_stack_single).add(
    AwsSDKConfigAspect(app, "SDKUserAgentSingle", solution_id, version)
)

# add PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python to handle protobuf breaking changes
Aspects.of(mlops_stack_single).add(ProtobufConfigAspect(app, "ProtobufConfigSingle"))


mlops_stack_multi = MLOpsStack(
    app,
    "mlops-workload-orchestrator-multi-account",
    multi_account=True,
    description=f"({solution_id}-ma) - MLOps Workload Orchestrator (Multi Account Option). Version {version}",
    synthesizer=DefaultStackSynthesizer(generate_bootstrap_version_rule=False),
)

# add AppRegistry to multi account stack
Aspects.of(mlops_stack_multi).add(
    AppRegistry(
        mlops_stack_multi,
        "AppRegistryMultiAccount",
        solution_id=solution_id,
        solution_name=solution_name,
        solution_version=version,
        app_registry_name=app_registry_name,
        application_type=application_type,
    )
)

Aspects.of(mlops_stack_multi).add(
    AwsSDKConfigAspect(app, "SDKUserAgentMulti", solution_id, version)
)

# add PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python to handle protobuf breaking changes
Aspects.of(mlops_stack_multi).add(ProtobufConfigAspect(app, "ProtobufConfigMulti"))

custom_image_builder = BYOMCustomAlgorithmImageBuilderStack(
    app,
    "BYOMCustomAlgorithmImageBuilderStack",
    description=(
        f"({solution_id}byom-caib) - Bring Your Own Model pipeline to build custom algorithm docker images"
        f"in MLOps Workload Orchestrator. Version {version}"
    ),
    synthesizer=DefaultStackSynthesizer(generate_bootstrap_version_rule=False),
)

# add AppRegistry to custom image builder
Aspects.of(custom_image_builder).add(
    AppRegistry(
        custom_image_builder,
        "AppRegistryImageBuilder",
        solution_id=solution_id,
        solution_name=solution_name,
        solution_version=version,
        app_registry_name=app_registry_name,
        application_type=application_type,
    )
)

batch_stack = BYOMBatchStack(
    app,
    "BYOMBatchStack",
    description=(
        f"({solution_id}byom-bt) - BYOM Batch Transform pipeline in MLOps Workload Orchestrator. Version {version}"
    ),
    synthesizer=DefaultStackSynthesizer(generate_bootstrap_version_rule=False),
)

# add AppRegistry to batch transform stack
Aspects.of(batch_stack).add(
    AppRegistry(
        batch_stack,
        "AppRegistryBatchTransform",
        solution_id=solution_id,
        solution_name=solution_name,
        solution_version=version,
        app_registry_name=app_registry_name,
        application_type=application_type,
    )
)


Aspects.of(batch_stack).add(
    AwsSDKConfigAspect(app, "SDKUserAgentBatch", solution_id, version)
)

# add PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python to handle protobuf breaking changes
Aspects.of(batch_stack).add(ProtobufConfigAspect(app, "ProtobufConfigBatch"))

data_quality_monitor_stack = ModelMonitorStack(
    app,
    "DataQualityModelMonitorStack",
    monitoring_type="DataQuality",
    description=(
        f"({solution_id}byom-dqmm) - DataQuality Model Monitor pipeline. Version {version}"
    ),
    synthesizer=DefaultStackSynthesizer(generate_bootstrap_version_rule=False),
)

# add AppRegistry to data quality stack
Aspects.of(data_quality_monitor_stack).add(
    AppRegistry(
        data_quality_monitor_stack,
        "AppRegistryDataQuality",
        solution_id=solution_id,
        solution_name=solution_name,
        solution_version=version,
        app_registry_name=app_registry_name,
        application_type=application_type,
    )
)

Aspects.of(data_quality_monitor_stack).add(
    AwsSDKConfigAspect(app, "SDKUserAgentDataMonitor", solution_id, version)
)


# add PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python to handle protobuf breaking changes
Aspects.of(data_quality_monitor_stack).add(
    ProtobufConfigAspect(app, "ProtobufConfigDataMonitor")
)

model_quality_monitor_stack = ModelMonitorStack(
    app,
    "ModelQualityModelMonitorStack",
    monitoring_type="ModelQuality",
    description=(
        f"({solution_id}byom-mqmm) - ModelQuality Model Monitor pipeline. Version {version}"
    ),
    synthesizer=DefaultStackSynthesizer(generate_bootstrap_version_rule=False),
)

# add AppRegistry to model quality stack
Aspects.of(model_quality_monitor_stack).add(
    AppRegistry(
        model_quality_monitor_stack,
        "AppRegistryDataQuality",
        solution_id=solution_id,
        solution_name=solution_name,
        solution_version=version,
        app_registry_name=app_registry_name,
        application_type=application_type,
    )
)

Aspects.of(model_quality_monitor_stack).add(
    AwsSDKConfigAspect(app, "SDKUserAgentModelQuality", solution_id, version)
)

# add PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python to handle protobuf breaking changes
Aspects.of(model_quality_monitor_stack).add(
    ProtobufConfigAspect(app, "ProtobufConfigModelQuality")
)

model_bias_monitor_stack = ModelMonitorStack(
    app,
    "ModelBiasModelMonitorStack",
    monitoring_type="ModelBias",
    description=(
        f"({solution_id}byom-mqmb) - ModelBias Model Monitor pipeline. Version {version}"
    ),
    synthesizer=DefaultStackSynthesizer(generate_bootstrap_version_rule=False),
)

# add AppRegistry to model bias stack
Aspects.of(model_bias_monitor_stack).add(
    AppRegistry(
        model_bias_monitor_stack,
        "AppRegistryModelBias",
        solution_id=solution_id,
        solution_name=solution_name,
        solution_version=version,
        app_registry_name=app_registry_name,
        application_type=application_type,
    )
)

Aspects.of(model_bias_monitor_stack).add(
    AwsSDKConfigAspect(app, "SDKUserAgentModelBias", solution_id, version)
)

# add PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python to handle protobuf breaking changes
Aspects.of(model_bias_monitor_stack).add(
    ProtobufConfigAspect(app, "ProtobufConfigModelBias")
)

model_explainability_monitor_stack = ModelMonitorStack(
    app,
    "ModelExplainabilityModelMonitorStack",
    monitoring_type="ModelExplainability",
    description=(
        f"({solution_id}byom-mqme) - ModelExplainability Model Monitor pipeline. Version {version}"
    ),
    synthesizer=DefaultStackSynthesizer(generate_bootstrap_version_rule=False),
)

# add AppRegistry to model bias stack
Aspects.of(model_explainability_monitor_stack).add(
    AppRegistry(
        model_explainability_monitor_stack,
        "AppRegistryModelExplainability",
        solution_id=solution_id,
        solution_name=solution_name,
        solution_version=version,
        app_registry_name=app_registry_name,
        application_type=application_type,
    )
)

Aspects.of(model_explainability_monitor_stack).add(
    AwsSDKConfigAspect(app, "SDKUserAgentModelExplainability", solution_id, version)
)

# add PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python to handle protobuf breaking changes
Aspects.of(model_explainability_monitor_stack).add(
    ProtobufConfigAspect(app, "ProtobufConfigModelExplainability")
)

realtime_stack = BYOMRealtimePipelineStack(
    app,
    "BYOMRealtimePipelineStack",
    description=(
        f"({solution_id}byom-rip) - BYOM Realtime Inference Pipeline. Version {version}"
    ),
    synthesizer=DefaultStackSynthesizer(generate_bootstrap_version_rule=False),
)

# add AppRegistry to realtime inference stack
Aspects.of(realtime_stack).add(
    AppRegistry(
        realtime_stack,
        "AppRegistryRealtimeInference",
        solution_id=solution_id,
        solution_name=solution_name,
        solution_version=version,
        app_registry_name=app_registry_name,
        application_type=application_type,
    )
)

Aspects.of(realtime_stack).add(
    AwsSDKConfigAspect(app, "SDKUserAgentRealtime", solution_id, version)
)

# add PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python to handle protobuf breaking changes
Aspects.of(realtime_stack).add(ProtobufConfigAspect(app, "ProtobufConfigRealtime"))

autopilot_stack = AutopilotJobStack(
    app,
    "AutopilotJobStack",
    description=(
        f"({solution_id}-autopilot) - Autopilot training pipeline. Version {version}"
    ),
    synthesizer=DefaultStackSynthesizer(generate_bootstrap_version_rule=False),
)

# add AppRegistry to autopilot stack
Aspects.of(autopilot_stack).add(
    AppRegistry(
        autopilot_stack,
        "AppRegistryAutopilot",
        solution_id=solution_id,
        solution_name=solution_name,
        solution_version=version,
        app_registry_name=app_registry_name,
        application_type=application_type,
    )
)

Aspects.of(autopilot_stack).add(
    AwsSDKConfigAspect(app, "SDKUserAgentAutopilot", solution_id, version)
)

# add PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python to handle protobuf breaking changes
Aspects.of(autopilot_stack).add(ProtobufConfigAspect(app, "ProtobufConfigAutopilot"))

training_stack = TrainingJobStack(
    app,
    "TrainingJobStack",
    training_type="TrainingJob",
    description=(
        f"({solution_id}-training) - Model Training pipeline. Version {version}"
    ),
    synthesizer=DefaultStackSynthesizer(generate_bootstrap_version_rule=False),
)

# add AppRegistry to model training stack
Aspects.of(training_stack).add(
    AppRegistry(
        training_stack,
        "AppRegistryModelTraining",
        solution_id=solution_id,
        solution_name=solution_name,
        solution_version=version,
        app_registry_name=app_registry_name,
        application_type=application_type,
    )
)

Aspects.of(training_stack).add(
    AwsSDKConfigAspect(app, "SDKUserAgentTraining", solution_id, version)
)

# add PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python to handle protobuf breaking changes
Aspects.of(training_stack).add(ProtobufConfigAspect(app, "ProtobufConfigTraining"))

hyperparameter_tunning_stack = TrainingJobStack(
    app,
    "HyperparamaterTunningJobStack",
    training_type="HyperparameterTuningJob",
    description=(
        f"({solution_id}-tuner) - Model Hyperparameter Tunning pipeline. Version {version}"
    ),
    synthesizer=DefaultStackSynthesizer(generate_bootstrap_version_rule=False),
)

# add AppRegistry to hyperparamater training stack
Aspects.of(hyperparameter_tunning_stack).add(
    AppRegistry(
        hyperparameter_tunning_stack,
        "AppRegistryTuner",
        solution_id=solution_id,
        solution_name=solution_name,
        solution_version=version,
        app_registry_name=app_registry_name,
        application_type=application_type,
    )
)


Aspects.of(hyperparameter_tunning_stack).add(
    AwsSDKConfigAspect(app, "SDKUserAgentHyperparamater", solution_id, version)
)

# add PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python to handle protobuf breaking changes
Aspects.of(hyperparameter_tunning_stack).add(
    ProtobufConfigAspect(app, "ProtobufConfigHyperparamater")
)

single_account_codepipeline = SingleAccountCodePipelineStack(
    app,
    "SingleAccountCodePipelineStack",
    description=(
        f"({solution_id}byom-sac) - Single-account codepipeline. Version {version}"
    ),
    synthesizer=DefaultStackSynthesizer(generate_bootstrap_version_rule=False),
)

# add AppRegistry to single account single_account_codepipelinecodepipeline stack
Aspects.of(single_account_codepipeline).add(
    AppRegistry(
        single_account_codepipeline,
        "AppRegistrySingleCodepipeline",
        solution_id=solution_id,
        solution_name=solution_name,
        solution_version=version,
        app_registry_name=app_registry_name,
        application_type=application_type,
    )
)

multi_account_codepipeline = MultiAccountCodePipelineStack(
    app,
    "MultiAccountCodePipelineStack",
    description=(
        f"({solution_id}byom-mac) - Multi-account codepipeline. Version {version}"
    ),
    synthesizer=DefaultStackSynthesizer(generate_bootstrap_version_rule=False),
)

# add AppRegistry to single account single_account_codepipelinecodepipeline stack
Aspects.of(multi_account_codepipeline).add(
    AppRegistry(
        multi_account_codepipeline,
        "AppRegistryMultiCodepipeline",
        solution_id=solution_id,
        solution_name=solution_name,
        solution_version=version,
        app_registry_name=app_registry_name,
        application_type=application_type,
    )
)

app.synth()
