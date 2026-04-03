"""
FisTransfer — Mac Entry Point (Handshake Mode)
=================================================
Flow:
  1. Mac user does GRAB gesture (hold fist for 0.5s)
  2. Mac sends GRAB_READY signal to Windows
  3. Windows user does CATCH gesture (open palm for 0.3s)
  4. Windows sends CATCH_OK signal back to Mac
  5. Mac captures screen → compresses → sends image to Windows
  6. Windows shows catch animation

Usage:
    python -m mac

Controls:
    q — Quit
    t — Test send (bypasses gesture handshake)
"""

import socket
import struct
import threading
import time

import cv2

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mac.gesture_engine import GestureEngine
from mac.screen_capture import ScreenCapture
from config import (
    WIN_IP,
    SIGNAL_PORT,
    TRANSFER_PORT,
    SOCKET_BUFFER_SIZE,
    SIGNAL_GRAB_READY,
    SIGNAL_CATCH_ACCEPT,
    HANDSHAKE_TIMEOUT,
    ENABLE_PROFILING,
    MAC_CAMERA,
)


class MacApp:
    """Mac-side FisTransfer application."""

    def __init__(self):
        self.gesture = GestureEngine()
        self.capture = ScreenCapture()
        self.waiting_for_catch = False
        self.grab_sent_time = 0.0
        self._catch_received = threading.Event()
        self._listener_running = True

    def _start_catch_listener(self):
        """Background thread: listens for CATCH_OK signals from Windows."""
        self._listener_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listener_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listener_sock.settimeout(1.0)

        try:
            self._listener_sock.bind(("0.0.0.0", SIGNAL_PORT))
            self._listener_sock.listen(1)
            print(f"[Mac] 🔊 Listening for catch signals on port {SIGNAL_PORT}")

            while self._listener_running:
                try:
                    conn, addr = self._listener_sock.accept()
                    data = conn.recv(64)
                    conn.close()

                    if data == SIGNAL_CATCH_ACCEPT:
                        print(f"[Mac] 🖐 CATCH signal received from {addr[0]}!")
                        self._catch_received.set()

                except socket.timeout:
                    continue
        except OSError as e:
            print(f"[Mac] Listener error: {e}")
        finally:
            self._listener_sock.close()

    def _send_grab_signal(self):
        """Send GRAB_READY signal to Windows."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3.0)
            sock.connect((WIN_IP, SIGNAL_PORT))
            sock.sendall(SIGNAL_GRAB_READY)
            sock.close()
            print(f"[Mac] 🤜 GRAB signal sent to {WIN_IP}")
            return True
        except (ConnectionRefusedError, socket.timeout, OSError) as e:
            print(f"[Mac] ❌ Failed to send grab signal: {e}")
            return False

    def _send_image(self, jpeg_bytes):
        """Send the captured image to Windows over the transfer port."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, SOCKET_BUFFER_SIZE)
            sock.settimeout(5.0)
            sock.connect((WIN_IP, TRANSFER_PORT))

            header = struct.pack(">L", len(jpeg_bytes))
            t0 = time.perf_counter()
            sock.sendall(header + jpeg_bytes)
            t1 = time.perf_counter()
            sock.close()

            if ENABLE_PROFILING:
                print(f"  📡 Send: {round((t1-t0)*1000,1)}ms ({len(jpeg_bytes)/1024:.1f} KB)")
            return True
        except (ConnectionRefusedError, socket.timeout, OSError) as e:
            print(f"[Mac] ❌ Image send failed: {e}")
            return False

    def run(self):
        print("=" * 60)
        print("  FisTransfer — Mac Sender (Handshake Mode)")
        print("  GRAB your screen → Windows user CATCHES it!")
        print("=" * 60)
        print()
        print("  How it works:")
        print("    1. Close your fist (GRAB) and hold for 0.5s")
        print("    2. Wait for Windows user to show open palm (CATCH)")
        print("    3. Transfer happens automatically!")
        print()
        print("  Controls: q=Quit  t=Test send (bypass handshake)")
        print()

        # Start the catch signal listener
        listener_thread = threading.Thread(target=self._start_catch_listener, daemon=True)
        listener_thread.start()

        # Open webcam
        cap = cv2.VideoCapture(MAC_CAMERA)
        if not cap.isOpened():
            print("[Error] Cannot open webcam!")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        print("[Mac] Webcam opened. Show your fist to grab!")

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame = cv2.flip(frame, 1)
                result, annotated = self.gesture.process_frame(frame)

                # ── State machine ────────────────────────────────────────
                if not self.waiting_for_catch:
                    # STATE: Waiting for GRAB
                    if result["grab_confirmed"]:
                        print()
                        print("  🤜 GRAB CONFIRMED! Sending signal to Windows...")
                        if self._send_grab_signal():
                            self.waiting_for_catch = True
                            self.grab_sent_time = time.time()
                            self._catch_received.clear()
                            print("  ⏳ Waiting for Windows user to CATCH...")
                        else:
                            print("  ❌ Could not reach Windows. Is it running?")
                            self.gesture.mark_transfer_complete()

                else:
                    # STATE: Waiting for CATCH from Windows
                    elapsed = time.time() - self.grab_sent_time

                    # Show countdown on screen
                    remaining = max(0, HANDSHAKE_TIMEOUT - elapsed)
                    cv2.putText(
                        annotated, f"Waiting for CATCH... {remaining:.0f}s",
                        (10, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2,
                    )

                    if self._catch_received.is_set():
                        # CATCH received! Transfer!
                        print()
                        print("=" * 50)
                        print("  🎯 HANDSHAKE COMPLETE! Transferring...")
                        print("=" * 50)

                        t_start = time.perf_counter()
                        jpeg_bytes, cap_timing = self.capture.capture()
                        if ENABLE_PROFILING:
                            print(f"  📸 Capture: {cap_timing}")

                        self._send_image(jpeg_bytes)
                        t_end = time.perf_counter()

                        if ENABLE_PROFILING:
                            print(f"  ⏱  Total: {round((t_end-t_start)*1000,1)}ms")
                        print()

                        self.waiting_for_catch = False
                        self.gesture.mark_transfer_complete()

                    elif elapsed > HANDSHAKE_TIMEOUT:
                        print("  ⏰ Timeout! Windows didn't catch in time.")
                        self.waiting_for_catch = False
                        self.gesture.mark_transfer_complete()

                # Show preview
                cv2.imshow("FisTransfer — Mac (GRAB to send)", annotated)

                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break
                elif key == ord("t"):
                    print("[Mac] Test send (bypassing handshake)...")
                    jpeg_bytes, cap_timing = self.capture.capture()
                    if ENABLE_PROFILING:
                        print(f"  📸 Capture: {cap_timing}")
                    self._send_image(jpeg_bytes)

        except KeyboardInterrupt:
            print("\n[Mac] Interrupted.")
        finally:
            self._listener_running = False
            cap.release()
            cv2.destroyAllWindows()
            self.gesture.release()
            self.capture.release()
            print("[Mac] Shutdown complete.")


def main():
    app = MacApp()
    app.run()


if __name__ == "__main__":
    main()
