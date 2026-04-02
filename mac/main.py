"""
FisTransfer — Mac Entry Point
================================
Ties together: Webcam → Gesture Engine → Screen Capture → TCP Send.

Usage:
    python -m mac.main

Controls:
    q — Quit
    d — Toggle debug overlay
    t — Test send (capture + send without gesture)
"""

import time
import cv2

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mac.gesture_engine import GestureEngine
from mac.screen_capture import ScreenCapture
from mac.sender import Sender
from config import ENABLE_PROFILING


def main():
    print("=" * 60)
    print("  FisTransfer — Mac Sender")
    print("  Grab the screen with your hand and THROW it!")
    print("=" * 60)
    print()
    print("  Controls:")
    print("    q — Quit")
    print("    t — Test send (capture + send without gesture)")
    print()

    # ── Initialize components ────────────────────────────────────────────────
    gesture = GestureEngine()
    capture = ScreenCapture()
    sender = Sender()

    # ── Open webcam ──────────────────────────────────────────────────────────
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[Error] Cannot open webcam!")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)

    print("[Mac] Webcam opened. Starting gesture detection loop...")
    print("[Mac] Connecting to receiver...")
    sender.connect()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[Error] Failed to read webcam frame.")
                break

            # ── Mirror the frame (more intuitive for gestures) ───────────
            frame = cv2.flip(frame, 1)

            # ── Process gesture ──────────────────────────────────────────
            triggered, annotated, debug = gesture.process_frame(frame)

            if triggered:
                print()
                print("=" * 50)
                print("  🤜 THROW DETECTED!")
                print("=" * 50)

                # ── Capture screen ───────────────────────────────────────
                t_start = time.perf_counter()
                jpeg_bytes, cap_timing = capture.capture()

                # ── Send to Windows ──────────────────────────────────────
                send_timing = sender.send_image(jpeg_bytes)
                t_end = time.perf_counter()

                total_ms = round((t_end - t_start) * 1000, 1)

                if ENABLE_PROFILING:
                    print(f"  📸 Capture: {cap_timing}")
                    print(f"  📡 Send:    {send_timing}")
                    print(f"  ⏱  Total:   {total_ms}ms")
                print()

            # ── Show webcam preview ──────────────────────────────────────
            cv2.imshow("FisTransfer — Gesture Monitor", annotated)

            # ── Keyboard controls ────────────────────────────────────────
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                print("[Mac] Quitting...")
                break
            elif key == ord("t"):
                # Test send without gesture
                print("[Mac] Test send...")
                jpeg_bytes, cap_timing = capture.capture()
                send_timing = sender.send_image(jpeg_bytes)
                if ENABLE_PROFILING:
                    print(f"  📸 Capture: {cap_timing}")
                    print(f"  📡 Send:    {send_timing}")

    except KeyboardInterrupt:
        print("\n[Mac] Interrupted by user.")

    finally:
        # ── Cleanup ──────────────────────────────────────────────────────
        cap.release()
        cv2.destroyAllWindows()
        gesture.release()
        capture.release()
        sender.disconnect()
        print("[Mac] Shutdown complete.")


if __name__ == "__main__":
    main()
