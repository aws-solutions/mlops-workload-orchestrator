import os
import boto3
import pytest
CONFIG_FILE = "config_and_overrides.yaml"
@pytest.fixture(autouse=True)
def aws_credentials():
    """Mocked AWS Credentials"""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_REGION"] = "us-east-1"  # must be a valid region
