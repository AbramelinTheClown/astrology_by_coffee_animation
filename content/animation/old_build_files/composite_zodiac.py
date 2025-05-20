import os
from PIL import Image
import numpy as np
from moviepy import VideoClip, VideoFileClip # Added VideoFileClip
import logging
import math

# --- Basic Logger Setup ---
def setup_simple_logger(log_file_path, level=logging.INFO):
    logger = logging.getLogger(os.path.basename(log_file_path).split('.')[0])
    logger.setLevel(level)
    if logger.hasHandlers():
        logger.handlers.clear()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    log_dir = os.path.dirname(log_file_path)
    if log_dir: 
        os.makedirs(log_dir, exist_ok=True)
    fh = logging.FileHandler(log_file_path, mode='w')
    fh.setLevel(level)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger

# --- Configuration ---
OUTPUT_DIR = r"D:\AI\astrology_by_coffee_v1\video\zodiac_animation_final_tests" 
os.makedirs(OUTPUT_DIR, exist_ok=True)

LOG_FILE = os.path.join(OUTPUT_DIR, "spinning_zodiac_on_video_full.log") # Log for full render
logger = setup_simple_logger(LOG_FILE)

logger.info("Starting spinning zodiac on pre-rendered video script (full length)...")

# Video and Image Paths
BASE_VIDEO_PATH = r"D:\AI\astrology_by_coffee_v1\video\prerenders\coffee_body_with_animated_smoke.mp4"
ZODIAC_IMAGE_PATH = r"D:\AI\astrology_by_coffee_v1\images\scene\coffee_zodiac_resized_500x500.png"
NEBBLES_BODY_PATH = r"D:\AI\astrology_by_coffee_v1\images\scene\nebbles_body.png"

# Zodiac Parameters
TARGET_ZODIAC_SIZE = (500, 500)
ZODIAC_PLACEMENT_OFFSET_X = 205
ZODIAC_PLACEMENT_OFFSET_Y = 310
ROTATION_PERIOD = 30.0

# Video Parameters
FPS = 24
# VIDEO_DURATION_TEST is removed; we'll use the full base video duration.
OUTPUT_FILENAME = "spinning_zodiac_on_prerender_full_length.mp4" # Updated filename
OUTPUT_FILEPATH = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)

# --- Helper Functions ---
def read_image_rgba(path, image_description="Image"):
    logger.debug(f"Reading {image_description}: {path}")
    try:
        img = Image.open(path).convert('RGBA')
        logger.debug(f"Successfully loaded {image_description}: {path}")
        return img
    except FileNotFoundError:
        logger.error(f"{image_description} file not found: {path}")
        return None
    except Exception as e:
        logger.exception(f"Error loading {image_description} {path}: {e}")
        return None

# --- Load and Prepare Assets ---
logger.info("Loading and preparing assets...")

# 1. Load Base Video Clip
logger.info(f"Loading base video from: {BASE_VIDEO_PATH}")
base_video_clip = None
try:
    base_video_clip = VideoFileClip(BASE_VIDEO_PATH)
    logger.info(f"Base video loaded. Duration: {base_video_clip.duration:.2f}s, Size: {base_video_clip.size}")
    canvas_size = base_video_clip.size # Get canvas size from the video
except Exception as e:
    logger.critical(f"Failed to load base video: {BASE_VIDEO_PATH}. Error: {e}")
    logger.exception(e)
    exit()

# 2. Load and Resize Zodiac Image
original_zodiac_img = read_image_rgba(ZODIAC_IMAGE_PATH, "Original Zodiac")
if not original_zodiac_img:
    logger.critical("Original Zodiac image failed to load. Exiting.")
    if base_video_clip: base_video_clip.close()
    exit()

resized_zodiac_img = None
try:
    logger.info(f"Resizing zodiac image to {TARGET_ZODIAC_SIZE}...")
    resample_filter = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS
    resized_zodiac_img = original_zodiac_img.resize(TARGET_ZODIAC_SIZE, resample_filter)
    logger.info("Zodiac image resized successfully.")
except Exception as e:
    logger.critical(f"Failed to resize zodiac image: {e}")
    if base_video_clip: base_video_clip.close()
    exit()

# 3. Load Nebbles Body Image
nebbles_body_img = read_image_rgba(NEBBLES_BODY_PATH, "Nebbles Body")

# Calculate the final top-left paste position for the (unrotated) resized zodiac image
canvas_center_x = canvas_size[0] / 2
canvas_center_y = canvas_size[1] / 2
target_zodiac_center_x = canvas_center_x + ZODIAC_PLACEMENT_OFFSET_X
target_zodiac_center_y = canvas_center_y + ZODIAC_PLACEMENT_OFFSET_Y
zodiac_paste_x = int(round(target_zodiac_center_x - resized_zodiac_img.width / 2))
zodiac_paste_y = int(round(target_zodiac_center_y - resized_zodiac_img.height / 2))
logger.info(f"Resized zodiac will be pasted at top-left: ({zodiac_paste_x}, {zodiac_paste_y}) for its centered placement.")


# --- Frame Generation Function ---
def make_frame(t):
    # 1. Get current frame from the base video
    # Ensure t does not exceed the base video's duration (MoviePy handles this for get_frame)
    base_video_frame_np = base_video_clip.get_frame(t)
    current_frame_pil = Image.fromarray(base_video_frame_np).convert('RGBA')

    # 2. Prepare and Paste Spinning Zodiac
    if resized_zodiac_img:
        angle_degrees = -(t / ROTATION_PERIOD) * 360 
        angle_degrees %= -360 
        
        resample_filter_rotate = Image.Resampling.BICUBIC if hasattr(Image, "Resampling") else Image.BICUBIC
        rotated_zodiac = resized_zodiac_img.rotate(angle_degrees, resample=resample_filter_rotate, expand=False)
        
        current_frame_pil.paste(rotated_zodiac, (zodiac_paste_x, zodiac_paste_y), rotated_zodiac)

    # 3. Paste Nebbles Body (on top)
    if nebbles_body_img:
        current_frame_pil.paste(nebbles_body_img, (0, 0), nebbles_body_img)
    
    current_frame_rgb_pil = current_frame_pil.convert('RGB')
    return np.array(current_frame_rgb_pil)

# --- Create and Write Video ---
# Determine the actual duration for the output clip - it will be the full base video duration
final_video_duration = base_video_clip.duration
logger.info(f"Starting video creation. Output Duration: {final_video_duration:.2f}s, FPS: {FPS}")
logger.info(f"Output will be saved to: {OUTPUT_FILEPATH}")

try:
    video_clip = VideoClip(make_frame, duration=final_video_duration)
    
    video_clip.write_videofile(
        OUTPUT_FILEPATH,
        fps=FPS,
        codec='libx264',
        audio=False, 
        threads=os.cpu_count() or 2,
        logger='bar',
        preset='medium' 
    )
    logger.info(f"Successfully rendered video to {OUTPUT_FILEPATH}")

except Exception as e:
    logger.critical("An error occurred during video writing:")
    logger.exception(e)
finally:
    if base_video_clip:
        try:
            base_video_clip.close()
            logger.info("Base video clip closed.")
        except Exception as e_close:
            logger.error(f"Error closing base video clip: {e_close}")

logger.info("Spinning zodiac on pre-rendered video script finished.")