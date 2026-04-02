"""
FisTransfer — Screen Capture Test
====================================
Tests the screen capture pipeline independently.
Captures a screenshot, saves it, and prints timing info.

Usage:
    python tests/test_capture.py
"""

import sys
import os
import time

import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mac.screen_capture import ScreenCapture


def main():
    print("=" * 60)
    print("  FisTransfer — Screen Capture Test")
    print("=" * 60)
    print()

    capture = ScreenCapture()

    # ── Run 5 capture cycles to get timing averages ──────────────────────
    timings_list = []
    for i in range(5):
        jpeg_bytes, timings = capture.capture()
        timings_list.append(timings)
        print(f"  Capture {i+1}: {timings}")

    # ── Save the last capture to verify quality ──────────────────────────
    output_path = os.path.join(os.path.dirname(__file__), "..", "test_capture_output.jpg")
    with open(output_path, "wb") as f:
        f.write(jpeg_bytes)

    # ── Print averages ───────────────────────────────────────────────────
    print()
    print("-" * 50)
    if timings_list and "total_ms" in timings_list[0]:
        avg_total = sum(t["total_ms"] for t in timings_list) / len(timings_list)
        avg_grab = sum(t["grab_ms"] for t in timings_list) / len(timings_list)
        avg_resize = sum(t["resize_ms"] for t in timings_list) / len(timings_list)
        avg_encode = sum(t["encode_ms"] for t in timings_list) / len(timings_list)
        avg_size = sum(t["size_kb"] for t in timings_list) / len(timings_list)

        print(f"  Average grab:    {avg_grab:.1f}ms")
        print(f"  Average resize:  {avg_resize:.1f}ms")
        print(f"  Average encode:  {avg_encode:.1f}ms")
        print(f"  Average total:   {avg_total:.1f}ms")
        print(f"  Average size:    {avg_size:.1f} KB")
        print()

        target = 55.0
        if avg_total < target:
            print(f"  ✅ PASS — Average {avg_total:.1f}ms is under {target}ms target!")
        else:
            print(f"  ⚠ SLOW — Average {avg_total:.1f}ms exceeds {target}ms target.")
            print(f"  Try lowering JPEG_QUALITY or TARGET resolution in config.py")

    print(f"\n  Saved test screenshot to: {os.path.abspath(output_path)}")
    print("-" * 50)

    capture.release()


if __name__ == "__main__":
    main()
