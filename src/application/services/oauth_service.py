from __future__ import annotations

import secrets
from typing import Dict, Optional

import requests

from config import Settings


class OAuthService:
    """Handles OAuth authorization flow against a generic provider."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def build_authorization_url(self, state: Optional[str] = None, scope: str = "openid email profile") -> Dict[str, str]:
        if not self.settings.oauth_authorize_url:
            raise RuntimeError("OAuth não configurado.")
        if not state:
            state = secrets.token_urlsafe(16)
        params = {
            "response_type": "code",
            "client_id": self.settings.oauth_client_id,
            "redirect_uri": self.settings.oauth_redirect_uri,
            "scope": scope,
            "state": state,
        }
        query = "&".join(f"{key}={requests.utils.quote(value)}" for key, value in params.items())
        return {"url": f"{self.settings.oauth_authorize_url}?{query}", "state": state}

    def exchange_code(self, code: str) -> Dict[str, str]:
        if not self.settings.oauth_token_url:
            raise RuntimeError("OAuth não configurado.")
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.settings.oauth_redirect_uri,
            "client_id": self.settings.oauth_client_id,
            "client_secret": self.settings.oauth_client_secret,
        }
        response = requests.post(self.settings.oauth_token_url, data=payload, timeout=30)
        response.raise_for_status()
        return response.json()
