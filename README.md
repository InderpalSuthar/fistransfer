# FisTransfer 🤜➡💻

**Gesture-driven screen transfer** — grab your screen with your hand and throw it from your MacBook to a Windows laptop.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![MediaPipe](https://img.shields.io/badge/MediaPipe-Hand_Tracking-green?logo=google)
![PyQt6](https://img.shields.io/badge/PyQt6-UI-purple?logo=qt)

---

## How It Works

1. **Grab** — Pinch your thumb and index finger together in front of your webcam
2. **Swipe** — Move your hand in the throw direction (left or right)
3. **Catch** — Your screen appears on the Windows laptop with a smooth slide-in animation

```
MacBook                          Windows Laptop
┌─────────┐    TCP Socket     ┌─────────────────┐
│ Webcam   │   ──────────────►│ PyQt6 Catch      │
│ MediaPipe│   JPEG over TCP  │ Window           │
│ mss      │                  │ Slide-in anim    │
└─────────┘                  └─────────────────┘
```

---

## Project Structure

```
fistransfer/
├── config.py                # Shared configuration (IPs, ports, thresholds)
├── requirements_mac.txt     # Mac dependencies
├── requirements_win.txt     # Windows dependencies
│
├── mac/                     # Runs on MacBook
│   ├── gesture_engine.py    # MediaPipe hand detection
│   ├── screen_capture.py    # mss screenshot + JPEG compression
│   ├── sender.py            # TCP socket client
│   └── main.py              # Mac entry point
│
├── win/                     # Runs on Windows
│   ├── receiver.py          # TCP socket server (QThread)
│   ├── catch_window.py      # PyQt6 transparent animation window
│   └── main.py              # Windows entry point
│
└── tests/
    ├── test_socket.py       # Socket communication test
    └── test_gesture.py      # Gesture detection tuning
```

---

## Setup

### Prerequisites

- **Python 3.10+** on both machines
- Both machines on the **same network** (wired or 5GHz Wi-Fi recommended)
- Webcam on the MacBook

### 1. Configure Network

Edit `config.py` and set your Windows laptop's IP:

```python
RECEIVER_IP = "192.168.1.100"   # ← Change to your Windows IP
RECEIVER_PORT = 5005
```

**Find your Windows IP:** Open Command Prompt → `ipconfig` → look for IPv4 Address.

### 2. Open Firewall (Windows)

On the Windows laptop, open port 5005:

```powershell
# Run in PowerShell as Administrator
New-NetFirewallRule -DisplayName "FisTransfer" -Direction Inbound -LocalPort 5005 -Protocol TCP -Action Allow
```

### 3. Install Dependencies

**On Mac:**
```bash
cd fistransfer
pip install -r requirements_mac.txt
```

**On Windows:**
```bash
cd fistransfer
pip install -r requirements_win.txt
```

### 4. Run

**Step 1 — Start the Windows receiver first:**
```bash
python -m win.main
```

**Step 2 — Start the Mac sender:**
```bash
python -m mac.main
```

### 5. Throw!

1. Hold your hand in front of the webcam
2. Pinch thumb + index finger together (grab)
3. Swipe your hand left (or right, depending on `SWIPE_DIRECTION` in config)
4. Watch the screen appear on your Windows laptop!

---

## Testing

### Socket Test (on a single machine)

```bash
python tests/test_socket.py
```

### Gesture Tuning

```bash
python tests/test_gesture.py
```

Use this to fine-tune `GRAB_THRESHOLD` and `SWIPE_VELOCITY_THRESHOLD` in `config.py`.

---

## Configuration Reference

| Setting | Default | Description |
|---------|---------|-------------|
| `RECEIVER_IP` | `192.168.1.100` | Windows laptop IP |
| `RECEIVER_PORT` | `5005` | TCP port |
| `JPEG_QUALITY` | `65` | Compression (60–70 optimal) |
| `TARGET_WIDTH` | `1920` | Downscale width |
| `TARGET_HEIGHT` | `1080` | Donscale height |
| `GRAB_THRESHOLD` | `0.07` | Grab sensitivity |
| `SWIPE_VELOCITY_THRESHOLD` | `0.02` | Swipe sensitivity |
| `SWIPE_DIRECTION` | `"left"` | `"left"` or `"right"` |
| `COOLDOWN_SECONDS` | `2.0` | Debounce between throws |
| `ANIMATION_DURATION_MS` | `300` | Slide-in speed |
| `AUTO_DISMISS_SECONDS` | `5` | Image display time |

---

## Keyboard Shortcuts

### Mac (Gesture Monitor)
| Key | Action |
|-----|--------|
| `q` | Quit |
| `t` | Test send (capture + send without gesture) |

### Windows (Catch Window)
| Action | Behavior |
|--------|----------|
| Double-click | Dismiss image immediately |
| Drag | Move image around |
| System tray → Quit | Exit cleanly |

---

## Performance Targets

| Stage | Target |
|-------|--------|
| Screen capture (mss) | < 25ms |
| JPEG encode (Q65) | < 20ms |
| Network transfer | < 50ms |
| Decode + render | < 20ms |
| **Total end-to-end** | **< 200ms** |

Enable profiling in `config.py` to see per-stage timings:
```python
ENABLE_PROFILING = True
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Connection refused | Check Windows firewall, verify IP in config |
| Gesture too sensitive | Increase `GRAB_THRESHOLD` (e.g., 0.09) |
| Gesture not triggering | Decrease `GRAB_THRESHOLD` (e.g., 0.05) |
| Image too large/slow | Lower `JPEG_QUALITY` (e.g., 50) |
| Webcam not found | Check `cv2.VideoCapture(0)` — try index 1 |
| High latency | Use wired connection or 5GHz Wi-Fi |
