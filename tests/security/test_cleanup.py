import pytest

from tests.security.cleanup import CleanupError, run_cleanup


def test_cleanup_continues_after_failure():
    """A failed cleanup must not prevent later actions."""

    executed = []

    def delete_access_key():
        executed.append("access_key")

    def delete_policy():
        executed.append("policy")
        raise RuntimeError("Simulated IAM service failure")

    def delete_user():
        executed.append("user")

    def delete_bucket():
        executed.append("bucket")

    with pytest.raises(CleanupError) as error:
        run_cleanup(
            [
                ("Delete access key", delete_access_key),
                ("Delete policy", delete_policy),
                ("Delete user", delete_user),
                ("Delete bucket", delete_bucket),
            ]
        )

    assert executed == [
        "access_key",
        "policy",
        "user",
        "bucket",
    ]

    assert "Delete policy" in str(error.value)
    assert "Simulated IAM service failure" in str(error.value)


def test_cleanup_reports_multiple_failures():
    """Every cleanup failure must appear in the final error."""

    executed = []

    def failing_policy():
        executed.append("policy")
        raise RuntimeError("Policy deletion failed")

    def failing_bucket():
        executed.append("bucket")
        raise RuntimeError("Bucket deletion failed")

    with pytest.raises(CleanupError) as error:
        run_cleanup(
            [
                ("Delete policy", failing_policy),
                ("Delete bucket", failing_bucket),
            ]
        )

    assert executed == ["policy", "bucket"]

    message = str(error.value)

    assert "2 cleanup action(s) failed" in message
    assert "Policy deletion failed" in message
    assert "Bucket deletion failed" in message


def test_cleanup_succeeds_when_all_actions_pass():
    """Successful cleanup must not raise an exception."""

    executed = []

    run_cleanup(
        [
            ("First", lambda: executed.append("first")),
            ("Second", lambda: executed.append("second")),
        ]
    )

    assert executed == ["first", "second"]


def test_cleanup_handles_empty_action_list():
    """No resources created means nothing needs cleaning up."""

    run_cleanup([])
