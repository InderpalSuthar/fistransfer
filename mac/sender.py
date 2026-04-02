"""
FisTransfer — TCP Sender
==========================
Sends compressed JPEG images over a TCP socket to the Windows receiver.
Packet format: [4-byte big-endian size header] + [JPEG data bytes]
"""

import socket
import struct
import time

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import (
    RECEIVER_IP,
    RECEIVER_PORT,
    SOCKET_BUFFER_SIZE,
    ENABLE_PROFILING,
)


class Sender:
    """TCP socket client that sends framed JPEG images."""

    def __init__(self):
        self.sock = None
        self.connected = False

    def connect(self):
        """Establish TCP connection to the Windows receiver."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # ── Performance tuning ───────────────────────────────────────
            # Disable Nagle's algorithm — send packets immediately
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            # Increase send buffer
            self.sock.setsockopt(
                socket.SOL_SOCKET, socket.SO_SNDBUF, SOCKET_BUFFER_SIZE
            )
            # Connection timeout
            self.sock.settimeout(5.0)

            print(f"[Sender] Connecting to {RECEIVER_IP}:{RECEIVER_PORT} ...")
            self.sock.connect((RECEIVER_IP, RECEIVER_PORT))
            self.connected = True
            print(f"[Sender] ✅ Connected!")
            return True
        except (ConnectionRefusedError, socket.timeout, OSError) as e:
            print(f"[Sender] ❌ Connection failed: {e}")
            self.connected = False
            return False

    def send_image(self, jpeg_bytes: bytes) -> dict:
        """
        Send a JPEG image with a 4-byte size header.

        Parameters
        ----------
        jpeg_bytes : bytes
            The raw JPEG buffer to transmit.

        Returns
        -------
        timings : dict
            Send timing in milliseconds.
        """
        timings = {}

        if not self.connected:
            if not self.connect():
                return {"error": "Not connected"}

        try:
            t0 = time.perf_counter()

            # ── Frame header: 4-byte big-endian unsigned int ─────────────
            header = struct.pack(">L", len(jpeg_bytes))
            self.sock.sendall(header + jpeg_bytes)

            t1 = time.perf_counter()

            if ENABLE_PROFILING:
                timings = {
                    "send_ms": round((t1 - t0) * 1000, 1),
                    "payload_kb": round(len(jpeg_bytes) / 1024, 1),
                }

            return timings

        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            print(f"[Sender] ❌ Send failed: {e}")
            self.connected = False
            self._close_socket()
            return {"error": str(e)}

    def _close_socket(self):
        """Safely close the socket."""
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None

    def disconnect(self):
        """Disconnect from the receiver."""
        self._close_socket()
        self.connected = False
        print("[Sender] Disconnected.")
