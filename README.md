# Matai Raspberry Pi Communications and Sonar Stack

This repository documents the working Raspberry Pi 4 deployment used on Oceanova's Matai USV.

## Working stack

- Raspberry Pi OS / Debian Trixie on ARM64
- Waveshare SIM7600X LTE HAT using QMI
- Wi-Fi preferred, LTE automatic fallback
- Persistent LTE startup after reboot
- LTE watchdog with automatic redial
- NetBird remote access
- MAVLink Router forwarding Pixhawk telemetry to Mission Planner or QGroundControl
- MAVLink-to-NMEA GPS forwarder for SonarView
- Cerulean sonar on a dedicated Ethernet subnet
- SonarView in Docker with automatic restart
- Camera RTP/H.264 stream to the ground station
- Field recording, diagnostics, recovery, and post-mission data handling runbook

## Port map

| Service | Protocol | Port |
|---|---:|---:|
| MAVLink to ground station | UDP | 14550 |
| MAVLink Router local TCP server | TCP | 5760 |
| SonarView GPS NMEA input | UDP | 10110 |
| SonarView web interface | TCP | 7077 |
| Cerulean Surveyor data | TCP | 62312 |
| Camera stream | UDP | 5600 |
| SSH | TCP | 22 |

## Network layout

- `wlan0`: normal Wi-Fi connection, preferred default route
- `wwan0`: One NZ LTE fallback route
- `wt0`: NetBird overlay network
- `eth0`: dedicated sonar network, static address `192.168.2.10/24`
- Cerulean sonar: `192.168.2.86`

Do not add a default gateway to `eth0`. Internet traffic must continue through Wi-Fi or LTE.

## SonarView GPS chain

```text
Pixhawk GPS
  -> MAVLink Router TCP 127.0.0.1:5760
  -> scripts/mavlink_to_nmea.py
  -> NMEA GGA/RMC over UDP 127.0.0.1:10110
  -> SonarView Generic GPS Device
```

The GPS forwarder runs as `matai-gps-bridge.service` and starts automatically at boot.

For recording, both the Generic GPS device and the Cerulean Surveyor must be included in the active SonarView session plan. Defining the GPS device alone is not sufficient if its device ID is omitted from the plan.

## Documentation

- [Installation and validation guide](docs/SETUP.md)
- [Field operations runbook](docs/FIELD_OPERATIONS.md)
- [SonarView session reference](examples/sonarview-session.json)

## Included files

- `scripts/matai-lte-start.sh` — starts the QMI LTE session
- `scripts/matai-lte-watchdog.sh` — monitors LTE and automatically reconnects
- `scripts/mavlink_to_nmea.py` — converts Pixhawk MAVLink GPS into NMEA GGA/RMC for SonarView
- `systemd/matai-lte.service` — LTE startup service
- `systemd/matai-lte-watchdog.service` — LTE watchdog service
- `systemd/matai-gps-bridge.service` — persistent SonarView GPS forwarder
- `examples/mavlink-router.conf` — MAVLink Router configuration template
- `examples/sonarview-session.json` — reference sonar and GPS recording plan
- `docs/FIELD_OPERATIONS.md` — deployment, diagnostics, recovery, and data handling procedures
