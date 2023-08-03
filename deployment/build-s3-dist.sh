#!/bin/bash
#
# This script packages your project into a solution distributable that can be
# used as an input to the solution builder validation pipeline.
#
# Important notes and prereq's:
#   1. This script should be run from the repo's /deployment folder.
#
# This script will perform the following tasks:
#   1. Remove any old dist files from previous runs.
#   2. Install dependencies for the cdk-solution-helper; responsible for
#      converting standard 'cdk synth' output into solution assets.
#   3. Build and synthesize your CDK project.
#   4. Run the cdk-solution-helper on template outputs and organize
#      those outputs into the /global-s3-assets folder.
#   5. Organize source code artifacts into the /regional-s3-assets folder.
#   6. Remove any temporary files used for staging.
#
# Parameters:
#  - source-bucket-base-name: Name for the S3 bucket location where the template will source the Lambda
#    code from. The template will append '-[region_name]' to this bucket name.
#    For example: ./build-s3-dist.sh solutions v1.0.0
#    The template will then expect the source code to be located in the solutions-[region_name] bucket
#  - solution-name: name of the solution for consistency
#  - version-code: version of the package

[ "$DEBUG" == 'true' ] && set -x
set -e

# Important: CDK global version number
cdk_version=2.87.0

# Check to see if the required parameters have been provided:
if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
    echo "Please provide the base source bucket name, trademark approved solution name and version where the lambda code will eventually reside."
    echo "For example: ./build-s3-dist.sh solutions trademarked-solution-name v1.0.0"
    exit 1
fi

# Get reference for all important folders
template_dir="$PWD"
staging_dist_dir="$template_dir/staging"
template_dist_dir="$template_dir/global-s3-assets"
build_dist_dir="$template_dir/regional-s3-assets"
source_dir="$template_dir/../source"

echo "------------------------------------------------------------------------------"
echo "[Init] Remove any old dist files from previous runs"
echo "------------------------------------------------------------------------------"

echo "rm -rf $template_dist_dir"
rm -rf $template_dist_dir
echo "mkdir -p $template_dist_dir"
mkdir -p $template_dist_dir
echo "rm -rf $build_dist_dir"
rm -rf $build_dist_dir
echo "mkdir -p $build_dist_dir"
mkdir -p $build_dist_dir
echo "rm -rf $staging_dist_dir"
rm -rf $staging_dist_dir
echo "mkdir -p $staging_dist_dir"
mkdir -p $staging_dist_dir

echo "------------------------------------------------------------------------------"
echo "[Init] Setup the Python environment"
echo "------------------------------------------------------------------------------"

echo "cd $source_dir"
cd $source_dir

# setup lambda layers (building sagemaker layer using lambda build environment for python 3.10)
echo 'docker run --entrypoint /bin/bash -v "$source_dir"/infrastructure/lib/blueprints/lambdas/sagemaker_layer:/var/task public.ecr.aws/lambda/python:3.10 -c "cat requirements.txt; pip3 install -r requirements.txt -t ./python; exit"'
docker run --entrypoint /bin/bash -v "$source_dir"/infrastructure/lib/blueprints/lambdas/sagemaker_layer:/var/task public.ecr.aws/lambda/python:3.10 -c "cat requirements.txt; pip3 install -r requirements.txt -t ./python; exit"

# Remove tests and cache stuff (to reduce size)
find "$source_dir"/infrastructure/lib/blueprints/lambdas/sagemaker_layer/python -type d -name "tests" -exec rm -rfv {} +
find "$source_dir"/infrastructure/lib/blueprints/lambdas/sagemaker_layer/python -type d -name "__pycache__" -exec rm -rfv {} +

echo "python3 -m venv .venv-prod"
python3 -m venv .venv-prod
echo "source .venv-prod/bin/activate"
source .venv-prod/bin/activate
echo "upgrading pip -> python3 -m pip install --upgrade pip"
python3 -m pip install --upgrade pip
echo "pip install -r requirements.txt"
pip install -r requirements.txt

# setup crhelper for custom resource (copying s3 assets)
echo "pip install -r ./lambdas/custom_resource/requirements.txt -t ./lambdas/custom_resource/"
pip install -r ./lambdas/custom_resource/requirements.txt -t ./lambdas/custom_resource/

# setup crhelper for custom resource (solution helper)
echo "pip install -r ./lambdas/solution_helper/requirements.txt -t ./lambdas/solution_helper/"
pip install -r ./lambdas/solution_helper/requirements.txt -t ./lambdas/solution_helper/

# setup crhelper for invoke lambda custom resource
echo "pip install -r ./infrastructure/lib/blueprints/lambdas/invoke_lambda_custom_resource/requirements.txt -t ./infrastructure/lib/blueprints/lambdas/invoke_lambda_custom_resource/"
pip install -r ./infrastructure/lib/blueprints/lambdas/invoke_lambda_custom_resource/requirements.txt -t ./infrastructure/lib/blueprints/lambdas/invoke_lambda_custom_resource/

echo "------------------------------------------------------------------------------"
echo "[Init] Install dependencies for the cdk-solution-helper"
echo "------------------------------------------------------------------------------"

echo "cd $template_dir/cdk-solution-helper"
cd $template_dir/cdk-solution-helper
echo "npm ci --only=prod"
npm ci --only=prod

echo "------------------------------------------------------------------------------"
echo "[Synth] CDK Project"
echo "------------------------------------------------------------------------------"

# Install the global aws-cdk package
echo "cd $source_dir"
cd $source_dir
echo "npm install -g aws-cdk@$cdk_version"
npm install -g aws-cdk@$cdk_version

# move to the infrastructure dir
cd $source_dir/infrastructure
#Run 'cdk synth for BYOM blueprints
echo "cdk synth DataQualityModelMonitorStack > $staging_dist_dir/byom_data_quality_monitor.yaml --path-metadata false --version-reporting false"
cdk synth DataQualityModelMonitorStack > $staging_dist_dir/byom_data_quality_monitor.yaml --path-metadata false --version-reporting false
echo "cdk synth ModelQualityModelMonitorStack > $staging_dist_dir/byom_model_quality_monitor.yaml --path-metadata false --version-reporting false"
cdk synth ModelQualityModelMonitorStack > $staging_dist_dir/byom_model_quality_monitor.yaml --path-metadata false --version-reporting false
echo "cdk synth ModelBiasModelMonitorStack > $staging_dist_dir/byom_model_bias_monitor.yaml --path-metadata false --version-reporting false"
cdk synth ModelBiasModelMonitorStack > $staging_dist_dir/byom_model_bias_monitor.yaml --path-metadata false --version-reporting false
echo "cdk synth ModelExplainabilityModelMonitorStack > $staging_dist_dir/byom_model_explainability_monitor.yaml --path-metadata false --version-reporting false"
cdk synth ModelExplainabilityModelMonitorStack > $staging_dist_dir/byom_model_explainability_monitor.yaml --path-metadata false --version-reporting false
echo "cdk synth SingleAccountCodePipelineStack > $staging_dist_dir/single_account_codepipeline.yaml --path-metadata false --version-reporting false"
cdk synth SingleAccountCodePipelineStack > $staging_dist_dir/single_account_codepipeline.yaml --path-metadata false --version-reporting false
echo "cdk synth MultiAccountCodePipelineStack > $staging_dist_dir/multi_account_codepipeline.yaml --path-metadata false --version-reporting false"
cdk synth MultiAccountCodePipelineStack > $staging_dist_dir/multi_account_codepipeline.yaml --path-metadata false --version-reporting false
echo "cdk synth BYOMRealtimePipelineStack > $staging_dist_dir/byom_realtime_inference_pipeline.yaml --path-metadata false --version-reporting false"
cdk synth BYOMRealtimePipelineStack > $staging_dist_dir/byom_realtime_inference_pipeline.yaml --path-metadata false --version-reporting false
echo "cdk synth BYOMCustomAlgorithmImageBuilderStack > $staging_dist_dir/byom_custom_algorithm_image_builder.yaml --path-metadata false --version-reporting false"
cdk synth BYOMCustomAlgorithmImageBuilderStack > $staging_dist_dir/byom_custom_algorithm_image_builder.yaml --path-metadata false --version-reporting false
echo "cdk synth BYOMBatchStack > $staging_dist_dir/byom_batch_pipeline.yaml --path-metadata false --version-reporting false"
cdk synth BYOMBatchStack > $staging_dist_dir/byom_batch_pipeline.yaml --path-metadata false --version-reporting false
echo "cdk synth AutopilotJobStack > $staging_dist_dir/autopilot_training_pipeline.yaml --path-metadata false --version-reporting false"
cdk synth AutopilotJobStack > $staging_dist_dir/autopilot_training_pipeline.yaml --path-metadata false --version-reporting false
echo "cdk synth TrainingJobStack > $staging_dist_dir/model_training_pipeline.yaml --path-metadata false --version-reporting false"
cdk synth TrainingJobStack > $staging_dist_dir/model_training_pipeline.yaml --path-metadata false --version-reporting false
echo "cdk synth HyperparamaterTunningJobStack > $staging_dist_dir/model_hyperparameter_tunning_pipeline.yaml --path-metadata false --version-reporting false"
cdk synth HyperparamaterTunningJobStack > $staging_dist_dir/model_hyperparameter_tunning_pipeline.yaml --path-metadata false --version-reporting false

# Replace %%VERSION%% in other templates
replace="s/%%VERSION%%/$3/g"
echo "sed -i -e $replace $staging_dist_dir/byom_data_quality_monitor.yaml"
sed -i -e $replace $staging_dist_dir/byom_data_quality_monitor.yaml
echo "sed -i -e $replace $staging_dist_dir/byom_model_quality_monitor.yaml"
sed -i -e $replace $staging_dist_dir/byom_model_quality_monitor.yaml
echo "sed -i -e $replace $staging_dist_dir/byom_model_bias_monitor.yaml"
sed -i -e $replace $staging_dist_dir/byom_model_bias_monitor.yaml
echo "sed -i -e $replace $staging_dist_dir/byom_model_explainability_monitor.yaml"
sed -i -e $replace $staging_dist_dir/byom_model_explainability_monitor.yaml
echo "sed -i -e $replace $staging_dist_dir/byom_realtime_inference_pipeline.yaml"
sed -i -e $replace $staging_dist_dir/byom_realtime_inference_pipeline.yaml
echo "sed -i -e $replace $staging_dist_dir/single_account_codepipeline.yaml"
sed -i -e $replace $staging_dist_dir/single_account_codepipeline.yaml
echo "sed -i -e $replace $staging_dist_dir/multi_account_codepipeline.yaml"
sed -i -e $replace $staging_dist_dir/multi_account_codepipeline.yaml
echo "sed -i -e $replace $staging_dist_dir/byom_custom_algorithm_image_builder.yaml"
sed -i -e $replace $staging_dist_dir/byom_custom_algorithm_image_builder.yaml
echo "sed -i -e $replace $staging_dist_dir/byom_batch_pipeline.yaml"
sed -i -e $replace $staging_dist_dir/byom_batch_pipeline.yaml
echo "sed -i -e $replace $staging_dist_dir/autopilot_training_pipeline.yaml"
sed -i -e $replace $staging_dist_dir/autopilot_training_pipeline.yaml
echo "sed -i -e $replace $staging_dist_dir/model_training_pipeline.yaml"
sed -i -e $replace $staging_dist_dir/model_training_pipeline.yaml
echo "sed -i -e $replace $staging_dist_dir/model_hyperparameter_tunning_pipeline.yaml"
sed -i -e $replace $staging_dist_dir/model_hyperparameter_tunning_pipeline.yaml

# replace %%SOLUTION_NAME%% for AppRegistry app
replace="s/%%SOLUTION_NAME%%/$2/g"
echo "sed -i -e $replace $staging_dist_dir/byom_data_quality_monitor.yaml"
sed -i -e $replace $staging_dist_dir/byom_data_quality_monitor.yaml
echo "sed -i -e $replace $staging_dist_dir/byom_model_quality_monitor.yaml"
sed -i -e $replace $staging_dist_dir/byom_model_quality_monitor.yaml
echo "sed -i -e $replace $staging_dist_dir/byom_model_bias_monitor.yaml"
sed -i -e $replace $staging_dist_dir/byom_model_bias_monitor.yaml
echo "sed -i -e $replace $staging_dist_dir/byom_model_explainability_monitor.yaml"
sed -i -e $replace $staging_dist_dir/byom_model_explainability_monitor.yaml
echo "sed -i -e $replace $staging_dist_dir/byom_realtime_inference_pipeline.yaml"
sed -i -e $replace $staging_dist_dir/byom_realtime_inference_pipeline.yaml
echo "sed -i -e $replace $staging_dist_dir/single_account_codepipeline.yaml"
sed -i -e $replace $staging_dist_dir/single_account_codepipeline.yaml
echo "sed -i -e $replace $staging_dist_dir/multi_account_codepipeline.yaml"
sed -i -e $replace $staging_dist_dir/multi_account_codepipeline.yaml
echo "sed -i -e $replace $staging_dist_dir/byom_custom_algorithm_image_builder.yaml"
sed -i -e $replace $staging_dist_dir/byom_custom_algorithm_image_builder.yaml
echo "sed -i -e $replace $staging_dist_dir/byom_batch_pipeline.yaml"
sed -i -e $replace $staging_dist_dir/byom_batch_pipeline.yaml
echo "sed -i -e $replace $staging_dist_dir/autopilot_training_pipeline.yaml"
sed -i -e $replace $staging_dist_dir/autopilot_training_pipeline.yaml
echo "sed -i -e $replace $staging_dist_dir/model_training_pipeline.yaml"
sed -i -e $replace $staging_dist_dir/model_training_pipeline.yaml
echo "sed -i -e $replace $staging_dist_dir/model_hyperparameter_tunning_pipeline.yaml"
sed -i -e $replace $staging_dist_dir/model_hyperparameter_tunning_pipeline.yaml


# Run 'cdk synth' for main templates to generate raw solution outputs
echo "cdk synth mlops-workload-orchestrator-single-account --path-metadata false --version-reporting false --output=$staging_dist_dir"
cdk synth mlops-workload-orchestrator-single-account --path-metadata false --version-reporting false --output=$staging_dist_dir
echo "cdk synth mlops-workload-orchestrator-multi-account --path-metadata false --version-reporting false --output=$staging_dist_dir"
cdk synth mlops-workload-orchestrator-multi-account --path-metadata false --version-reporting false --output=$staging_dist_dir

# Remove unnecessary output files
echo "cd $staging_dist_dir"
cd $staging_dist_dir
echo "rm tree.json manifest.json cdk.out"
rm tree.json manifest.json cdk.out

echo "------------------------------------------------------------------------------"
echo "[Packing] Template artifacts"
echo "------------------------------------------------------------------------------"

# Move outputs from staging to template_dist_dir
echo "Move outputs from staging to template_dist_dir"
echo "cp $template_dir/*.template $template_dist_dir/"
cp $staging_dist_dir/mlops-workload-orchestrator-single-account.template.json $template_dist_dir/
cp $staging_dist_dir/mlops-workload-orchestrator-multi-account.template.json $template_dist_dir/
rm *.template.json

# Rename all *.template.json files to *.template
echo "Rename all *.template.json to *.template"
echo "copy templates and rename"
for f in $template_dist_dir/*.template.json; do
    mv -- "$f" "${f%.template.json}.template"
done

# Run the helper to clean-up the templates and remove unnecessary CDK elements
echo "Run the helper to clean-up the templates and remove unnecessary CDK elements"
echo "node $template_dir/cdk-solution-helper/index"
node $template_dir/cdk-solution-helper/index
if [ "$?" = "1" ]; then
	echo "(cdk-solution-helper) ERROR: there is likely output above." 1>&2
	exit 1
fi

# Find and replace bucket_name, solution_name, and version
echo "Find and replace bucket_name, solution_name, and version"
cd $template_dist_dir
echo "Updating code source bucket in template with $1"
replace="s/%%BUCKET_NAME%%/$1/g"

echo "sed -i -e $replace $template_dist_dir/mlops-workload-orchestrator-single-account.template"
sed -i -e $replace $template_dist_dir/mlops-workload-orchestrator-single-account.template
echo "sed -i -e $replace $template_dist_dir/mlops-workload-orchestrator-multi-account.template"
sed -i -e $replace $template_dist_dir/mlops-workload-orchestrator-multi-account.template

replace="s/%%SOLUTION_NAME%%/$2/g"
echo "sed -i -e $replace $template_dist_dir/mlops-workload-orchestrator-single-account"
sed -i -e $replace $template_dist_dir/mlops-workload-orchestrator-single-account.template
echo "sed -i -e $replace $template_dist_dir/mlops-workload-orchestrator-multi-account.template"
sed -i -e $replace $template_dist_dir/mlops-workload-orchestrator-multi-account.template

replace="s/%%VERSION%%/$3/g"
echo "sed -i -e $replace $template_dist_dir/mlops-workload-orchestrator-single-account.template"
sed -i -e $replace $template_dist_dir/mlops-workload-orchestrator-single-account.template
echo "sed -i -e $replace $template_dist_dir/mlops-workload-orchestrator-multi-account.template"
sed -i -e $replace $template_dist_dir/mlops-workload-orchestrator-multi-account.template


echo "------------------------------------------------------------------------------"
echo "[Packing] Source code artifacts"
echo "------------------------------------------------------------------------------"
cd $staging_dist_dir
# ... For each asset.* source code artifact in the temporary /staging folder...
for d in `find . -mindepth 1 -maxdepth 1 -type d`; do

    # Rename the artifact, removing the period for handler compatibility
    pfname="$(basename -- $d)"
    fname="$(echo $pfname | sed -e 's/\.//g')"
    mv $d $fname

    # Zip the artifact
    cd $fname
    echo "zip -qr ../$fname.zip *"
    zip -qr ../$fname.zip *
    cd ..

    # Copy the zipped artifact from /staging to /regional-s3-assets
    echo "cp $fname.zip $build_dist_dir"
    cp $fname.zip $build_dist_dir

    # Remove the old, unzipped artifact from /staging
    echo "rm -rf $fname"
    rm -rf $fname

    # Remove the old, zipped artifact from /staging
    echo "rm $fname.zip"
    rm $fname.zip

    # ... repeat until all source code artifacts are zipped and placed in the
    # ... /regional-s3-assets folder

done

echo "Creating zip files for the blueprint stacks"
echo "mkdir -p $template_dir/bp_staging"
mkdir -p $template_dir/bp_staging
echo "cp -r $source_dir/infrastructure/lib/blueprints $template_dir/bp_staging/"
cp -r $source_dir/infrastructure/lib/blueprints $template_dir/bp_staging/



echo "cp -r $source_dir/lambdas/pipeline_orchestration/shared $template_dir/bp_staging/"
cp -r $source_dir/lambdas/pipeline_orchestration/shared $template_dir/bp_staging/

# Cleaning up blueprint staging folder
cd $template_dir/bp_staging/
rm -rf **/__pycache__/
rm -rf **/*.egg-info/
cd $template_dir/bp_staging/blueprints

# copy *.yaml templaes to the main blueprints folder
echo "cp -r $staging_dist_dir/*.yaml $template_dir/bp_staging/blueprints/"
cp -r $staging_dist_dir/*.yaml $template_dir/bp_staging/blueprints/

# Loop through all blueprint directories in blueprints
for bp in `find . -mindepth 1 -maxdepth 1 -type d`; do
    echo "subdirector: $bp"
    # # Loop through all subdirectories in blueprints/<blueprint_type>
    if [ $bp != "./lambdas" ]; then
        # Remove any directory that is not 'lambdas'
        rm -rf $bp
    fi
done

cd lambdas
# Loop through all lambda directories of the <blueprint_type>
for lambda in `find . -mindepth 1 -maxdepth 1 -type d`; do

    # Copying shared source codes to each lambda function
    echo "cp -r $template_dir/bp_staging/shared $lambda"
    cp -r $template_dir/bp_staging/shared $lambda

    # Removing './' from the directory name to use for zip file
    echo "lambda_dir_name=`echo $lambda | cut -d '/' -f 2`"
    lambda_dir_name=`echo $lambda | cut -d '/' -f 2`

    cd $lambda_dir_name

    # Creating the zip file for each lambda
    echo "zip -r9 ../$lambda_dir_name.zip *"
    zip -r9 ../$lambda_dir_name.zip *
    cd ..

    # Removing the lambda directories after creating zip files of them
    echo "rm -rf $lambda"
    rm -rf $lambda
    
done

cd $template_dir/bp_staging/blueprints
# Remove all .py files in subdirectories since they are not necessary anymore
rm -f *.py
rm -f */*.py
rm -f */*/*.py
rm -f */__pycache__

cd $template_dir/bp_staging

# Creating a zip file of blueprints directory and putting it in regional-s3-assets
echo "zip -r9 blueprints.zip blueprints"
zip -r9 blueprints.zip blueprints

echo "mv blueprints.zip $build_dist_dir"
mv blueprints.zip $build_dist_dir

# Remove temporary directory
rm -rf $template_dir/bp_staging

echo "------------------------------------------------------------------------------"
echo "[Cleanup] Remove temporary files"
echo "------------------------------------------------------------------------------"

# Delete the temporary /staging folder
echo "rm -rf $staging_dist_dir"
rm -rf $staging_dist_dir
