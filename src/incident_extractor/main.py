"""
Incident Extractor - Application Launcher.

This module provides the main entry point and development server configuration
for the Incident Extractor API. It handles both development and production
deployment scenarios with proper configuration management.
"""

import signal
import sys
from typing import Any, Callable, Dict, List, Optional

import uvicorn
from uvicorn.config import Config
from uvicorn.server import Server

from .api.app import create_app
from .config import get_logger, get_settings


class ApplicationManager:
    """
    Manages the application lifecycle with graceful shutdown handling.

    This class provides centralized management for the application instance,
    server configuration, and resource cleanup with proper error handling.
    """

    def __init__(self) -> None:
        """Initialize the application manager."""
        self.app = None
        self.server: Optional[Server] = None
        self.logger = get_logger("app.manager")
        self._shutdown_handlers: List[Callable[[], None]] = []

    def create_application(self):
        """
        Create the FastAPI application instance.

        Returns:
            FastAPI: Configured application instance
        """
        if self.app is None:
            self.logger.info("Creating new application instance")
            self.app = create_app()
            self.logger.info("Application instance created successfully")

        return self.app

    def register_shutdown_handler(self, handler: Callable[[], None]) -> None:
        """
        Register a cleanup handler for graceful shutdown.

        Args:
            handler: Callable to execute during shutdown
        """
        self._shutdown_handlers.append(handler)
        self.logger.debug("Shutdown handler registered", handler=handler.__name__)

    def shutdown(self) -> None:
        """
        Perform graceful shutdown with resource cleanup.

        Executes all registered shutdown handlers and cleans up resources.
        """
        self.logger.info("Initiating graceful shutdown")

        try:
            # Execute shutdown handlers
            for handler in self._shutdown_handlers:
                try:
                    handler()
                    self.logger.debug("Shutdown handler executed", handler=handler.__name__)
                except Exception as e:
                    self.logger.error("Shutdown handler failed", handler=handler.__name__, error=str(e), exc_info=True)

            # Stop server if running
            if self.server:
                self.logger.info("Stopping server")
                self.server.should_exit = True

            self.logger.info("Graceful shutdown completed")

        except Exception as e:
            self.logger.error("Shutdown process failed", error=str(e), exc_info=True)
            raise


# Global application manager instance
app_manager = ApplicationManager()


def setup_signal_handlers() -> None:
    """
    Setup signal handlers for graceful shutdown.

    Configures SIGTERM and SIGINT handlers for production deployment.
    """
    logger = get_logger("app.signals")

    def signal_handler(signum: int, frame) -> None:
        """Handle shutdown signals gracefully."""
        signal_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT" if signum == signal.SIGINT else f"Signal-{signum}"

        logger.info("Shutdown signal received", signal=signal_name)

        # Perform graceful shutdown
        app_manager.shutdown()
        sys.exit(0)

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.info("Signal handlers configured")


def get_server_config(host: str = "0.0.0.0", port: int = 8000, **kwargs) -> Dict[str, Any]:
    """
    Get server configuration for development and production.

    Args:
        host: Server host address
        port: Server port number
        **kwargs: Additional server configuration options

    Returns:
        Dict[str, Any]: Server configuration dictionary
    """
    settings = get_settings()
    logger = get_logger("app.config")

    # Base configuration
    config = {
        "host": host,
        "port": port,
        "log_level": "info" if not settings.debug else "debug",
        "access_log": True,
        "server_header": False,  # Security: hide server header
        "date_header": False,  # Security: hide date header
    }

    # Development-specific configuration
    if settings.debug:
        config.update(
            {
                "reload": True,
                "reload_dirs": ["src"],
                "reload_includes": ["*.py"],
                "log_level": "debug",
            }
        )
        logger.info("Development server configuration applied")
    else:
        # Production-specific configuration
        config.update(
            {
                "workers": 1,  # Single worker for now, can be scaled later
                "loop": "auto",
                "http": "auto",
                "ws": "auto",
            }
        )
        logger.info("Production server configuration applied")

    # Override with any provided kwargs
    config.update(kwargs)

    logger.info("Server configuration prepared", config={k: v for k, v in config.items() if k != "reload_dirs"})
    return config


def create_application():
    """
    Create the FastAPI application instance.

    This function uses the application factory pattern to create
    and configure the FastAPI application for external usage.

    Returns:
        FastAPI: Configured application instance
    """
    return app_manager.create_application()


def run_development_server(host: str | None = None, port: int | None = None, reload: bool = True, **kwargs) -> None:
    """
    Run the development server with hot reload and debug features.

    This function is designed for development use with automatic reloading
    and enhanced logging for debugging purposes.

    Args:
        host: Server host address (defaults to settings)
        port: Server port number (defaults to settings)
        reload: Enable auto-reload for development
        **kwargs: Additional server configuration
    """
    logger = get_logger("app.dev")
    settings = get_settings()

    # Use settings defaults if not provided
    host = host or settings.api_host
    port = port or settings.api_port

    logger.info("Starting development server", host=host, port=port, reload=reload, debug=settings.debug)

    try:
        # Setup signal handlers
        setup_signal_handlers()

        # Create application
        app = app_manager.create_application()

        # Get server configuration
        config = get_server_config(host=host, port=port, reload=reload, **kwargs)

        # Run server
        uvicorn.run(app, **config)

    except KeyboardInterrupt:
        logger.info("Development server stopped by user")
    except Exception as e:
        logger.error("Development server failed", error=str(e), exc_info=True)
        raise


def run_production_server(host: str = "0.0.0.0", port: int = 8000, **kwargs) -> None:
    """
    Run the production server with optimized configuration.

    This function is designed for production deployment with proper
    error handling, logging, and performance optimization.

    Args:
        host: Server host address
        port: Server port number
        **kwargs: Additional server configuration
    """
    logger = get_logger("app.prod")

    logger.info("Starting production server", host=host, port=port)

    try:
        # Setup signal handlers
        setup_signal_handlers()

        # Create application
        app = app_manager.create_application()

        # Get production server configuration
        config = get_server_config(host=host, port=port, **kwargs)
        config.update(
            {
                "reload": False,  # Disable reload in production
                "access_log": True,
            }
        )

        # Create and store server instance for shutdown handling
        server_config = Config(app, **config)
        app_manager.server = Server(server_config)

        # Run server
        app_manager.server.run()

    except KeyboardInterrupt:
        logger.info("Production server stopped by user")
    except Exception as e:
        logger.error("Production server failed", error=str(e), exc_info=True)
        raise


def get_application():
    """
    Get the application instance for external usage.

    This function provides access to the configured FastAPI application
    for use by WSGI servers, testing, or other deployment scenarios.

    Returns:
        FastAPI: The configured application instance
    """
    return app_manager.create_application()


if __name__ == "__main__":
    # Direct execution - run development server
    run_development_server()
