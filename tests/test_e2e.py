"""
FisTransfer — End-to-End Integration Test
=============================================
Runs both the sender pipeline and receiver on the same machine
to verify the full flow: capture → compress → send → receive → decode.

Usage:
    python tests/test_e2e.py
"""

import socket
import struct
import threading
import time
import sys
import os

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mac.screen_capture import ScreenCapture
from config import RECEIVER_PORT, SOCKET_BUFFER_SIZE


def receiver_thread(port, result, ready_event):
    """Receive one image and decode it."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    server.bind(("127.0.0.1", port))
    server.listen(1)
    ready_event.set()

    conn, addr = server.accept()
    conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    # Read header
    header = b""
    while len(header) < 4:
        header += conn.recv(4 - len(header))

    img_size = struct.unpack(">L", header)[0]

    # Read image
    t0 = time.perf_counter()
    data = b""
    while len(data) < img_size:
        chunk = conn.recv(min(img_size - len(data), 65536))
        if not chunk:
            break
        data += chunk
    t_recv = time.perf_counter()

    # Decode
    jpg_arr = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(jpg_arr, cv2.IMREAD_COLOR)
    t_decode = time.perf_counter()

    result["data_size"] = len(data)
    result["image"] = image
    result["recv_ms"] = round((t_recv - t0) * 1000, 1)
    result["decode_ms"] = round((t_decode - t_recv) * 1000, 1)

    conn.close()
    server.close()


def main():
    print("=" * 60)
    print("  FisTransfer — End-to-End Integration Test")
    print("=" * 60)
    print()

    test_port = RECEIVER_PORT + 200  # Avoid conflicts

    # ── Start receiver ───────────────────────────────────────────────────
    result = {}
    ready = threading.Event()
    recv = threading.Thread(target=receiver_thread, args=(test_port, result, ready))
    recv.start()
    ready.wait(timeout=5)
    time.sleep(0.1)

    # ── Capture real screen ──────────────────────────────────────────────
    print("[E2E] Capturing screen...")
    capture = ScreenCapture()
    t_cap_start = time.perf_counter()
    jpeg_bytes, cap_timing = capture.capture()
    t_cap_end = time.perf_counter()
    capture.release()

    print(f"[E2E] Capture: {cap_timing}")

    # ── Send over TCP ────────────────────────────────────────────────────
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    sock.connect(("127.0.0.1", test_port))

    header = struct.pack(">L", len(jpeg_bytes))
    t_send_start = time.perf_counter()
    sock.sendall(header + jpeg_bytes)
    t_send_end = time.perf_counter()
    sock.close()

    send_ms = round((t_send_end - t_send_start) * 1000, 1)
    print(f"[E2E] Send: {send_ms}ms ({len(jpeg_bytes)/1024:.1f} KB)")

    # ── Wait for receiver ────────────────────────────────────────────────
    recv.join(timeout=10)

    # ── Results ──────────────────────────────────────────────────────────
    print()
    print("=" * 50)
    print("  End-to-End Results")
    print("=" * 50)

    if result.get("image") is not None:
        img = result["image"]
        total_ms = cap_timing.get("total_ms", 0) + send_ms + result["recv_ms"] + result["decode_ms"]

        print(f"  📸 Capture:   {cap_timing.get('total_ms', '?')}ms")
        print(f"  📡 Send:      {send_ms}ms")
        print(f"  📥 Receive:   {result['recv_ms']}ms")
        print(f"  🖼  Decode:    {result['decode_ms']}ms")
        print(f"  ─────────────────────────")
        print(f"  ⏱  TOTAL:     {total_ms:.1f}ms")
        print(f"  📐 Image:     {img.shape[1]}×{img.shape[0]}")
        print(f"  💾 Payload:   {result['data_size']/1024:.1f} KB")
        print()

        if total_ms < 200:
            print(f"  ✅ PASS — {total_ms:.1f}ms is under 200ms target!")
        elif total_ms < 300:
            print(f"  ⚠ CLOSE — {total_ms:.1f}ms is near the 200ms target.")
        else:
            print(f"  ❌ SLOW — {total_ms:.1f}ms exceeds 200ms target.")

        # Save result
        out = os.path.join(os.path.dirname(__file__), "..", "test_e2e_output.jpg")
        cv2.imwrite(out, img)
        print(f"  💾 Saved to: {os.path.abspath(out)}")
    else:
        print("  ❌ FAILED — No image received!")

    print("=" * 50)


if __name__ == "__main__":
    main()
