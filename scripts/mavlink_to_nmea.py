#!/usr/bin/env python3

import math
import socket
import time
from datetime import datetime, timezone

from pymavlink import mavutil

MAVLINK_CONNECTION = "tcp:127.0.0.1:5760"
NMEA_HOST = "127.0.0.1"
NMEA_PORT = 10110
SEND_INTERVAL = 0.2


def nmea_checksum(sentence: str) -> str:
    checksum = 0
    for char in sentence:
        checksum ^= ord(char)
    return f"${sentence}*{checksum:02X}\r\n"


def decimal_to_nmea(value: float, is_latitude: bool) -> tuple[str, str]:
    if is_latitude:
        direction = "N" if value >= 0 else "S"
        degrees_width = 2
    else:
        direction = "E" if value >= 0 else "W"
        degrees_width = 3

    absolute = abs(value)
    degrees = int(absolute)
    minutes = (absolute - degrees) * 60
    return f"{degrees:0{degrees_width}d}{minutes:07.4f}", direction


def build_gga(latitude: float, longitude: float, altitude: float,
              satellites: int, hdop: float, fix_type: int) -> str:
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%H%M%S.%f")[:9]
    lat_value, lat_dir = decimal_to_nmea(latitude, True)
    lon_value, lon_dir = decimal_to_nmea(longitude, False)

    if fix_type >= 6:
        quality = 4
    elif fix_type == 5:
        quality = 5
    elif fix_type >= 3:
        quality = 1
    else:
        quality = 0

    sentence = (
        f"GPGGA,{timestamp},{lat_value},{lat_dir},{lon_value},{lon_dir},"
        f"{quality},{satellites:02d},{hdop:.1f},{altitude:.2f},M,0.0,M,,"
    )
    return nmea_checksum(sentence)


def build_rmc(latitude: float, longitude: float, speed_mps: float,
              course_deg: float, valid: bool) -> str:
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%H%M%S.%f")[:9]
    date = now.strftime("%d%m%y")
    lat_value, lat_dir = decimal_to_nmea(latitude, True)
    lon_value, lon_dir = decimal_to_nmea(longitude, False)
    speed_knots = speed_mps * 1.943844
    status = "A" if valid else "V"

    sentence = (
        f"GPRMC,{timestamp},{status},{lat_value},{lat_dir},"
        f"{lon_value},{lon_dir},{speed_knots:.2f},{course_deg:.2f},"
        f"{date},,,A"
    )
    return nmea_checksum(sentence)


def main() -> None:
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while True:
        try:
            print(f"Connecting to MAVLink at {MAVLINK_CONNECTION}", flush=True)
            mavlink = mavutil.mavlink_connection(
                MAVLINK_CONNECTION,
                autoreconnect=True,
            )
            mavlink.wait_heartbeat(timeout=30)
            print("MAVLink heartbeat received", flush=True)

            latest_gps = None
            latest_position = None
            last_send = 0.0

            while True:
                message = mavlink.recv_match(blocking=True, timeout=2)
                if message is None:
                    continue

                message_type = message.get_type()
                if message_type == "GPS_RAW_INT":
                    latest_gps = message
                elif message_type == "GLOBAL_POSITION_INT":
                    latest_position = message

                if latest_gps is None or latest_position is None:
                    continue

                now = time.monotonic()
                if now - last_send < SEND_INTERVAL:
                    continue

                latitude = latest_position.lat / 1e7
                longitude = latest_position.lon / 1e7
                altitude = latest_position.alt / 1000.0
                speed_mps = math.sqrt(
                    latest_position.vx ** 2 + latest_position.vy ** 2
                ) / 100.0
                course_deg = latest_position.hdg / 100.0
                if latest_position.hdg == 65535:
                    course_deg = 0.0

                satellites = int(latest_gps.satellites_visible)
                if satellites == 255:
                    satellites = 0

                hdop = latest_gps.eph / 100.0
                if latest_gps.eph == 65535:
                    hdop = 99.9

                fix_type = int(latest_gps.fix_type)
                valid = fix_type >= 3

                udp_socket.sendto(
                    build_gga(latitude, longitude, altitude, satellites, hdop, fix_type).encode("ascii"),
                    (NMEA_HOST, NMEA_PORT),
                )
                udp_socket.sendto(
                    build_rmc(latitude, longitude, speed_mps, course_deg, valid).encode("ascii"),
                    (NMEA_HOST, NMEA_PORT),
                )
                last_send = now

        except Exception as error:
            print(f"Bridge error: {error}", flush=True)
            time.sleep(5)


if __name__ == "__main__":
    main()
