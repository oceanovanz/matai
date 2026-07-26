# SonarView GPS Forwarder

This setup forwards the Pixhawk's GPS position from MAVLink Router into SonarView as NMEA 0183.

## Data path

```text
Pixhawk GPS
  -> MAVLink Router TCP server at 127.0.0.1:5760
  -> mavlink_to_nmea.py
  -> UDP NMEA at 127.0.0.1:10110
  -> SonarView Generic GPS Device
```

The bridge emits:

- `GPGGA` for fix quality, satellites, HDOP, altitude and position
- `GPRMC` for valid position, speed over ground, course over ground and UTC date/time

## 1. Confirm MAVLink Router TCP access

The MAVLink Router configuration must include:

```ini
[General]
TcpServerPort = 5760
```

Test it:

```bash
nc -vz 127.0.0.1 5760
```

Expected:

```text
Connection to 127.0.0.1 5760 port [tcp/*] succeeded!
```

## 2. Install the Python environment

```bash
sudo apt install -y python3-pip python3-venv
sudo mkdir -p /opt/matai-gps-bridge
sudo python3 -m venv /opt/matai-gps-bridge/venv
sudo /opt/matai-gps-bridge/venv/bin/pip install \
  --index-url https://www.piwheels.org/simple \
  --extra-index-url https://pypi.org/simple \
  --timeout 120 \
  --retries 10 \
  pymavlink
```

## 3. Install the bridge

From the repository root:

```bash
sudo install -m 0755 \
  scripts/mavlink_to_nmea.py \
  /opt/matai-gps-bridge/mavlink_to_nmea.py

sudo install -m 0644 \
  systemd/matai-gps-bridge.service \
  /etc/systemd/system/matai-gps-bridge.service
```

Enable it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now matai-gps-bridge
```

Check:

```bash
systemctl is-enabled matai-gps-bridge
systemctl is-active matai-gps-bridge
sudo systemctl status matai-gps-bridge --no-pager -l
```

Expected:

```text
enabled
active
```

## 4. Verify NMEA output

```bash
sudo tcpdump -A -ni lo udp port 10110
```

Expected output includes live sentences similar to:

```text
$GPGGA,...
$GPRMC,...
```

## 5. Configure SonarView

Open SonarView through the Pi's NetBird address:

```text
http://PI_NETBIRD_IP:7077
```

In **Session Configurations**, add a device with:

```text
Device Nickname: mataigps
Device Type: Generic GPS Device
Protocol: UDP
Host: 127.0.0.1
Port: 10110
```

Add the sonar as another saved device, for example:

```text
Device Nickname: matai-surveyor
Device Type: Surveyor 240-16
Protocol: TCP
Host: 192.168.2.86
Port: 62312
```

Create a session containing both:

```text
Session Name: Matai Survey
Devices:
  - matai-surveyor
  - mataigps
```

Connect to the combined session rather than the standalone Surveyor discovery card.

A yellow UDP reachability warning may appear because UDP is connectionless. The real validation is that the GPS device shows connected and SonarView displays live latitude and longitude.

## 6. Reboot validation

After rebooting the Pi:

```bash
sudo systemctl status matai-gps-bridge --no-pager -l
sudo tcpdump -A -ni lo udp port 10110
```

Then reconnect to the saved SonarView session and confirm live position returns automatically.

## Notes

- GPS quality is inherited from the GPS connected to the Pixhawk.
- The bridge maps a standard 3D fix to NMEA quality `1`.
- RTK float and fixed states are mapped when available.
- Course over ground can wander while the vessel is stationary; this does not affect position output.
- The bridge reconnects automatically if the MAVLink TCP stream temporarily disappears.
