"""Core API routes.

Provides system status, health checks, and general API endpoints.
"""

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from ...core.config import get_config_manager
from ..schemas import (
    APIResponse,
    StatusResponse,
    BrightnessRequest,
    RotationRequest,
    LoginRequest,
    SetupPasswordRequest,
)
from ..auth import SessionManager, hash_password, verify_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["api"])

# Track start time for uptime
_start_time = time.time()


def get_session_manager(request: Request) -> SessionManager:
    """Get session manager from app state."""
    return request.app.state.session_manager


@router.get("/health")
async def health_check() -> APIResponse:
    """Health check endpoint (no auth required)."""
    return APIResponse(success=True, message="OK")


@router.get("/status")
async def get_status(request: Request) -> StatusResponse:
    """Get system status."""
    from ...apps import get_app_scheduler
    from ...display import get_display_manager
    from ...network import get_network_manager

    scheduler = get_app_scheduler()
    display = get_display_manager()
    network = get_network_manager()

    config = get_config_manager().get()

    # Get network info (async)
    import asyncio

    network_info = asyncio.run(network.get_connection_info())

    return StatusResponse(
        active_app=scheduler.active_app_name if scheduler else None,
        brightness=display.brightness,
        rotation_enabled=config.apps.rotation_enabled,
        rotation_interval=config.apps.rotation_interval,
        network=network_info,
        uptime=time.time() - _start_time,
    )


@router.post("/display/brightness")
async def set_brightness(request: BrightnessRequest) -> APIResponse:
    """Set display brightness."""
    from ...display import get_display_manager

    display = get_display_manager()
    display.set_brightness(request.brightness)

    # Persist to config
    config_manager = get_config_manager()
    config_manager.update_display(brightness=request.brightness)

    logger.info("Brightness set to %d", request.brightness)

    return APIResponse(
        success=True,
        message=f"Brightness set to {request.brightness}%",
        data={"brightness": request.brightness},
    )


@router.post("/display/test")
async def test_display() -> APIResponse:
    """Run display test pattern."""
    from ...display import get_display_manager

    display = get_display_manager()
    display.draw_test_pattern()

    return APIResponse(success=True, message="Test pattern displayed")


@router.post("/rotation")
async def set_rotation(request: RotationRequest) -> APIResponse:
    """Configure app rotation."""
    from ...apps import get_app_scheduler

    scheduler = get_app_scheduler()
    if scheduler:
        scheduler.set_rotation(request.enabled, request.interval)

    # Persist to config
    config_manager = get_config_manager()
    config_manager.update(
        apps={
            "rotation_enabled": request.enabled,
            "rotation_interval": request.interval,
        }
    )

    return APIResponse(
        success=True,
        message="Rotation settings updated",
        data={"enabled": request.enabled, "interval": request.interval},
    )


@router.post("/auth/login")
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    session_manager: SessionManager = Depends(get_session_manager),
) -> APIResponse:
    """Authenticate and create session."""
    config = get_config_manager().get()

    if not config.web.admin_password_hash or not config.web.admin_password_salt:
        raise HTTPException(status_code=400, detail="Password not configured")

    if not verify_password(
        body.password.get_secret_value(),
        config.web.admin_password_hash,
        config.web.admin_password_salt,
    ):
        logger.warning("Failed login attempt from %s", request.client.host if request.client else "unknown")
        raise HTTPException(status_code=401, detail="Invalid password")

    # Create session
    client_ip = request.client.host if request.client else "unknown"
    token = session_manager.create_session(client_ip)

    # Set cookie
    response.set_cookie(
        "session",
        token,
        httponly=True,
        samesite="strict",
        max_age=config.web.session_lifetime,
    )

    logger.info("User logged in from %s", client_ip)

    return APIResponse(success=True, message="Login successful")


@router.post("/auth/logout")
async def logout(
    request: Request,
    response: Response,
    session_manager: SessionManager = Depends(get_session_manager),
) -> APIResponse:
    """End session and logout."""
    token = request.cookies.get("session")
    if token:
        session_manager.invalidate_session(token)

    response.delete_cookie("session")

    return APIResponse(success=True, message="Logged out")


@router.post("/auth/setup")
async def setup_password(body: SetupPasswordRequest) -> APIResponse:
    """Initial password setup (only works if no password set)."""
    config_manager = get_config_manager()
    config = config_manager.get()

    if config.web.admin_password_hash:
        raise HTTPException(status_code=400, detail="Password already configured")

    # Hash and save password
    password_hash, salt = hash_password(body.password.get_secret_value())
    config_manager.set_admin_password(password_hash, salt)

    logger.info("Admin password configured")

    return APIResponse(success=True, message="Password configured successfully")


@router.post("/system/restart")
async def restart_service() -> APIResponse:
    """Restart the LED display service."""
    import asyncio
    import subprocess

    logger.warning("Service restart requested")

    # Restart asynchronously
    async def do_restart():
        await asyncio.sleep(1)
        subprocess.Popen(["sudo", "systemctl", "restart", "led-display"])

    asyncio.create_task(do_restart())

    return APIResponse(success=True, message="Restarting service...")


@router.post("/system/reboot")
async def reboot_system() -> APIResponse:
    """Reboot the Raspberry Pi."""
    import asyncio
    import subprocess

    logger.warning("System reboot requested")

    async def do_reboot():
        await asyncio.sleep(2)
        subprocess.Popen(["sudo", "reboot"])

    asyncio.create_task(do_reboot())

    return APIResponse(success=True, message="Rebooting system...")
