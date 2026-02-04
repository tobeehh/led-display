"""Flask web application for LED display configuration."""

import threading
from typing import Any

from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_cors import CORS

from apps.manager import get_app_manager
from config import get_config
from display.manager import get_display_manager
from network.manager import get_network_manager


def create_app() -> Flask:
    """Create and configure the Flask application.

    Returns:
        The configured Flask app.
    """
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    CORS(app)

    config = get_config()

    # ============ Dashboard Routes ============

    @app.route("/")
    def index():
        """Dashboard home page."""
        app_manager = get_app_manager()
        network_manager = get_network_manager()
        display_manager = get_display_manager()

        apps = {}
        active_app = ""
        if app_manager:
            apps = {name: app for name, app in app_manager.get_all_apps().items()}
            active_app = app_manager.get_active_app_name()

        network_info = {}
        if network_manager:
            network_info = network_manager.get_connection_info()

        return render_template(
            "index.html",
            apps=apps,
            active_app=active_app,
            network_info=network_info,
            brightness=display_manager.get_brightness() if display_manager else 50,
        )

    @app.route("/app/<app_name>/activate", methods=["POST"])
    def activate_app(app_name: str):
        """Activate a specific app."""
        app_manager = get_app_manager()
        if app_manager:
            success = app_manager.set_active_app(app_name)
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": success})
        return redirect(url_for("index"))

    @app.route("/app/next", methods=["POST"])
    def next_app():
        """Switch to next app."""
        app_manager = get_app_manager()
        if app_manager:
            new_app = app_manager.next_app()
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"success": True, "active_app": new_app})
        return redirect(url_for("index"))

    # ============ App Configuration Routes ============

    @app.route("/apps")
    def apps_list():
        """List all apps and their configurations."""
        app_manager = get_app_manager()
        apps = {}
        if app_manager:
            apps = {name: app for name, app in app_manager.get_all_apps().items()}

        return render_template("apps/index.html", apps=apps)

    @app.route("/apps/<app_name>")
    def app_config(app_name: str):
        """Configure a specific app."""
        app_manager = get_app_manager()
        if not app_manager:
            return redirect(url_for("apps_list"))

        app = app_manager.get_app(app_name)
        if not app:
            return redirect(url_for("apps_list"))

        return render_template(
            "apps/config.html",
            app=app,
            app_config=app.config,
            schema=app.config_schema,
        )

    @app.route("/apps/<app_name>/save", methods=["POST"])
    def save_app_config(app_name: str):
        """Save app configuration."""
        app_manager = get_app_manager()
        if not app_manager:
            return jsonify({"success": False, "error": "App manager not available"})

        app = app_manager.get_app(app_name)
        if not app:
            return jsonify({"success": False, "error": "App not found"})

        # Parse form data based on config schema
        new_config = {}
        for field_name, field_info in app.config_schema.items():
            field_type = field_info.get("type", "string")

            if field_type == "bool":
                new_config[field_name] = field_name in request.form
            elif field_type == "int":
                try:
                    new_config[field_name] = int(request.form.get(field_name, 0))
                except ValueError:
                    new_config[field_name] = field_info.get("default", 0)
            else:
                new_config[field_name] = request.form.get(
                    field_name, field_info.get("default", "")
                )

        # Preserve enabled status
        new_config["enabled"] = "enabled" in request.form

        # Update app config
        app.config = new_config
        config.set_app_config(app_name, new_config)

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": True})
        return redirect(url_for("app_config", app_name=app_name))

    # ============ WiFi Configuration Routes ============

    @app.route("/wifi")
    def wifi_config():
        """WiFi configuration page."""
        network_manager = get_network_manager()

        networks = []
        connection_info = {}
        if network_manager:
            networks = network_manager.scan_networks()
            connection_info = network_manager.get_connection_info()

        return render_template(
            "wifi.html",
            networks=networks,
            connection_info=connection_info,
        )

    @app.route("/wifi/scan")
    def wifi_scan():
        """Scan for WiFi networks."""
        network_manager = get_network_manager()
        networks = []
        if network_manager:
            networks = network_manager.scan_networks()
        return jsonify({"networks": networks})

    @app.route("/wifi/connect", methods=["POST"])
    def wifi_connect():
        """Connect to a WiFi network."""
        network_manager = get_network_manager()
        if not network_manager:
            return jsonify({"success": False, "error": "Network manager not available"})

        ssid = request.form.get("ssid", "")
        password = request.form.get("password", "")

        if not ssid:
            return jsonify({"success": False, "error": "SSID required"})

        success = network_manager.connect(ssid, password)

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({
                "success": success,
                "error": "" if success else "Connection failed",
            })

        return redirect(url_for("wifi_config"))

    @app.route("/wifi/disconnect", methods=["POST"])
    def wifi_disconnect():
        """Disconnect from current WiFi network."""
        network_manager = get_network_manager()
        if network_manager:
            network_manager.disconnect()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": True})
        return redirect(url_for("wifi_config"))

    @app.route("/wifi/forget", methods=["POST"])
    def wifi_forget():
        """Forget saved WiFi configuration."""
        network_manager = get_network_manager()
        if network_manager:
            network_manager.forget_network()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": True})
        return redirect(url_for("wifi_config"))

    @app.route("/wifi/captive-portal/start", methods=["POST"])
    def start_captive_portal():
        """Start the captive portal."""
        network_manager = get_network_manager()
        if network_manager:
            success = network_manager.start_captive_portal()
            return jsonify({"success": success})
        return jsonify({"success": False})

    # ============ System Routes ============

    @app.route("/system")
    def system_settings():
        """System settings page."""
        display_manager = get_display_manager()
        display_config = config.get("display")
        apps_config = config.get("apps")

        return render_template(
            "system.html",
            brightness=display_manager.get_brightness() if display_manager else 50,
            display_config=display_config,
            rotation_enabled=apps_config.get("rotation_enabled", False),
            rotation_interval=apps_config.get("rotation_interval", 30),
        )

    @app.route("/system/brightness", methods=["POST"])
    def set_brightness():
        """Set display brightness."""
        display_manager = get_display_manager()
        if display_manager:
            try:
                brightness = int(request.form.get("brightness", 50))
                display_manager.set_brightness(brightness)
                return jsonify({"success": True, "brightness": brightness})
            except ValueError:
                return jsonify({"success": False, "error": "Invalid brightness value"})
        return jsonify({"success": False, "error": "Display not available"})

    @app.route("/system/rotation", methods=["POST"])
    def set_rotation():
        """Configure app rotation."""
        app_manager = get_app_manager()
        if app_manager:
            enabled = "enabled" in request.form
            try:
                interval = int(request.form.get("interval", 30))
            except ValueError:
                interval = 30

            app_manager.set_rotation(enabled, interval)
            return jsonify({"success": True})
        return jsonify({"success": False})

    @app.route("/system/restart", methods=["POST"])
    def restart_system():
        """Restart the system."""
        import subprocess

        subprocess.Popen(["sudo", "reboot"])
        return jsonify({"success": True, "message": "Rebooting..."})

    @app.route("/system/test-display", methods=["POST"])
    def test_display():
        """Run display test pattern."""
        display_manager = get_display_manager()
        if display_manager:
            display_manager.draw_test_pattern()
            return jsonify({"success": True})
        return jsonify({"success": False})

    # ============ API Routes ============

    @app.route("/api/status")
    def api_status():
        """Get system status."""
        app_manager = get_app_manager()
        network_manager = get_network_manager()
        display_manager = get_display_manager()

        return jsonify({
            "active_app": app_manager.get_active_app_name() if app_manager else "",
            "network": network_manager.get_connection_info() if network_manager else {},
            "brightness": display_manager.get_brightness() if display_manager else 50,
        })

    @app.route("/api/apps")
    def api_apps():
        """Get list of apps."""
        app_manager = get_app_manager()
        if not app_manager:
            return jsonify({"apps": []})

        apps = []
        for name, app in app_manager.get_all_apps().items():
            apps.append({
                "name": name,
                "display_name": app.display_name,
                "enabled": app.enabled,
                "requires_credentials": app.requires_credentials,
            })

        return jsonify({
            "apps": apps,
            "active_app": app_manager.get_active_app_name(),
        })

    return app


# Global Flask app instance
_web_app: Flask | None = None
_web_thread: threading.Thread | None = None


def get_web_app() -> Flask | None:
    """Get the global Flask app instance."""
    return _web_app


def start_web_server(host: str = "0.0.0.0", port: int = 5000) -> None:
    """Start the web server in a background thread.

    Args:
        host: Host to bind to.
        port: Port to listen on.
    """
    global _web_app, _web_thread

    _web_app = create_app()

    def run_server():
        _web_app.run(host=host, port=port, threaded=True, use_reloader=False)

    _web_thread = threading.Thread(target=run_server, daemon=True)
    _web_thread.start()

    print(f"[Web] Server started on http://{host}:{port}")
