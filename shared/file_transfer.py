"""
FisTransfer — File Transfer Protocol
========================================
Handles sending and receiving actual files over TCP.

Protocol:
    [4 bytes: header_json_size]
    [header_json: {"filename": str, "filesize": int, "is_zipped": bool, "original_name": str}]
    [file_bytes: raw binary data in 64KB chunks]
"""

import json
import os
import socket
import struct
import time
from pathlib import Path

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import FILE_TRANSFER_PORT, SOCKET_BUFFER_SIZE, ENABLE_PROFILING


CHUNK_SIZE = 65536  # 64 KB


class FileSender:
    """Send a file to the peer over TCP."""

    @staticmethod
    def send(peer_ip, prepared_info):
        """
        Send a prepared file to the peer.

        Parameters
        ----------
        peer_ip : str
        prepared_info : dict — from FilePicker.prepare_for_transfer()

        Returns
        -------
        bool — success
        """
        filepath = prepared_info["transfer_path"]
        filesize = prepared_info["transfer_size"]
        filename = prepared_info["transfer_name"]

        # Build header
        header = json.dumps({
            "filename": filename,
            "filesize": filesize,
            "is_zipped": prepared_info["is_zipped"],
            "original_name": prepared_info["original_name"],
        }).encode("utf-8")

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, SOCKET_BUFFER_SIZE)
            sock.settimeout(30.0)
            sock.connect((peer_ip, FILE_TRANSFER_PORT))

            # Send header length + header
            sock.sendall(struct.pack(">L", len(header)))
            sock.sendall(header)

            # Send file data in chunks
            t0 = time.perf_counter()
            sent = 0
            with open(filepath, "rb") as f:
                while sent < filesize:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    sock.sendall(chunk)
                    sent += len(chunk)

                    # Progress
                    pct = int(sent / filesize * 100)
                    if pct % 20 == 0:
                        print(f"  📤 Sending: {pct}% ({sent/1024/1024:.1f}/{filesize/1024/1024:.1f} MB)")

            t1 = time.perf_counter()
            sock.close()

            speed_mbps = (filesize / 1024 / 1024) / max(t1 - t0, 0.001)
            print(f"  ✅ File sent: {filename} ({filesize/1024/1024:.1f} MB in {(t1-t0)*1000:.0f}ms, {speed_mbps:.1f} MB/s)")
            return True

        except (ConnectionRefusedError, socket.timeout, OSError) as e:
            print(f"  ❌ File send failed: {e}")
            return False


class FileReceiver:
    """Background listener for incoming file transfers."""

    def __init__(self, save_directory=None):
        if save_directory:
            self.save_dir = Path(save_directory)
        else:
            self.save_dir = Path.home() / "Downloads"
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self._running = True
        self.last_received = None  # Path of last received file

    def listen(self):
        """Blocking listener — run in a background thread."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, SOCKET_BUFFER_SIZE)
        server.settimeout(1.0)

        try:
            server.bind(("0.0.0.0", FILE_TRANSFER_PORT))
            server.listen(1)
            print(f"[FileReceiver] 🔊 Listening on port {FILE_TRANSFER_PORT}")

            while self._running:
                try:
                    conn, addr = server.accept()
                except socket.timeout:
                    continue

                conn.settimeout(30.0)
                try:
                    self._receive_file(conn, addr)
                except (socket.timeout, OSError) as e:
                    print(f"[FileReceiver] Error: {e}")
                finally:
                    conn.close()

        except OSError as e:
            print(f"[FileReceiver] Listener error: {e}")
        finally:
            server.close()

    def _receive_file(self, conn, addr):
        """Receive a single file from a connection."""
        # Read header length
        header_len_data = self._recv_exact(conn, 4)
        if not header_len_data:
            return

        header_len = struct.unpack(">L", header_len_data)[0]
        if header_len > 10_000:  # Sanity check
            return

        # Read header JSON
        header_data = self._recv_exact(conn, header_len)
        if not header_data:
            return

        header = json.loads(header_data.decode("utf-8"))
        filename = header["filename"]
        filesize = header["filesize"]
        is_zipped = header.get("is_zipped", False)
        original_name = header.get("original_name", filename)

        print(f"\n[FileReceiver] 📥 Incoming: {original_name} ({filesize/1024/1024:.1f} MB)")
        if is_zipped:
            print(f"  📦 Folder (zipped as {filename})")

        # Receive file data
        out_path = self.save_dir / filename
        t0 = time.perf_counter()
        received = 0

        with open(out_path, "wb") as f:
            while received < filesize:
                remaining = filesize - received
                chunk = conn.recv(min(CHUNK_SIZE, remaining))
                if not chunk:
                    break
                f.write(chunk)
                received += len(chunk)

                pct = int(received / filesize * 100)
                if pct % 20 == 0:
                    print(f"  📥 Receiving: {pct}% ({received/1024/1024:.1f}/{filesize/1024/1024:.1f} MB)")

        t1 = time.perf_counter()

        if received == filesize:
            speed_mbps = (filesize / 1024 / 1024) / max(t1 - t0, 0.001)
            self.last_received = str(out_path)
            print(f"  ✅ Saved: {out_path}")
            print(f"     {filesize/1024/1024:.1f} MB in {(t1-t0)*1000:.0f}ms ({speed_mbps:.1f} MB/s)")

            # ── Auto Handle Post-Transfer ──
            if is_zipped:
                import zipfile
                extract_dir = self.save_dir / original_name
                # Avoid folder name collisions
                base = original_name
                counter = 1
                while extract_dir.exists():
                    extract_dir = self.save_dir / f"{base}_{counter}"
                    counter += 1
                
                print(f"  📂 Extracting to {extract_dir} ...")
                try:
                    with zipfile.ZipFile(out_path, 'r') as zip_ref:
                        zip_ref.extractall(extract_dir)
                    os.remove(out_path)  # Keep it clean
                    self._open_in_os(extract_dir)
                except Exception as e:
                    print(f"  ❌ Extraction failed: {e}")
            else:
                ext = out_path.suffix.lower()
                if ext in [".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"]:
                    import multiprocessing
                    from shared.glass_viewer import show_glass_window
                    print(f"  ✨ Spawning Glass Viewer")
                    p = multiprocessing.Process(target=show_glass_window, args=(str(out_path),))
                    p.daemon = True
                    p.start()
                else:
                    # Open standard files immediately
                    self._open_in_os(out_path)

        else:
            print(f"  ❌ Incomplete: got {received}/{filesize} bytes")

    def _open_in_os(self, path):
        """Open a path natively using the OS shell."""
        import subprocess
        import sys
        try:
            if sys.platform == "win32":
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.run(["open", str(path)])
            else:
                subprocess.run(["xdg-open", str(path)])
        except Exception as e:
            print(f"  ⚠️ Could not open path automatically: {e}")

    def _recv_exact(self, conn, size):
        data = b""
        while len(data) < size:
            chunk = conn.recv(min(size - len(data), CHUNK_SIZE))
            if not chunk:
                return None
            data += chunk
        return data

    def stop(self):
        self._running = False
