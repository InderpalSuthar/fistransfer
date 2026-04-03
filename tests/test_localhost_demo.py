"""
FisTransfer — Localhost Demo
================================
Runs BOTH Mac sender and Windows receiver on the SAME machine
to demonstrate the full handshake flow without needing two laptops.

Usage:
    python tests/test_localhost_demo.py

Flow:
    Terminal 1: Runs this script (starts receiver in background)
    Webcam: Shows gesture detection
    1. Close fist (GRAB) → holds for 0.5s
    2. Open palm (CATCH) → holds for 0.3s  
    3. Screenshot transfers and pops up!
"""

import socket
import struct
import threading
import time
import sys
import os

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mac.gesture_engine import GestureEngine
from mac.screen_capture import ScreenCapture
from config import (
    SIGNAL_PORT,
    TRANSFER_PORT,
    SOCKET_BUFFER_SIZE,
    SIGNAL_GRAB_READY,
    SIGNAL_CATCH_ACCEPT,
    HANDSHAKE_TIMEOUT,
    ENABLE_PROFILING,
)

HOST = "127.0.0.1"


class LocalhostDemo:
    """Full handshake demo on a single machine."""

    def __init__(self):
        self.gesture = GestureEngine()
        self.capture = ScreenCapture()

        # State
        self.state = "IDLE"  # IDLE → GRABBED → WAITING_CATCH → TRANSFERRING
        self.grab_confirmed_time = 0
        self.received_image = None
        self.image_display_time = 0

        # Background threads
        self._running = True
        self._grab_received = threading.Event()
        self._catch_received = threading.Event()

    def _signal_listener(self):
        """Listens for both GRAB and CATCH signals on localhost."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.settimeout(1.0)
        server.bind((HOST, SIGNAL_PORT))
        server.listen(2)

        while self._running:
            try:
                conn, _ = server.accept()
                data = conn.recv(64)
                conn.close()

                if data == SIGNAL_GRAB_READY:
                    print("  📨 [Receiver] Got GRAB signal!")
                    self._grab_received.set()
                elif data == SIGNAL_CATCH_ACCEPT:
                    print("  📨 [Sender] Got CATCH signal!")
                    self._catch_received.set()
            except socket.timeout:
                continue
        server.close()

    def _transfer_listener(self):
        """Listens for image data on localhost."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.settimeout(1.0)
        server.bind((HOST, TRANSFER_PORT))
        server.listen(1)

        while self._running:
            try:
                conn, _ = server.accept()
            except socket.timeout:
                continue

            conn.settimeout(5.0)
            try:
                header = b""
                while len(header) < 4:
                    chunk = conn.recv(4 - len(header))
                    if not chunk:
                        break
                    header += chunk

                if len(header) == 4:
                    img_size = struct.unpack(">L", header)[0]
                    data = b""
                    while len(data) < img_size:
                        chunk = conn.recv(min(img_size - len(data), 65536))
                        if not chunk:
                            break
                        data += chunk

                    if len(data) == img_size:
                        arr = np.frombuffer(data, dtype=np.uint8)
                        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                        if img is not None:
                            self.received_image = img
                            self.image_display_time = time.time()
                            print(f"  🎯 [Receiver] Image caught! ({img.shape[1]}×{img.shape[0]})")
            except Exception as e:
                print(f"  [Transfer] Error: {e}")
            finally:
                conn.close()
        server.close()

    def _send_signal(self, signal_bytes):
        """Send a signal over localhost."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            sock.connect((HOST, SIGNAL_PORT))
            sock.sendall(signal_bytes)
            sock.close()
            return True
        except Exception as e:
            print(f"  Signal error: {e}")
            return False

    def _send_image(self, jpeg_bytes):
        """Send image over localhost."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.settimeout(5.0)
            sock.connect((HOST, TRANSFER_PORT))
            header = struct.pack(">L", len(jpeg_bytes))
            sock.sendall(header + jpeg_bytes)
            sock.close()
            return True
        except Exception as e:
            print(f"  Send error: {e}")
            return False

    def run(self):
        print("=" * 60)
        print("  FisTransfer — Localhost Demo")
        print("  Full handshake on a single machine!")
        print("=" * 60)
        print()
        print("  Steps:")
        print("    1. 🤜 Close your FIST and hold 0.5s → GRAB")
        print("    2. 🖐  Open your PALM and hold 0.3s → CATCH")
        print("    3. 📸 Screenshot transfers automatically!")
        print()
        print("  Press q to quit")
        print()

        # Start background services
        threading.Thread(target=self._signal_listener, daemon=True).start()
        time.sleep(0.2)
        threading.Thread(target=self._transfer_listener, daemon=True).start()
        time.sleep(0.2)

        # Open webcam
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[Error] Cannot open webcam!")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        print("[Demo] Webcam ready. Close your fist to start!\n")

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame = cv2.flip(frame, 1)
                result, annotated = self.gesture.process_frame(frame)

                # ── State machine ────────────────────────────────────
                if self.state == "IDLE":
                    cv2.putText(annotated, "Step 1: Close your FIST",
                                (10, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

                    if result["grab_confirmed"]:
                        print("  🤜 GRAB CONFIRMED!")
                        self._send_signal(SIGNAL_GRAB_READY)
                        self.state = "GRABBED"
                        self.grab_confirmed_time = time.time()

                elif self.state == "GRABBED":
                    # Wait a moment then prompt for catch
                    if self._grab_received.is_set():
                        self._grab_received.clear()
                        self.state = "WAITING_CATCH"
                        print("  🖐 Now show your OPEN PALM to catch!")

                elif self.state == "WAITING_CATCH":
                    remaining = max(0, HANDSHAKE_TIMEOUT - (time.time() - self.grab_confirmed_time))

                    cv2.rectangle(annotated, (5, 120), (635, 175), (0, 80, 0), -1)
                    cv2.putText(annotated, f"Step 2: Show OPEN PALM to catch! [{remaining:.0f}s]",
                                (10, 155), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)

                    if result["catch_confirmed"]:
                        print("  🖐 CATCH CONFIRMED! Transferring...")
                        self._send_signal(SIGNAL_CATCH_ACCEPT)
                        self.state = "TRANSFERRING"

                    elif remaining <= 0:
                        print("  ⏰ Timeout!")
                        self.state = "IDLE"
                        self.gesture.mark_transfer_complete()

                elif self.state == "TRANSFERRING":
                    if self._catch_received.is_set():
                        self._catch_received.clear()

                        # Capture and send
                        t0 = time.perf_counter()
                        jpeg_bytes, timing = self.capture.capture()
                        self._send_image(jpeg_bytes)
                        t1 = time.perf_counter()

                        print(f"  📸 Captured & sent in {round((t1-t0)*1000,1)}ms")
                        print(f"     {timing}")

                        self.state = "DONE"
                        self.gesture.mark_transfer_complete()

                elif self.state == "DONE":
                    cv2.rectangle(annotated, (5, 120), (635, 175), (0, 100, 0), -1)
                    cv2.putText(annotated, "Transfer complete! Check the other window.",
                                (10, 155), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)

                    # Auto-reset after 3s
                    if time.time() - self.image_display_time > 3:
                        self.state = "IDLE"

                # ── Show received image ──────────────────────────────
                if self.received_image is not None:
                    img = self.received_image
                    h, w = img.shape[:2]
                    scale = min(1280 / w, 720 / h, 1.0)
                    display = cv2.resize(img, (int(w * scale), int(h * scale)))
                    cv2.imshow("FisTransfer — Caught Screenshot!", display)
                    self.received_image = None

                cv2.imshow("FisTransfer — Localhost Demo", annotated)

                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break

        except KeyboardInterrupt:
            pass
        finally:
            self._running = False
            cap.release()
            cv2.destroyAllWindows()
            self.gesture.release()
            self.capture.release()
            print("\n[Demo] Done!")


def main():
    demo = LocalhostDemo()
    demo.run()


if __name__ == "__main__":
    main()
