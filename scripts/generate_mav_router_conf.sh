#!/usr/bin/env bash
set -euo pipefail

OUTPUT_CONF="/etc/mavlink-router/main.conf"
TMP_CONF="/tmp/mavlink-router.conf.tmp"

cat << 'EOF' > "$TMP_CONF"
[General]
TcpServerPort = 5760
ReportStats = false
MavlinkDialect = common

[UartEndpoint pixhawk]
Device = /dev/ttyACM0
Baud = 115200

EOF

netbird status --json 2>/dev/null | jq -r '
    .peers.details[]
    | select((.hostname // .fqdn // "") | contains("gs"))
    | select(.ip != null or .netbirdIp != null)
    |
    "[UdpEndpoint \(.hostname // .fqdn // "n/a")]
Mode = Normal
Address = \(.ip // .netbirdIp)
Port = 14550
"
' >> "$TMP_CONF"

mkdir -p "$(dirname "$OUTPUT_CONF")"
install -m 644 "$TMP_CONF" "$OUTPUT_CONF"
rm "$TMP_CONF"

systemctl enable mavlink-router >/dev/null

if systemctl is-active --quiet mavlink-router; then
    systemctl restart mavlink-router
else
    systemctl start mavlink-router
fi