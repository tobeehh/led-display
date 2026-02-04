"""WiFi management API routes.

Provides endpoints for WiFi scanning, connection, and management.
"""

import asyncio
import logging

from fastapi import APIRouter, HTTPException

from ..schemas import (
    APIResponse,
    WiFiConnectRequest,
    WiFiNetworksResponse,
    WiFiStatusResponse,
    WiFiNetwork,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wifi", tags=["wifi"])


@router.get("/status")
async def wifi_status() -> WiFiStatusResponse:
    """Get WiFi connection status."""
    from ...network import get_network_manager

    manager = get_network_manager()
    info = await manager.get_connection_info()

    return WiFiStatusResponse(
        connected=info.get("connected", False),
        ssid=info.get("ssid"),
        ip_address=info.get("ip_address"),
        has_internet=info.get("has_internet", False),
        portal_active=info.get("portal_active", False),
    )


@router.get("/networks")
async def scan_networks() -> WiFiNetworksResponse:
    """Scan for available WiFi networks."""
    from ...network import get_network_manager

    manager = get_network_manager()

    try:
        networks = await manager.scan_networks()

        return WiFiNetworksResponse(
            networks=[
                WiFiNetwork(
                    ssid=n.ssid,
                    signal=n.signal,
                    security=n.security,
                    in_use=n.in_use,
                )
                for n in networks
            ]
        )

    except Exception as e:
        logger.error("WiFi scan failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


@router.post("/connect")
async def wifi_connect(request: WiFiConnectRequest) -> APIResponse:
    """Connect to a WiFi network."""
    from ...network import get_network_manager

    manager = get_network_manager()

    logger.info("Connecting to WiFi: %s", request.ssid)

    try:
        success = await manager.connect(request.ssid, request.password)

        if success:
            return APIResponse(
                success=True,
                message=f"Connected to {request.ssid}",
                data={"ssid": request.ssid},
            )
        else:
            raise HTTPException(status_code=400, detail="Connection failed")

    except Exception as e:
        logger.error("WiFi connection error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disconnect")
async def wifi_disconnect() -> APIResponse:
    """Disconnect from current WiFi network."""
    from ...network import get_network_manager

    manager = get_network_manager()

    await manager.disconnect()

    return APIResponse(success=True, message="Disconnected")


@router.post("/portal/start")
async def start_portal() -> APIResponse:
    """Start the captive portal for WiFi setup."""
    from ...network import get_network_manager

    manager = get_network_manager()

    success = await manager.start_captive_portal()

    if success:
        return APIResponse(success=True, message="Captive portal started")
    else:
        raise HTTPException(status_code=500, detail="Failed to start portal")


@router.post("/portal/stop")
async def stop_portal() -> APIResponse:
    """Stop the captive portal."""
    from ...network import get_network_manager

    manager = get_network_manager()

    await manager.stop_captive_portal()

    return APIResponse(success=True, message="Captive portal stopped")


@router.post("/forget")
async def forget_network() -> APIResponse:
    """Forget the saved WiFi network."""
    from ...network.wifi import WiFiManager

    wifi = WiFiManager()
    await wifi.forget_network()

    return APIResponse(success=True, message="Network forgotten")
