"""
FisTransfer — Mac Entry Point (Bidirectional)
================================================
GRAB to send your screen to Windows.
CATCH to receive Windows' screen.

Usage:
    python -m mac
"""

import sys, os
import multiprocessing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.app_core import FisTransferApp
from shared.discovery import discover_peer
from config import MAC_CAMERA, WIN_IP, DISCOVERY_PORT


def main():
    print(f"\n🍏 FisTransfer Mac — Starting Up")
    
    # Check for manual IP argument
    if len(sys.argv) > 1:
        peer_ip = sys.argv[1]
        print(f"[MAC] 🎯 Using manual peer IP: {peer_ip}")
    else:
        peer_ip = discover_peer("mac", DISCOVERY_PORT)
        if not peer_ip:
            peer_ip = WIN_IP

    app = FisTransferApp(
        side="Mac",
        camera_source=MAC_CAMERA,
        peer_ip=peer_ip,
    )
    app.run()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
