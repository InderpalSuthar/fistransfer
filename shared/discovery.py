"""
FisTransfer — Auto Discovery
=============================
Uses UDP broadcast to automatically detect the IP addresses
of the peer device on the same Hotspot/WiFi network.
"""

import socket
import time
import threading
from config import SIGNAL_PORT

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
            sock.settimeout(0.1)
            
            while not stop_event.is_set():
                try:
                    data, addr = sock.recvfrom(1024)
                    if data in [b"mac", b"win", b"android"] and data != my_msg:
                        peer_ip = addr[0]
                        
                        # Fix for 2-minute hang:
                        # If we found the peer, they might still be waiting for us.
                        # Blast a few targeted packets directly to them so they can unlock immediately!
                        try:
                            ack_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                            for _ in range(5):
                                ack_sock.sendto(my_msg, (peer_ip, discovery_port))
                                time.sleep(0.05)
                            ack_sock.close()
                        except Exception:
                            pass
                            
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
    
    # Common Hotspot Gateways to probe directly
    gateways = ["192.168.43.1", "192.168.233.1", "192.168.1.1", "192.168.0.1", "172.20.10.1"]
    
    my_ip = "0.0.0.0"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        my_ip = s.getsockname()[0]
        s.close()
        if my_ip.count(".") == 3:
            prefix = ".".join(my_ip.split(".")[:-1])
            gateways.append(f"{prefix}.1")
    except Exception:
        pass

    def tcp_sweep():
        nonlocal peer_ip
        if my_ip == "0.0.0.0": return
        prefix = ".".join(my_ip.split(".")[:-1])
        
        def check_ip(target):
            nonlocal peer_ip
            if stop_event.is_set(): return
            try:
                # Fast TCP attempt on signal port
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.5)
                res = s.connect_ex((target, SIGNAL_PORT))
                if res == 0:
                    # Found SOMETHING listening. Let's assume it's the peer for now.
                    # (In a more robust system, we'd send a HELLO packet)
                    peer_ip = target
                    stop_event.set()
                s.close()
            except Exception:
                pass

        threads = []
        # Sweep the local /24 subnet in chunks
        for i in range(1, 255):
            t = threading.Thread(target=check_ip, args=(f"{prefix}.{i}",))
            t.daemon = True
            t.start()
            threads.append(t)
            if i % 20 == 0: time.sleep(0.1) # Throttle to avoid OS socket limits

    print(f"[{my_side.upper()}] 🔍 Searching for peer (Auto-Discovery + Hotspot Probe)...")
    
    start_time = time.time()
    sweep_started = False
    
    while not stop_event.is_set() and (time.time() - start_time) < timeout:
        try:
            # 1. Standard Broadcast
            send_sock.sendto(my_msg, ("<broadcast>", discovery_port))
            
            # 2. Direct Hotspot Probe
            for gw in gateways:
                send_sock.sendto(my_msg, (gw, discovery_port))
            
            # 3. Active TCP Sweep (Fallback after 3 seconds)
            if not sweep_started and (time.time() - start_time) > 3.0:
                print(f"[{my_side.upper()}] 🕵️  UDP silent. Starting active TCP subnet sweep...")
                threading.Thread(target=tcp_sweep, daemon=True).start()
                sweep_started = True

        except OSError:
            pass
        stop_event.wait(0.2)
        
    send_sock.close()
    stop_event.set()
    listener_thread.join(timeout=2.0)
    
    if peer_ip:
        print(f"[{my_side.upper()}] ✨ Found peer automatically at: {peer_ip}")
    else:
        print(f"[{my_side.upper()}] ❌ Peer auto-discovery timed out. Falling back to config.py IP.")
        
    return peer_ip
