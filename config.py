"""
FisTransfer — Shared Configuration
===================================
Central config used by BOTH Mac and Windows sides.
Each machine runs gesture detection + screen capture + send + receive.

Transfer modes:
  A) SCREENSHOT: GRAB → CATCH handshake → screenshot transfer
  B) FILE:       PINCH file → release pinch on Windows → file transfer
"""

# ─── Network ────────────────────────────────────────────────────────────────────
DISCOVERY_PORT = 5004               # UDP port for automatic IP discovery
SIGNAL_PORT = 5005                  # TCP port for handshake signals
TRANSFER_PORT = 5006                # TCP port for image data transfer
FILE_TRANSFER_PORT = 5007           # TCP port for file transfers
SOCKET_BUFFER_SIZE = 1_048_576      # 1 MB send/recv buffer

MAC_IP = "10.211.55.2"              # (Fallback) Mac on Parallels
WIN_IP = "10.211.55.3"              # (Fallback) Windows VM on Parallels

# ─── Camera Sources ─────────────────────────────────────────────────────────────
MAC_CAMERA = 0                                      # Mac: built-in webcam (index 0)
WIN_CAMERA = "http://10.108.233.61:4747/video"       # Windows: DroidCam IP stream

# ─── Handshake Protocol ─────────────────────────────────────────────────────────
# Signal bytes sent between machines
SIGNAL_GRAB_READY = b"GRAB"         # GRAB → CATCH screenshot handshake
SIGNAL_CATCH_ACCEPT = b"CATCH"       # Peer accepted screenshot
SIGNAL_FILE_READY = b"FILE_OFFER"    # PINCH → file picked up, ready to send
SIGNAL_FILE_ACCEPT = b"FILE_ACCEPT"   # Peer accepted file (pinch released)
SIGNAL_HEARTBEAT = b"HEARTBEAT"      # Keep-alive ping
HANDSHAKE_TIMEOUT = 15.0            # Seconds to wait for peer response

# ─── Screen Capture ─────────────────────────────────────────────────────────────
JPEG_QUALITY = 95                   # JPEG quality (95 = near-lossless, like native screenshot)
TARGET_WIDTH = 0                    # 0 = native resolution (no downscale)
TARGET_HEIGHT = 0                   # Set to 1920x1080 to downscale for slower networks

# ─── Gesture Detection ──────────────────────────────────────────────────────────
GRAB_THRESHOLD = 0.35               # Normalized thumb–index distance for "grab"
                                    # Open hand ≈ 0.5+, closed fist ≈ 0.2–0.3
CATCH_THRESHOLD = 0.45              # Distance ABOVE which hand is "open" (catch)
PINCH_THRESHOLD = 0.22              # Thumb+index close = pinch (fingers extended)
PINCH_RELEASE_THRESHOLD = 0.35      # Thumb+index apart after pinch = release/drop
SWIPE_VELOCITY_THRESHOLD = 0.02     # Min X-velocity (optional)
SMA_WINDOW = 10                     # Frames for Simple Moving Average
COOLDOWN_SECONDS = 3.0              # Debounce after a transfer

# ─── Cursor Control ─────────────────────────────────────────────────────────────
CURSOR_ENABLED = False              # Hand controls the mouse cursor
CURSOR_SMOOTHING = 5                # Frames of position averaging (anti-jitter)
CURSOR_SPEED = 1.5                  # Cursor speed multiplier

# ─── UI Animation ───────────────────────────────────────────────────────────────
SHOW_CAMERA_WINDOW = False          # Set to True to see the camera feed and gesture debug info
ANIMATION_DURATION_MS = 300         # Slide-in duration
ANIMATION_EASING = "OutQuad"        # QEasingCurve type
AUTO_DISMISS_SECONDS = 5            # Seconds before fade-out
FADE_DURATION_MS = 500              # Fade-out duration

# ─── Profiling ───────────────────────────────────────────────────────────────────
ENABLE_PROFILING = True             # Print timing at each pipeline stage
