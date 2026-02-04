"""App management API routes.

Provides endpoints for listing, configuring, and switching apps.
"""

import logging

from fastapi import APIRouter, HTTPException

from ...core.config import get_config_manager
from ..schemas import (
    APIResponse,
    AppInfo,
    AppsListResponse,
    AppConfigRequest,
    ActivateAppRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/apps", tags=["apps"])


@router.get("")
async def list_apps() -> AppsListResponse:
    """List all registered apps with their configuration."""
    from ...apps import get_app_scheduler

    scheduler = get_app_scheduler()
    if not scheduler:
        return AppsListResponse(apps=[])

    apps_list = []
    active_name = scheduler.active_app_name

    for name, app in scheduler.get_all_apps().items():
        metadata = app.metadata

        # Build config schema for UI
        schema = {}
        for field_name, field_schema in app.config_schema.items():
            schema[field_name] = {
                "type": field_schema.type,
                "label": field_schema.label,
                "description": field_schema.description,
                "default": field_schema.default,
                "required": field_schema.required,
                "min_value": field_schema.min_value,
                "max_value": field_schema.max_value,
                "options": field_schema.options,
            }

        apps_list.append(
            AppInfo(
                name=name,
                display_name=metadata.display_name,
                description=metadata.description,
                enabled=app.enabled,
                active=(name == active_name),
                requires_network=metadata.requires_network,
                requires_credentials=metadata.requires_credentials,
                config_schema=schema,
                current_config=app.config,
            )
        )

    return AppsListResponse(apps=apps_list)


@router.get("/{app_name}")
async def get_app(app_name: str) -> AppInfo:
    """Get details for a specific app."""
    from ...apps import get_app_scheduler

    scheduler = get_app_scheduler()
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not running")

    app = scheduler.get_app(app_name)
    if not app:
        raise HTTPException(status_code=404, detail=f"App not found: {app_name}")

    metadata = app.metadata
    active_name = scheduler.active_app_name

    schema = {}
    for field_name, field_schema in app.config_schema.items():
        schema[field_name] = {
            "type": field_schema.type,
            "label": field_schema.label,
            "description": field_schema.description,
            "default": field_schema.default,
            "required": field_schema.required,
        }

    return AppInfo(
        name=app_name,
        display_name=metadata.display_name,
        description=metadata.description,
        enabled=app.enabled,
        active=(app_name == active_name),
        requires_network=metadata.requires_network,
        requires_credentials=metadata.requires_credentials,
        config_schema=schema,
        current_config=app.config,
    )


@router.post("/{app_name}/activate")
async def activate_app(app_name: str) -> APIResponse:
    """Activate a specific app."""
    from ...apps import get_app_scheduler

    scheduler = get_app_scheduler()
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not running")

    if scheduler.set_active_app(app_name):
        # Persist to config
        config_manager = get_config_manager()
        config_manager.set_active_app(app_name)

        logger.info("Activated app: %s", app_name)
        return APIResponse(
            success=True,
            message=f"Activated {app_name}",
            data={"active_app": app_name},
        )
    else:
        raise HTTPException(status_code=404, detail=f"App not found or failed to activate: {app_name}")


@router.put("/{app_name}/config")
async def update_app_config(app_name: str, request: AppConfigRequest) -> APIResponse:
    """Update app configuration."""
    from ...apps import get_app_scheduler

    scheduler = get_app_scheduler()
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not running")

    app = scheduler.get_app(app_name)
    if not app:
        raise HTTPException(status_code=404, detail=f"App not found: {app_name}")

    try:
        # Build new config
        new_config = {"enabled": request.enabled, **request.settings}
        app.configure(new_config)

        # Persist to config
        config_manager = get_config_manager()
        config_manager.update_app(app_name, **new_config)

        logger.info("Updated config for %s", app_name)

        return APIResponse(
            success=True,
            message="Configuration updated",
            data={"config": app.config},
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/next")
async def next_app() -> APIResponse:
    """Switch to the next app."""
    from ...apps import get_app_scheduler

    scheduler = get_app_scheduler()
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not running")

    next_name = scheduler.next_app()
    if next_name:
        # Persist to config
        config_manager = get_config_manager()
        config_manager.set_active_app(next_name)

        return APIResponse(
            success=True,
            message=f"Switched to {next_name}",
            data={"active_app": next_name},
        )
    else:
        raise HTTPException(status_code=404, detail="No apps available")


@router.post("/previous")
async def previous_app() -> APIResponse:
    """Switch to the previous app."""
    from ...apps import get_app_scheduler

    scheduler = get_app_scheduler()
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not running")

    prev_name = scheduler.previous_app()
    if prev_name:
        # Persist to config
        config_manager = get_config_manager()
        config_manager.set_active_app(prev_name)

        return APIResponse(
            success=True,
            message=f"Switched to {prev_name}",
            data={"active_app": prev_name},
        )
    else:
        raise HTTPException(status_code=404, detail="No apps available")
