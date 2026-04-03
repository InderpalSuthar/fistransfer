"""
FisTransfer — Windows Entry Point (Bidirectional)
====================================================
GRAB to send your screen to Mac.
CATCH to receive Mac's screen.

Usage:
    python -m win
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.app_core import FisTransferApp
from config import WIN_CAMERA, MAC_IP


def main():
    app = FisTransferApp(
        side="Win",
        camera_source=WIN_CAMERA,
        peer_ip=MAC_IP,
    )
    app.run()


if __name__ == "__main__":
    main()
