# Matai Field Operations Runbook

This runbook records the field-tested startup, recording, monitoring, and recovery sequence for the Matai Raspberry Pi communications and sonar stack.

## 1. Pre-deployment power check

The Raspberry Pi must receive a stable 5 V rail under load. A bench reading alone is not enough because cable and connector voltage drop can trigger undervoltage during camera, LTE, Docker, or sonar activity.

Run:

```bash
vcgencmd get_throttled
```

Healthy result:

```text
throttled=0x0
```

Useful live checks:

```bash
watch -n 2 vcgencmd measure_volts core
watch -n 2 vcgencmd get_throttled
```

If an undervoltage flag appears, first improve the 5 V supply, wiring, connector, and cable gauge. Do not keep increasing regulator voltage without confirming the voltage at the Raspberry Pi under load.

## 2. Whole-stack startup

The normal services should start automatically after boot. Confirm them with:

```bash
sudo systemctl status matai-lte --no-pager -l
sudo systemctl status matai-lte-watchdog --no-pager -l
sudo systemctl status mavlink-router --no-pager -l
sudo systemctl status matai-gps-bridge --no-pager -l
netbird status
docker ps
```

If SonarView is not running:

```bash
docker start sonarview
```

If the container does not exist, recreate it:

```bash
sudo mkdir -p /usr/SonarView
sudo chown -R "$USER":"$USER" /usr/SonarView

docker run -d \
  --name sonarview \
  --network host \
  --restart unless-stopped \
  -v /usr/SonarView:/userdata \
  nicknothom/sonarview:latest
```

## 3. Validate the sonar and GPS chain

Confirm the Cerulean sonar is reachable:

```bash
ping -c 4 192.168.2.86
```

Confirm the GPS bridge service:

```bash
sudo systemctl status matai-gps-bridge --no-pager -l
sudo journalctl -u matai-gps-bridge -n 50 --no-pager
```

Confirm NMEA packets are being emitted locally:

```bash
sudo tcpdump -ni lo udp port 10110
```

Confirm SonarView is listening:

```bash
sudo ss -lntup | grep 7077
```

Open SonarView at:

```text
http://PI_NETBIRD_IP:7077
```

## 4. SonarView device configuration

Use these device endpoints:

- Cerulean Surveyor 240-16: `tcp://192.168.2.86:62312`
- Generic GPS: `udp://127.0.0.1:10110`

The GPS device must be included in the active recording/session plan as well as being defined in the device list. A device that exists in the configuration but is omitted from the active plan may not be recorded with the sonar data.

A reference configuration is provided in `examples/sonarview-session.json`.

## 5. Start a survey recording

Before pressing record:

```bash
ping -c 2 192.168.2.86
sudo systemctl is-active matai-gps-bridge
sudo tcpdump -c 5 -ni lo udp port 10110
docker ps --filter name=sonarview
```

During recording, watch the container and storage:

```bash
docker logs -f --tail 50 sonarview
```

In another shell:

```bash
watch -n 2 'df -h /usr/SonarView; find /usr/SonarView -type f -printf "%TY-%Tm-%Td %TH:%TM:%TS %10s %p\n" | sort | tail -n 10'
```

Record a short test line before the full mission and confirm:

- sonar data is updating;
- GPS position is updating;
- the output file grows in `/usr/SonarView`;
- timestamps are correct;
- the vessel direction and heading are sensible.

## 6. CPU, memory, temperature, and container monitoring

Quick system view:

```bash
top
```

Better process view:

```bash
sudo apt install -y htop
htop
```

Raspberry Pi temperature and throttling:

```bash
watch -n 2 'vcgencmd measure_temp; vcgencmd get_throttled'
```

Docker resource use:

```bash
docker stats sonarview
```

One-line whole-stack snapshot:

```bash
printf '\n=== SERVICES ===\n'; \
systemctl --no-pager --full status matai-lte matai-lte-watchdog mavlink-router matai-gps-bridge | grep -E 'Loaded:|Active:'; \
printf '\n=== NETWORK ===\n'; ip -br addr; ip route; \
printf '\n=== DOCKER ===\n'; docker ps; \
printf '\n=== POWER ===\n'; vcgencmd get_throttled; vcgencmd measure_temp; \
printf '\n=== STORAGE ===\n'; df -h /usr/SonarView
```

## 7. Recovery sequence

### SonarView stopped

```bash
docker restart sonarview
docker logs --tail 100 sonarview
```

### GPS missing in SonarView

```bash
sudo systemctl restart matai-gps-bridge
sudo journalctl -u matai-gps-bridge -n 100 --no-pager
sudo tcpdump -c 10 -ni lo udp port 10110
```

Then confirm the Generic GPS device is enabled in the active SonarView session plan.

### Sonar unreachable

```bash
ip -br addr show eth0
ip route
ping -c 4 192.168.2.86
sudo ethtool eth0
```

Expected local address:

```text
192.168.2.10/24
```

There must be no default route through `eth0`.

### LTE unavailable

```bash
sudo systemctl restart matai-lte
sudo systemctl restart matai-lte-watchdog
sudo qmicli -d /dev/cdc-wdm0 --nas-get-signal-strength
ip -br addr show wwan0
ip route
```

### NetBird unavailable

```bash
sudo systemctl restart netbird
netbird status
```

## 8. Post-mission data handling

List the newest files:

```bash
find /usr/SonarView -type f -printf '%TY-%Tm-%Td %TH:%TM:%TS %10s %p\n' | sort | tail -n 30
```

Create a mission archive without deleting the source:

```bash
MISSION="matai-$(date +%Y%m%d-%H%M)"
tar -C /usr/SonarView -czf "$HOME/${MISSION}.tar.gz" .
sha256sum "$HOME/${MISSION}.tar.gz" > "$HOME/${MISSION}.tar.gz.sha256"
```

Copy the archive to the processing computer, verify the checksum, and retain the original data until processing and delivery are complete.

## 9. Minimum deployment gate

Do not begin the primary survey line until all of the following are true:

- `vcgencmd get_throttled` returns `0x0`;
- sonar responds at `192.168.2.86`;
- GPS NMEA packets are visible on UDP `10110`;
- SonarView sees both sonar and GPS;
- a short recording test creates a growing output file;
- remote access and a local/manual control fallback are available;
- sufficient storage and battery capacity remain for the mission.