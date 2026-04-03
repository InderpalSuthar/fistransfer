"""
FisTransfer — Shared Configuration
===================================
Central config used by BOTH Mac and Windows sides.
Each machine runs gesture detection + screen capture + send + receive.

Transfer is a TWO-STEP HANDSHAKE:
  1. Mac:     GRAB gesture → sends "READY" signal
  2. Windows: CATCH gesture → sends "ACCEPT" signal
  3. Mac captures screen and sends it to Windows
"""

# ─── Network ────────────────────────────────────────────────────────────────────
MAC_IP = "10.211.55.2"              # Mac on Parallels network (bridge100)
WIN_IP = "10.211.55.3"              # Windows VM on Parallels
SIGNAL_PORT = 5005                  # TCP port for handshake signals
TRANSFER_PORT = 5006                # TCP port for image data transfer
SOCKET_BUFFER_SIZE = 1_048_576      # 1 MB send/recv buffer

# ─── Camera Sources ─────────────────────────────────────────────────────────────
MAC_CAMERA = 0                                      # Mac: built-in webcam (index 0)
WIN_CAMERA = "http://10.120.92.47:4747/video"       # Windows: DroidCam IP stream

# ─── Handshake Protocol ─────────────────────────────────────────────────────────
# Signal bytes sent between machines
SIGNAL_GRAB_READY = b"GRAB_READY"   # Mac → Windows: "I grabbed, ready to send"
SIGNAL_CATCH_ACCEPT = b"CATCH_OK"   # Windows → Mac: "I caught, send it!"
SIGNAL_HEARTBEAT = b"HEARTBEAT"     # Keep-alive ping
HANDSHAKE_TIMEOUT = 10.0            # Seconds to wait for catch after grab

# ─── Screen Capture ─────────────────────────────────────────────────────────────
JPEG_QUALITY = 95                   # JPEG quality (95 = near-lossless, like native screenshot)
TARGET_WIDTH = 0                    # 0 = native resolution (no downscale)
TARGET_HEIGHT = 0                   # Set to 1920x1080 to downscale for slower networks

# ─── Gesture Detection ──────────────────────────────────────────────────────────
GRAB_THRESHOLD = 0.35               # Normalized thumb–index distance for "grab"
                                    # Open hand ≈ 0.5+, closed fist ≈ 0.2–0.3
CATCH_THRESHOLD = 0.55              # Distance ABOVE which hand is "open" (catch)
                                    # Open palm = catch gesture on Windows
SWIPE_VELOCITY_THRESHOLD = 0.02     # Min X-velocity (used as optional extra)
SMA_WINDOW = 10                     # Frames for Simple Moving Average
COOLDOWN_SECONDS = 3.0              # Debounce after a transfer

# ─── UI Animation ───────────────────────────────────────────────────────────────
ANIMATION_DURATION_MS = 300         # Slide-in duration
ANIMATION_EASING = "OutQuad"        # QEasingCurve type
AUTO_DISMISS_SECONDS = 5            # Seconds before fade-out
FADE_DURATION_MS = 500              # Fade-out duration

# ─── Profiling ───────────────────────────────────────────────────────────────────
ENABLE_PROFILING = True             # Print timing at each pipeline stage
