
from datetime import datetime, timedelta, timezone


def retry_delay_seconds(
    attempts: int,
    base_delay: int = 10,
    max_delay: int = 300,
) -> int:
    if attempts < 1:
        raise ValueError("attempts must be >= 1")

    return min(
        base_delay * (2 ** (attempts - 1)),
        max_delay,
    )


def next_retry_time(
    attempts: int,
    now: datetime | None = None,
) -> datetime:
    now = now or datetime.now(timezone.utc)

    return now + timedelta(
        seconds=retry_delay_seconds(attempts)
    )
