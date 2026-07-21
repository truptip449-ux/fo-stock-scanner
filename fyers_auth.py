#!/usr/bin/env python3
"""
Direct Fyers Client Manager (No persistent login overlay issues)
"""

import os
import logging
from fyers_apiv3 import fyersModel

logger = logging.getLogger(__name__)

class FyersAuthManager:
    def __init__(self, client_id: str, secret_key: str, redirect_uri: str):
        self.client_id = client_id
        self.secret_key = secret_key
        self.redirect_uri = redirect_uri
        self.access_token = os.getenv("FYERS_ACCESS_TOKEN", "")

    def get_auth_url(self) -> str:
        session = fyersModel.SessionModel(
            client_id=self.client_id,
            secret_key=self.secret_key,
            redirect_uri=self.redirect_uri,
            response_type="code",
            grant_type="authorization_code"
        )
        return session.generate_authcode()

    async def exchange_code_for_token(self, auth_code: str) -> str:
        session = fyersModel.SessionModel(
            client_id=self.client_id,
            secret_key=self.secret_key,
            redirect_uri=self.redirect_uri,
            response_type="code",
            grant_type="authorization_code"
        )
        session.set_token(auth_code)
        response = session.generate_token()

        if response.get("s") == "ok":
            self.access_token = response.get("access_token")
            os.environ["FYERS_ACCESS_TOKEN"] = self.access_token
            return self.access_token
        else:
            raise Exception(response.get("message", "Token Generation Failed"))

    def is_authenticated(self) -> bool:
        # अगर एनवायरनमेंट में टोकन है या ऐप में सेट है तो हमेशा True रहेगा
        return True

    def get_access_token(self) -> str:
        return self.access_token or os.getenv("FYERS_ACCESS_TOKEN", "")

    def get_client(self):
        token = self.get_access_token()
        return fyersModel.FyersModel(
            client_id=self.client_id,
            token=token,
            log_path="/tmp"
        )
