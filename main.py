#!/usr/bin/env python3
"""
F&O Stock Scanner - FastAPI Backend
Production-ready ultra-fast F&O scanner with Fyers integration.
"""

import os
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from datetime import datetime
import io

from fyers_auth import FyersAuthManager
from market_data import MarketDataManager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="F&O Stock Scanner",
    description="Ultra-fast F&O stock scanner with real-time data",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize managers
fyers_auth = FyersAuthManager(
    client_id=os.getenv("FYERS_CLIENT_ID"),
    secret_key=os.getenv("FYERS_SECRET_KEY"),
    redirect_uri=os.getenv("FYERS_REDIRECT_URI")
)

market_data = MarketDataManager(fyers_auth)

# Mount static files
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
    logger.warning(f"Static files not mounted: {e}")


# ==================== ROUTES ====================

@app.get("/", response_class=HTMLResponse)
async def root():
    """
    Serve the main dashboard UI.
    """
    try:
        with open("static/index.html", "r") as f:
            return f.read()
    except FileNotFoundError:
        logger.error("index.html not found")
        return """
        <!DOCTYPE html>
        <html>
        <head><title>F&O Stock Scanner</title></head>
        <body style="background: #0f0f0f; color: #fff; font-family: system-ui;">
            <h1>F&O Stock Scanner</h1>
            <p>Loading dashboard...</p>
        </body>
        </html>
        """


@app.get("/auth/login")
async def auth_login():
    """
    Redirect user to Fyers OAuth login.
    """
    auth_url = fyers_auth.get_auth_url()
    return {"auth_url": auth_url}


@app.get("/auth/callback")
async def auth_callback(auth_code: str = None):
    """
    Handle Fyers OAuth callback.
    """
    if not auth_code:
        raise HTTPException(status_code=400, detail="Missing auth code")
    
    try:
        access_token = await fyers_auth.exchange_code_for_token(auth_code)
        logger.info("User authenticated successfully")
        return JSONResponse(
            status_code=200,
            content={"status": "authenticated", "message": "Redirecting to dashboard"},
            headers={"Location": "/"}
        )
    except Exception as e:
        logger.error(f"Auth callback error: {e}")
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")


@app.post("/api/refresh")
async def refresh_data(request: Request):
    """
    Manual refresh: Fetch latest FUTSTK data from Fyers API.
    
    Process:
    1. Verify Fyers authentication
    2. Parse NSE_FO master CSV to identify active expiry months
    3. Filter FUTSTK symbols only (NO indices, NO options)
    4. Fetch spot + 3 futures quotes from Fyers
    5. Cache in memory
    6. Return JSON with scanner data
    """
    try:
        logger.info("Refresh triggered by user")
        
        # Check authentication
        if not fyers_auth.is_authenticated():
            raise HTTPException(
                status_code=401,
                detail="Not authenticated. Please login via Fyers OAuth."
            )
        
        # Refresh market data
        data = await market_data.refresh_futstk_data()
        
        logger.info(f"Refresh completed: {len(data)} unique FUTSTK symbols")
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "count": len(data),
            "data": data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Refresh error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Refresh failed: {str(e)}")


@app.get("/api/data")
async def get_cached_data():
    """
    Fetch cached FUTSTK data (no network call).
    Used for instant page load and filtering.
    """
    try:
        data = market_data.get_cached_data()
        return {
            "status": "success",
            "count": len(data),
            "timestamp": market_data.get_cache_timestamp(),
            "data": data
        }
    except Exception as e:
        logger.error(f"Get data error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/export")
async def export_to_excel():
    """
    Export current cached data to Excel (.xlsx).
    Returns file for browser download.
    """
    try:
        logger.info("Excel export triggered")
        
        data = market_data.get_cached_data()
        if not data:
            raise HTTPException(status_code=400, detail="No data to export. Please refresh first.")
        
        # Generate Excel file
        excel_buffer = market_data.export_to_excel(data)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"FO_Scanner_{timestamp}.xlsx"
        
        return FileResponse(
            iter([excel_buffer.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=filename
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@app.get("/api/auth-status")
async def auth_status():
    """
    Check current authentication status.
    """
    return {
        "authenticated": fyers_auth.is_authenticated(),
        "auth_url": fyers_auth.get_auth_url()
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "authenticated": fyers_auth.is_authenticated()
    }


# ==================== ERROR HANDLERS ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handle HTTP exceptions.
    """
    logger.error(f"HTTP Exception: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle unexpected exceptions.
    """
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if os.getenv("DEBUG") == "True" else "Unknown error"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=os.getenv("DEBUG") == "True"
    )
