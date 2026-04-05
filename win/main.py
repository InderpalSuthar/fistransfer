"""
FisTransfer — Windows Entry Point (Bidirectional)
====================================================
GRAB to send your screen to Mac.
CATCH to receive Mac's screen.

Usage:
    python -m win
"""

import sys, os
import multiprocessing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.app_core import FisTransferApp
from shared.discovery import discover_peer
from config import WIN_CAMERA, MAC_IP, DISCOVERY_PORT


def main():
    print("\n" + "="*60)
    print("  🖥️  FisTransfer Setup (Windows)")
    print("="*60 + "\n")
    
    # ── Camera Setup ──
    print(f"Default Camera: {WIN_CAMERA}")
    print("  (Type 0 for laptop webcam, 1 for USB cam, or IP URL limit)")
    custom_cam = input("Enter Camera (or press Enter to use default): ").strip()
    
    if not custom_cam:
        target_cam = WIN_CAMERA
    elif custom_cam.isdigit():
        target_cam = int(custom_cam)
    else:
        target_cam = custom_cam

    # ── Peer IP Auto-Discovery ──
    target_ip = discover_peer("win", DISCOVERY_PORT)
    if not target_ip:
        target_ip = MAC_IP

    print("\n[OK] Starting FisTransfer...\n")

    app = FisTransferApp(
        side="Win",
        camera_source=target_cam,
        peer_ip=target_ip,
    )
    app.run()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
