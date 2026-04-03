"""
FisTransfer — Cursor Control
================================
Maps hand landmark positions to screen cursor coordinates.
Uses pyautogui to move the actual mouse pointer.
"""

import sys
import os
from collections import deque

import pyautogui

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import CURSOR_SMOOTHING, CURSOR_SPEED

# Disable pyautogui fail-safe (moving to corner won't crash)
pyautogui.FAILSAFE = False
# Disable the tiny pause between pyautogui actions for speed
pyautogui.PAUSE = 0


class CursorController:
    """Maps index finger tip position to mouse cursor."""

    def __init__(self):
        self.screen_w, self.screen_h = pyautogui.size()
        self._x_history = deque(maxlen=CURSOR_SMOOTHING)
        self._y_history = deque(maxlen=CURSOR_SMOOTHING)
        self._enabled = True

    def update(self, index_tip_x, index_tip_y):
        """
        Move cursor based on normalized hand landmark position.

        Parameters
        ----------
        index_tip_x : float  — Normalized X (0.0 to 1.0, mirrored)
        index_tip_y : float  — Normalized Y (0.0 to 1.0)
        """
        if not self._enabled:
            return

        # Map to screen coordinates (X is mirrored since webcam is flipped)
        raw_x = index_tip_x * self.screen_w * CURSOR_SPEED
        raw_y = index_tip_y * self.screen_h * CURSOR_SPEED

        # Clamp to screen bounds
        raw_x = max(0, min(self.screen_w - 1, raw_x))
        raw_y = max(0, min(self.screen_h - 1, raw_y))

        # Smooth with moving average
        self._x_history.append(raw_x)
        self._y_history.append(raw_y)

        smooth_x = sum(self._x_history) / len(self._x_history)
        smooth_y = sum(self._y_history) / len(self._y_history)

        pyautogui.moveTo(int(smooth_x), int(smooth_y), _pause=False)

    def toggle(self):
        """Toggle cursor control on/off."""
        self._enabled = not self._enabled
        state = "ON" if self._enabled else "OFF"
        print(f"[Cursor] Control: {state}")
        return self._enabled

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value
