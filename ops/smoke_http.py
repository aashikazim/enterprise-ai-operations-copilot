"""Read-only HTTP smoke check. Example: python3 ops/smoke_http.py http://localhost:8080"""
import sys
from urllib.request import urlopen
from urllib.error import HTTPError
from urllib.parse import urlsplit


def main(origin):
    parsed = urlsplit(origin)
    if parsed.scheme not in {'http', 'https'} or parsed.username or parsed.password or parsed.query:
        raise ValueError('Expected HTTP origin without credentials/query')
    for path, expected in [('/', 200), ('/chat', 200), ('/api/health', 200),
                           ('/api/ready', 200), ('/api/auth/me', 401)]:
        try:
            response = urlopen(origin.rstrip('/') + path, timeout=10)
        except HTTPError as error:
            response = error
        with response:
            assert response.status == expected, f'{path}: unexpected status'
            assert response.headers.get('X-Content-Type-Options') == 'nosniff'
            assert response.headers.get('Content-Security-Policy')
        print(f'{path}: {expected}, security headers present')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080')
