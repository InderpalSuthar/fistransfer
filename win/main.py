"""
FisTransfer — Windows Entry Point
====================================
Starts the PyQt6 catch window and the TCP receiver thread.

Usage:
    python -m win.main
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt

from win.receiver import ReceiverThread
from win.catch_window import CatchWindow
from config import RECEIVER_PORT


def main():
    print("=" * 60)
    print("  FisTransfer — Windows Receiver")
    print(f"  Listening on port {RECEIVER_PORT}")
    print("=" * 60)
    print()
    print("  The catch window will appear when an image arrives.")
    print("  Double-click the image to dismiss it early.")
    print("  Right-click the system tray icon to quit.")
    print()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running when window hides

    # ── Create the catch window ──────────────────────────────────────────
    catch_window = CatchWindow()

    # ── Create and start the receiver thread ─────────────────────────────
    receiver = ReceiverThread()
    receiver.image_received.connect(
        catch_window.catch_image, Qt.ConnectionType.QueuedConnection
    )
    receiver.status_changed.connect(
        lambda msg: print(f"[Status] {msg}")
    )
    receiver.start()

    # ── System tray icon (for clean exit) ────────────────────────────────
    tray = QSystemTrayIcon()
    tray.setToolTip("FisTransfer — Waiting for images...")

    tray_menu = QMenu()
    quit_action = QAction("Quit FisTransfer")
    quit_action.triggered.connect(lambda: _shutdown(app, receiver))
    tray_menu.addAction(quit_action)
    tray.setContextMenu(tray_menu)
    tray.show()

    print("[Windows] Application started. Waiting for incoming images...")

    # ── Run event loop ───────────────────────────────────────────────────
    exit_code = app.exec()

    # ── Cleanup ──────────────────────────────────────────────────────────
    _shutdown(app, receiver)
    sys.exit(exit_code)


def _shutdown(app, receiver):
    """Gracefully shut down the receiver thread and app."""
    print("[Windows] Shutting down...")
    receiver.stop()
    receiver.wait(3000)  # Wait up to 3s for thread to finish
    app.quit()


if __name__ == "__main__":
    main()
