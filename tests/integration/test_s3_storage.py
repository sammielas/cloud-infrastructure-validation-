import os

import boto3
import pytest
from botocore.config import Config


@pytest.fixture(scope="module")
def s3_client():
    endpoint = os.environ["FLOCI_S3_ENDPOINT"]

    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name="eu-west-2",
        aws_access_key_id="test",
        aws_secret_access_key="test",
        config=Config(s3={"addressing_style": "path"}),
    )


@pytest.fixture(scope="module")
def bucket_name():
    return os.environ.get(
        "TEST_S3_BUCKET",
        "platform-artifacts-local-dev",
    )


def test_bucket_exists(s3_client, bucket_name):
    response = s3_client.head_bucket(Bucket=bucket_name)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200


def test_public_access_block(s3_client, bucket_name):
    response = s3_client.get_public_access_block(Bucket=bucket_name)

    settings = response["PublicAccessBlockConfiguration"]

    assert settings["BlockPublicAcls"] is True
    assert settings["BlockPublicPolicy"] is True
    assert settings["IgnorePublicAcls"] is True
    assert settings["RestrictPublicBuckets"] is True


def test_default_encryption(s3_client, bucket_name):
    response = s3_client.get_bucket_encryption(Bucket=bucket_name)

    rules = response["ServerSideEncryptionConfiguration"]["Rules"]

    assert any(
        rule["ApplyServerSideEncryptionByDefault"]["SSEAlgorithm"] == "AES256"
        for rule in rules
    )


def test_versioning_enabled(s3_client, bucket_name):
    response = s3_client.get_bucket_versioning(Bucket=bucket_name)

    assert response["Status"] == "Enabled"
