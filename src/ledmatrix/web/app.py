"""FastAPI application for the LED Display web interface.

Provides REST API and web UI for device configuration.
"""

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..core.config import get_config_manager
from .auth import (
    SessionManager,
    AuthMiddleware,
    CSRFMiddleware,
    RateLimiter,
    RateLimitMiddleware,
)
from .routes import api_router, apps_router, wifi_router

logger = logging.getLogger(__name__)

# Module directory for templates/static
MODULE_DIR = Path(__file__).parent


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI app
    """
    config = get_config_manager().get()

    app = FastAPI(
        title="LED Display",
        description="LED Matrix Display System API",
        version="1.0.0",
        docs_url="/api/docs" if not config.web.require_auth else None,
        redoc_url=None,
    )

    # Initialize components
    session_manager = SessionManager(lifetime=config.web.session_lifetime)
    rate_limiter = RateLimiter(requests_per_minute=60)

    # Store in app state
    app.state.session_manager = session_manager

    # Add middleware (order matters - last added runs first)
    app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)
    app.add_middleware(CSRFMiddleware)
    app.add_middleware(AuthMiddleware, session_manager=session_manager)

    # Mount static files
    static_dir = MODULE_DIR / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Setup templates
    templates_dir = MODULE_DIR / "templates"
    templates = None
    if templates_dir.exists():
        templates = Jinja2Templates(directory=str(templates_dir))

    # Include API routers
    app.include_router(api_router)
    app.include_router(apps_router)
    app.include_router(wifi_router)

    # Web UI routes
    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """Dashboard page."""
        if templates:
            return templates.TemplateResponse("index.html", {"request": request})
        return _minimal_dashboard()

    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        """Login page."""
        config = get_config_manager().get()

        # If no password set, redirect to setup
        if not config.web.admin_password_hash:
            return RedirectResponse(url="/setup", status_code=303)

        return _minimal_login_page()

    @app.get("/setup", response_class=HTMLResponse)
    async def setup_page(request: Request):
        """Initial setup page."""
        config = get_config_manager().get()

        # If password already set, redirect to login
        if config.web.admin_password_hash:
            return RedirectResponse(url="/login", status_code=303)

        return _minimal_setup_page()

    @app.get("/apps", response_class=HTMLResponse)
    async def apps_page(request: Request):
        """Apps management page."""
        if templates:
            return templates.TemplateResponse("apps.html", {"request": request})
        return RedirectResponse(url="/")

    @app.get("/wifi", response_class=HTMLResponse)
    async def wifi_page(request: Request):
        """WiFi configuration page."""
        if templates:
            return templates.TemplateResponse("wifi.html", {"request": request})
        return RedirectResponse(url="/")

    @app.get("/system", response_class=HTMLResponse)
    async def system_page(request: Request):
        """System settings page."""
        if templates:
            return templates.TemplateResponse("system.html", {"request": request})
        return RedirectResponse(url="/")

    return app


def _minimal_dashboard() -> HTMLResponse:
    """Minimal dashboard when templates not available."""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>LED Display</title>
        <style>
            * { box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                color: #fff;
                min-height: 100vh;
                margin: 0;
                padding: 20px;
            }
            .container {
                max-width: 600px;
                margin: 0 auto;
            }
            h1 { text-align: center; margin-bottom: 30px; }
            .card {
                background: rgba(255,255,255,0.1);
                border-radius: 15px;
                padding: 20px;
                margin-bottom: 20px;
            }
            .card h2 { margin-top: 0; font-size: 18px; opacity: 0.8; }
            .btn {
                display: inline-block;
                padding: 12px 24px;
                background: linear-gradient(135deg, #00d4ff 0%, #0099ff 100%);
                color: #fff;
                text-decoration: none;
                border-radius: 8px;
                border: none;
                cursor: pointer;
                margin: 5px;
            }
            .btn:hover { opacity: 0.9; }
            .status { font-size: 24px; font-weight: bold; }
            #brightness { width: 100%; margin: 10px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>LED Display</h1>

            <div class="card">
                <h2>Current App</h2>
                <p class="status" id="current-app">Loading...</p>
                <button class="btn" onclick="nextApp()">Next App</button>
            </div>

            <div class="card">
                <h2>Brightness</h2>
                <input type="range" id="brightness" min="0" max="100" value="50" onchange="setBrightness(this.value)">
                <p><span id="brightness-value">50</span>%</p>
            </div>

            <div class="card">
                <h2>Network</h2>
                <p id="network-status">Loading...</p>
            </div>

            <div class="card">
                <h2>Actions</h2>
                <button class="btn" onclick="location.href='/api/docs'">API Docs</button>
                <button class="btn" onclick="logout()">Logout</button>
            </div>
        </div>

        <script>
            async function loadStatus() {
                try {
                    const resp = await fetch('/api/status');
                    const data = await resp.json();
                    document.getElementById('current-app').textContent = data.active_app || 'None';
                    document.getElementById('brightness').value = data.brightness;
                    document.getElementById('brightness-value').textContent = data.brightness;
                    document.getElementById('network-status').textContent =
                        data.network.connected ? `Connected to ${data.network.ssid}` : 'Not connected';
                } catch (e) {
                    console.error('Failed to load status', e);
                }
            }

            async function nextApp() {
                await fetch('/api/apps/next', { method: 'POST' });
                loadStatus();
            }

            async function setBrightness(value) {
                document.getElementById('brightness-value').textContent = value;
                await fetch('/api/display/brightness', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ brightness: parseInt(value) })
                });
            }

            async function logout() {
                await fetch('/api/auth/logout', { method: 'POST' });
                location.href = '/login';
            }

            loadStatus();
            setInterval(loadStatus, 5000);
        </script>
    </body>
    </html>
    """)


def _minimal_login_page() -> HTMLResponse:
    """Minimal login page."""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Login - LED Display</title>
        <style>
            * { box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                color: #fff;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0;
            }
            .container {
                max-width: 400px;
                width: 100%;
                padding: 40px;
                background: rgba(255,255,255,0.1);
                border-radius: 20px;
            }
            h1 { text-align: center; margin-bottom: 30px; }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 8px; opacity: 0.8; }
            input {
                width: 100%;
                padding: 15px;
                border: none;
                border-radius: 10px;
                background: rgba(255,255,255,0.1);
                color: #fff;
                font-size: 16px;
            }
            button {
                width: 100%;
                padding: 15px;
                border: none;
                border-radius: 10px;
                background: linear-gradient(135deg, #00d4ff 0%, #0099ff 100%);
                color: #fff;
                font-size: 16px;
                font-weight: bold;
                cursor: pointer;
            }
            .error { color: #ff6b6b; text-align: center; margin-top: 15px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>LED Display</h1>
            <form id="login-form">
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" id="password" required>
                </div>
                <button type="submit">Login</button>
                <p class="error" id="error" style="display:none"></p>
            </form>
        </div>
        <script>
            document.getElementById('login-form').onsubmit = async (e) => {
                e.preventDefault();
                const password = document.getElementById('password').value;
                try {
                    const resp = await fetch('/api/auth/login', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ password })
                    });
                    if (resp.ok) {
                        location.href = '/';
                    } else {
                        document.getElementById('error').textContent = 'Invalid password';
                        document.getElementById('error').style.display = 'block';
                    }
                } catch (e) {
                    document.getElementById('error').textContent = 'Connection error';
                    document.getElementById('error').style.display = 'block';
                }
            };
        </script>
    </body>
    </html>
    """)


def _minimal_setup_page() -> HTMLResponse:
    """Minimal initial setup page."""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Setup - LED Display</title>
        <style>
            * { box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                color: #fff;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0;
            }
            .container {
                max-width: 400px;
                width: 100%;
                padding: 40px;
                background: rgba(255,255,255,0.1);
                border-radius: 20px;
            }
            h1 { text-align: center; margin-bottom: 10px; }
            p { text-align: center; opacity: 0.7; margin-bottom: 30px; }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 8px; opacity: 0.8; }
            input {
                width: 100%;
                padding: 15px;
                border: none;
                border-radius: 10px;
                background: rgba(255,255,255,0.1);
                color: #fff;
                font-size: 16px;
            }
            button {
                width: 100%;
                padding: 15px;
                border: none;
                border-radius: 10px;
                background: linear-gradient(135deg, #00d4ff 0%, #0099ff 100%);
                color: #fff;
                font-size: 16px;
                font-weight: bold;
                cursor: pointer;
            }
            .error { color: #ff6b6b; text-align: center; margin-top: 15px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Welcome!</h1>
            <p>Create an admin password to secure your device.</p>
            <form id="setup-form">
                <div class="form-group">
                    <label>Password (min 8 characters)</label>
                    <input type="password" id="password" minlength="8" required>
                </div>
                <div class="form-group">
                    <label>Confirm Password</label>
                    <input type="password" id="confirm" minlength="8" required>
                </div>
                <button type="submit">Set Password</button>
                <p class="error" id="error" style="display:none"></p>
            </form>
        </div>
        <script>
            document.getElementById('setup-form').onsubmit = async (e) => {
                e.preventDefault();
                const password = document.getElementById('password').value;
                const confirm = document.getElementById('confirm').value;

                if (password !== confirm) {
                    document.getElementById('error').textContent = 'Passwords do not match';
                    document.getElementById('error').style.display = 'block';
                    return;
                }

                try {
                    const resp = await fetch('/api/auth/setup', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ password, confirm_password: confirm })
                    });
                    if (resp.ok) {
                        location.href = '/login';
                    } else {
                        const data = await resp.json();
                        document.getElementById('error').textContent = data.detail || 'Setup failed';
                        document.getElementById('error').style.display = 'block';
                    }
                } catch (e) {
                    document.getElementById('error').textContent = 'Connection error';
                    document.getElementById('error').style.display = 'block';
                }
            };
        </script>
    </body>
    </html>
    """)


# Global app instance
_app: FastAPI | None = None


def get_app() -> FastAPI:
    """Get or create the FastAPI application.

    Returns:
        FastAPI application instance
    """
    global _app
    if _app is None:
        _app = create_app()
    return _app
