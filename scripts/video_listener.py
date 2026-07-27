#!/usr/bin/env python3

import socket
import json
import subprocess

LISTEN_PORT = 5000

pipeline_process = None


def create_udp_pipeline(ip, port):
    return [
        "gst-launch-1.0",
        "-e",
        "libcamerasrc",
        "!",
        "queue", 
        "max-size-buffers=4",
        "leaky=downstream",
        "!",
        "video/x-raw,format=I420,width=960,height=540,framerate=20/1",
        "!",
        "v4l2h264enc",
        "extra-controls=controls,video_bitrate=2500000,h264_i_frame_period=30",
        "!",
        "h264parse",
        "config-interval=1",
        "!",
        "rtph264pay",
        "config-interval=1",
        "pt=96",
        "!",
        "udpsink",
        f"host={ip}",
        f"port={port}",
    ]


def create_srt_pipeline(port):
    return [
        "gst-launch-1.0",
        "-e",
        "libcamerasrc",
        "!",
        "queue",
        "max-size-buffers=4",
        "leaky=downstream",
        "!",
        "video/x-raw,format=I420,width=960,height=540,framerate=20/1",
        "!",
        "v4l2h264enc",
        "extra-controls=controls,video_bitrate=2500000,h264_i_frame_period=30",
        "!",
        "video/x-h264,profile=baseline,level=(string)3.1",
        "!",
        "h264parse",
        "config-interval=1",
        "!",
        "mpegtsmux",
        "alignment=7",
        "!",
        "srtsink",
        f"uri=srt://:{port}?mode=listener&latency=120",
    ]


def stop_stream():
    global pipeline_process

    if pipeline_process:
        print("Stopping video stream")
        pipeline_process.terminate()

        try:
            pipeline_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pipeline_process.kill()

        pipeline_process = None


def start_stream(stream_type, ip, port):
    global pipeline_process

    stop_stream()
    print(f"Starting {stream_type} stream " f"to {ip}:{port}")

    if stream_type == "udp":
        cmd = create_udp_pipeline(ip, port)
    elif stream_type == "srt":
        cmd = create_srt_pipeline(port)
    else:
        print("Unknown stream type")
        return

    print("Launching:")
    print(" ".join(cmd))

    pipeline_process = subprocess.Popen(cmd)


def main():

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", LISTEN_PORT))

    print(f"Listening on UDP {LISTEN_PORT}")

    while True:
        data, addr = sock.recvfrom(4096)

        try:
            msg = json.loads(data.decode("utf-8"))
            print("Request from", addr)
            print(msg)

            command = msg.get("command")
            if command == "start":
                start_stream(msg["type"], addr[0], msg["port"])

            elif command == "stop":
                stop_stream()

        except json.JSONDecodeError as e:
            print("Invalid JSON:", e)
            continue


if __name__ == "__main__":

    main()

