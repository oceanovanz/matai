#!/bin/bash
set -u

IFACE="${IFACE:-wwan0}"
CHECK_IP="${CHECK_IP:-1.1.1.1}"
FAIL_LIMIT="${FAIL_LIMIT:-3}"
CHECK_INTERVAL="${CHECK_INTERVAL:-30}"
RECOVERY_WAIT="${RECOVERY_WAIT:-20}"
FAIL_COUNT=0

logger -t matai-lte-watchdog "LTE watchdog started"

while true; do
    if ip link show "$IFACE" >/dev/null 2>&1 && \
       ping -I "$IFACE" -c 2 -W 5 "$CHECK_IP" >/dev/null 2>&1; then

        if [ "$FAIL_COUNT" -gt 0 ]; then
            logger -t matai-lte-watchdog \
                "LTE connection recovered after $FAIL_COUNT failed checks"
        fi

        FAIL_COUNT=0
    else
        FAIL_COUNT=$((FAIL_COUNT + 1))

        logger -t matai-lte-watchdog \
            "LTE health check failed ($FAIL_COUNT/$FAIL_LIMIT)"

        if [ "$FAIL_COUNT" -ge "$FAIL_LIMIT" ]; then
            logger -t matai-lte-watchdog \
                "LTE unavailable; restarting matai-lte.service"

            systemctl restart matai-lte.service
            sleep "$RECOVERY_WAIT"

            if ping -I "$IFACE" -c 2 -W 5 "$CHECK_IP" >/dev/null 2>&1; then
                logger -t matai-lte-watchdog "LTE successfully restored"
            else
                logger -t matai-lte-watchdog \
                    "LTE restart completed but connectivity is still unavailable"
            fi

            FAIL_COUNT=0
        fi
    fi

    sleep "$CHECK_INTERVAL"
done
