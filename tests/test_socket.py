"""
FisTransfer — Socket Test (Sprint 1)
=======================================
Verifies end-to-end TCP image transfer on localhost.

Usage:
    python tests/test_socket.py

This test runs both sender and receiver in the same process using threads,
so it works on a single machine for development.
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
from config import RECEIVER_PORT, JPEG_QUALITY, SOCKET_BUFFER_SIZE


def create_test_image(width=640, height=480):
    """Create a colorful test image with gradient and text."""
    img = np.zeros((height, width, 3), dtype=np.uint8)

    # Gradient background
    for y in range(height):
        for x in range(width):
            img[y, x] = [
                int(255 * x / width),       # Blue gradient
                int(255 * y / height),       # Green gradient
                128,                          # Red constant
            ]

    # Add text
    cv2.putText(
        img, "FisTransfer Test Image",
        (50, height // 2), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3,
    )
    cv2.putText(
        img, f"{width}x{height}",
        (50, height // 2 + 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (200, 200, 200), 2,
    )

    return img


def compress_image(img, quality=JPEG_QUALITY):
    """Compress an image to JPEG bytes."""
    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return buf.tobytes()


def run_receiver(port, result_holder, ready_event):
    """Simple receiver that saves the first received image."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", port))
    server.listen(1)
    ready_event.set()  # Signal that receiver is ready

    conn, addr = server.accept()
    print(f"[Test Receiver] Connected from {addr}")

    # Read header
    header = b""
    while len(header) < 4:
        header += conn.recv(4 - len(header))

    img_size = struct.unpack(">L", header)[0]
    print(f"[Test Receiver] Expecting {img_size} bytes...")

    # Read image data
    data = b""
    while len(data) < img_size:
        chunk = conn.recv(min(img_size - len(data), 65536))
        if not chunk:
            break
        data += chunk

    result_holder["data"] = data
    result_holder["size"] = img_size

    conn.close()
    server.close()
    print(f"[Test Receiver] Received {len(data)} bytes ✅")


def run_sender(port, jpeg_bytes):
    """Simple sender that transmits JPEG bytes."""
    time.sleep(0.2)  # Brief wait for receiver to be ready

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    sock.connect(("127.0.0.1", port))

    header = struct.pack(">L", len(jpeg_bytes))
    t0 = time.perf_counter()
    sock.sendall(header + jpeg_bytes)
    t1 = time.perf_counter()

    sock.close()
    print(f"[Test Sender] Sent {len(jpeg_bytes)} bytes in {(t1-t0)*1000:.1f}ms ✅")


def main():
    print("=" * 60)
    print("  FisTransfer — Socket Test")
    print("=" * 60)
    print()

    # Use a different port to avoid conflicts
    test_port = RECEIVER_PORT + 100

    # ── Create test image ────────────────────────────────────────────────
    print("[Test] Creating test image...")
    img = create_test_image(1920, 1080)
    jpeg_bytes = compress_image(img)
    print(f"[Test] Test image: 1920×1080 → {len(jpeg_bytes) / 1024:.1f} KB JPEG")

    # ── Start receiver thread ────────────────────────────────────────────
    result = {}
    ready = threading.Event()
    recv_thread = threading.Thread(
        target=run_receiver, args=(test_port, result, ready)
    )
    recv_thread.start()

    # Wait for receiver to be ready
    ready.wait(timeout=5)
    time.sleep(0.1)

    # ── Send the image ───────────────────────────────────────────────────
    print("[Test] Sending image...")
    t_start = time.perf_counter()
    run_sender(test_port, jpeg_bytes)
    recv_thread.join(timeout=10)
    t_end = time.perf_counter()

    # ── Verify ───────────────────────────────────────────────────────────
    print()
    print("-" * 40)
    if "data" in result and len(result["data"]) == len(jpeg_bytes):
        # Decode received image and verify
        received_array = np.frombuffer(result["data"], dtype=np.uint8)
        received_img = cv2.imdecode(received_array, cv2.IMREAD_COLOR)

        if received_img is not None and received_img.shape == img.shape[:2] + (3,):
            print("✅ TEST PASSED — Image transferred and decoded successfully!")
            print(f"   Original size:  {len(jpeg_bytes):,} bytes")
            print(f"   Received size:  {len(result['data']):,} bytes")
            print(f"   Image shape:    {received_img.shape}")
            print(f"   Round-trip:     {(t_end - t_start) * 1000:.1f}ms")
        else:
            print("❌ TEST FAILED — Image decoded but shape mismatch")
            if received_img is not None:
                print(f"   Expected: {img.shape}, Got: {received_img.shape}")
    else:
        print("❌ TEST FAILED — Byte count mismatch")
        print(f"   Sent: {len(jpeg_bytes)}, Received: {result.get('size', 'N/A')}")

    print("-" * 40)


if __name__ == "__main__":
    main()
