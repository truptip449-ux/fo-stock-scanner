#!/usr/bin/env python3
"""
Fyers OAuth Authentication Manager
Handles token exchange and session management.
"""

import os
import logging
import httpx
from typing import Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class FyersAuthManager:
    """
    Manages Fyers OAuth flow and token handling.
    """
    
    FYERS_AUTH_URL = "https://api-t1.fyers.in/api/v3/token"
    FYERS_AUTH_ENDPOINT = "https://api-t1.fyers.in/api/v3/auth/login"
    
    def __init__(self, client_id: str, secret_key: str, redirect_uri: str):
        """
        Initialize Fyers auth manager.
        
        Args:
            client_id: Fyers API client ID
            secret_key: Fyers API secret key
            redirect_uri: OAuth redirect URI
        """
        self.client_id = client_id
        self.secret_key = secret_key
        self.redirect_uri = redirect_uri
        
        self.access_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        
        logger.info("FyersAuthManager initialized")
    
    def get_auth_url(self) -> str:
        """
        Generate Fyers OAuth login URL.
        """
        auth_url = f"{self.FYERS_AUTH_ENDPOINT}?client_id={self.client_id}&redirect_uri={self.redirect_uri}&response_type=code&state=STATE"
        logger.info(f"Generated auth URL")
        return auth_url
    
    async def exchange_code_for_token(self, auth_code: str) -> str:
        """
        Exchange authorization code for access token.
        
        Args:
            auth_code: Authorization code from Fyers callback
            
        Returns:
            Access token string
            
        Raises:
            Exception: If token exchange fails
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                payload = {
                    "client_id": self.client_id,
                    "client_secret": self.secret_key,
                    "code": auth_code,
                    "grant_type": "authorization_code",
                    "state": "STATE"
                }
                
                response = await client.post(self.FYERS_AUTH_URL, json=payload)
                response.raise_for_status()
                
                data = response.json()
                self.access_token = data.get("access_token")
                
                # Set token expiry (usually 24 hours)
                expires_in = data.get("expires_in", 86400)
                self.token_expiry = datetime.now() + timedelta(seconds=expires_in)
                
                logger.info(f"Token obtained. Expires at: {self.token_expiry}")
                return self.access_token
        
        except httpx.HTTPError as e:
            logger.error(f"Token exchange failed: {e}")
            raise Exception(f"Failed to exchange auth code: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in token exchange: {e}")
            raise
    
    def is_authenticated(self) -> bool:
        """
        Check if user is currently authenticated and token is valid.
        """
        if not self.access_token:
            return False
        
        if self.token_expiry and datetime.now() >= self.token_expiry:
            logger.warning("Token has expired")
            self.access_token = None
            return False
        
        return True
    
    def get_access_token(self) -> Optional[str]:
        """
        Get current access token if valid.
        """
        if self.is_authenticated():
            return self.access_token
        return None
    
    def set_token(self, token: str, expires_in: int = 86400):
        """
        Manually set access token (for testing/manual flow).
        
        Args:
            token: Access token string
            expires_in: Seconds until expiry (default 24h)
        """
        self.access_token = token
        self.token_expiry = datetime.now() + timedelta(seconds=expires_in)
        logger.info("Token manually set")
    
    def clear_token(self):
        """
        Clear authentication (logout).
        """
        self.access_token = None
        self.token_expiry = None
        logger.info("Token cleared")
