"""Google OAuth for the GBP API.

Per-client flow: har client ek baar browser me authorize karega,
refresh token tokens/<slug>.json me save hoga (gitignored).
Secrets kabhi code/config/chat me nahi aane chahiye.
"""
import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

SCOPES = ["https://www.googleapis.com/auth/business.manage"]

BASE_DIR = Path(__file__).resolve().parent.parent
TOKENS_DIR = BASE_DIR / "tokens"
TOKENS_DIR.mkdir(exist_ok=True)


def token_path(slug: str) -> Path:
    return TOKENS_DIR / f"{slug}.json"


def build_flow(client_secrets_path: str, redirect_uri: str) -> Flow:
    """OAuth Flow banao — client_secrets_path Google Cloud se download ki hui JSON hai."""
    return Flow.from_client_secrets_file(
        client_secrets_path, scopes=SCOPES, redirect_uri=redirect_uri
    )


def authorization_url(flow: Flow, state: str) -> str:
    url, _ = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", state=state,
        prompt="consent",  # refresh_token pakka mile
    )
    return url


def save_credentials(slug: str, creds: Credentials) -> None:
    data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes or SCOPES),
    }
    token_path(slug).write_text(json.dumps(data), encoding="utf-8")


def load_credentials(slug: str) -> Credentials | None:
    """Saved credentials lao; expired ho to refresh karo. None = connect nahi hua."""
    p = token_path(slug)
    if not p.exists():
        return None
    try:
        creds = Credentials.from_authorized_user_file(str(p), SCOPES)
    except Exception:
        return None
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            save_credentials(slug, creds)
        except Exception:
            return None
    return creds if (creds and creds.valid) else None


def is_connected(slug: str) -> bool:
    return load_credentials(slug) is not None


def disconnect(slug: str) -> None:
    p = token_path(slug)
    if p.exists():
        p.unlink()
