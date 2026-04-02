"""
FisTransfer — Catch Window (PyQt6)
=====================================
Frameless, transparent, always-on-top window that "catches" thrown images
with a smooth slide-in animation from the left edge of the screen.
"""

import numpy as np

from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QGraphicsDropShadowEffect,
    QApplication,
)
from PyQt6.QtCore import (
    Qt,
    QPoint,
    QPropertyAnimation,
    QEasingCurve,
    QTimer,
    QSize,
)
from PyQt6.QtGui import QImage, QPixmap, QColor, QPainter, QPainterPath, QRegion

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import (
    ANIMATION_DURATION_MS,
    AUTO_DISMISS_SECONDS,
    FADE_DURATION_MS,
)


class CatchWindow(QWidget):
    """
    A transparent, frameless window that displays a received screenshot
    with a slide-in animation from the left edge.
    """

    CORNER_RADIUS = 16
    PADDING = 20
    SHADOW_RADIUS = 30

    def __init__(self):
        super().__init__()

        # ── Window flags ─────────────────────────────────────────────────
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool              # Don't show in taskbar
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # ── Image label ──────────────────────────────────────────────────
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet(
            f"border-radius: {self.CORNER_RADIUS}px; "
            f"background: transparent;"
        )

        # ── Layout ───────────────────────────────────────────────────────
        layout = QVBoxLayout()
        layout.setContentsMargins(
            self.PADDING, self.PADDING, self.PADDING, self.PADDING
        )
        layout.addWidget(self.image_label)
        self.setLayout(layout)

        # ── Drop shadow ──────────────────────────────────────────────────
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(self.SHADOW_RADIUS)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 8)
        self.image_label.setGraphicsEffect(shadow)

        # ── Slide-in animation ───────────────────────────────────────────
        self.slide_anim = QPropertyAnimation(self, b"pos")
        self.slide_anim.setDuration(ANIMATION_DURATION_MS)
        self.slide_anim.setEasingCurve(QEasingCurve.Type.OutQuad)

        # ── Fade-out animation ───────────────────────────────────────────
        self.fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_anim.setDuration(FADE_DURATION_MS)
        self.fade_anim.setStartValue(1.0)
        self.fade_anim.setEndValue(0.0)
        self.fade_anim.finished.connect(self._on_fade_finished)

        # ── Auto-dismiss timer ───────────────────────────────────────────
        self.dismiss_timer = QTimer()
        self.dismiss_timer.setSingleShot(True)
        self.dismiss_timer.timeout.connect(self._start_fade_out)

        # ── Drag support ─────────────────────────────────────────────────
        self._drag_pos = None

    # ── Public API ───────────────────────────────────────────────────────────

    def catch_image(self, cv_image: np.ndarray):
        """
        Display a caught image with slide-in animation.

        Parameters
        ----------
        cv_image : ndarray
            BGR image from OpenCV.
        """
        # ── Convert OpenCV BGR → QPixmap ─────────────────────────────────
        h, w, ch = cv_image.shape
        bytes_per_line = ch * w
        rgb = np.ascontiguousarray(cv_image[:, :, ::-1])  # BGR → RGB (contiguous)
        q_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)

        # ── Scale to fit nicely on screen (max 60% of screen) ────────────
        screen = QApplication.primaryScreen().availableGeometry()
        max_w = int(screen.width() * 0.6)
        max_h = int(screen.height() * 0.6)
        pixmap = pixmap.scaled(
            QSize(max_w, max_h),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        # ── Apply rounded corners via mask ───────────────────────────────
        rounded = self._round_pixmap(pixmap, self.CORNER_RADIUS)
        self.image_label.setPixmap(rounded)

        # ── Size the window ──────────────────────────────────────────────
        total_w = pixmap.width() + 2 * self.PADDING
        total_h = pixmap.height() + 2 * self.PADDING
        self.setFixedSize(total_w, total_h)

        # ── Calculate positions ──────────────────────────────────────────
        center_x = (screen.width() - total_w) // 2
        center_y = (screen.height() - total_h) // 2

        start_pos = QPoint(-total_w, center_y)   # Off-screen left
        end_pos = QPoint(center_x, center_y)      # Centered

        # ── Reset and animate ────────────────────────────────────────────
        self.setWindowOpacity(1.0)
        self.move(start_pos)
        self.show()

        self.slide_anim.stop()
        self.slide_anim.setStartValue(start_pos)
        self.slide_anim.setEndValue(end_pos)
        self.slide_anim.start()

        # ── Start auto-dismiss countdown ─────────────────────────────────
        self.dismiss_timer.stop()
        self.dismiss_timer.start(AUTO_DISMISS_SECONDS * 1000)

        print(f"[CatchWindow] 🎯 Image caught! ({pixmap.width()}×{pixmap.height()})")

    # ── Rounded pixmap helper ────────────────────────────────────────────────

    @staticmethod
    def _round_pixmap(pixmap, radius):
        """Apply rounded corners to a QPixmap."""
        rounded = QPixmap(pixmap.size())
        rounded.fill(Qt.GlobalColor.transparent)

        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(
            0.0, 0.0, float(pixmap.width()), float(pixmap.height()),
            float(radius), float(radius),
        )
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()

        return rounded

    # ── Animation callbacks ──────────────────────────────────────────────────

    def _start_fade_out(self):
        """Begin the fade-out animation."""
        self.fade_anim.stop()
        self.fade_anim.setStartValue(1.0)
        self.fade_anim.setEndValue(0.0)
        self.fade_anim.start()

    def _on_fade_finished(self):
        """Hide the window after fade completes."""
        self.hide()
        self.setWindowOpacity(1.0)

    # ── Mouse events (click to dismiss + drag) ───────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Double-click to dismiss immediately."""
        self.dismiss_timer.stop()
        self._start_fade_out()
        super().mouseDoubleClickEvent(event)

    # ── Paint event for subtle background ────────────────────────────────────

    def paintEvent(self, event):
        """Draw a semi-transparent dark background behind the image."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(
            0.0, 0.0, float(self.width()), float(self.height()),
            float(self.CORNER_RADIUS + 4), float(self.CORNER_RADIUS + 4),
        )
        painter.fillPath(path, QColor(20, 20, 30, 200))
        painter.end()
