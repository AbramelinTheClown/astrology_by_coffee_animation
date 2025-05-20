import os
from PIL import Image, ImageEnhance
import numpy as np
from moviepy import VideoClip
import logging
import math # For sine wave

# --- Basic Logger Setup ---
def setup_simple_logger(log_file_path, level=logging.INFO):
    logger = logging.getLogger(os.path.basename(log_file_path).split('.')[0]) # Use script name as logger name
    logger.setLevel(level)
    if logger.hasHandlers():
        logger.handlers.clear()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    fh = logging.FileHandler(log_file_path, mode='w')
    fh.setLevel(level)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger

# --- Configuration ---
OUTPUT_DIR = r"D:\AI\astrology_by_coffee_v1\video\prerenders" # Dedicated output for this pre-render
os.makedirs(OUTPUT_DIR, exist_ok=True)

LOG_FILE = os.path.join(OUTPUT_DIR, "smoke_animation_prerender.log")
logger = setup_simple_logger(LOG_FILE)

logger.info("Starting smoke animation pre-render script...")

# Image Paths (ensure these are correct)
BACKGROUND_PATH = r"D:\AI\astrology_by_coffee_v1\images\scene\coffee_house_back_stage.png"
SMOKE_1_PATH = r"D:\AI\astrology_by_coffee_v1\images\scene\smoke_1.png"
SMOKE_2_PATH = r"D:\AI\astrology_by_coffee_v1\images\scene\smoke_2.png"
SMOKE_3_PATH = r"D:\AI\astrology_by_coffee_v1\images\scene\smoke_3.png"
COFFEE_BODY_PATH = r"D:\AI\astrology_by_coffee_v1\images\scene\coffee_body.png"

# Video Parameters
VIDEO_DURATION_MINUTES = 11
VIDEO_DURATION_SECONDS = 11
TOTAL_DURATION = (VIDEO_DURATION_MINUTES * 60) + VIDEO_DURATION_SECONDS  # 671 seconds
FPS = 24 # Frames per second
OUTPUT_FILENAME = "coffee_body_with_animated_smoke.mp4"
OUTPUT_FILEPATH = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)

# Smoke Animation Parameters (customize these for variation)
# Each dict: min_opacity, max_opacity, period (seconds for one pulse cycle), phase_offset (0 to 2*pi)
smoke_params = {
    "smoke_1": {"min": 0.2, "max": 0.7, "period": 5.0, "phase": 0.0},
    "smoke_2": {"min": 0.15, "max": 0.6, "period": 6.5, "phase": np.pi / 2}, # Different period and phase
    "smoke_3": {"min": 0.25, "max": 0.75, "period": 4.0, "phase": np.pi},    # Different again
}

# --- Helper Functions ---
def read_image_rgba(path):
    logger.debug(f"Reading image: {path}")
    try:
        img = Image.open(path).convert('RGBA')
        logger.debug(f"Successfully loaded image: {path}")
        return img
    except FileNotFoundError:
        logger.error(f"Image file not found: {path}")
        return None
    except Exception as e:
        logger.exception(f"Error loading image {path}: {e}")
        return None

def get_animated_opacity(t, min_opacity, max_opacity, period, phase_offset):
    """Calculates opacity based on a sine wave for pulsing effect."""
    if period == 0: return max_opacity # Avoid division by zero
    # Sine wave oscillates between -1 and 1. We map it to 0 and 1, then to min_opacity and max_opacity.
    # (sin(x) + 1) / 2 gives a range of [0, 1]
    normalized_oscillation = (math.sin((2 * math.pi * t / period) + phase_offset) + 1) / 2.0
    opacity = min_opacity + (max_opacity - min_opacity) * normalized_oscillation
    return max(0.0, min(1.0, opacity)) # Clamp between 0 and 1

# --- Load Images ---
logger.info("Loading images...")
background_img = read_image_rgba(BACKGROUND_PATH)
smoke_images_orig = {
    "smoke_1": read_image_rgba(SMOKE_1_PATH),
    "smoke_2": read_image_rgba(SMOKE_2_PATH),
    "smoke_3": read_image_rgba(SMOKE_3_PATH),
}
coffee_body_img = read_image_rgba(COFFEE_BODY_PATH)

# Validate essential images
if not background_img:
    logger.critical("Background image failed to load. Exiting.")
    exit()
if not coffee_body_img:
    logger.critical("Coffee body image failed to load. Exiting.")
    exit()
for name, img in smoke_images_orig.items():
    if not img:
        logger.warning(f"{name} image failed to load. It will be skipped.")

canvas_size = background_img.size
logger.info(f"Canvas size set to: {canvas_size}")

# --- Frame Generation Function ---
def make_frame(t):
    logger.debug(f"Generating frame for t={t:.2f}s")
    
    # Start with a copy of the background
    current_frame = background_img.copy()

    # Composite animated smoke layers
    for smoke_name, smoke_original_img in smoke_images_orig.items():
        if not smoke_original_img: # Skip if this smoke image failed to load
            continue

        params = smoke_params[smoke_name]
        opacity = get_animated_opacity(t, params["min"], params["max"], params["period"], params["phase"])
        
        if smoke_original_img.mode != 'RGBA': # Should already be RGBA due to read_image_rgba
            logger.warning(f"{smoke_name} is not RGBA, attempting conversion for alpha manipulation.")
            smoke_to_animate = smoke_original_img.convert('RGBA')
        else:
            smoke_to_animate = smoke_original_img.copy() # Work on a copy

        # Get the alpha channel
        alpha = smoke_to_animate.getchannel('A')
        
        # Modify alpha: each pixel's current alpha is multiplied by the calculated opacity
        # The 'point' method applies a function to each pixel in the channel
        # Ensure opacity is between 0 and 1
        clamped_opacity = max(0.0, min(1.0, opacity)) 
        modified_alpha_pixels = alpha.point(lambda p: int(p * clamped_opacity))
        
        smoke_to_animate.putalpha(modified_alpha_pixels)
        
        # Paste the smoke layer using its own modified alpha channel as the mask
        current_frame.paste(smoke_to_animate, (0, 0), smoke_to_animate)
        logger.debug(f"  {smoke_name} opacity: {opacity:.2f}")

    # Composite coffee body on top of everything
    current_frame.paste(coffee_body_img, (0, 0), coffee_body_img) # Assuming coffee_body_img is RGBA

    # Convert to RGB for MoviePy (MoviePy typically expects RGB frames)
    # If you need alpha in the output video, you'd use a different codec and keep RGBA
    # For MP4, RGB is standard.
    current_frame_rgb = current_frame.convert('RGB')
    
    return np.array(current_frame_rgb)

# --- Create and Write Video ---
logger.info(f"Starting video creation. Duration: {TOTAL_DURATION}s, FPS: {FPS}")
logger.info(f"Output will be saved to: {OUTPUT_FILEPATH}")

try:
    video_clip = VideoClip(make_frame, duration=TOTAL_DURATION)
    
    # For very long videos, MoviePy might benefit from specific audio settings even if none is added,
    # or you might want to ensure no audio track is created if it's silent.
    # If you want a truly silent video (no audio track):
    # video_clip.write_videofile(OUTPUT_FILEPATH, fps=FPS, codec='libx264', audio=False, threads=os.cpu_count() or 2, logger='bar', preset='medium')
    
    video_clip.write_videofile(
        OUTPUT_FILEPATH,
        fps=FPS,
        codec='libx264', # Common codec for MP4
        audio=False, # Explicitly no audio track for this pre-render
        threads=os.cpu_count() or 4, # Use available CPUs
        logger='bar', # Progress bar
        preset='medium' # 'ultrafast', 'fast', 'medium', 'slow', 'veryslow' - affects speed vs quality/size
    )
    logger.info(f"Successfully pre-rendered video to {OUTPUT_FILEPATH}")

except Exception as e:
    logger.critical("An error occurred during video writing:")
    logger.exception(e)

logger.info("Pre-render script finished.")