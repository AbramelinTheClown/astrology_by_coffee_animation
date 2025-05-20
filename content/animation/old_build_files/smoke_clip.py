import os
from PIL import Image
import numpy as np # Not strictly needed for PIL image saving, but often a dependency
import logging
import random
import math # For smoke opacity

# --- Basic Logger Setup ---
def setup_simple_logger(log_file_path, level=logging.INFO):
    logger_name = os.path.basename(log_file_path).split('.')[0] + "_" + str(random.randint(1,10000))
    logger = logging.getLogger(logger_name) 
    logger.setLevel(level)
    if logger.hasHandlers(): 
        logger.handlers.clear()
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
    
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
MAIN_OUTPUT_DIR = r"D:\AI\astrology_by_coffee_v1\video\transparent_prerenders_granular" 
os.makedirs(MAIN_OUTPUT_DIR, exist_ok=True)

LOG_FILE = os.path.join(MAIN_OUTPUT_DIR, "prerender_just_smoke.log")
logger = setup_simple_logger(LOG_FILE)

logger.info("Starting pre-render script for JUST animated smoke sequence...")

# Image Paths
SMOKE_1_PATH = r"D:\AI\astrology_by_coffee_v1\images\scene\smoke_1.png"
SMOKE_2_PATH = r"D:\AI\astrology_by_coffee_v1\images\scene\smoke_2.png"
SMOKE_3_PATH = r"D:\AI\astrology_by_coffee_v1\images\scene\smoke_3.png"

# Animation Parameters
VIDEO_DURATION_MINUTES = 11
VIDEO_DURATION_SECONDS = 11
TOTAL_DURATION = (VIDEO_DURATION_MINUTES * 60) + VIDEO_DURATION_SECONDS
FPS = 24 
CANVAS_WIDTH = 1920 # Define the canvas size for the smoke animation
CANVAS_HEIGHT = 1080
CANVAS_SIZE = (CANVAS_WIDTH, CANVAS_HEIGHT)

# Smoke Animation Parameters
# pos_x_offset and pos_y_offset are relative to the CANVAS_CENTER
# You might want these to be relative to (0,0) if the smoke is always at a fixed screen spot
# or relative to a specific point if you intend to place this smoke layer over a cup later.
# For a generic smoke layer, centering them on the canvas might be a good default.
SMOKE_CANVAS_CENTER_X = CANVAS_WIDTH // 2
SMOKE_CANVAS_CENTER_Y = CANVAS_HEIGHT // 2

smoke_params = {
    "smoke_1": {"min": 0.1, "max": 0.5, "period": 4.0, "phase": 0.0,        "pos_x_offset": 0, "pos_y_offset": -150}, 
    "smoke_2": {"min": 0.05, "max": 0.4, "period": 5.5, "phase": np.pi / 3, "pos_x_offset": -20, "pos_y_offset": -160},
    "smoke_3": {"min": 0.15, "max": 0.6, "period": 3.0, "phase": np.pi * 2/3, "pos_x_offset": 20, "pos_y_offset": -140}, 
}

# Output folder names for PNG sequences
SMOKE_ONLY_ANIM_OUTPUT_FOLDER = os.path.join(MAIN_OUTPUT_DIR, "smoke_only_animation_rgba_frames")
os.makedirs(SMOKE_ONLY_ANIM_OUTPUT_FOLDER, exist_ok=True)

# --- Helper Function ---
def read_image_rgba(path, image_description="Image"):
    logger.debug(f"Reading {image_description}: {path}")
    try:
        img = Image.open(path).convert('RGBA') 
        logger.info(f"Successfully loaded {image_description}: {path} (Size: {img.size})")
        return img
    except FileNotFoundError:
        logger.error(f"{image_description} file not found: {path}")
        return None
    except Exception as e:
        logger.exception(f"Error loading {image_description} {path}: {e}")
        return None

def get_animated_opacity(t, min_opacity, max_opacity, period, phase_offset):
    if period == 0: return max_opacity 
    normalized_oscillation = (math.sin((2 * math.pi * t / period) + phase_offset) + 1) / 2.0
    opacity = min_opacity + (max_opacity - min_opacity) * normalized_oscillation
    return max(0.0, min(1.0, opacity)) 

# --- Frame Generation Function for SMOKE ONLY Layer ---
def make_smoke_only_frame(t, smoke_images_dict, smoke_anim_params_dict):
    current_frame_pil = Image.new('RGBA', CANVAS_SIZE, (0, 0, 0, 0)) # Start with a transparent canvas
    
    for smoke_name, smoke_original_img in smoke_images_dict.items():
        if not smoke_original_img: 
            logger.debug(f"Skipping {smoke_name} for frame at t={t:.2f}s as it's not loaded.")
            continue
        
        params = smoke_anim_params_dict[smoke_name]
        opacity = get_animated_opacity(t, params["min"], params["max"], params["period"], params["phase"])
        
        smoke_to_animate = smoke_original_img.copy() 
        alpha_channel = smoke_to_animate.getchannel('A')
        clamped_opacity = max(0.0, min(1.0, opacity)) 
        
        # Create new alpha data by scaling existing alpha
        modified_alpha_data = [int(p * clamped_opacity) for p in alpha_channel.getdata()]
        modified_alpha_channel = Image.new('L', alpha_channel.size)
        modified_alpha_channel.putdata(modified_alpha_data)
        
        smoke_to_animate.putalpha(modified_alpha_channel)
        
        # Smoke position relative to the layer's canvas center + its specific offset
        smoke_paste_x = SMOKE_CANVAS_CENTER_X + params["pos_x_offset"] - (smoke_to_animate.width // 2)
        smoke_paste_y = SMOKE_CANVAS_CENTER_Y + params["pos_y_offset"] - (smoke_to_animate.height // 2)
        
        current_frame_pil.paste(smoke_to_animate, (smoke_paste_x, smoke_paste_y), smoke_to_animate)
        # logger.debug(f"  Smoke '{smoke_name}' opacity: {opacity:.2f} at ({smoke_paste_x},{smoke_paste_y}) for t={t:.2f}s") # Can be verbose
        
    return current_frame_pil 

# --- Main Rendering Logic ---
def render_smoke_sequence():
    logger.info("Loading smoke images for pre-render...")
    smoke_images_loaded = {
        "smoke_1": read_image_rgba(SMOKE_1_PATH, "Smoke 1"),
        "smoke_2": read_image_rgba(SMOKE_2_PATH, "Smoke 2"),
        "smoke_3": read_image_rgba(SMOKE_3_PATH, "Smoke 3"),
    }

    # Check if at least one smoke image was loaded
    if not any(smoke_images_loaded.values()):
        logger.error("No smoke images were loaded. Aborting smoke sequence rendering.")
        return

    total_frames_to_render = int(TOTAL_DURATION * FPS)
    logger.info(f"Total frames to render for smoke sequence: {total_frames_to_render} ({TOTAL_DURATION}s at {FPS} FPS)")
    logger.warning("RENDERING SMOKE SEQUENCE WILL TAKE A VERY LONG TIME AND CONSUME SIGNIFICANT DISK SPACE!")

    logger.info(f"Starting SMOKE ONLY animation pre-render to: {SMOKE_ONLY_ANIM_OUTPUT_FOLDER}")
    
    for i in range(total_frames_to_render):
        t = i / FPS
        if i % (FPS * 30) == 0: # Log progress every 30 seconds of video time
            logger.info(f"Smoke Only Anim: Processing frame {i}/{total_frames_to_render} (t={t:.2f}s)")
        
        frame_pil = make_smoke_only_frame(t, smoke_images_loaded, smoke_params)
        try:
            frame_pil.save(os.path.join(SMOKE_ONLY_ANIM_OUTPUT_FOLDER, f"smoke_only_frame_{i:05d}.png"))
        except Exception as e:
            logger.exception(f"Error saving Smoke Only frame {i}: {e}"); break 
    logger.info("SMOKE ONLY animation pre-render finished.")


if __name__ == "__main__":
    confirm = input(f"This script will render {int(TOTAL_DURATION * FPS)} PNG frames for the smoke animation ({TOTAL_DURATION/60:.2f} minutes). This will take a very long time and a lot of disk space. Are you sure you want to proceed? (yes/no): ")
    if confirm.lower() == 'yes':
        render_smoke_sequence()
    else:
        logger.info("Smoke pre-rendering cancelled by user.")
    
    logger.info("Smoke pre-render script finished.")
