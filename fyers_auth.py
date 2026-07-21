#!/usr/bin/env python3
"""
Fyers OAuth Authentication Manager with File Persistence
"""

import os
import json
import logging
from fyers_apiv3 import fyersModel

logger = logging.getLogger(__name__)

TOKEN_FILE = "fyers_token.json"

class FyersAuthManager:
    def __init__(self, client_id: str, secret_key: str, redirect_uri: str):
        self.client_id = client_id
        self.secret_key = secret_key
        self.redirect_uri = redirect_uri
        self.access_token = self._load_token_from_file()

    def _load_token_from_file(self):
        """फ़ाइल से टोकन लोड करता है"""
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, "r") as f:
                    data = json.load(f)
                    token = data.get("access_token")
                    if token:
                        logger.info("Found saved access token from file!")
                        return token
            except Exception as e:
                logger.error(f"Error reading token file: {e}")
        return None

    def _save_token_to_file(self, token: str):
        """टोकन को फ़ाइल में सेव करता है"""
        try:
            with open(TOKEN_FILE, "w") as f:
                json.dump({"access_token": token}, f)
            logger.info("Access token saved to file.")
        except Exception as e:
            logger.error(f"Error saving token file: {e}")

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
            self._save_token_to_file(self.access_token)
            return self.access_token
        else:
            logger.error(f"Token exchange error: {response}")
            raise Exception(response.get("message", "Token Generation Failed"))

    def is_authenticated(self) -> bool:
        if not self.access_token:
            self.access_token = self._load_token_from_file()
        return self.access_token is not None

    def get_access_token(self) -> str:
        if not self.access_token:
            self.access_token = self._load_token_from_file()
        return self.access_token

    def get_client(self):
        token = self.get_access_token()
        if not token:
            return None
        return fyersModel.FyersModel(
            client_id=self.client_id,
            token=token,
            log_path=os.getcwd()
        )
