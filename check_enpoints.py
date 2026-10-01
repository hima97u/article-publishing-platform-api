"""Smoke-test all configured API URL routes.

Usage:
    python check_all_urls.py
    python check_all_urls.py --base-url http://localhost:8080

For authenticated GET checks, set API_EMAIL and API_PASSWORD or pass them as
arguments. The script only reads data and does not create or delete records.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import Iterable

import requests


UUID = "00000000-0000-4000-8000-000000000000"


@dataclass(frozen=True)
class Endpoint:
    path: str
    methods: str
    authenticated: bool = False


@dataclass(frozen=True)
class AuthTokens:
    access: str
    refresh: str | None = None


ENDPOINTS = [
    Endpoint("/", "GET"),
    Endpoint("/redoc/", "GET"),
    Endpoint("/supersecret/", "GET"),
    Endpoint("/supersecret/login/", "GET, POST"),
    Endpoint("/api/v1/auth/login/", "POST"),
    Endpoint("/api/v1/auth/logout/", "GET, POST", True),
    Endpoint("/api/v1/auth/user", "GET, PUT, PATCH", True),
    Endpoint("/api/v1/auth/user/", "GET, PUT, PATCH", True),
    Endpoint("/api/v1/auth/password/change/", "POST", True),
    Endpoint("/api/v1/auth/password/reset/", "POST"),
    Endpoint("/api/v1/auth/password/reset/confirm/", "POST"),
    Endpoint("/api/v1/auth/password/reset/confirm/test-token/test/", "POST"),
    Endpoint("/api/v1/auth/token/refresh/", "POST"),
    Endpoint("/api/v1/auth/token/verify/", "POST"),
    Endpoint("/api/v1/auth/registration/", "POST"),
    Endpoint("/api/v1/auth/registration/resend-email/", "POST"),
    Endpoint("/api/v1/auth/registration/verify-email/", "POST"),
    Endpoint("/api/v1/auth/registration/account-email-verification-sent/", "GET"),
    Endpoint("/api/v1/auth/registration/account-confirm-email/test/", "GET"),
    Endpoint("/api/v1/profiles/all/", "GET", True),
    Endpoint("/api/v1/profiles/me/", "GET", True),
    Endpoint("/api/v1/profiles/me/update/", "GET, PATCH", True),
    Endpoint("/api/v1/profiles/me/followers/", "GET", True),
    Endpoint(f"/api/v1/profiles/{UUID}/follow/", "POST", True),
    Endpoint(f"/api/v1/profiles/{UUID}/unfollow/", "POST", True),
    Endpoint("/api/v1/articles/", "GET, POST", True),
    Endpoint(f"/api/v1/articles/{UUID}/", "GET, PUT, PATCH, DELETE", True),
    Endpoint(f"/api/v1/articles/{UUID}/clap/", "POST, DELETE", True),
    Endpoint(f"/api/v1/ratings/rate_article/{UUID}/", "POST", True),
    Endpoint(f"/api/v1/bookmarks/bookmark_article/{UUID}/", "POST", True),
    Endpoint(f"/api/v1/bookmarks/remove_bookmark/{UUID}/", "DELETE", True),
    Endpoint(f"/api/v1/responses/article/{UUID}/", "GET, POST", True),
    Endpoint(f"/api/v1/responses/{UUID}/", "GET, PUT, PATCH, DELETE", True),
    Endpoint("/api/v1/search/search/", "GET"),
]


# Useful checks for paths that are commonly expected but are not configured here.
EXTRA_CHECKS = [
    Endpoint("/api/v1/search/", "GET"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.getenv("API_BASE_URL", "http://localhost:8080"),
        help="API base URL (default: API_BASE_URL or http://localhost:8080)",
    )
    parser.add_argument("--email", default=os.getenv("API_EMAIL"))
    parser.add_argument("--password", default=os.getenv("API_PASSWORD"))
    parser.add_argument(
        "--verification-token",
        default=os.getenv("API_VERIFICATION_TOKEN"),
        help="Email verification key (default: API_VERIFICATION_TOKEN)",
    )
    parser.add_argument(
        "--ask-verification-token",
        action="store_true",
        help="Prompt securely for the email verification key (default behavior)",
    )
    parser.add_argument(
        "--skip-verification-token",
        action="store_true",
        help="Skip the verification-token prompt",
    )
    return parser.parse_args()


def login(
    session: requests.Session, base_url: str, email: str, password: str
) -> AuthTokens | None:
    try:
        response = session.post(
            f"{base_url}/api/v1/auth/login/",
            json={"email": email, "password": password},
            timeout=10,
        )
    except requests.RequestException as error:
        print(f"LOGIN ERROR: {error}")
        return None

    if response.status_code >= 400:
        print(f"LOGIN FAILED: HTTP {response.status_code}")
        return None

    try:
        data = response.json()
        access = data.get("access")
        if not access:
            print("LOGIN FAILED: access token was not returned")
            return None
        refresh = data.get("refresh") or response.cookies.get("authors-refresh-token")
        return AuthTokens(access=access, refresh=refresh)
    except ValueError:
        print("LOGIN FAILED: response was not JSON")
        return None


def classify(status: int | None, authenticated: bool) -> str:
    if status is None:
        return "ERROR"
    if 200 <= status < 400:
        return "WORKING"
    if status in {401, 403}:
        return "AUTH REQUIRED" if authenticated else "WORKING"
    if status == 405:
        return "WORKING (method restricted)"
    if status == 404:
        return "NOT FOUND"
    if status >= 500:
        return "SERVER ERROR"
    return "HTTP ERROR"


def check_endpoint(
    session: requests.Session,
    base_url: str,
    endpoint: Endpoint,
) -> tuple[int | None, str]:
    try:
        response = session.options(f"{base_url}{endpoint.path}", timeout=10)
        return response.status_code, classify(response.status_code, endpoint.authenticated)
    except requests.RequestException as error:
        print(f"REQUEST ERROR {endpoint.path}: {error}")
        return None, "ERROR"


def check_auth_tokens(
    session: requests.Session,
    base_url: str,
    tokens: AuthTokens,
) -> tuple[int, int]:
    print("\nAuthentication token checks")
    print("==========================")
    checks = [("access token verify", "/api/v1/auth/token/verify/", {"token": tokens.access})]
    if tokens.refresh:
        checks.append(
            ("refresh token", "/api/v1/auth/token/refresh/", {"refresh": tokens.refresh})
        )

    working = 0
    failing = 0
    for label, path, payload in checks:
        try:
            response = session.post(f"{base_url}{path}", json=payload, timeout=10)
            result = classify(response.status_code, True)
            print(f"{result:24} HTTP {response.status_code:<3} {label}")
            if result in {"NOT FOUND", "SERVER ERROR", "ERROR", "HTTP ERROR"}:
                failing += 1
            else:
                working += 1
        except requests.RequestException as error:
            print(f"ERROR                    {label}: {error}")
            failing += 1
    return working, failing


def check_email_verification(
    session: requests.Session,
    base_url: str,
    verification_token: str,
) -> tuple[int, int]:
    print("\nEmail verification token check")
    print("==============================")
    try:
        response = session.post(
            f"{base_url}/api/v1/auth/registration/verify-email/",
            json={"key": verification_token},
            timeout=10,
        )
        if 200 <= response.status_code < 300:
            print(f"WORKING                  HTTP {response.status_code:<3} email verification token")
            return 1, 0
        if response.status_code in {400, 404}:
            print(
                f"INVALID TOKEN             HTTP {response.status_code:<3} "
                "email verification token"
            )
            return 0, 1
        print(f"SERVER ERROR              HTTP {response.status_code:<3} email verification token")
        return 0, 1
    except requests.RequestException as error:
        print(f"ERROR                    email verification token: {error}")
        return 0, 1


def check_authenticated_reads(
    session: requests.Session,
    base_url: str,
) -> tuple[int, int]:
    print("\nAuthenticated read checks")
    print("=========================")
    paths = [
        "/api/v1/auth/user/",
        "/api/v1/profiles/all/",
        "/api/v1/profiles/me/",
        "/api/v1/profiles/me/followers/",
        "/api/v1/articles/",
        "/api/v1/responses/article/00000000-0000-4000-8000-000000000000/",
    ]
    working = 0
    failing = 0
    for path in paths:
        try:
            response = session.get(f"{base_url}{path}", timeout=10)
            if response.status_code in {401, 403}:
                result = "AUTH FAILED"
                failing += 1
            elif response.status_code >= 500:
                result = "SERVER ERROR"
                failing += 1
            elif response.status_code == 404:
                result = "AUTH OK (resource missing)"
                working += 1
            else:
                result = "AUTH OK"
                working += 1
            print(f"{result:24} HTTP {response.status_code:<3} GET {path}")
        except requests.RequestException as error:
            print(f"ERROR                    GET {path}: {error}")
            failing += 1
    return working, failing


def run_checks(
    session: requests.Session,
    base_url: str,
    endpoints: Iterable[Endpoint],
    title: str,
) -> tuple[int, int]:
    print(f"\n{title}")
    print("=" * len(title))
    working = 0
    failing = 0

    for endpoint in endpoints:
        status, result = check_endpoint(session, base_url, endpoint)
        status_text = str(status) if status is not None else "-"
        print(f"{result:24} HTTP {status_text:3} {endpoint.methods:24} {endpoint.path}")
        if result in {"NOT FOUND", "SERVER ERROR", "ERROR", "HTTP ERROR"}:
            failing += 1
        else:
            working += 1

    return working, failing


def main() -> int:
    args = parse_args()
    base_url = args.base_url.rstrip("/")
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})

    if args.email and args.password:
        tokens = login(session, base_url, args.email, args.password)
        if tokens:
            session.headers.update({"Authorization": f"Bearer {tokens.access}"})
            print("Authenticated checks: enabled")
            token_working, token_failing = check_auth_tokens(session, base_url, tokens)
            auth_working, auth_failing = check_authenticated_reads(session, base_url)
        else:
            print("Authenticated checks: unavailable; route checks will continue")
            token_working = token_failing = auth_working = auth_failing = 0
    else:
        print("Authenticated checks: unavailable; set API_EMAIL and API_PASSWORD to enable them")
        token_working = token_failing = auth_working = auth_failing = 0

    verification_working = verification_failing = 0
    verification_token = args.verification_token
    if not args.skip_verification_token and not verification_token:
        verification_token = input("Email verification token: ").strip()
    if verification_token:
        verification_working, verification_failing = check_email_verification(
            session, base_url, verification_token
        )

    working, failing = run_checks(session, base_url, ENDPOINTS, "Configured URLS")
    extra_working, extra_failing = run_checks(
        session, base_url, EXTRA_CHECKS, "Additional expected-path checks"
    )
    working += (
        extra_working
        + token_working
        + auth_working
        + verification_working
    )
    failing += (
        extra_failing
        + token_failing
        + auth_failing
        + verification_failing
    )

    print(f"\nSUMMARY: {working} working, {failing} not working")
    return 1 if failing else 0


if __name__ == "__main__":
    raise SystemExit(main())
