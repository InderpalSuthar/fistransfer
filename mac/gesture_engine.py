"""
FisTransfer — Gesture Engine
==============================
Detects "Grab and Swipe" gestures using MediaPipe HandLandmarker (Tasks API).

Grab:  Thumb tip (LM4) close to Index tip (LM8), normalized by hand size.
Swipe: Simple Moving Average of palm X-coordinate velocity.
"""

import math
import os
import time
from collections import deque

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    HandLandmarker,
    HandLandmarkerOptions,
    HandLandmarksConnections,
    RunningMode,
)

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import (
    GRAB_THRESHOLD,
    SWIPE_VELOCITY_THRESHOLD,
    SMA_WINDOW,
    SWIPE_DIRECTION,
    COOLDOWN_SECONDS,
    ENABLE_PROFILING,
)

# ── Resolve model path ──────────────────────────────────────────────────────
_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "models", "hand_landmarker.task"
)

# ── Pre-build the connection set for drawing ─────────────────────────────────
_HAND_CONNECTIONS = HandLandmarksConnections.HAND_CONNECTIONS


class GestureEngine:
    """Detects a 'grab + swipe' gesture from webcam frames."""

    def __init__(self):
        # ── MediaPipe Tasks API setup ────────────────────────────────────
        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=_MODEL_PATH),
            running_mode=RunningMode.VIDEO,
            num_hands=1,                         # Single hand = less CPU
            min_hand_detection_confidence=0.7,
            min_tracking_confidence=0.6,
        )
        self.detector = HandLandmarker.create_from_options(options)
        self._frame_ts = 0  # Monotonic timestamp for VIDEO mode

        # ── State ────────────────────────────────────────────────────────
        self.is_grabbed = False
        self.x_history = deque(maxlen=SMA_WINDOW)
        self.last_trigger_time = 0.0

    # ── Landmark helpers ─────────────────────────────────────────────────

    @staticmethod
    def _distance(lm_a, lm_b):
        """Euclidean distance between two NormalizedLandmark objects."""
        return math.sqrt(
            (lm_a.x - lm_b.x) ** 2
            + (lm_a.y - lm_b.y) ** 2
            + (lm_a.z - lm_b.z) ** 2
        )

    def _hand_size(self, landmarks):
        """Reference distance: wrist (LM0) → middle-finger MCP (LM9).
        Used to normalize grab distance so it works at any webcam distance."""
        return self._distance(landmarks[0], landmarks[9])

    def _grab_distance(self, landmarks):
        """Distance between thumb tip (LM4) and index tip (LM8), normalized."""
        raw = self._distance(landmarks[4], landmarks[8])
        size = self._hand_size(landmarks)
        if size < 1e-6:
            return 1.0  # Avoid division by zero
        return raw / size

    def _palm_x(self, landmarks):
        """X-coordinate of the palm center (LM9 — middle-finger MCP)."""
        return landmarks[9].x

    # ── Velocity via SMA ─────────────────────────────────────────────────

    def _compute_velocity(self):
        """Simple Moving Average velocity over the X-position history."""
        if len(self.x_history) < 3:
            return 0.0
        return (self.x_history[-1] - self.x_history[0]) / len(self.x_history)

    # ── Draw landmarks on frame ──────────────────────────────────────────

    @staticmethod
    def _draw_landmarks(frame, landmarks):
        """Draw hand landmarks and connections onto a BGR frame."""
        h, w, _ = frame.shape

        # Draw connections
        for conn in _HAND_CONNECTIONS:
            start = landmarks[conn.start]
            end = landmarks[conn.end]
            pt1 = (int(start.x * w), int(start.y * h))
            pt2 = (int(end.x * w), int(end.y * h))
            cv2.line(frame, pt1, pt2, (0, 255, 0), 2)

        # Draw landmark points
        for lm in landmarks:
            cx, cy = int(lm.x * w), int(lm.y * h)
            cv2.circle(frame, (cx, cy), 5, (255, 0, 0), -1)

    # ── Main processing ──────────────────────────────────────────────────

    def process_frame(self, bgr_frame):
        """
        Process a single BGR webcam frame.

        Returns
        -------
        (triggered: bool, annotated_frame: ndarray, debug_info: dict)
        """
        triggered = False
        debug = {
            "grabbed": False,
            "grab_dist": None,
            "velocity": 0.0,
            "hand_detected": False,
        }

        # Convert BGR → RGB for MediaPipe
        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        # Detect with monotonically increasing timestamp
        self._frame_ts += 33  # ~30 FPS in milliseconds
        results = self.detector.detect_for_video(mp_image, self._frame_ts)

        if results.hand_landmarks:
            lm = results.hand_landmarks[0]  # First (only) hand
            debug["hand_detected"] = True

            # ── Draw landmarks on frame ──────────────────────────────
            self._draw_landmarks(bgr_frame, lm)

            # ── Grab detection ───────────────────────────────────────
            grab_dist = self._grab_distance(lm)
            self.is_grabbed = grab_dist < GRAB_THRESHOLD
            debug["grabbed"] = self.is_grabbed
            debug["grab_dist"] = round(grab_dist, 4)

            # ── Track palm X for velocity ────────────────────────────
            self.x_history.append(self._palm_x(lm))
            velocity = self._compute_velocity()
            debug["velocity"] = round(velocity, 5)

            # ── Check trigger condition ──────────────────────────────
            now = time.time()
            cooldown_ok = (now - self.last_trigger_time) > COOLDOWN_SECONDS

            if self.is_grabbed and cooldown_ok:
                if SWIPE_DIRECTION == "left" and velocity < -SWIPE_VELOCITY_THRESHOLD:
                    triggered = True
                    self.last_trigger_time = now
                elif SWIPE_DIRECTION == "right" and velocity > SWIPE_VELOCITY_THRESHOLD:
                    triggered = True
                    self.last_trigger_time = now

            # ── Visual feedback ──────────────────────────────────────
            color = (0, 0, 255) if self.is_grabbed else (0, 255, 0)
            status = "GRABBED" if self.is_grabbed else "OPEN"
            cv2.putText(
                bgr_frame, f"{status} | dist={grab_dist:.3f}",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2,
            )
            cv2.putText(
                bgr_frame, f"Vel: {velocity:.4f}",
                (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 200, 0), 2,
            )

            if triggered:
                cv2.putText(
                    bgr_frame, ">>> THROW DETECTED <<<",
                    (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 3,
                )
        else:
            # No hand: clear history
            self.x_history.clear()
            self.is_grabbed = False

        return triggered, bgr_frame, debug

    def release(self):
        """Release MediaPipe resources."""
        self.detector.close()
