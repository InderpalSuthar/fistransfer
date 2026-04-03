"""
FisTransfer — Glassmorphic Image Viewer
=========================================
Spawns a sleek, translucent floating borderless window to display
received screenshots and image files gracefully over the active desktop.
"""

import sys
import tkinter as tk
from PIL import Image, ImageTk

def show_glass_window(image_path):
    root = tk.Tk()
    
    # ── Remove standard window borders ──
    # Setting overrideredirect avoids the clunky OS title bar.
    root.overrideredirect(True)
    
    # ── Glassmorphism alpha blending ──
    # 92% opacity gives a slight translucent peek at the background
    root.attributes("-alpha", 0.92)
    
    # Force it to sit over all other windows
    root.attributes("-topmost", True)
    
    # Dark modern background
    bg_color = "#18181A"
    root.configure(bg=bg_color)
    
    try:
        img = Image.open(image_path)
    except Exception as e:
        print(f"Error loading image for preview: {e}")
        return

    # ── Smart UI Scaling ──
    # Prevent giant 4k photos from breaking out of the screen bounds
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    
    max_w = int(screen_w * 0.75)
    max_h = int(screen_h * 0.75)
    
    orig_w, orig_h = img.size
    
    # Maintain aspect ratio while shrinking if needed
    scale = min(max_w / orig_w, max_h / orig_h)
    if scale < 1.0:
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    else:
        new_w, new_h = orig_w, orig_h

    photo = ImageTk.PhotoImage(img)
    
    # ── Center window perfectly on the primary screen ──
    x = int((screen_w / 2) - (new_w / 2))
    y = int((screen_h / 2) - (new_h / 2))
    root.geometry(f"{new_w}x{new_h}+{x}+{y}")
    
    # ── Create a slim pseudo-border for the glass look ──
    frame = tk.Frame(root, bg=bg_color, highlightbackground="#3A3A3D", highlightthickness=2)
    frame.pack(fill="both", expand=True)

    lbl = tk.Label(frame, image=photo, bg=bg_color)
    lbl.image = photo  # Keep a reference!
    lbl.pack(fill="both", expand=True)
    
    # "Click to dismiss" hint logic
    hint = tk.Label(frame, text=" Click anywhere to dismiss ", bg="#000000", fg="#BBBBBB", font=("Arial", 11))
    hint.place(relx=0.5, rely=0.96, anchor="center")

    # ── Event Binding ──
    def close_app(event=None):
        root.destroy()
        
    # Close immediately if the user touches the image
    root.bind("<Button-1>", close_app)
    root.bind("<Escape>", close_app)
    
    # Alternatively, auto-dismiss after 6 seconds to not block their flow
    root.after(6000, close_app)

    # Launch UI
    root.mainloop()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        show_glass_window(sys.argv[1])
