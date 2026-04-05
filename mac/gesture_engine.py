"""
FisTransfer — Gesture Engine
==============================
Detects TWO gestures using MediaPipe HandLandmarker (Tasks API):

  GRAB:  Closed fist — thumb tip (LM4) close to index tip (LM8)
  CATCH: Open palm  — thumb tip (LM4) far from index tip (LM8)

The same engine runs on BOTH Mac and Windows.
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
    CATCH_THRESHOLD,
    PINCH_THRESHOLD,
    PINCH_RELEASE_THRESHOLD,
    SWIPE_VELOCITY_THRESHOLD,
    SMA_WINDOW,
    COOLDOWN_SECONDS,
    ENABLE_PROFILING,
)

# ── Resolve model path ──────────────────────────────────────────────────────
# PyInstaller unpacks data to sys._MEIPASS in the compiled executable
if hasattr(sys, '_MEIPASS'):
    _MODEL_PATH = os.path.join(sys._MEIPASS, "models", "hand_landmarker.task")
else:
    _MODEL_PATH = os.path.join(
        os.path.dirname(__file__), "..", "models", "hand_landmarker.task"
    )

# ── Pre-build the connection set for drawing ─────────────────────────────────
_HAND_CONNECTIONS = HandLandmarksConnections.HAND_CONNECTIONS


class GestureEngine:
    """Detects grab (closed fist) and catch (open palm) gestures."""

    def __init__(self):
        # ── MediaPipe Tasks API setup ────────────────────────────────────
        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=_MODEL_PATH),
            running_mode=RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.detector = HandLandmarker.create_from_options(options)
        self._frame_ts = 0

        # ── State ────────────────────────────────────────────────────────
        self.is_grabbed = False
        self.is_open = False
        self.x_history = deque(maxlen=SMA_WINDOW)
        self.last_trigger_time = 0.0

        # ── Grab hold tracking ───────────────────────────────────────────
        self._grab_start_time = None
        self._grab_hold_required = 0.15  # Must hold grab for 0.15s (super snappy)
        self.grab_confirmed = False     # True when grab held long enough

        # ── Catch tracking ───────────────────────────────────────────────
        self._catch_start_time = None
        self._catch_hold_required = 0.1  # Must show open palm for 0.1s
        self.catch_confirmed = False

        # ── Pinch tracking ───────────────────────────────────────────
        self.is_pinched = False
        self._was_pinched = False       # For detecting pinch → release
        self.pinch_released = False     # True for one frame on release
        self._pinch_start_time = None
        self._pinch_hold_required = 0.1 # Must hold pinch for 0.1s
        self.pinch_confirmed = False

        # ── Cursor position ──────────────────────────────────────────
        self.cursor_x = 0.5            # Normalized index finger tip X
        self.cursor_y = 0.5            # Normalized index finger tip Y

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
        """Reference distance: wrist (LM0) → middle-finger MCP (LM9)."""
        return self._distance(landmarks[0], landmarks[9])

    def _grab_distance(self, landmarks):
        """Normalized distance between thumb tip (LM4) and index tip (LM8)."""
        raw = self._distance(landmarks[4], landmarks[8])
        size = self._hand_size(landmarks)
        if size < 1e-6:
            return 1.0
        return raw / size

    def _is_finger_folded(self, landmarks, tip_idx, mcp_idx):
        """Check if a finger is folded by comparing distance to wrist."""
        wrist = landmarks[0]
        dist_tip = self._distance(landmarks[tip_idx], wrist)
        dist_mcp = self._distance(landmarks[mcp_idx], wrist)
        # If tip is closer to wrist than the knuckle, it's folded
        return dist_tip < dist_mcp

    def _is_fist(self, landmarks):
        """Check if middle, ring, pinky are folded (grab/fist gesture)."""
        tips = [12, 16, 20]     # Middle, Ring, Pinky tips
        mcps = [9, 13, 17]      # Their MCP joints
        folded_count = sum(1 for t, m in zip(tips, mcps) if self._is_finger_folded(landmarks, t, m))
        return folded_count >= 2  # At least 2 of 3 folded = fist

    def _all_fingers_extended(self, landmarks):
        """Check if all fingers are extended (open palm)."""
        tips = [8, 12, 16, 20]     # Index, Middle, Ring, Pinky tips
        mcps = [5, 9, 13, 17]      # Their MCP joints

        extended_count = sum(1 for t, m in zip(tips, mcps) if not self._is_finger_folded(landmarks, t, m))

        # Thumb: compare x distance from wrist (works for both hands)
        thumb_tip = landmarks[4]
        thumb_mcp = landmarks[2]
        if abs(thumb_tip.x - landmarks[0].x) > abs(thumb_mcp.x - landmarks[0].x):
            extended_count += 1

        return extended_count >= 4  # At least 4 of 5 fingers extended

    def _palm_x(self, landmarks):
        """X-coordinate of the palm center (LM9)."""
        return landmarks[9].x

    # ── Velocity via SMA ─────────────────────────────────────────────────

    def _compute_velocity(self):
        if len(self.x_history) < 3:
            return 0.0
        return (self.x_history[-1] - self.x_history[0]) / len(self.x_history)

    # ── Draw landmarks ───────────────────────────────────────────────────

    @staticmethod
    def _draw_landmarks(frame, landmarks, color=(0, 255, 0)):
        h, w, _ = frame.shape
        for conn in _HAND_CONNECTIONS:
            start = landmarks[conn.start]
            end = landmarks[conn.end]
            pt1 = (int(start.x * w), int(start.y * h))
            pt2 = (int(end.x * w), int(end.y * h))
            cv2.line(frame, pt1, pt2, color, 2)
        for lm in landmarks:
            cx, cy = int(lm.x * w), int(lm.y * h)
            cv2.circle(frame, (cx, cy), 5, (255, 0, 0), -1)

    # ── Main processing ──────────────────────────────────────────────────

    def process_frame(self, bgr_frame):
        """
        Process a single BGR webcam frame.

        Returns
        -------
        result : dict with keys:
            'grab_confirmed' : bool — held grab for required duration
            'catch_confirmed': bool — held open palm for required duration
            'is_grabbed'     : bool — currently in grab state
            'is_open'        : bool — currently showing open palm
            'grab_dist'      : float — normalized thumb-index distance
            'velocity'       : float — palm X velocity
            'hand_detected'  : bool
        annotated_frame : ndarray
        """
        result = {
            "grab_confirmed": False,
            "catch_confirmed": False,
            "pinch_confirmed": False,
            "pinch_released": False,
            "is_grabbed": False,
            "is_open": False,
            "is_pinched": False,
            "grab_dist": None,
            "velocity": 0.0,
            "hand_detected": False,
            "cursor_x": 0.5,
            "cursor_y": 0.5,
        }

        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        self._frame_ts += 33
        results = self.detector.detect_for_video(mp_image, self._frame_ts)

        now = time.time()

        if results.hand_landmarks:
            lm = results.hand_landmarks[0]
            result["hand_detected"] = True

            # ── Grab distance ────────────────────────────────────────
            grab_dist = self._grab_distance(lm)
            result["grab_dist"] = round(grab_dist, 4)

            # ── Structural hand properties ───────────────────────────
            is_fist = self._is_fist(lm)

            # ── Detect GRAB (closed fist) ────────────────────────────
            # A grab is a fist (other fingers folded) where thumb/index are close.
            self.is_grabbed = (grab_dist < GRAB_THRESHOLD) and is_fist
            result["is_grabbed"] = self.is_grabbed

            if self.is_grabbed:
                if self._grab_start_time is None:
                    self._grab_start_time = now
                elif (now - self._grab_start_time) >= self._grab_hold_required:
                    if (now - self.last_trigger_time) > COOLDOWN_SECONDS:
                        self.grab_confirmed = True
                        result["grab_confirmed"] = True
            else:
                self._grab_start_time = None
                self.grab_confirmed = False

            # ── Detect CATCH (open palm) ─────────────────────────────
            fingers_open = self._all_fingers_extended(lm)
            self.is_open = fingers_open and grab_dist > CATCH_THRESHOLD
            result["is_open"] = self.is_open

            if self.is_open:
                if self._catch_start_time is None:
                    self._catch_start_time = now
                elif (now - self._catch_start_time) >= self._catch_hold_required:
                    if (now - self.last_trigger_time) > COOLDOWN_SECONDS:
                        self.catch_confirmed = True
                        result["catch_confirmed"] = True
            else:
                self._catch_start_time = None
                self.catch_confirmed = False

            # ── Detect PINCH (thumb + index very close) ──────────────
            # A pinch is thumb/index close but NOT a fist (other fingers open/relaxed).
            self.is_pinched = (grab_dist < PINCH_THRESHOLD) and not is_fist
            result["is_pinched"] = self.is_pinched

            if self.is_pinched:
                if self._pinch_start_time is None:
                    self._pinch_start_time = now
                elif (now - self._pinch_start_time) >= self._pinch_hold_required:
                    if (now - self.last_trigger_time) > COOLDOWN_SECONDS:
                        self.pinch_confirmed = True
                        result["pinch_confirmed"] = True
                self._was_pinched = True
            else:
                self._pinch_start_time = None
                # Detect release: was pinched → now open
                if self._was_pinched and grab_dist > PINCH_RELEASE_THRESHOLD:
                    self.pinch_released = True
                    result["pinch_released"] = True
                    self._was_pinched = False
                else:
                    self.pinch_released = False
                self.pinch_confirmed = False

            # ── Cursor position (index finger tip LM8) ───────────────
            self.cursor_x = lm[8].x
            self.cursor_y = lm[8].y
            result["cursor_x"] = self.cursor_x
            result["cursor_y"] = self.cursor_y

            # ── Velocity ─────────────────────────────────────────────
            self.x_history.append(self._palm_x(lm))
            velocity = self._compute_velocity()
            result["velocity"] = round(velocity, 5)

            # ── Draw ─────────────────────────────────────────────────
            if self.is_pinched:
                draw_color = (255, 0, 255)     # Magenta = pinched
            elif self.is_grabbed:
                draw_color = (0, 0, 255)       # Red = grabbed
            elif self.is_open:
                draw_color = (255, 200, 0)     # Cyan = open/catching
            else:
                draw_color = (0, 255, 0)       # Green = neutral
            self._draw_landmarks(bgr_frame, lm, draw_color)

            # ── Visual feedback ──────────────────────────────────────
            if self.is_pinched:
                status = "PINCH"
                hold_pct = ""
                if self._pinch_start_time:
                    elapsed = min(now - self._pinch_start_time, self._pinch_hold_required)
                    pct = int(elapsed / self._pinch_hold_required * 100)
                    hold_pct = f" [{pct}%]"
                color = (255, 0, 255)
            elif self.is_grabbed:
                status = "GRABBED"
                hold_pct = ""
                if self._grab_start_time:
                    elapsed = min(now - self._grab_start_time, self._grab_hold_required)
                    pct = int(elapsed / self._grab_hold_required * 100)
                    hold_pct = f" [{pct}%]"
                color = (0, 0, 255)
            elif self.is_open:
                status = "OPEN PALM"
                hold_pct = ""
                if self._catch_start_time:
                    elapsed = min(now - self._catch_start_time, self._catch_hold_required)
                    pct = int(elapsed / self._catch_hold_required * 100)
                    hold_pct = f" [{pct}%]"
                color = (255, 200, 0)
            else:
                status = "NEUTRAL"
                hold_pct = ""
                color = (0, 255, 0)

            cv2.putText(
                bgr_frame, f"{status}{hold_pct} | dist={grab_dist:.3f}",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2,
            )
            cv2.putText(
                bgr_frame, f"Vel: {velocity:.4f}",
                (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 200, 0), 2,
            )

            if result["pinch_confirmed"]:
                cv2.putText(
                    bgr_frame, ">>> PINCH — File picked up! <<<",
                    (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2,
                )
            elif result["pinch_released"]:
                cv2.putText(
                    bgr_frame, ">>> RELEASE — File dropped! <<<",
                    (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2,
                )
            elif result["grab_confirmed"]:
                cv2.putText(
                    bgr_frame, ">>> GRAB READY — waiting for catch <<<",
                    (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2,
                )
            elif result["catch_confirmed"]:
                cv2.putText(
                    bgr_frame, ">>> CATCH! Receiving... <<<",
                    (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2,
                )
        else:
            self.x_history.clear()
            self.is_grabbed = False
            self.is_open = False
            self.is_pinched = False
            self._was_pinched = False
            self.pinch_released = False
            self._grab_start_time = None
            self._catch_start_time = None
            self._pinch_start_time = None
            self.grab_confirmed = False
            self.catch_confirmed = False
            self.pinch_confirmed = False

        return result, bgr_frame

    def mark_transfer_complete(self):
        """Call after a successful transfer to reset cooldown."""
        self.last_trigger_time = time.time()
        self.grab_confirmed = False
        self.catch_confirmed = False
        self._grab_start_time = None
        self._catch_start_time = None

    def release(self):
        self.detector.close()
