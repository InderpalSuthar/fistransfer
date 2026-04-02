"""
FisTransfer — Gesture Test (Both GRAB + CATCH)
=================================================
Tests both gesture types on a single machine.

Usage:
    python tests/test_gesture.py

Controls:
    q — Quit
    g — Print debug info
"""

import sys
import os
import time

import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mac.gesture_engine import GestureEngine
from config import GRAB_THRESHOLD, CATCH_THRESHOLD


def main():
    print("=" * 60)
    print("  FisTransfer — Gesture Test (GRAB + CATCH)")
    print("=" * 60)
    print()
    print(f"  Grab threshold:  {GRAB_THRESHOLD} (closed fist)")
    print(f"  Catch threshold: {CATCH_THRESHOLD} (open palm)")
    print()
    print("  Try these gestures:")
    print("    🤜 Close your fist   → should show GRABBED")
    print("    🖐  Open your palm    → should show OPEN PALM")
    print("    ✊ Hold fist 0.5s    → should show GRAB READY")
    print("    🖐  Hold palm 0.3s   → should show CATCH!")
    print()

    engine = GestureEngine()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[Error] Cannot open webcam!")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    grab_count = 0
    catch_count = 0
    fps_start = time.time()
    frame_count = 0
    current_fps = 0.0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            result, annotated = engine.process_frame(frame)

            # FPS counter
            frame_count += 1
            elapsed = time.time() - fps_start
            if elapsed > 1.0:
                current_fps = frame_count / elapsed
                frame_count = 0
                fps_start = time.time()

            cv2.putText(
                annotated, f"FPS: {current_fps:.0f}",
                (530, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 255, 100), 2,
            )

            # Count events
            if result["grab_confirmed"]:
                grab_count += 1
                print(f"  🤜 GRAB #{grab_count} CONFIRMED!")
                engine.mark_transfer_complete()

            if result["catch_confirmed"]:
                catch_count += 1
                print(f"  🖐 CATCH #{catch_count} CONFIRMED!")
                engine.mark_transfer_complete()

            # Stats bar
            cv2.putText(
                annotated, f"Grabs: {grab_count} | Catches: {catch_count}",
                (10, 470), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1,
            )

            cv2.imshow("FisTransfer — Gesture Test", annotated)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("g"):
                print(f"  [Debug] {result}")

    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        cv2.destroyAllWindows()
        engine.release()

    print(f"\n  Grabs: {grab_count} | Catches: {catch_count}")


if __name__ == "__main__":
    main()
