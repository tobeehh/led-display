"""App scheduler for managing app lifecycle and rendering.

Provides:
- App registration and discovery
- Thread-safe app switching
- Automatic render and update loops
- App rotation support
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from PIL import Image

from ..core.threading import StoppableThread, ThreadSafeDict, LockedValue
from .base import BaseApp, AppState, RenderResult

logger = logging.getLogger(__name__)


@dataclass
class ScheduledApp:
    """Wrapper for scheduled app with timing info."""

    app: BaseApp
    last_update: datetime | None = None
    last_render: datetime | None = None
    update_errors: int = 0
    render_errors: int = 0


class AppScheduler:
    """Manages app scheduling, updates, and rendering.

    Features:
    - Thread-safe app registration and switching
    - Separate render and update threads
    - Automatic app rotation
    - Error tracking and recovery

    Usage:
        scheduler = AppScheduler(on_frame_ready=display.render_image)
        scheduler.register_app(ClockApp())
        scheduler.start()
        scheduler.set_active_app("clock")
    """

    MAX_UPDATE_ERRORS = 3
    MAX_RENDER_ERRORS = 5

    def __init__(
        self,
        on_frame_ready: Callable[[Image.Image], None],
        default_width: int = 64,
        default_height: int = 64,
    ) -> None:
        """Initialize the app scheduler.

        Args:
            on_frame_ready: Callback for rendered frames
            default_width: Display width
            default_height: Display height
        """
        self._on_frame_ready = on_frame_ready
        self._width = default_width
        self._height = default_height

        # App storage
        self._apps: ThreadSafeDict[str, ScheduledApp] = ThreadSafeDict()
        self._active_app_name: LockedValue[str | None] = LockedValue(None)

        # Threads
        self._render_thread: StoppableThread | None = None
        self._update_thread: StoppableThread | None = None
        self._running = False

        # Rotation settings
        self._rotation_enabled = False
        self._rotation_interval = 30.0
        self._last_rotation = time.time()

        # Thread synchronization
        self._lock = threading.RLock()

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running

    @property
    def active_app_name(self) -> str | None:
        """Get the name of the currently active app."""
        return self._active_app_name.get()

    def register_app(self, app: BaseApp) -> None:
        """Register an app with the scheduler.

        Args:
            app: App instance to register
        """
        name = app.metadata.name
        self._apps[name] = ScheduledApp(app=app)
        logger.info("Registered app: %s (%s)", name, app.metadata.display_name)

    def unregister_app(self, name: str) -> None:
        """Unregister an app from the scheduler.

        Args:
            name: App name to unregister
        """
        if name in self._apps:
            scheduled = self._apps.pop(name)
            if scheduled.app.state == AppState.ACTIVE:
                scheduled.app.deactivate()
            logger.info("Unregistered app: %s", name)

    def get_app(self, name: str) -> BaseApp | None:
        """Get an app by name.

        Args:
            name: App name

        Returns:
            App instance or None if not found
        """
        scheduled = self._apps.get(name)
        return scheduled.app if scheduled else None

    def get_all_apps(self) -> dict[str, BaseApp]:
        """Get all registered apps.

        Returns:
            Dict mapping app names to app instances
        """
        with self._lock:
            return {name: s.app for name, s in self._apps.items()}

    def get_enabled_apps(self) -> list[str]:
        """Get names of enabled apps in registration order.

        Returns:
            List of enabled app names
        """
        with self._lock:
            return [name for name, s in self._apps.items() if s.app.enabled]

    def set_active_app(self, name: str) -> bool:
        """Set the currently active app.

        Deactivates the current app and activates the new one.

        Args:
            name: Name of app to activate

        Returns:
            True if successful, False if app not found or activation failed
        """
        with self._lock:
            if name not in self._apps:
                logger.warning("App not found: %s", name)
                return False

            current = self._active_app_name.get()

            # Deactivate current app
            if current and current in self._apps:
                try:
                    self._apps[current].app.deactivate()
                except Exception as e:
                    logger.error("Error deactivating %s: %s", current, e)

            # Activate new app
            try:
                scheduled = self._apps[name]
                scheduled.app.activate()
                scheduled.render_errors = 0
                scheduled.update_errors = 0

                self._active_app_name.set(name)
                self._last_rotation = time.time()

                logger.info("Activated app: %s", name)
                return True

            except Exception as e:
                logger.error("Error activating %s: %s", name, e)
                self._active_app_name.set(None)
                return False

    def next_app(self) -> str | None:
        """Switch to the next enabled app.

        Returns:
            Name of the newly active app, or None if no apps available
        """
        with self._lock:
            enabled = self.get_enabled_apps()
            if not enabled:
                return None

            current = self._active_app_name.get()
            if current in enabled:
                idx = (enabled.index(current) + 1) % len(enabled)
            else:
                idx = 0

            next_name = enabled[idx]
            if self.set_active_app(next_name):
                return next_name
            return None

    def previous_app(self) -> str | None:
        """Switch to the previous enabled app.

        Returns:
            Name of the newly active app, or None if no apps available
        """
        with self._lock:
            enabled = self.get_enabled_apps()
            if not enabled:
                return None

            current = self._active_app_name.get()
            if current in enabled:
                idx = (enabled.index(current) - 1) % len(enabled)
            else:
                idx = 0

            prev_name = enabled[idx]
            if self.set_active_app(prev_name):
                return prev_name
            return None

    def set_rotation(self, enabled: bool, interval: float = 30.0) -> None:
        """Configure automatic app rotation.

        Args:
            enabled: Whether to enable rotation
            interval: Seconds between app switches
        """
        self._rotation_enabled = enabled
        self._rotation_interval = max(5.0, interval)
        self._last_rotation = time.time()
        logger.info("Rotation %s (interval: %.1fs)", "enabled" if enabled else "disabled", interval)

    def start(self) -> None:
        """Start the scheduler threads."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        logger.info("Starting app scheduler")
        self._running = True

        # Start render thread
        self._render_thread = StoppableThread(
            target=self._render_loop,
            name="AppRenderThread",
        )
        self._render_thread.start()

        # Start update thread
        self._update_thread = StoppableThread(
            target=self._update_loop,
            name="AppUpdateThread",
        )
        self._update_thread.start()

        # Set initial app if none active
        if self._active_app_name.get() is None:
            enabled = self.get_enabled_apps()
            if enabled:
                self.set_active_app(enabled[0])

    def stop(self) -> None:
        """Stop the scheduler threads."""
        if not self._running:
            return

        logger.info("Stopping app scheduler")
        self._running = False

        # Stop threads
        if self._render_thread:
            self._render_thread.stop(timeout=2.0)
            self._render_thread = None

        if self._update_thread:
            self._update_thread.stop(timeout=2.0)
            self._update_thread = None

        # Deactivate current app
        current = self._active_app_name.get()
        if current and current in self._apps:
            try:
                self._apps[current].app.deactivate()
            except Exception:
                pass

        self._active_app_name.set(None)

    def _render_loop(self, thread: StoppableThread) -> None:
        """Main render loop.

        Renders the active app at the configured frame rate.
        """
        logger.debug("Render loop started")

        while not thread.should_stop():
            try:
                sleep_time = self._do_render()
                thread.wait(sleep_time)
            except Exception as e:
                logger.exception("Render loop error: %s", e)
                thread.wait(1.0)

        logger.debug("Render loop stopped")

    def _do_render(self) -> float:
        """Perform one render cycle.

        Returns:
            Sleep time before next render
        """
        # Handle rotation
        if self._rotation_enabled:
            now = time.time()
            if now - self._last_rotation >= self._rotation_interval:
                self.next_app()

        current_name = self._active_app_name.get()
        if not current_name or current_name not in self._apps:
            return 1.0

        scheduled = self._apps.get(current_name)
        if not scheduled:
            return 1.0

        try:
            with self._lock:
                result: RenderResult = scheduled.app.render(self._width, self._height)
                scheduled.last_render = datetime.now()
                scheduled.render_errors = 0

            # Send frame to display
            self._on_frame_ready(result.image)

            return result.next_render_in

        except Exception as e:
            scheduled.render_errors += 1
            logger.error("Render error for %s (%d): %s", current_name, scheduled.render_errors, e)

            if scheduled.render_errors >= self.MAX_RENDER_ERRORS:
                logger.error("Too many render errors, switching app")
                self.next_app()

            return 1.0

    def _update_loop(self, thread: StoppableThread) -> None:
        """Data update loop for all apps.

        Calls update_data() on apps that need it based on their intervals.
        """
        logger.debug("Update loop started")

        while not thread.should_stop():
            try:
                self._do_updates()
            except Exception as e:
                logger.exception("Update loop error: %s", e)

            thread.wait(1.0)

        logger.debug("Update loop stopped")

    def _do_updates(self) -> None:
        """Perform data updates for apps that need it."""
        now = datetime.now()

        with self._lock:
            for name, scheduled in self._apps.items():
                interval = scheduled.app.get_update_interval()
                if interval <= 0:
                    continue

                # Check if update is needed
                needs_update = (
                    scheduled.last_update is None
                    or (now - scheduled.last_update).total_seconds() >= interval
                )

                if needs_update:
                    try:
                        scheduled.app.update_data()
                        scheduled.last_update = now
                        scheduled.update_errors = 0
                    except Exception as e:
                        scheduled.update_errors += 1
                        logger.warning(
                            "Update error for %s (%d): %s",
                            name,
                            scheduled.update_errors,
                            e,
                        )

                        if scheduled.update_errors >= self.MAX_UPDATE_ERRORS:
                            logger.error("Too many update errors for %s", name)


# =============================================================================
# Singleton Instance
# =============================================================================

_app_scheduler: AppScheduler | None = None
_scheduler_lock = threading.Lock()


def get_app_scheduler() -> AppScheduler | None:
    """Get the global app scheduler instance.

    Returns:
        AppScheduler singleton instance or None if not initialized
    """
    global _app_scheduler
    with _scheduler_lock:
        return _app_scheduler


def init_app_scheduler(
    on_frame_ready: Callable[[Image.Image], None],
    width: int = 64,
    height: int = 64,
) -> AppScheduler:
    """Initialize and return the global app scheduler.

    Args:
        on_frame_ready: Callback for rendered frames
        width: Display width
        height: Display height

    Returns:
        AppScheduler singleton instance
    """
    global _app_scheduler
    with _scheduler_lock:
        if _app_scheduler is None:
            _app_scheduler = AppScheduler(on_frame_ready, width, height)
        return _app_scheduler


def reset_app_scheduler() -> None:
    """Reset the app scheduler singleton (for testing)."""
    global _app_scheduler
    with _scheduler_lock:
        if _app_scheduler is not None:
            _app_scheduler.stop()
            _app_scheduler = None
