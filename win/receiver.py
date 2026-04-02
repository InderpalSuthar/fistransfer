"""
FisTransfer — TCP Receiver (QThread)
======================================
Socket server that listens for incoming JPEG images from the Mac sender.
Runs on a QThread so it doesn't block the PyQt6 UI.

Packet format: [4-byte big-endian size header] + [JPEG data bytes]
"""

import socket
import struct
import time

import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import (
    RECEIVER_PORT,
    SOCKET_BUFFER_SIZE,
    ENABLE_PROFILING,
)


class ReceiverThread(QThread):
    """
    Background TCP listener that emits a signal when an image is received.

    Signals
    -------
    image_received(ndarray)
        Emitted with the decoded BGR image when a frame arrives.
    status_changed(str)
        Emitted with status messages for UI display.
    """

    image_received = pyqtSignal(np.ndarray)
    status_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True

    def run(self):
        """Main thread loop: listen → accept → receive frames."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        server.setsockopt(
            socket.SOL_SOCKET, socket.SO_RCVBUF, SOCKET_BUFFER_SIZE
        )
        server.settimeout(1.0)  # Allow periodic _running checks

        try:
            server.bind(("0.0.0.0", RECEIVER_PORT))
            server.listen(1)
            self.status_changed.emit(f"Listening on port {RECEIVER_PORT}...")
            print(f"[Receiver] 🔊 Listening on 0.0.0.0:{RECEIVER_PORT}")

            while self._running:
                # ── Accept connection ────────────────────────────────────
                try:
                    conn, addr = server.accept()
                except socket.timeout:
                    continue

                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                conn.setsockopt(
                    socket.SOL_SOCKET, socket.SO_RCVBUF, SOCKET_BUFFER_SIZE
                )
                conn.settimeout(2.0)  # Timeout for recv to avoid hanging
                self.status_changed.emit(f"Connected: {addr[0]}")
                print(f"[Receiver] ✅ Connection from {addr[0]}:{addr[1]}")

                # ── Receive loop ─────────────────────────────────────────
                try:
                    while self._running:
                        # Read 4-byte header
                        header = self._recv_exact(conn, 4)
                        if header is None:
                            break

                        img_size = struct.unpack(">L", header)[0]
                        if img_size == 0 or img_size > 50_000_000:  # Sanity
                            print(f"[Receiver] ⚠ Invalid size: {img_size}")
                            break

                        # Read image data
                        t0 = time.perf_counter()
                        img_data = self._recv_exact(conn, img_size)
                        if img_data is None:
                            break
                        t1 = time.perf_counter()

                        # Decode JPEG
                        jpg_array = np.frombuffer(img_data, dtype=np.uint8)
                        image = cv2.imdecode(jpg_array, cv2.IMREAD_COLOR)
                        t2 = time.perf_counter()

                        if image is not None:
                            if ENABLE_PROFILING:
                                print(
                                    f"[Receiver] 📥 Received {img_size / 1024:.1f} KB"
                                    f" | recv={round((t1-t0)*1000,1)}ms"
                                    f" | decode={round((t2-t1)*1000,1)}ms"
                                )
                            self.image_received.emit(image)
                        else:
                            print("[Receiver] ⚠ Failed to decode image")

                except (ConnectionResetError, BrokenPipeError, OSError) as e:
                    print(f"[Receiver] Connection lost: {e}")
                    self.status_changed.emit("Disconnected. Waiting...")
                finally:
                    conn.close()

        except OSError as e:
            print(f"[Receiver] ❌ Server error: {e}")
            self.status_changed.emit(f"Error: {e}")
        finally:
            server.close()
            print("[Receiver] Server shut down.")

    def _recv_exact(self, conn, size):
        """Receive exactly `size` bytes (handles partial reads)."""
        data = b""
        while len(data) < size:
            try:
                chunk = conn.recv(min(size - len(data), 65536))
            except socket.timeout:
                if not self._running:
                    return None
                continue
            if not chunk:
                return None  # Connection closed
            data += chunk
        return data

    def stop(self):
        """Signal the thread to stop."""
        self._running = False
