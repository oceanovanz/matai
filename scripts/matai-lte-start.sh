#!/bin/bash
set -euo pipefail

MODEM="/dev/cdc-wdm0"
IFACE="wwan0"
APN="${APN:-web}"
ROUTE_METRIC="${ROUTE_METRIC:-700}"

log() {
    logger -t matai-lte "$*"
    echo "$*"
}

for _ in $(seq 1 30); do
    if [ -e "$MODEM" ] && [ -d "/sys/class/net/$IFACE" ]; then
        break
    fi
    sleep 2
done

if [ ! -e "$MODEM" ]; then
    log "QMI control device $MODEM not found"
    exit 1
fi

if [ ! -d "/sys/class/net/$IFACE" ]; then
    log "Network interface $IFACE not found"
    exit 1
fi

ip link set "$IFACE" down || true

echo Y > "/sys/class/net/$IFACE/qmi/raw_ip"
ip link set "$IFACE" up

log "Starting LTE session with APN $APN"
qmicli \
    -d "$MODEM" \
    --device-open-proxy \
    --wds-start-network="apn=$APN,ip-type=4" \
    --client-no-release-cid

udhcpc -i "$IFACE" -q

GATEWAY=$(ip route show dev "$IFACE" default | awk '/default/ {print $3; exit}')

if [ -z "$GATEWAY" ]; then
    log "No LTE gateway was assigned"
    exit 1
fi

ip route del default dev "$IFACE" 2>/dev/null || true
ip route add default via "$GATEWAY" dev "$IFACE" metric "$ROUTE_METRIC"

log "LTE connected through $IFACE with gateway $GATEWAY and metric $ROUTE_METRIC"
