"""Constants for the WGDashboard Monitor integration."""

DOMAIN = "wgdashboard_monitor"

CONF_HOST = "host"
CONF_API_KEY = "api_key"
CONF_CONFIG_NAME = "config_name"
CONF_VERIFY_SSL = "verify_ssl"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_CONFIG_NAME = "wg0"
DEFAULT_SCAN_INTERVAL = 15  # seconds
DEFAULT_VERIFY_SSL = False

# WGDashboard considers a peer "online" if its last handshake is recent.
# WireGuard peers re-handshake roughly every 2 minutes when active, so
# anything older than this is treated as disconnected.
HANDSHAKE_TIMEOUT_SECONDS = 180

API_HEADER_KEY = "wg-dashboard-apikey"
