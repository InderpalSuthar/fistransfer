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
    print("\n" + "="*60)
    print("  FisTransfer Setup")
    print("="*60 + "\n")
    
    # ── Peer IP Setup ──
    print(f"Default Mac IP: {MAC_IP}")
    custom_ip = input("Enter Mac IP Address (or press Enter to use default): ").strip()
    target_ip = custom_ip if custom_ip else MAC_IP

    # ── Camera Setup ──
    print(f"\nDefault Camera: {WIN_CAMERA}")
    print("  (Type 0 for laptop webcam, 1 for USB cam, or IP URL limit)")
    custom_cam = input("Enter Camera (or press Enter to use default): ").strip()
    
    if not custom_cam:
        target_cam = WIN_CAMERA
    elif custom_cam.isdigit():
        target_cam = int(custom_cam)
    else:
        target_cam = custom_cam

    print("\n[OK] Starting FisTransfer...\n")

    app = FisTransferApp(
        side="Win",
        camera_source=target_cam,
        peer_ip=target_ip,
    )
    app.run()


if __name__ == "__main__":
    main()
