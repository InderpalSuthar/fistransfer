"""
FisTransfer — Gesture Test (Sprint 2)
========================================
Runs the webcam and gesture engine to tune thresholds.
Logs gesture events to the console.

Usage:
    python tests/test_gesture.py

Controls:
    q — Quit
    g — Print current grab threshold info
"""

import sys
import os
import time

import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mac.gesture_engine import GestureEngine
from config import GRAB_THRESHOLD, SWIPE_VELOCITY_THRESHOLD, SWIPE_DIRECTION


def main():
    print("=" * 60)
    print("  FisTransfer — Gesture Tuning Mode")
    print("=" * 60)
    print()
    print(f"  Grab threshold:     {GRAB_THRESHOLD}")
    print(f"  Swipe threshold:    {SWIPE_VELOCITY_THRESHOLD}")
    print(f"  Swipe direction:    {SWIPE_DIRECTION}")
    print()
    print("  Controls:")
    print("    q — Quit")
    print("    g — Print debug info")
    print()

    engine = GestureEngine()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[Error] Cannot open webcam!")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    throw_count = 0
    fps_start = time.time()
    frame_count = 0
    current_fps = 0.0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            triggered, annotated, debug = engine.process_frame(frame)

            # FPS counter
            frame_count += 1
            elapsed = time.time() - fps_start
            if elapsed > 1.0:
                current_fps = frame_count / elapsed
                frame_count = 0
                fps_start = time.time()

            cv2.putText(
                annotated, f"FPS: {current_fps:.0f}",
                (500, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 255, 100), 2,
            )

            if triggered:
                throw_count += 1
                print(f"  🤜 THROW #{throw_count} DETECTED! {debug}")

            cv2.imshow("FisTransfer — Gesture Test", annotated)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("g"):
                print(f"  [Debug] {debug}")

    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        cv2.destroyAllWindows()
        engine.release()

    print(f"\n  Total throws detected: {throw_count}")


if __name__ == "__main__":
    main()
