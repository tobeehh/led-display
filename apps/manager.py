"""App manager for scheduling and controlling LED display applications."""

import threading
import time
from typing import Any

from PIL import Image

from config import get_config
from display import DisplayManager, Renderer


class AppManager:
    """Manages LED display applications."""

    def __init__(self, display_manager: DisplayManager):
        """Initialize the app manager.

        Args:
            display_manager: The display manager instance.
        """
        self._display = display_manager
        self._config = get_config()
        self._renderer = Renderer(display_manager.width, display_manager.height)

        self._apps: dict[str, Any] = {}  # Registered apps
        self._active_app: Any = None
        self._active_app_name: str = ""

        self._running = False
        self._render_thread: threading.Thread | None = None
        self._update_thread: threading.Thread | None = None
        self._lock = threading.Lock()

        self._rotation_enabled = False
        self._rotation_interval = 30
        self._last_rotation_time = time.time()

    def register_app(self, app: Any) -> None:
        """Register an app with the manager.

        Args:
            app: The app instance to register.
        """
        self._apps[app.name] = app

    def get_app(self, name: str) -> Any | None:
        """Get an app by name.

        Args:
            name: The app name.

        Returns:
            The app instance or None if not found.
        """
        return self._apps.get(name)

    def get_all_apps(self) -> dict[str, Any]:
        """Get all registered apps."""
        return self._apps.copy()

    def get_enabled_apps(self) -> list[str]:
        """Get list of enabled app names in order."""
        enabled = []
        for name, app in self._apps.items():
            if app.enabled:
                enabled.append(name)
        return enabled

    def set_active_app(self, name: str) -> bool:
        """Set the active app by name.

        Args:
            name: The app name.

        Returns:
            True if successful, False if app not found.
        """
        if name not in self._apps:
            return False

        with self._lock:
            # Cleanup current app
            if self._active_app:
                self._active_app.cleanup()

            # Switch to new app
            self._active_app = self._apps[name]
            self._active_app_name = name
            self._config.set_active_app(name)

            # Setup new app
            if not self._active_app.setup():
                print(f"[AppManager] Warning: App '{name}' setup failed")

            self._last_rotation_time = time.time()

        return True

    def get_active_app_name(self) -> str:
        """Get the name of the currently active app."""
        return self._active_app_name

    def next_app(self) -> str:
        """Switch to the next enabled app.

        Returns:
            The name of the new active app.
        """
        enabled = self.get_enabled_apps()
        if not enabled:
            return ""

        if self._active_app_name in enabled:
            current_index = enabled.index(self._active_app_name)
            next_index = (current_index + 1) % len(enabled)
        else:
            next_index = 0

        next_name = enabled[next_index]
        self.set_active_app(next_name)
        return next_name

    def previous_app(self) -> str:
        """Switch to the previous enabled app.

        Returns:
            The name of the new active app.
        """
        enabled = self.get_enabled_apps()
        if not enabled:
            return ""

        if self._active_app_name in enabled:
            current_index = enabled.index(self._active_app_name)
            prev_index = (current_index - 1) % len(enabled)
        else:
            prev_index = 0

        prev_name = enabled[prev_index]
        self.set_active_app(prev_name)
        return prev_name

    def set_rotation(self, enabled: bool, interval: int = 30) -> None:
        """Enable or disable automatic app rotation.

        Args:
            enabled: Whether to enable rotation.
            interval: Rotation interval in seconds.
        """
        self._rotation_enabled = enabled
        self._rotation_interval = interval
        self._config.set("apps", "rotation_enabled", enabled)
        self._config.set("apps", "rotation_interval", interval)

    def start(self) -> None:
        """Start the app manager."""
        if self._running:
            return

        self._running = True

        # Load rotation settings
        apps_config = self._config.get("apps")
        self._rotation_enabled = apps_config.get("rotation_enabled", False)
        self._rotation_interval = apps_config.get("rotation_interval", 30)

        # Set initial active app
        active_name = self._config.get_active_app()
        if active_name in self._apps:
            self.set_active_app(active_name)
        elif self._apps:
            # Default to first enabled app or first app
            enabled = self.get_enabled_apps()
            if enabled:
                self.set_active_app(enabled[0])
            else:
                self.set_active_app(list(self._apps.keys())[0])

        # Start render thread
        self._render_thread = threading.Thread(target=self._render_loop, daemon=True)
        self._render_thread.start()

        # Start update thread
        self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self._update_thread.start()

    def stop(self) -> None:
        """Stop the app manager."""
        self._running = False

        if self._render_thread:
            self._render_thread.join(timeout=2.0)
            self._render_thread = None

        if self._update_thread:
            self._update_thread.join(timeout=2.0)
            self._update_thread = None

        if self._active_app:
            self._active_app.cleanup()
            self._active_app = None

    def _render_loop(self) -> None:
        """Main render loop."""
        while self._running:
            try:
                with self._lock:
                    if self._active_app:
                        # Check for rotation
                        if self._rotation_enabled:
                            if time.time() - self._last_rotation_time > self._rotation_interval:
                                self.next_app()

                        # Render the app
                        image = self._active_app.render(
                            self._display.width, self._display.height
                        )

                        # Draw to display
                        canvas = self._display.get_canvas()
                        if canvas:
                            self._renderer.image_to_canvas(image, canvas)
                            self._display.swap_canvas()

                        # Get render interval
                        interval = self._active_app.get_render_interval()
                    else:
                        interval = 1.0

                time.sleep(interval)

            except Exception as e:
                print(f"[AppManager] Render error: {e}")
                time.sleep(1.0)

    def _update_loop(self) -> None:
        """Data update loop for apps."""
        last_updates: dict[str, float] = {}

        while self._running:
            try:
                current_time = time.time()

                for name, app in self._apps.items():
                    update_interval = app.get_update_interval()
                    if update_interval > 0:
                        last_update = last_updates.get(name, 0)
                        if current_time - last_update >= update_interval:
                            try:
                                app.update()
                                last_updates[name] = current_time
                            except Exception as e:
                                print(f"[AppManager] Update error for {name}: {e}")

                time.sleep(1.0)

            except Exception as e:
                print(f"[AppManager] Update loop error: {e}")
                time.sleep(1.0)

    def render_message(self, message: str, color: tuple[int, int, int] = (255, 255, 255)) -> None:
        """Render a temporary message on the display.

        Args:
            message: The message to display.
            color: RGB color tuple.
        """
        image = self._renderer.render_centered_text(
            message, color=color, font_size=12
        )

        canvas = self._display.get_canvas()
        if canvas:
            self._renderer.image_to_canvas(image, canvas)
            self._display.swap_canvas()


# Global app manager instance
_app_manager: AppManager | None = None


def get_app_manager() -> AppManager | None:
    """Get the global app manager instance."""
    return _app_manager


def set_app_manager(manager: AppManager) -> None:
    """Set the global app manager instance."""
    global _app_manager
    _app_manager = manager
