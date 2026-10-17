import os
import sys
import httpx

BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://localhost:8000",
)


def check(path, expected_status):
    response = httpx.get(
        f"{BASE_URL}{path}",
        timeout=10,
    )

    print(
        f"GET {path}: "
        f"{response.status_code}"
    )

    if response.status_code != expected_status:
        raise RuntimeError(
            f"Expected {expected_status}, "
            f"got {response.status_code}"
        )


def main():
    check("/health", 200)
    check("/tickets/", 401)

    print("Docker smoke tests passed!")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Smoke test failed: {exc}")
        sys.exit(1)