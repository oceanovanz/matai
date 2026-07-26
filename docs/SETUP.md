# Matai Raspberry Pi Setup

This guide records the working installation from a clean Raspberry Pi OS / Debian Trixie ARM64 image.

## 1. Confirm interfaces

```bash
ip -br link
ip -br addr
```

Expected interfaces include:

- `eth0`
- `wlan0`
- `wwan0`
- `wt0`

## 2. SIM7600 LTE setup

Install the required packages:

```bash
sudo apt update
sudo apt install -y modemmanager network-manager minicom libqmi-utils udhcpc
```

Confirm the modem devices and QMI driver:

```bash
lsusb
ls -l /dev/ttyUSB*
ls -l /dev/cdc-wdm*
lsmod | grep -E 'qmi_wwan|cdc_wdm|option|usb_wwan'
```

Validate the modem and SIM:

```bash
sudo qmicli -d /dev/cdc-wdm0 --dms-get-operating-mode
sudo qmicli -d /dev/cdc-wdm0 --uim-get-card-status
sudo qmicli -d /dev/cdc-wdm0 --nas-get-signal-strength
sudo qmicli -d /dev/cdc-wdm0 --nas-get-serving-system
```

For One NZ, the APN used in this deployment is:

```text
web
```

### Manual connection test

```bash
sudo ip link set wwan0 down
echo Y | sudo tee /sys/class/net/wwan0/qmi/raw_ip
sudo ip link set wwan0 up

sudo qmicli \
  -d /dev/cdc-wdm0 \
  --device-open-proxy \
  --wds-start-network="apn=web,ip-type=4" \
  --client-no-release-cid

sudo udhcpc -i wwan0
```

Validate:

```bash
ip addr show wwan0
ip route
ping -I wwan0 -c 4 1.1.1.1
curl --interface wwan0 https://api.ipify.org
echo
```

### Route priority

The working route arrangement is:

- Wi-Fi metric `600`
- LTE metric `700`

Example:

```bash
sudo ip route del default via LTE_GATEWAY dev wwan0
sudo ip route add default via LTE_GATEWAY dev wwan0 metric 700
```

The startup script calculates the LTE gateway automatically.

## 3. Install persistent LTE startup

Copy the supplied script and unit:

```bash
sudo install -m 0755 scripts/matai-lte-start.sh /usr/local/sbin/matai-lte-start.sh
sudo install -m 0644 systemd/matai-lte.service /etc/systemd/system/matai-lte.service

sudo systemctl daemon-reload
sudo systemctl enable --now matai-lte.service
```

Check:

```bash
sudo systemctl status matai-lte --no-pager -l
```

## 4. Install LTE watchdog

```bash
sudo install -m 0755 scripts/matai-lte-watchdog.sh /usr/local/sbin/matai-lte-watchdog.sh
sudo install -m 0644 systemd/matai-lte-watchdog.service /etc/systemd/system/matai-lte-watchdog.service

sudo systemctl daemon-reload
sudo systemctl enable --now matai-lte-watchdog.service
```

Check:

```bash
sudo systemctl status matai-lte-watchdog --no-pager -l
sudo journalctl -t matai-lte-watchdog -n 20 --no-pager
```

## 5. NetBird

Install and enrol NetBird using your organisation's normal process.

Validate:

```bash
netbird status
ip route get GROUND_STATION_NETBIRD_IP
ping -c 4 GROUND_STATION_NETBIRD_IP
```

The route should use `wt0`.

## 6. MAVLink Router

Install MAVLink Router and configure the Pixhawk serial endpoint plus a UDP destination for the Windows ground station.

Use `examples/mavlink-router.conf` as the template, replacing:

- `GROUND_STATION_NETBIRD_IP`
- the Pixhawk device path if necessary
- the baud rate if necessary

Enable and check:

```bash
sudo systemctl enable --now mavlink-router
sudo systemctl status mavlink-router --no-pager -l
```

Confirm outgoing telemetry:

```bash
sudo tcpdump -ni wt0 udp port 14550
```

Mission Planner or QGroundControl should listen on UDP port `14550`.

On Windows:

```powershell
netstat -ano | findstr :14550
```

If needed, add a firewall rule from Administrator PowerShell:

```powershell
New-NetFirewallRule `
  -DisplayName "Matai MAVLink UDP 14550" `
  -Direction Inbound `
  -Protocol UDP `
  -LocalPort 14550 `
  -Action Allow
```

Only one application can bind the same UDP port unless socket sharing is explicitly supported. Close extra Mission Planner or QGroundControl instances if Windows reports that the socket address is already in use.

## 7. Configure the sonar Ethernet interface

Create a persistent NetworkManager profile:

```bash
sudo nmcli connection add \
  type ethernet \
  ifname eth0 \
  con-name sonar-ethernet \
  ipv4.method manual \
  ipv4.addresses 192.168.2.10/24 \
  ipv4.never-default yes \
  ipv6.method disabled

sudo nmcli connection up sonar-ethernet
```

Validate:

```bash
ip -br addr show eth0
ip route
ping -c 4 192.168.2.86
```

Expected route:

```text
192.168.2.0/24 dev eth0
```

There must be no default gateway on `eth0`.

## 8. Install Docker

```bash
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg \
  -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y \
  docker-ce \
  docker-ce-cli \
  containerd.io \
  docker-buildx-plugin \
  docker-compose-plugin

sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

Log out and back in, or run:

```bash
newgrp docker
```

Test:

```bash
docker version
docker run --rm hello-world
```

## 9. Install SonarView

```bash
sudo mkdir -p /usr/SonarView
sudo chown -R "$USER":"$USER" /usr/SonarView

docker pull nicknothom/sonarview:latest

docker run -d \
  --name sonarview \
  --network host \
  --restart unless-stopped \
  -v /usr/SonarView:/userdata \
  nicknothom/sonarview:latest
```

Validate:

```bash
docker ps
docker logs --tail 100 sonarview
sudo ss -lntup | grep 7077
```

Open SonarView through the Pi's NetBird address:

```text
http://PI_NETBIRD_IP:7077
```

The `--restart unless-stopped` policy makes SonarView return automatically after reboot.

## 10. Reboot validation

```bash
sudo reboot
```

After reconnecting:

```bash
sudo systemctl status matai-lte --no-pager -l
sudo systemctl status matai-lte-watchdog --no-pager -l
sudo systemctl status mavlink-router --no-pager -l
netbird status
ip route
ping -I wwan0 -c 4 1.1.1.1
ping -c 4 192.168.2.86
docker ps
sudo ss -lntup | grep 7077
```

Expected state:

- Wi-Fi route metric `600`
- LTE route metric `700`
- NetBird connected
- MAVLink Router running
- SonarView container running
- sonar reachable at `192.168.2.86`
- LTE watchdog running
