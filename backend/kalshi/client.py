from __future__ import annotations

import base64
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.asymmetric.padding import PSS

from app.config import settings


class KalshiClient:
    """
    Minimal Kalshi HTTP client using RSA-PSS signed headers.
    Supports demo and prod environments.
    """

    DEMO_BASE = "https://demo-api.kalshi.co"
    PROD_BASE = "https://api.elections.kalshi.com"
    MARKETS_PATH = "/trade-api/v2/markets"

    def __init__(
        self,
        key_id: str,
        private_key_pem: str,
        environment: str = "prod",
        base_url_override: Optional[str] = None,
    ):
        self.key_id = key_id
        self.environment = environment.lower()
        if base_url_override:
            self.base_url = base_url_override.rstrip("/")
        else:
            self.base_url = self.PROD_BASE if self.environment == "prod" else self.DEMO_BASE

        self.private_key = self._load_private_key(private_key_pem)

        self.last_api_call: datetime = datetime.now()

    def _load_private_key(self, pem_str: str) -> rsa.RSAPrivateKey:
        """
        Load RSA private key from PEM string. Handles common cases where the PEM is provided
        on a single line with literal "\n" sequences.
        """
        # Trim and replace literal \n with real newlines if present
        candidate = pem_str.strip()
        if "\\n" in candidate:
            candidate = candidate.replace("\\n", "\n")
        try:
            key = serialization.load_pem_private_key(candidate.encode("utf-8"), password=None)
        except Exception as e:
            raise ValueError("Failed to load Kalshi RSA private key; check PEM formatting") from e
        if not isinstance(key, rsa.RSAPrivateKey):
            raise ValueError("Kalshi private key must be an RSA private key")
        return key

    def rate_limit(self) -> None:
        threshold_ms = 100
        now = datetime.now()
        if now - self.last_api_call < timedelta(milliseconds=threshold_ms):
            time.sleep(threshold_ms / 1000)
        self.last_api_call = datetime.now()

    def _sign(self, method: str, path: str) -> Dict[str, str]:
        """
        Build auth headers for Kalshi signed requests.
        Signature is over timestamp + method + path (without query).
        """
        ts_ms = int(time.time() * 1000)
        ts_str = str(ts_ms)

        # strip query params
        path_no_query = path.split("?", 1)[0]
        msg = f"{ts_str}{method}{path_no_query}".encode("utf-8")

        signature = self.private_key.sign(
            msg,
            PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
            hashes.SHA256(),
        )
        sig_b64 = base64.b64encode(signature).decode("utf-8")
        return {
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-SIGNATURE": sig_b64,
            "KALSHI-ACCESS-TIMESTAMP": ts_str,
        }

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> httpx.Response:
        self.rate_limit()
        url = f"{self.base_url}{path}"
        headers = self._sign("GET", path)
        resp = httpx.get(url, headers=headers, params=params or {}, timeout=10.0)
        resp.raise_for_status()
        return resp


def build_kalshi_client() -> Optional[KalshiClient]:
    """
    Build a KalshiClient from settings if credentials are provided.
    Returns None if missing creds.
    """
    key = settings.kalshi_key_id
    pk = settings.kalshi_private_key
    if not key or not pk:
        return None
    return KalshiClient(
        key_id=key,
        private_key_pem=pk,
        environment=settings.kalshi_environment,
        base_url_override=settings.kalshi_api_base,
    )
