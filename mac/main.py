"""
FisTransfer — Mac Entry Point (Bidirectional)
================================================
GRAB to send your screen to Windows.
CATCH to receive Windows' screen.

Usage:
    python -m mac
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.app_core import FisTransferApp
from config import MAC_CAMERA, WIN_IP


def main():
    app = FisTransferApp(
        side="Mac",
        camera_source=MAC_CAMERA,
        peer_ip=WIN_IP,
    )
    app.run()


if __name__ == "__main__":
    main()
