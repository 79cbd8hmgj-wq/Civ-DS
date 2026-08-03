#!/usr/bin/env python3
"""Minimal bounded GDB-remote capture client; writes normalized JSON only."""

from __future__ import annotations
import argparse
import json
import socket
import time


def receive(sock: socket.socket) -> str:
    while sock.recv(1) != b"$":
        pass
    payload = bytearray()
    while True:
        char = sock.recv(1)
        if char == b"#":
            break
        payload += char
    checksum = sock.recv(2)
    if int(checksum, 16) != sum(payload) % 256:
        raise RuntimeError("GDB checksum mismatch")
    sock.sendall(b"+")
    return payload.decode("ascii")


def request(sock: socket.socket, command: str) -> str:
    payload = command.encode("ascii")
    sock.sendall(b"$" + payload + b"#" + f"{sum(payload) % 256:02x}".encode())
    while sock.recv(1) != b"+":
        pass
    return receive(sock)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--address", default="02000800")
    parser.add_argument("--size", type=lambda value: int(value, 0), default=32)
    args = parser.parse_args()
    deadline = time.monotonic() + 5
    while True:
        try:
            sock = socket.create_connection(("127.0.0.1", args.port), timeout=1)
            break
        except OSError:
            if time.monotonic() > deadline:
                raise
            time.sleep(0.05)
    with sock:
        sock.settimeout(3)
        stop = request(sock, "?")
        registers = request(sock, "g")
        memory = request(sock, f"m{args.address},{args.size:x}")
    result = {
        "stop_reply": stop,
        "register_bytes_hex": registers,
        "memory": {
            "runtime_address": f"0x{int(args.address, 16):08x}",
            "size": args.size,
            "bytes_hex": memory,
        },
    }
    with open(args.output, "w", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
