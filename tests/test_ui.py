"""
FisTransfer — UI Catch Test
===============================
Tests the PyQt6 catch window with a synthetic image.
Run this on the Windows side to verify the animation independently.

Usage:
    python tests/test_ui.py
"""

import sys
import os

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from win.catch_window import CatchWindow


def create_test_image(width=1920, height=1080):
    """Create a visually rich test image."""
    img = np.zeros((height, width, 3), dtype=np.uint8)

    # ── Background gradient ──────────────────────────────────────────────
    for y in range(height):
        ratio = y / height
        img[y, :, 0] = int(30 + 60 * ratio)       # Blue
        img[y, :, 1] = int(20 + 40 * (1 - ratio))  # Green
        img[y, :, 2] = int(80 + 100 * ratio)       # Red

    # ── Central banner ───────────────────────────────────────────────────
    banner_y1, banner_y2 = height // 3, 2 * height // 3
    cv2.rectangle(img, (100, banner_y1), (width - 100, banner_y2),
                  (40, 40, 50), -1)
    cv2.rectangle(img, (100, banner_y1), (width - 100, banner_y2),
                  (100, 200, 255), 3)

    # ── Title text ───────────────────────────────────────────────────────
    cv2.putText(
        img, "FisTransfer",
        (width // 2 - 300, height // 2 - 30),
        cv2.FONT_HERSHEY_SIMPLEX, 3.0, (255, 255, 255), 5,
    )
    cv2.putText(
        img, "Screen Caught Successfully!",
        (width // 2 - 350, height // 2 + 50),
        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (100, 200, 255), 3,
    )

    # ── Corner decorations ───────────────────────────────────────────────
    for cx, cy in [(150, 150), (width-150, 150),
                    (150, height-150), (width-150, height-150)]:
        cv2.circle(img, (cx, cy), 40, (100, 200, 255), 3)
        cv2.circle(img, (cx, cy), 15, (255, 200, 100), -1)

    # ── Info text ────────────────────────────────────────────────────────
    cv2.putText(
        img, f"{width}x{height} | Test Image",
        (width // 2 - 200, height - 80),
        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (150, 150, 150), 2,
    )

    return img


def main():
    print("=" * 60)
    print("  FisTransfer — UI Catch Test")
    print("=" * 60)
    print()
    print("  A test image will slide in from the left.")
    print("  It will auto-dismiss after 5 seconds.")
    print("  Double-click to dismiss early.")
    print("  A second image will appear 2 seconds after the first.")
    print()

    app = QApplication(sys.argv)
    window = CatchWindow()

    # ── First image: appears immediately ─────────────────────────────────
    test_img_1 = create_test_image(1920, 1080)
    QTimer.singleShot(500, lambda: window.catch_image(test_img_1))

    # ── Second image: appears 8 seconds later (after first auto-dismisses)
    test_img_2 = create_test_image(1280, 720)
    cv2.putText(test_img_2, "Image #2", (50, 100),
                cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 255, 255), 4)
    QTimer.singleShot(8000, lambda: window.catch_image(test_img_2))

    # ── Auto-quit after 15 seconds ───────────────────────────────────────
    QTimer.singleShot(15000, app.quit)

    print("[Test] Running... (auto-quits in 15 seconds)")
    app.exec()
    print("[Test] Done!")


if __name__ == "__main__":
    main()
