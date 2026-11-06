"""Scan Git-visible text without printing potential secret values.

This is a small local guard, not a comprehensive credential-history scanner.
Ignored files, customer data and environment files are never opened.
"""
from pathlib import Path
import re
import subprocess


PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "provider_key": re.compile(r"\b(?:sk-proj-|sk-|hf_)[A-Za-z0-9_-]{24,}"),
    "slack_token": re.compile(r"\bxox[baprs]-\d{6,}-[A-Za-z0-9-]{12,}"),
    "jwt_literal": re.compile(r"\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}"),
}


def findings(content):
    return [(number, name) for number, line in enumerate(content.splitlines(), 1)
            for name, pattern in PATTERNS.items() if pattern.search(line)]


def main():
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
                            cwd=root, capture_output=True, check=True)
    count = 0
    for name in set(result.stdout.decode().split("\0")) - {""}:
        path = root / name
        if not path.is_file() or path.is_symlink() or path.stat().st_size > 2 * 1024 * 1024:
            continue
        if path.name.startswith(".env") and path.name != ".env.example":
            continue
        body = path.read_bytes()
        try:
            content = body.decode("utf-16" if body.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8")
        except UnicodeError:
            continue
        for line, rule in findings(content):
            print(f"{name}:{line}: potential {rule} (value suppressed)")
            count += 1
    print(f"Secret scan: {count} potential findings; ignored files were excluded")
    return 1 if count else 0


if __name__ == "__main__":
    raise SystemExit(main())
