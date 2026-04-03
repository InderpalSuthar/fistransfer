"""
FisTransfer — Screen Capture
==============================
High-speed screen capture using mss, with downscale and JPEG compression.
Target: full capture pipeline in < 55ms.
"""

import time

import cv2
import numpy as np
import mss

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import (
    JPEG_QUALITY,
    TARGET_WIDTH,
    TARGET_HEIGHT,
    ENABLE_PROFILING,
)


class ScreenCapture:
    """Captures the screen, downscales, and compresses to JPEG."""

    def __init__(self):
        self.sct = mss.mss()
        # Capture the primary monitor (index 1 = first real monitor)
        self.monitor = self.sct.monitors[1]

    def capture(self):
        """
        Grab the screen → resize → compress → return JPEG bytes.

        Returns
        -------
        jpeg_bytes : bytes
            Raw JPEG-compressed image data, ready to send over the wire.
        timings : dict
            Per-stage timing in milliseconds (only if ENABLE_PROFILING).
        """
        timings = {}

        # ── 1. Screen grab ───────────────────────────────────────────────────
        t0 = time.perf_counter()
        raw = self.sct.grab(self.monitor)
        t1 = time.perf_counter()

        # mss returns BGRA — convert to numpy BGR
        frame = np.array(raw)
        frame = frame[:, :, :3]  # Drop alpha channel (BGRA → BGR)
        t2 = time.perf_counter()

        # ── 2. Downscale to target resolution (skip if 0 = native) ────────
        if TARGET_WIDTH > 0 and TARGET_HEIGHT > 0:
            frame = cv2.resize(
                frame, (TARGET_WIDTH, TARGET_HEIGHT),
                interpolation=cv2.INTER_AREA,
            )
        t3 = time.perf_counter()

        # ── 3. JPEG compression ──────────────────────────────────────────────
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
        success, jpeg_buf = cv2.imencode(".jpg", frame, encode_params)
        t4 = time.perf_counter()

        if not success:
            raise RuntimeError("JPEG encoding failed")

        jpeg_bytes = jpeg_buf.tobytes()

        if ENABLE_PROFILING:
            timings = {
                "grab_ms": round((t1 - t0) * 1000, 1),
                "convert_ms": round((t2 - t1) * 1000, 1),
                "resize_ms": round((t3 - t2) * 1000, 1),
                "encode_ms": round((t4 - t3) * 1000, 1),
                "total_ms": round((t4 - t0) * 1000, 1),
                "size_kb": round(len(jpeg_bytes) / 1024, 1),
            }

        return jpeg_bytes, timings

    def release(self):
        """Release mss resources."""
        self.sct.close()
