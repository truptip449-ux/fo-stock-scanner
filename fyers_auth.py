#!/usr/bin/env python3
"""
Fyers OAuth Authentication Manager (v3 Library)
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
        self.access_token = None
        self.fyers_instance = None

    def get_auth_url(self) -> str:
        """Official Fyers SDK SessionModel से Auth URL बनाएगा"""
        session = fyersModel.SessionModel(
            client_id=self.client_id,
            secret_key=self.secret_key,
            redirect_uri=self.redirect_uri,
            response_type="code",
            grant_type="authorization_code"
        )
        return session.generate_authcode()

    async def exchange_code_for_token(self, auth_code: str) -> str:
        """Auth Code से Access Token प्राप्त करेगा"""
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
            self.fyers_instance = fyersModel.FyersModel(
                client_id=self.client_id,
                token=self.access_token,
                log_path=os.getcwd()
            )
            logger.info("Fyers Access Token Generated Successfully!")
            return self.access_token
        else:
            logger.error(f"Token generation failed: {response}")
            raise Exception(response.get("message", "Token Generation Failed"))

    def is_authenticated(self) -> bool:
        return self.access_token is not None

    def get_access_token(self) -> str:
        return self.access_token
