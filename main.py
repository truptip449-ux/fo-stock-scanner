#!/usr/bin/env python3
"""
F&O Stock Scanner - FastAPI Backend
"""

import os
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from datetime import datetime

from fyers_auth import FyersAuthManager
from market_data import MarketDataManager

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="F&O Stock Scanner", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FYERS_CLIENT_ID = os.getenv("FYERS_CLIENT_ID", "")
FYERS_SECRET_KEY = os.getenv("FYERS_SECRET_KEY", "")
FYERS_REDIRECT_URI = os.getenv("FYERS_REDIRECT_URI", "")

fyers_auth = FyersAuthManager(
    client_id=FYERS_CLIENT_ID,
    secret_key=FYERS_SECRET_KEY,
    redirect_uri=FYERS_REDIRECT_URI
)

market_data = MarketDataManager(fyers_auth)

try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
    logger.warning(f"Static files mount notice: {e}")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request, auth_code: str = None, code: str = None, s: str = None):
    received_code = auth_code or code or request.query_params.get("auth_code") or request.query_params.get("code")
    
    if received_code:
        try:
            logger.info("Found auth code on homepage, generating token...")
            await fyers_auth.exchange_code_for_token(received_code)
            return RedirectResponse(url="/")
        except Exception as e:
            logger.error(f"Error exchanging code on root: {e}")

    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>F&O Stock Scanner</h1><p>static/index.html not found</p>"

@app.get("/auth/login")
async def auth_login():
    auth_url = fyers_auth.get_auth_url()
    return RedirectResponse(url=auth_url)

@app.get("/auth/callback")
async def auth_callback(request: Request, auth_code: str = None, code: str = None):
    received_code = auth_code or code or request.query_params.get("auth_code") or request.query_params.get("code")
    
    if received_code:
        try:
            await fyers_auth.exchange_code_for_token(received_code)
        except Exception as e:
            logger.error(f"Callback error: {e}")
            
    return RedirectResponse(url="/")

@app.post("/api/refresh")
async def refresh_data():
    if not fyers_auth.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated. Please login via Fyers.")
    try:
        data = await market_data.refresh_futstk_data()
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "count": len(data),
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Refresh failed: {str(e)}")

@app.get("/api/data")
async def get_cached_data():
    data = market_data.get_cached_data()
    return {
        "status": "success",
        "count": len(data),
        "timestamp": market_data.get_cache_timestamp(),
        "data": data
    }

@app.get("/api/export")
async def export_to_excel():
    data = market_data.get_cached_data()
    if not data:
        raise HTTPException(status_code=400, detail="No data to export. Please refresh first.")
    
    excel_buffer = market_data.export_to_excel(data)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"FO_Scanner_{timestamp}.xlsx"
    
    return FileResponse(
        iter([excel_buffer.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename
    )

@app.get("/api/auth-status")
async def auth_status():
    return {
        "authenticated": fyers_auth.is_authenticated(),
        "auth_url": "/auth/login"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "authenticated": fyers_auth.is_authenticated()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
