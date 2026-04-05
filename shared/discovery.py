"""
FisTransfer — Auto Discovery
=============================
Uses UDP broadcast to automatically detect the IP addresses
of the peer device on the same Hotspot/WiFi network.
"""

import socket
import time
import threading

def discover_peer(my_side, discovery_port, timeout=120.0):
    """
    Broadcasts presence and listens for the peer.
    my_side: 'mac' or 'win'
    Returns: Peer IP string, or None if timeout.
    """
    peer_side = b"win" if my_side == "mac" else b"mac"
    my_msg = my_side.encode("utf-8")
    
    peer_ip = None
    stop_event = threading.Event()
    
    # ── 1. Listener Thread ──
    def listen():
        nonlocal peer_ip
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Mac specific port reuse
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except AttributeError:
                pass
                
            sock.bind(("", discovery_port))
            sock.settimeout(1.0)
            
            while not stop_event.is_set():
                try:
                    data, addr = sock.recvfrom(1024)
                    if data == peer_side:
                        peer_ip = addr[0]
                        stop_event.set()
                        break
                except socket.timeout:
                    continue
                except OSError:
                    break
        finally:
            sock.close()
            
    listener_thread = threading.Thread(target=listen, daemon=True)
    listener_thread.start()
    
    # ── 2. Broadcaster ──
    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    send_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    print(f"[{my_side.upper()}] 🔍 Searching for peer on network (auto-discovery)...")
    
    start_time = time.time()
    while not stop_event.is_set() and (time.time() - start_time) < timeout:
        try:
            # Broadcast on local subnet
            send_sock.sendto(my_msg, ("<broadcast>", discovery_port))
        except OSError:
            pass
        time.sleep(1.0)
        
    send_sock.close()
    stop_event.set()
    listener_thread.join(timeout=2.0)
    
    if peer_ip:
        print(f"[{my_side.upper()}] ✨ Found peer automatically at: {peer_ip}")
    else:
        print(f"[{my_side.upper()}] ❌ Peer auto-discovery timed out. Falling back to config.py IP.")
        
    return peer_ip
