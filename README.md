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

- **Python 3.10+** on desktops
- **Android 8.0+** for mobile
- Both machines on the **same network** (wired or 5GHz Wi-Fi recommended)

### 🚀 Android Integration (New!)

FisTransfer now supports full **Android-to-Desktop** and **Android-to-Android** transfers with persistent background support.

1.  **Install the APK**: Located in `android/app/build/outputs/apk/debug/app-debug.apk`.
2.  **Enable Background Mode**: Tap "Activate Floating Gestures" to keep the app connected even when minimized.
3.  **Floating Gesture Bubble**: Use the draggable circular camera preview to perform gestures while using other apps.
4.  **Universal Discovery**: Phones will automatically find Laptops or other Phones on the same network.

---

## Technical Highlights (Mobile)

*   **Foreground Service**: Keeps network listeners alive via a persistent notification.
*   **MediaProjection API**: Captures system-wide screenshots from any app.
*   **Floating Camera Overlay**: Bypasses Android's background camera restrictions for continuous gesture tracking.
*   **Stream-to-Disk**: Handles large files (>500MB) without memory issues.

---

## Performance Targets

| Stage | Target |
|-------|--------|
| Screen capture (mss/projection) | < 35ms |
| JPEG encode (Q70) | < 25ms |
| Network transfer (TCP/UDP) | < 40ms |
| Decode + render | < 20ms |
| **Total end-to-end** | **< 200ms** |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Connection refused | Check Firewall, verify IP/Hotspot settings |
| Background Gestures lag | Ensure "No restrictions" in Battery settings |
| Bubble disappears | Re-grant "Display Over Other Apps" permission |
| Peer not found | Verify both devices are on the same 2.4/5GHz band |
