"""
FisTransfer — Bidirectional App Core
========================================
Unified app that runs on BOTH Mac and Windows.
Each side can GRAB (send screen) or CATCH (receive screen).

The only difference between sides is:
  - Camera source (local webcam vs DroidCam URL)
  - Peer IP (who to send signals/images to)
"""

import socket
import struct
import threading
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mac.gesture_engine import GestureEngine
from mac.screen_capture import ScreenCapture
from shared.file_transfer import FileSender, FileReceiver
from config import (
    SIGNAL_PORT,
    TRANSFER_PORT,
    SOCKET_BUFFER_SIZE,
    SIGNAL_GRAB_READY,
    SIGNAL_CATCH_ACCEPT,
    SIGNAL_FILE_READY,
    SIGNAL_FILE_ACCEPT,
    HANDSHAKE_TIMEOUT,
    ENABLE_PROFILING,
    CURSOR_ENABLED,
    SHOW_CAMERA_WINDOW,
)

# Conditional import — cursor control only works on Mac with pyautogui
try:
    from mac.cursor_control import CursorController
    HAS_CURSOR = True
except ImportError:
    HAS_CURSOR = False

# Conditional import — file picker depends on OS
HAS_FILE_PICKER = False
if sys.platform == "darwin":
    try:
        from mac.file_picker import FilePicker
        HAS_FILE_PICKER = True
    except ImportError:
        pass
elif sys.platform == "win32":
    try:
        from win.file_picker import FilePicker
        HAS_FILE_PICKER = True
    except ImportError as e:
        print(f"Windows FilePicker init warning: {e}")


class FisTransferApp:
    """
    Bidirectional FisTransfer app.

    Parameters
    ----------
    side : str
        "mac" or "win" — used for display labels only.
    camera_source : int or str
        Camera index (0) or URL ("http://...").
    peer_ip : str
        IP address of the other machine.
    """

    def __init__(self, side, camera_source, peer_ip):
        self.side = side.upper()
        self.camera_source = camera_source
        self.peer_ip = peer_ip

        self.gesture = GestureEngine()
        self.capture = ScreenCapture()

        # ── State ────────────────────────────────────────────────────────
        # IDLE → GRAB_SENT → (waiting for catch)
        # IDLE → CATCH_PROMPT → (waiting for user to catch)
        self.state = "IDLE"
        self.state_time = 0

        # ── Threading ────────────────────────────────────────────────────
        self._running = True
        self._grab_from_peer = threading.Event()    # Peer sent GRAB_READY
        self._catch_from_peer = threading.Event()   # Peer sent CATCH_OK
        self._received_image = None
        self._image_lock = threading.Lock()
        self._image_show_time = 0

        # ── Image display / save ─────────────────────────────────────────
        self._display_image = None       # Currently displayed caught image
        self._display_original = None    # Full-res original for saving
        self._save_count = 0
        self._caught_window = f"FisTransfer — Caught! [{self.side}]"

        # ── File transfer ────────────────────────────────────────────
        self._file_receiver = FileReceiver()
        self._file_from_peer = threading.Event()     # Peer sent FILE_READY
        self._file_accept_from_peer = threading.Event()  # Peer sent FILE_OK
        self._picked_file = None   # FilePicker result when pinch detected

        # ── Cursor control ──────────────────────────────────────────
        self._cursor = None
        if HAS_CURSOR and CURSOR_ENABLED:
            self._cursor = CursorController()
            print(f"[{self.side}] 🖐 Cursor control enabled")

    # ═══════════════════════════════════════════════════════════════════════
    # NETWORK: Listeners
    # ═══════════════════════════════════════════════════════════════════════

    def _signal_listener(self):
        """Listen for GRAB_READY and CATCH_OK signals from peer."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.settimeout(1.0)

        try:
            server.bind(("0.0.0.0", SIGNAL_PORT))
            server.listen(2)
            print(f"[{self.side}] 🔊 Signal listener on port {SIGNAL_PORT}")

            while self._running:
                try:
                    conn, addr = server.accept()
                    data = conn.recv(64)
                    conn.close()

                    if data == SIGNAL_GRAB_READY:
                        print(f"\n[{self.side}] 🤜 Peer GRAB signal from {addr[0]}!")
                        self._grab_from_peer.set()
                    elif data == SIGNAL_CATCH_ACCEPT:
                        print(f"\n[{self.side}] 🖐 Peer CATCH signal from {addr[0]}!")
                        self._catch_from_peer.set()
                    elif data == SIGNAL_FILE_READY:
                        print(f"\n[{self.side}] 🤏 Peer FILE signal from {addr[0]}!")
                        self._file_from_peer.set()
                    elif data == SIGNAL_FILE_ACCEPT:
                        print(f"\n[{self.side}] 🖐 Peer FILE ACCEPT from {addr[0]}!")
                        self._file_accept_from_peer.set()

                except socket.timeout:
                    continue
        except OSError as e:
            print(f"[{self.side}] Signal listener error: {e}")
        finally:
            server.close()

    def _transfer_listener(self):
        """Listen for incoming image data from peer."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, SOCKET_BUFFER_SIZE)
        server.settimeout(1.0)

        try:
            server.bind(("0.0.0.0", TRANSFER_PORT))
            server.listen(1)
            print(f"[{self.side}] 🔊 Transfer listener on port {TRANSFER_PORT}")

            while self._running:
                try:
                    conn, addr = server.accept()
                except socket.timeout:
                    continue

                conn.settimeout(5.0)
                try:
                    header = self._recv_exact(conn, 4)
                    if header is None:
                        conn.close()
                        continue

                    img_size = struct.unpack(">L", header)[0]
                    if img_size == 0 or img_size > 50_000_000:
                        conn.close()
                        continue

                    t0 = time.perf_counter()
                    img_data = self._recv_exact(conn, img_size)
                    t1 = time.perf_counter()

                    if img_data:
                        arr = np.frombuffer(img_data, dtype=np.uint8)
                        image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                        t2 = time.perf_counter()

                        if image is not None:
                            with self._image_lock:
                                self._received_image = image
                                self._image_show_time = time.time()

                            if ENABLE_PROFILING:
                                print(f"[{self.side}] 📥 Received {img_size/1024:.1f}KB"
                                      f" | recv={round((t1-t0)*1000,1)}ms"
                                      f" | decode={round((t2-t1)*1000,1)}ms")
                            print(f"[{self.side}] 🎯 Image caught!")

                except (socket.timeout, OSError) as e:
                    print(f"[{self.side}] Transfer error: {e}")
                finally:
                    conn.close()
        except OSError as e:
            print(f"[{self.side}] Transfer listener error: {e}")
        finally:
            server.close()

    def _recv_exact(self, conn, size):
        data = b""
        while len(data) < size:
            try:
                chunk = conn.recv(min(size - len(data), 65536))
            except socket.timeout:
                return None
            if not chunk:
                return None
            data += chunk
        return data

    # ═══════════════════════════════════════════════════════════════════════
    # NETWORK: Senders
    # ═══════════════════════════════════════════════════════════════════════

    def _send_signal(self, signal_bytes):
        """Send a signal to the peer."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3.0)
            sock.connect((self.peer_ip, SIGNAL_PORT))
            sock.sendall(signal_bytes)
            sock.close()
            return True
        except (ConnectionRefusedError, socket.timeout, OSError) as e:
            print(f"[{self.side}] ❌ Signal send failed: {e}")
            return False

    def _send_image(self, jpeg_bytes):
        """Send image to the peer."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, SOCKET_BUFFER_SIZE)
            sock.settimeout(5.0)
            sock.connect((self.peer_ip, TRANSFER_PORT))

            header = struct.pack(">L", len(jpeg_bytes))
            t0 = time.perf_counter()
            sock.sendall(header + jpeg_bytes)
            t1 = time.perf_counter()
            sock.close()

            if ENABLE_PROFILING:
                print(f"  📡 Send: {round((t1-t0)*1000,1)}ms ({len(jpeg_bytes)/1024:.1f}KB)")
            return True
        except (ConnectionRefusedError, socket.timeout, OSError) as e:
            print(f"[{self.side}] ❌ Image send failed: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════════════
    # MAIN LOOP
    # ═══════════════════════════════════════════════════════════════════════

    def run(self):
        print("=" * 60)
        print(f"  FisTransfer — {self.side} (Bidirectional)")
        print(f"  Peer: {self.peer_ip}")
        print("=" * 60)
        print()
        print("  🤜 Close FIST (0.5s)  → GRAB and send your screen")
        print("  🖐  Open PALM (0.3s)   → CATCH and receive their screen")
        print("  🤏 PINCH (0.3s)        → Pick up selected file")
        print("  🤏→🖐 Release pinch   → Drop/accept incoming file")
        print()
        print("  Controls:")
        print("    q — Quit")
        print("    t — Test send (bypass handshake)")
        print("    m — Toggle cursor control")
        print()
        print("  When a screenshot is caught:")
        print("    s — Save to Desktop")
        print("    d — Save to Downloads")
        print("    p — Save as PNG (lossless)")
        print("    c — Save to current directory")
        print("    Esc — Dismiss")
        print()

        # Start listeners
        threading.Thread(target=self._signal_listener, daemon=True).start()
        time.sleep(0.1)
        threading.Thread(target=self._transfer_listener, daemon=True).start()
        time.sleep(0.1)
        threading.Thread(target=self._file_receiver.listen, daemon=True).start()
        time.sleep(0.1)

        # Open camera
        print(f"[{self.side}] Opening camera: {self.camera_source}")
        cap = cv2.VideoCapture(self.camera_source)
        if not cap.isOpened():
            print(f"[{self.side}] ❌ Cannot open camera!")
            print(f"[{self.side}] Running headless (auto-accept mode)...")
            self._run_headless()
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        print(f"[{self.side}] Camera ready!\n")

        window_name = f"FisTransfer — {self.side}"

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.01)
                    continue

                frame = cv2.flip(frame, 1)
                result, annotated = self.gesture.process_frame(frame)

                # ── Cursor control (move mouse with hand) ────────────────
                if self._cursor and self._cursor.enabled and result["hand_detected"]:
                    self._cursor.update(result["cursor_x"], result["cursor_y"])

                # ── Handle incoming grab from peer (screenshot) ──────────
                if self._grab_from_peer.is_set() and self.state == "IDLE":
                    self._grab_from_peer.clear()
                    self.state = "CATCH_PROMPT"
                    self.state_time = time.time()
                    print(f"  🖐 Peer wants to send screenshot! Show OPEN PALM!")

                # ── Handle incoming file signal from peer ────────────────
                if self._file_from_peer.is_set() and self.state == "IDLE":
                    self._file_from_peer.clear()
                    self.state = "FILE_RECEIVE_PROMPT"
                    self.state_time = time.time()
                    print(f"  🤏 Peer wants to send a file! Release PINCH to accept!")

                # ── State machine ────────────────────────────────────────
                self._process_state(result, annotated)

                # ── Show received image ──────────────────────────────────
                self._show_received_image()

                # ── Display ──────────────────────────────────────────────
                if SHOW_CAMERA_WINDOW:
                    cv2.imshow(window_name, annotated)

                    key = cv2.waitKey(1) & 0xFF
                    if key == ord("q"):
                        break
                    elif key == ord("t"):
                        self._test_send()
                    elif key == ord("m"):
                        if self._cursor:
                            self._cursor.toggle()
                else:
                    # Provide a minimal delay to allow thread switching if needed
                    # (cv2.VideoCapture.read() is generally blocking and handles framerate,
                    # but it's good practice)
                    time.sleep(0.001)

        except KeyboardInterrupt:
            print(f"\n[{self.side}] Interrupted.")
        finally:
            self._running = False
            cap.release()
            cv2.destroyAllWindows()
            self.gesture.release()
            self.capture.release()
            print(f"[{self.side}] Shutdown complete.")

    def _process_state(self, result, annotated):
        """Handle the GRAB/CATCH state machine."""
        now = time.time()

        if self.state == "IDLE":
            # ── Show idle status ─────────────────────────────────────
            cv2.putText(annotated, "FIST=Screenshot | PINCH=File | PALM=Catch",
                        (10, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

            # ── Check for PINCH (file pick) — higher priority ────────
            if result["pinch_confirmed"] and HAS_FILE_PICKER:
                file_info = FilePicker.get_selected_file()
                if file_info:
                    print(f"\n  🤏 PINCH! Picked: {file_info['name']} ({file_info['size']/1024:.0f}KB)")
                    prepared = FilePicker.prepare_for_transfer(file_info)
                    self._picked_file = prepared

                    if self._send_signal(SIGNAL_FILE_READY):
                        self.state = "FILE_SENT"
                        self.state_time = now
                        self._file_accept_from_peer.clear()
                        print(f"  ⏳ Waiting for peer to accept file...")
                    else:
                        print(f"  ❌ Peer unreachable. Is it running?")
                        FilePicker.cleanup(prepared)
                        self._picked_file = None
                        self.gesture.mark_transfer_complete()
                else:
                    print(f"\n  🤏 PINCH! But no file selected in Finder.")
                    print(f"      Select a file in Finder first, then pinch.")
                    self.gesture.mark_transfer_complete()

            # ── Check for GRAB (screenshot) ──────────────────────────
            elif result["grab_confirmed"]:
                print(f"\n  🤜 GRAB! Sending signal to peer...")
                if self._send_signal(SIGNAL_GRAB_READY):
                    self.state = "GRAB_SENT"
                    self.state_time = now
                    self._catch_from_peer.clear()
                    print(f"  ⏳ Waiting for peer to CATCH...")
                else:
                    print(f"  ❌ Peer unreachable. Is it running?")
                    self.gesture.mark_transfer_complete()

        elif self.state == "GRAB_SENT":
            # ── Waiting for peer's CATCH ─────────────────────────────
            remaining = max(0, HANDSHAKE_TIMEOUT - (now - self.state_time))

            cv2.rectangle(annotated, (5, 120), (635, 175), (0, 0, 80), -1)
            cv2.putText(annotated, f"Waiting for peer to CATCH... [{remaining:.0f}s]",
                        (10, 155), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 150, 255), 2)

            if self._catch_from_peer.is_set():
                self._catch_from_peer.clear()
                print(f"\n  🎯 HANDSHAKE COMPLETE! Capturing & sending...")

                t0 = time.perf_counter()
                jpeg_bytes, timing = self.capture.capture()
                if ENABLE_PROFILING:
                    print(f"  📸 Capture: {timing}")
                self._send_image(jpeg_bytes)
                t1 = time.perf_counter()
                if ENABLE_PROFILING:
                    print(f"  ⏱  Total: {round((t1-t0)*1000,1)}ms")

                self.state = "IDLE"
                self.gesture.mark_transfer_complete()

            elif remaining <= 0:
                print(f"  ⏰ Timeout! Peer didn't catch.")
                self.state = "IDLE"
                self.gesture.mark_transfer_complete()

        elif self.state == "FILE_SENT":
            # ── Waiting for peer to accept file ──────────────────────
            remaining = max(0, HANDSHAKE_TIMEOUT - (now - self.state_time))

            cv2.rectangle(annotated, (5, 120), (635, 175), (100, 0, 100), -1)
            name = self._picked_file["original_name"] if self._picked_file else "?"
            cv2.putText(annotated, f"Sending '{name}'... wait for peer [{remaining:.0f}s]",
                        (10, 155), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 180, 255), 2)

            if self._file_accept_from_peer.is_set():
                self._file_accept_from_peer.clear()
                print(f"\n  🎯 FILE ACCEPTED! Sending file...")

                # Send in background so UI stays responsive
                def _bg_send():
                    success = FileSender.send(self.peer_ip, self._picked_file)
                    if success:
                        print(f"  ✅ File transfer complete!")
                    FilePicker.cleanup(self._picked_file)
                    self._picked_file = None

                threading.Thread(target=_bg_send, daemon=True).start()
                self.state = "IDLE"
                self.gesture.mark_transfer_complete()

            elif remaining <= 0:
                print(f"  ⏰ Timeout! Peer didn't accept file.")
                if self._picked_file:
                    FilePicker.cleanup(self._picked_file)
                    self._picked_file = None
                self.state = "IDLE"
                self.gesture.mark_transfer_complete()

        elif self.state == "CATCH_PROMPT":
            # ── Peer wants to send screenshot — show catch prompt ─────
            remaining = max(0, HANDSHAKE_TIMEOUT - (now - self.state_time))

            cv2.rectangle(annotated, (5, 120), (635, 175), (0, 80, 0), -1)
            cv2.putText(annotated, f"Peer wants to send! Show OPEN PALM [{remaining:.0f}s]",
                        (10, 155), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

            if result["catch_confirmed"]:
                print(f"  🖐 CATCH! Accepting transfer...")
                self._send_signal(SIGNAL_CATCH_ACCEPT)
                self.state = "IDLE"
                self.gesture.mark_transfer_complete()

            elif remaining <= 0:
                print(f"  ⏰ Timeout! Peer's grab expired.")
                self.state = "IDLE"
                self.gesture.mark_transfer_complete()

        elif self.state == "FILE_RECEIVE_PROMPT":
            # ── Peer wants to send a file — release pinch to accept ───
            remaining = max(0, HANDSHAKE_TIMEOUT - (now - self.state_time))

            cv2.rectangle(annotated, (5, 120), (635, 175), (100, 0, 100), -1)
            cv2.putText(annotated, f"Incoming file! Release PINCH to accept [{remaining:.0f}s]",
                        (10, 155), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 180, 255), 2)

            if result["pinch_released"] or result["catch_confirmed"]:
                print(f"  🖐 ACCEPTED! Receiving file...")
                self._send_signal(SIGNAL_FILE_ACCEPT)
                self.state = "IDLE"
                self.gesture.mark_transfer_complete()

            elif remaining <= 0:
                print(f"  ⏰ Timeout! Peer's file offer expired.")
                self.state = "IDLE"
                self.gesture.mark_transfer_complete()

    def _show_received_image(self):
        """Auto-save received screenshot and trigger the glassmorphic viewer."""
        with self._image_lock:
            if self._received_image is None:
                return
            original = self._received_image.copy()
            self._received_image = None

        # Auto-save to Downloads
        directory = Path.home() / "Downloads"
        directory.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = directory / f"screenshot_{timestamp}.png"
        
        cv2.imwrite(str(filepath), original)
        print(f"[{self.side}] 📸 Saved screenshot to: {filepath}")
        self._save_count += 1
        
        # Spawn the beautiful UI presentation
        import multiprocessing
        from shared.glass_viewer import show_glass_window
        p = multiprocessing.Process(target=show_glass_window, args=(str(filepath),))
        p.daemon = True
        p.start()



    def _test_send(self):
        """Test send bypassing gesture handshake."""
        print(f"[{self.side}] Test send...")
        jpeg_bytes, timing = self.capture.capture()
        if ENABLE_PROFILING:
            print(f"  📸 {timing}")
        self._send_image(jpeg_bytes)

    # ═══════════════════════════════════════════════════════════════════════
    # HEADLESS MODE (no webcam)
    # ═══════════════════════════════════════════════════════════════════════

    def _run_headless(self):
        """Auto-accept grabs when no webcam is available."""
        print(f"[{self.side}] Headless: auto-accepting all grabs, press Ctrl+C to quit.")
        try:
            while self._running:
                if self._grab_from_peer.wait(timeout=1.0):
                    self._grab_from_peer.clear()
                    print(f"[{self.side}] Auto-accepting grab...")
                    time.sleep(0.3)
                    self._send_signal(SIGNAL_CATCH_ACCEPT)

                    # Wait for image
                    for _ in range(50):
                        time.sleep(0.1)
                        with self._image_lock:
                            if self._received_image is not None:
                                h, w = self._received_image.shape[:2]
                                out = f"received_{int(time.time())}.jpg"
                                cv2.imwrite(out, self._received_image)
                                self._received_image = None
                                print(f"[{self.side}] 💾 Saved: {out} ({w}×{h})")
                                break
        except KeyboardInterrupt:
            self._running = False
            print(f"\n[{self.side}] Headless stopped.")
