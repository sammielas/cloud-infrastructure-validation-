import json
import os
import uuid

import boto3
import pytest
from botocore.exceptions import ClientError

from tests.security.cleanup import run_cleanup


ENDPOINT = os.environ.get(
    "FLOCI_ENDPOINT",
    "http://127.0.0.1:4567",
)
REGION = "eu-west-2"


def aws_client(service, access_key, secret_key):
    """Create a Boto3 client targeting the Floci emulator."""
    return boto3.client(
        service,
        endpoint_url=ENDPOINT,
        region_name=REGION,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )


def admin_clients():
    """Return IAM and S3 clients using Floci bootstrap credentials."""
    admin_key = os.environ.get("FLOCI_ADMIN_ACCESS_KEY")
    admin_secret = os.environ.get("FLOCI_ADMIN_SECRET_KEY")

    if not admin_key or not admin_secret:
        pytest.fail("Missing FLOCI_ADMIN_ACCESS_KEY or FLOCI_ADMIN_SECRET_KEY")

    return (
        aws_client("iam", admin_key, admin_secret),
        aws_client("s3", admin_key, admin_secret),
    )


@pytest.fixture(scope="module")
def security_environment():
    """Create disposable IAM and S3 resources for security tests."""

    iam, admin_s3 = admin_clients()

    suffix = uuid.uuid4().hex[:10]
    bucket = f"checkout-security-{suffix}"
    username = f"checkout-reader-{suffix}"
    policy_name = "CheckoutReadOnly"

    bucket_created = False
    user_created = False
    policy_attached = False
    access_key_id = None

    try:
        # Create a temporary bucket.
        admin_s3.create_bucket(
            Bucket=bucket,
            CreateBucketConfiguration={
                "LocationConstraint": REGION,
            },
        )
        bucket_created = True

        # Create a restricted IAM user.
        iam.create_user(UserName=username)
        user_created = True

        # Grant only S3 list and read permissions.
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AllowBucketListing",
                    "Effect": "Allow",
                    "Action": "s3:ListBucket",
                    "Resource": f"arn:aws:s3:::{bucket}",
                },
                {
                    "Sid": "AllowObjectReading",
                    "Effect": "Allow",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket}/*",
                },
            ],
        }

        iam.put_user_policy(
            UserName=username,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy),
        )
        policy_attached = True

        # Generate credentials for the restricted user.
        credentials = iam.create_access_key(
            UserName=username,
        )["AccessKey"]

        access_key_id = credentials["AccessKeyId"]

        developer_s3 = aws_client(
            "s3",
            access_key_id,
            credentials["SecretAccessKey"],
        )

        yield {
            "bucket": bucket,
            "developer_s3": developer_s3,
            "admin_s3": admin_s3,
        }

    finally:
        cleanup_actions = []

        if access_key_id:
            cleanup_actions.append(
                (
                    "Delete developer access key",
                    lambda: iam.delete_access_key(
                        UserName=username,
                        AccessKeyId=access_key_id,
                    ),
                )
            )

        if policy_attached:
            cleanup_actions.append(
                (
                    "Delete developer inline policy",
                    lambda: iam.delete_user_policy(
                        UserName=username,
                        PolicyName=policy_name,
                    ),
                )
            )

        if user_created:
            cleanup_actions.append(
                (
                    "Delete developer IAM user",
                    lambda: iam.delete_user(
                        UserName=username,
                    ),
                )
            )

        if bucket_created:
            # Remove any objects created unexpectedly by tests.
            def empty_bucket():
                paginator = admin_s3.get_paginator("list_objects_v2")

                for page in paginator.paginate(Bucket=bucket):
                    for obj in page.get("Contents", []):
                        admin_s3.delete_object(
                            Bucket=bucket,
                            Key=obj["Key"],
                        )

            cleanup_actions.append(
                (
                    "Empty temporary S3 bucket",
                    empty_bucket,
                )
            )

            cleanup_actions.append(
                (
                    "Delete temporary S3 bucket",
                    lambda: admin_s3.delete_bucket(
                        Bucket=bucket,
                    ),
                )
            )

        run_cleanup(cleanup_actions)


def test_developer_can_list_bucket(security_environment):
    """A developer with ListBucket permission can list the bucket."""

    s3 = security_environment["developer_s3"]
    bucket = security_environment["bucket"]

    response = s3.list_objects_v2(Bucket=bucket)

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200


def test_developer_cannot_upload_object(security_environment):
    """An identity without PutObject permission cannot upload."""

    s3 = security_environment["developer_s3"]
    bucket = security_environment["bucket"]

    with pytest.raises(ClientError) as error:
        s3.put_object(
            Bucket=bucket,
            Key="unauthorized-receipt.txt",
            Body=b"IAM negative test",
        )

    assert error.value.response["Error"]["Code"] == "AccessDenied"


def test_explicit_deny_overrides_allow(security_environment):
    """An explicit Deny must override a broader S3 Allow."""

    bucket = security_environment["bucket"]
    admin_s3 = security_environment["admin_s3"]

    iam, _ = admin_clients()

    suffix = uuid.uuid4().hex[:10]
    username = f"deny-test-{suffix}"
    policy_name = "AllowS3ExceptDelete"
    object_key = f"protected-receipt-{suffix}.txt"

    access_key_id = None
    user_created = False
    policy_attached = False
    object_created = False

    try:
        # Seed an object with the bootstrap identity.
        admin_s3.put_object(
            Bucket=bucket,
            Key=object_key,
            Body=b"Protected receipt",
        )
        object_created = True

        # Create an independent IAM user.
        iam.create_user(UserName=username)
        user_created = True

        # Broad Allow combined with an explicit deletion Deny.
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AllowS3Operations",
                    "Effect": "Allow",
                    "Action": "s3:*",
                    "Resource": [
                        f"arn:aws:s3:::{bucket}",
                        f"arn:aws:s3:::{bucket}/*",
                    ],
                },
                {
                    "Sid": "DenyObjectDeletion",
                    "Effect": "Deny",
                    "Action": "s3:DeleteObject",
                    "Resource": f"arn:aws:s3:::{bucket}/*",
                },
            ],
        }

        iam.put_user_policy(
            UserName=username,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy),
        )
        policy_attached = True

        credentials = iam.create_access_key(
            UserName=username,
        )["AccessKey"]

        access_key_id = credentials["AccessKeyId"]

        restricted_s3 = aws_client(
            "s3",
            access_key_id,
            credentials["SecretAccessKey"],
        )

        # Positive control: reading is permitted.
        response = restricted_s3.get_object(
            Bucket=bucket,
            Key=object_key,
        )

        assert response["Body"].read() == b"Protected receipt"
        response["Body"].close()

        # Negative control: deletion must be denied.
        with pytest.raises(ClientError) as error:
            restricted_s3.delete_object(
                Bucket=bucket,
                Key=object_key,
            )

        assert error.value.response["Error"]["Code"] == "AccessDenied"

        # Confirm the denied deletion did not remove the object.
        admin_s3.head_object(
            Bucket=bucket,
            Key=object_key,
        )

    finally:
        cleanup_actions = []

        if object_created:
            cleanup_actions.append(
                (
                    "Delete protected test object",
                    lambda: admin_s3.delete_object(
                        Bucket=bucket,
                        Key=object_key,
                    ),
                )
            )

        if access_key_id:
            cleanup_actions.append(
                (
                    "Delete explicit-deny test access key",
                    lambda: iam.delete_access_key(
                        UserName=username,
                        AccessKeyId=access_key_id,
                    ),
                )
            )

        if policy_attached:
            cleanup_actions.append(
                (
                    "Delete explicit-deny inline policy",
                    lambda: iam.delete_user_policy(
                        UserName=username,
                        PolicyName=policy_name,
                    ),
                )
            )

        if user_created:
            cleanup_actions.append(
                (
                    "Delete explicit-deny IAM user",
                    lambda: iam.delete_user(
                        UserName=username,
                    ),
                )
            )

        run_cleanup(cleanup_actions)
