
import pytest

from app.jobs.retry_policy import retry_delay_seconds


def test_exponential_backoff():
    assert retry_delay_seconds(1) == 10
    assert retry_delay_seconds(2) == 20
    assert retry_delay_seconds(3) == 40


def test_backoff_is_capped():
    assert retry_delay_seconds(20) == 300


def test_invalid_attempt():
    with pytest.raises(ValueError):
        retry_delay_seconds(0)
