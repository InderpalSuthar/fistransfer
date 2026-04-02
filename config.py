"""
FisTransfer — Shared Configuration
===================================
Central config used by both Mac (sender) and Windows (receiver) sides.
Update RECEIVER_IP to match your Windows laptop's static IP.
"""

# ─── Network ────────────────────────────────────────────────────────────────────
RECEIVER_IP = "192.168.1.100"       # Windows laptop static IP — CHANGE THIS
RECEIVER_PORT = 5005                # TCP port (must be open in Windows Defender)
SOCKET_BUFFER_SIZE = 1_048_576      # 1 MB send/recv buffer

# ─── Screen Capture ─────────────────────────────────────────────────────────────
JPEG_QUALITY = 65                   # JPEG compression (60–70 sweet spot)
TARGET_WIDTH = 1920                 # Downscale to Windows resolution
TARGET_HEIGHT = 1080

# ─── Gesture Detection ──────────────────────────────────────────────────────────
GRAB_THRESHOLD = 0.35               # Normalized thumb–index distance for "grab"
                                    # Open hand ≈ 0.5+, closed fist ≈ 0.2–0.3, pinch ≈ 0.05
SWIPE_VELOCITY_THRESHOLD = 0.02     # Min X-velocity to trigger throw
SMA_WINDOW = 10                     # Frames for Simple Moving Average
SWIPE_DIRECTION = "left"            # "left" = Windows is to the left of Mac
                                    # "right" = Windows is to the right of Mac
COOLDOWN_SECONDS = 2.0              # Debounce after a throw

# ─── UI Animation ───────────────────────────────────────────────────────────────
ANIMATION_DURATION_MS = 300         # Slide-in duration
ANIMATION_EASING = "OutQuad"        # QEasingCurve type
AUTO_DISMISS_SECONDS = 5            # Seconds before fade-out
FADE_DURATION_MS = 500              # Fade-out duration

# ─── Profiling ───────────────────────────────────────────────────────────────────
ENABLE_PROFILING = True             # Print timing at each pipeline stage
