"""
FisTransfer — Windows Entry Point (Handshake Mode)
=====================================================
Flow:
  1. Listens for GRAB_READY signal from Mac
  2. Shows "Mac wants to send!" prompt
  3. Windows user does CATCH gesture (open palm)
  4. Sends CATCH_OK signal back to Mac
  5. Receives image and shows catch animation

Usage:
    python -m win

Controls:
    q — Quit
"""

import socket
import struct
import threading
import time

import cv2
import numpy as np

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import (
    MAC_IP,
    SIGNAL_PORT,
    TRANSFER_PORT,
    SOCKET_BUFFER_SIZE,
    SIGNAL_GRAB_READY,
    SIGNAL_CATCH_ACCEPT,
    HANDSHAKE_TIMEOUT,
    ENABLE_PROFILING,
)

# ── Import gesture engine from mac package (same code) ───────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mac"))
from gesture_engine import GestureEngine


class WinApp:
    """Windows-side FisTransfer application (console + OpenCV UI)."""

    def __init__(self):
        self.gesture = GestureEngine()
        self._grab_signal_received = threading.Event()
        self._listener_running = True
        self._received_image = None
        self._image_lock = threading.Lock()

    def _start_signal_listener(self):
        """Background thread: listens for GRAB_READY signals from Mac."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.settimeout(1.0)

        try:
            server.bind(("0.0.0.0", SIGNAL_PORT))
            server.listen(1)
            print(f"[Win] 🔊 Listening for grab signals on port {SIGNAL_PORT}")

            while self._listener_running:
                try:
                    conn, addr = server.accept()
                    data = conn.recv(64)
                    conn.close()

                    if data == SIGNAL_GRAB_READY:
                        print(f"\n[Win] 🤜 GRAB signal from Mac ({addr[0]})!")
                        print("[Win] 🖐  Show your OPEN PALM to catch!")
                        self._grab_signal_received.set()

                except socket.timeout:
                    continue
        except OSError as e:
            print(f"[Win] Signal listener error: {e}")
        finally:
            server.close()

    def _start_transfer_listener(self):
        """Background thread: listens for image data after handshake."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, SOCKET_BUFFER_SIZE)
        server.settimeout(1.0)

        try:
            server.bind(("0.0.0.0", TRANSFER_PORT))
            server.listen(1)
            print(f"[Win] 🔊 Listening for transfers on port {TRANSFER_PORT}")

            while self._listener_running:
                try:
                    conn, addr = server.accept()
                except socket.timeout:
                    continue

                conn.settimeout(5.0)
                try:
                    # Read 4-byte header
                    header = self._recv_exact(conn, 4)
                    if header is None:
                        conn.close()
                        continue

                    img_size = struct.unpack(">L", header)[0]
                    if img_size == 0 or img_size > 50_000_000:
                        conn.close()
                        continue

                    t0 = time.perf_counter()
                    img_data = self._recv_exact(conn, img_size)
                    t1 = time.perf_counter()

                    if img_data:
                        jpg_arr = np.frombuffer(img_data, dtype=np.uint8)
                        image = cv2.imdecode(jpg_arr, cv2.IMREAD_COLOR)
                        t2 = time.perf_counter()

                        if image is not None:
                            if ENABLE_PROFILING:
                                print(f"[Win] 📥 Received {img_size/1024:.1f}KB"
                                      f" | recv={round((t1-t0)*1000,1)}ms"
                                      f" | decode={round((t2-t1)*1000,1)}ms")

                            with self._image_lock:
                                self._received_image = image
                            print("[Win] 🎯 Image caught!")

                except (socket.timeout, OSError) as e:
                    print(f"[Win] Transfer error: {e}")
                finally:
                    conn.close()

        except OSError as e:
            print(f"[Win] Transfer listener error: {e}")
        finally:
            server.close()

    def _recv_exact(self, conn, size):
        """Receive exactly `size` bytes."""
        data = b""
        while len(data) < size:
            try:
                chunk = conn.recv(min(size - len(data), 65536))
            except socket.timeout:
                return None
            if not chunk:
                return None
            data += chunk
        return data

    def _send_catch_signal(self):
        """Send CATCH_OK signal to Mac."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3.0)
            sock.connect((MAC_IP, SIGNAL_PORT))
            sock.sendall(SIGNAL_CATCH_ACCEPT)
            sock.close()
            print(f"[Win] 🖐 CATCH signal sent to Mac!")
            return True
        except (ConnectionRefusedError, socket.timeout, OSError) as e:
            print(f"[Win] ❌ Failed to send catch signal: {e}")
            return False

    def _show_received_image(self):
        """Display the received image in a large window."""
        with self._image_lock:
            if self._received_image is None:
                return
            image = self._received_image.copy()
            self._received_image = None

        # Show in a named window
        h, w = image.shape[:2]
        # Scale to fit screen (max 80% of 1920x1080)
        max_w, max_h = 1536, 864
        scale = min(max_w / w, max_h / h, 1.0)
        if scale < 1.0:
            image = cv2.resize(image, (int(w * scale), int(h * scale)))

        cv2.namedWindow("FisTransfer — Caught!", cv2.WINDOW_NORMAL)
        cv2.imshow("FisTransfer — Caught!", image)
        print("[Win] 📺 Image displayed! Press any key on the image to close.")

    def run(self):
        print("=" * 60)
        print("  FisTransfer — Windows Receiver (Handshake Mode)")
        print("  Mac GRABs → You CATCH with open palm!")
        print("=" * 60)
        print()
        print("  How it works:")
        print("    1. Mac user closes fist (GRAB)")
        print("    2. You see 'Mac wants to send!' prompt")
        print("    3. Show your OPEN PALM to the webcam (CATCH)")
        print("    4. Screenshot transfers and appears!")
        print()
        print("  Controls: q=Quit")
        print()

        # Start listeners
        signal_thread = threading.Thread(target=self._start_signal_listener, daemon=True)
        signal_thread.start()

        transfer_thread = threading.Thread(target=self._start_transfer_listener, daemon=True)
        transfer_thread.start()

        # Open webcam
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[Error] Cannot open webcam!")
            print("[Win] Running in headless mode (no gesture, manual catch only)")
            self._run_headless()
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        print("[Win] Webcam opened. Waiting for Mac to GRAB...")

        waiting_for_catch = False
        grab_received_time = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame = cv2.flip(frame, 1)
                result, annotated = self.gesture.process_frame(frame)

                # ── Check for incoming grab signal ───────────────────
                if self._grab_signal_received.is_set() and not waiting_for_catch:
                    waiting_for_catch = True
                    grab_received_time = time.time()
                    self._grab_signal_received.clear()

                # ── State machine ────────────────────────────────────
                if waiting_for_catch:
                    elapsed = time.time() - grab_received_time
                    remaining = max(0, HANDSHAKE_TIMEOUT - elapsed)

                    # Prompt overlay
                    cv2.rectangle(annotated, (5, 120), (635, 180), (0, 0, 0), -1)
                    cv2.putText(
                        annotated, f"Mac wants to send! Show OPEN PALM [{remaining:.0f}s]",
                        (10, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2,
                    )

                    if result["catch_confirmed"]:
                        print("\n  🖐 CATCH CONFIRMED! Accepting transfer...")
                        self._send_catch_signal()
                        waiting_for_catch = False
                        self.gesture.mark_transfer_complete()

                    elif elapsed > HANDSHAKE_TIMEOUT:
                        print("  ⏰ Timeout! Mac's grab expired.")
                        waiting_for_catch = False
                        self.gesture.mark_transfer_complete()

                else:
                    cv2.putText(
                        annotated, "Waiting for Mac to GRAB...",
                        (10, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 1,
                    )

                # ── Check for received image ─────────────────────────
                with self._image_lock:
                    has_image = self._received_image is not None

                if has_image:
                    self._show_received_image()

                cv2.imshow("FisTransfer — Windows (CATCH to receive)", annotated)

                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break

        except KeyboardInterrupt:
            print("\n[Win] Interrupted.")
        finally:
            self._listener_running = False
            cap.release()
            cv2.destroyAllWindows()
            self.gesture.release()
            print("[Win] Shutdown complete.")

    def _run_headless(self):
        """Fallback mode without webcam — auto-accepts all grabs."""
        print("[Win] Headless mode: auto-accepting all grab signals.")
        try:
            while True:
                if self._grab_signal_received.wait(timeout=1.0):
                    self._grab_signal_received.clear()
                    print("[Win] Auto-accepting grab signal...")
                    time.sleep(0.5)
                    self._send_catch_signal()

                    # Wait for image
                    for _ in range(50):
                        time.sleep(0.1)
                        with self._image_lock:
                            if self._received_image is not None:
                                h, w = self._received_image.shape[:2]
                                out = f"received_{int(time.time())}.jpg"
                                cv2.imwrite(out, self._received_image)
                                self._received_image = None
                                print(f"[Win] 💾 Saved: {out} ({w}×{h})")
                                break
        except KeyboardInterrupt:
            print("\n[Win] Interrupted.")
            self._listener_running = False


def main():
    app = WinApp()
    app.run()


if __name__ == "__main__":
    main()
