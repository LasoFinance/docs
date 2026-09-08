#!/usr/bin/env python3
"""Connect to Laso and optionally install its skill. Python 3, no dependencies."""

import argparse
import getpass
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener


API = "https://laso.finance"
CALLABLES = "https://us-central1-kyc-ts.cloudfunctions.net"


class SetupError(Exception):
    pass


class ApiError(SetupError):
    def __init__(self, operation, status):
        self.status = status
        super().__init__(f"{operation} failed (HTTP {status}). No automatic retry.")


class NoRedirect(HTTPRedirectHandler):
    # Credentials belong only to the endpoint named in the request.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(url, *, token=None, data=None, timeout=25):
    headers = {"Accept": "application/json", "User-Agent": "laso-setup/1"}
    if token:
        if not isinstance(token, str) or any(char.isspace() for char in token):
            raise SetupError(
                "The credential contains invalid characters. Check the saved key or session."
            )
        headers["Authorization"] = f"Bearer {token}"
    body = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode()
    try:
        with build_opener(NoRedirect).open(
            Request(url, data=body, headers=headers), timeout=timeout
        ) as response:
            if response.status == 204:
                return None
            return response.read()
    except HTTPError as error:
        # Never relay response bodies or URLs: either can contain credentials.
        raise ApiError("Laso request", error.code) from None
    except (URLError, TimeoutError, OSError):
        raise SetupError("Could not reach Laso. Check network access and rerun.") from None


def request_json(url, **kwargs):
    raw = request(url, **kwargs)
    if raw is None:
        return None
    try:
        result = json.loads(raw)
    except (ValueError, UnicodeError):
        raise SetupError("Laso returned invalid JSON. No credentials were printed.") from None
    if not isinstance(result, dict):
        raise SetupError("Laso returned an unexpected response.")
    return result


def private_directory(directory):
    if directory.is_symlink():
        raise SetupError("The Laso credential directory must not be a symlink.")
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory.chmod(0o700)


def atomic_write(destination, content):
    if destination.is_symlink():
        raise SetupError(f"Refusing to replace a symlink: {destination.name}.")
    fd, temporary = tempfile.mkstemp(
        prefix=f".{destination.name}-", dir=destination.parent
    )
    try:
        with os.fdopen(fd, "wb") as output:
            os.fchmod(output.fileno(), 0o600)
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def save_json(destination, value):
    atomic_write(destination, (json.dumps(value, indent=2) + "\n").encode())


def load_json(source):
    if source.is_symlink():
        raise SetupError(f"Credential files must not be symlinks: {source.name}.")
    if not source.exists():
        return {}
    try:
        value = json.loads(source.read_text())
    except (ValueError, UnicodeError):
        raise SetupError(f"{source.name} is invalid JSON; it was left unchanged.") from None
    if not isinstance(value, dict):
        raise SetupError(f"{source.name} must contain a JSON object; it was left unchanged.")
    source.chmod(0o600)
    return value


def fresh(credentials):
    expiry = credentials.get("id_token_expires_at")
    return (
        isinstance(credentials.get("id_token"), str)
        and bool(credentials["id_token"])
        and isinstance(credentials.get("user_id"), str)
        and bool(credentials["user_id"])
        and isinstance(expiry, (int, float))
        and not isinstance(expiry, bool)
        and math.isfinite(expiry)
        and expiry > time.time() + 60
    )


def with_auth(credentials, response):
    if not isinstance(response, dict):
        raise SetupError("Laso returned an incomplete session; saved credentials were preserved.")
    auth = response.get("auth", response)
    try:
        expires_in = float(auth["expires_in"])
        if not math.isfinite(expires_in) or expires_in <= 60:
            raise ValueError()
        if not all(
            isinstance(auth[key], str) and auth[key]
            for key in ("id_token", "refresh_token")
        ):
            raise ValueError()
        if not isinstance(response["user_id"], str) or not response["user_id"]:
            raise ValueError()
    except (KeyError, TypeError, ValueError):
        raise SetupError(
            "Laso returned an incomplete session; saved credentials were preserved."
        ) from None
    return {
        **credentials,
        "user_id": response["user_id"],
        "id_token": auth["id_token"],
        "refresh_token": auth["refresh_token"],
        "id_token_expires_at": int(time.time() + expires_in),
    }


def authenticate(credentials):
    if credentials.get("api_key"):
        response = request_json(f"{CALLABLES}/agentAuth", token=credentials["api_key"])
    elif credentials.get("refresh_token"):
        response = request_json(
            f"{API}/auth",
            data={
                "grant_type": "refresh_token",
                "refresh_token": credentials["refresh_token"],
            },
        )
    else:
        raise SetupError(
            "No saved key. Supply LASO_API_KEY or --key-stdin, "
            "or use --signup for a new account."
        )
    return with_auth(credentials, response), response.get("auth_url")


def signup(state, agent_name):
    pending = load_json(state / "signup.json")
    expiry = pending.get("expires_at", 0)
    if not isinstance(expiry, (int, float)) or not math.isfinite(expiry):
        raise SetupError("signup.json has an invalid expiry; it was left unchanged.")
    if not pending or expiry <= time.time() * 1000:
        pending = request_json(
            f"{API}/signup", data={"agent_name": agent_name, "label": agent_name}
        )
        if not isinstance(pending, dict) or not all(
            pending.get(key)
            for key in ("claim_token", "claim_code", "claim_url", "expires_at")
        ):
            raise SetupError("Laso returned an incomplete signup response.")
        save_json(state / "signup.json", pending)
    return {
        "status": "awaiting_human",
        "claim_url": pending["claim_url"],
        "next_action": (
            "Send claim_url to your human now. Do not open it yourself. "
            "Then run this helper with --claim."
        ),
    }


def claim(state):
    pending = load_json(state / "signup.json")
    if not pending.get("claim_token") or not pending.get("claim_code"):
        raise SetupError(
            "No pending signup. Run with --signup first and send its claim_url to your human."
        )
    query = urlencode({key: pending[key] for key in ("claim_token", "claim_code")})
    response = request_json(f"{API}/signup-status?{query}", timeout=60)
    if response is None:
        return None
    if not response.get("api_key"):
        raise SetupError(
            "The signup key was already delivered. "
            "Use saved credentials or request a new key from the dashboard."
        )
    # Delivery is one-time. Persist the key before parsing the session or reading the wallet.
    credentials = {"api_key": response["api_key"], "user_id": response.get("user_id")}
    save_json(state / "credentials.json", credentials)
    credentials = with_auth(credentials, response)
    save_json(state / "credentials.json", credentials)
    return credentials


def install(state, skill_directory):
    # Keep the helper at one stable path, including when invoked from a registry package.
    atomic_write(state / "setup.py", Path(__file__).read_bytes())
    if not skill_directory:
        return None
    directory = Path(skill_directory).expanduser()
    skill = request(f"{API}/SKILL.md")
    if not skill or not skill.startswith(b"---\n") or b"name: laso-finance\n" not in skill:
        raise SetupError("The skill download was invalid; the installed skill was left unchanged.")
    directory.mkdir(parents=True, exist_ok=True)
    atomic_write(directory / "SKILL.md", skill)
    return str(directory / "SKILL.md")


def setup(args, state):
    private_directory(state)
    credentials_file = state / "credentials.json"
    credentials = load_json(credentials_file)
    key = os.environ.get("LASO_API_KEY", "").strip()
    if args.key_stdin:
        key = (
            getpass.getpass("Laso API key: ")
            if sys.stdin.isatty()
            else sys.stdin.readline()
        ).strip()
        if not key:
            raise SetupError("No key received on stdin.")
    if key and not re.fullmatch(r"lasoak_[A-Za-z0-9_-]+", key):
        raise SetupError("Expected a Laso API key starting with lasoak_.")
    if key and key != credentials.get("api_key"):
        # A changed key must never reuse another account's cached session.
        credentials = {"api_key": key}
        if not credentials_file.exists():
            save_json(credentials_file, credentials)

    # Even a partial saved account must not silently become a second signup.
    has_credentials = bool(credentials)
    claimed = False
    if not has_credentials:
        if args.signup:
            install(state, args.skill_dir)
            return signup(state, args.agent_name)
        if args.claim:
            credentials = claim(state)
            if credentials is None:
                return {
                    "status": "awaiting_human",
                    "next_action": "Signup is still waiting. Run --claim again; do not add a sleep.",
                }
            claimed = True
        else:
            raise SetupError(
                "No saved key. Supply LASO_API_KEY or --key-stdin, "
                "or use --signup for a new account."
            )

    auth_url = None
    reused = fresh(credentials)
    if not reused:
        credentials, auth_url = authenticate(credentials)
        save_json(credentials_file, credentials)

    def connect():
        if claimed:
            # The signup claim already recorded this connection.
            return request_json(f"{CALLABLES}/getAgentWallet", token=credentials["id_token"])
        announced = request_json(
            f"{CALLABLES}/announceAgentConnection",
            token=credentials["id_token"],
            data={"agentName": args.agent_name},
        )
        if not isinstance(announced, dict):
            raise SetupError("Laso returned an incomplete connection response.")
        return announced.get("wallet") or request_json(
            f"{CALLABLES}/getAgentWallet", token=credentials["id_token"]
        )

    try:
        wallet = connect()
    except ApiError as error:
        if error.status != 401 or not reused:
            raise
        # A cached token can be invalidated before its nominal expiry. Remint once.
        credentials, auth_url = authenticate(credentials)
        save_json(credentials_file, credentials)
        reused = False
        wallet = connect()

    if not isinstance(wallet, dict) or not all(
        isinstance(wallet.get(key), bool) for key in ("has_wallet", "needs_funding")
    ):
        raise SetupError(
            "Connected, but Laso did not return wallet funding state. Rerun the helper to read it."
        )
    try:
        installed = install(state, args.skill_dir)
    except SetupError as error:
        raise SetupError(
            f"Connected and credentials saved, but skill installation failed: {error}"
        ) from None
    result = {
        "status": "connected",
        "user_id": credentials["user_id"],
        "reused_session": reused,
        "credentials_path": str(credentials_file),
        "helper_path": str(state / "setup.py"),
        "skill_path": installed,
        "wallet": {
            key: wallet.get(key)
            for key in ("has_wallet", "wallet_address", "balance_usdc", "needs_funding")
        },
    }
    if auth_url:
        result["auth_url"] = auth_url
    if not wallet.get("has_wallet"):
        result["next_action"] = "Finish wallet setup at https://laso.finance/agent/dashboard."
    elif wallet.get("needs_funding"):
        result["next_action"] = "Give your human wallet_address to fund with USDC on Solana."
    else:
        result["next_action"] = "Ready for the requested task. Setup itself does not spend money."
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--agent-name",
        default="Agent via Laso setup",
        help="Name shown in your human's dashboard",
    )
    parser.add_argument(
        "--skill-dir",
        help="Install SKILL.md in this framework's skill directory; omit for session-only use",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--key-stdin",
        action="store_true",
        help="Read a new key from stdin (hidden prompt on a terminal)",
    )
    mode.add_argument(
        "--signup",
        action="store_true",
        help="Create or reuse a signup link only when no credentials exist",
    )
    mode.add_argument(
        "--claim",
        action="store_true",
        help="Wait once for your human to finish signup, then save the delivered key",
    )
    args = parser.parse_args()
    try:
        result = setup(args, Path.home() / ".laso")
    except (SetupError, OSError) as error:
        message = (
            str(error)
            if isinstance(error, SetupError)
            else "Could not access the local Laso files. Check filesystem permissions."
        )
        print(json.dumps({"status": "error", "error": message}), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
