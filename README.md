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
- Cerulean sonar on a dedicated Ethernet subnet
- SonarView in Docker with automatic restart
- Camera RTP/H.264 stream to the ground station

## Port map

| Service | Protocol | Port |
|---|---:|---:|
| MAVLink to ground station | UDP | 14550 |
| SonarView web interface | TCP | 7077 |
| Camera stream | UDP | 5600 |
| SSH | TCP | 22 |

## Network layout

- `wlan0`: normal Wi-Fi connection, preferred default route
- `wwan0`: One NZ LTE fallback route
- `wt0`: NetBird overlay network
- `eth0`: dedicated sonar network, static address `192.168.2.10/24`
- Cerulean sonar: `192.168.2.86`

Do not add a default gateway to `eth0`. Internet traffic must continue through Wi-Fi or LTE.

## Installation guide

See [docs/SETUP.md](docs/SETUP.md) for the complete installation and validation procedure.

## Included files

- `scripts/matai-lte-start.sh` — starts the QMI LTE session
- `scripts/matai-lte-watchdog.sh` — monitors LTE and automatically reconnects
- `systemd/matai-lte.service` — LTE startup service
- `systemd/matai-lte-watchdog.service` — LTE watchdog service
- `examples/mavlink-router.conf` — MAVLink Router configuration template


