import os
from PIL import Image
import numpy as np # For math functions like sin, pi
import logging
import random
import math # For math.sin

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
MAIN_OUTPUT_DIR = r"D:\AI\astrology_by_coffee_v1\video\transparent_prerenders_fresh" 
os.makedirs(MAIN_OUTPUT_DIR, exist_ok=True)

LOG_FILE = os.path.join(MAIN_OUTPUT_DIR, "prerender_coffee_character_sequence.log")
logger = setup_simple_logger(LOG_FILE)

logger.info("Starting pre-render script for Coffee Character sequence (smoke & blinks)...")

# Image Paths
COFFEE_BODY_PATH = r"D:\AI\astrology_by_coffee_v1\images\scene\coffee_body.png"
COFFEE_BLINK_IMAGE_PATH = r"D:\AI\astrology_by_coffee_v1\images\scene\coffee_blinks.png"
SMOKE_1_PATH = r"D:\AI\astrology_by_coffee_v1\images\scene\smoke_1.png"
SMOKE_2_PATH = r"D:\AI\astrology_by_coffee_v1\images\scene\smoke_2.png"
SMOKE_3_PATH = r"D:\AI\astrology_by_coffee_v1\images\scene\smoke_3.png"

# Animation Parameters
VIDEO_DURATION_MINUTES = 11
VIDEO_DURATION_SECONDS = 11
# For testing, uncomment below and comment out the full duration
# VIDEO_DURATION_MINUTES = 0
# VIDEO_DURATION_SECONDS = 10 # Short duration for testing
TOTAL_DURATION = (VIDEO_DURATION_MINUTES * 60) + VIDEO_DURATION_SECONDS
FPS = 24 

# Canvas size for this pre-rendered layer. Should ideally match your final video composition size.
CANVAS_WIDTH = 1920 
CANVAS_HEIGHT = 1080
CANVAS_SIZE = (CANVAS_WIDTH, CANVAS_HEIGHT)

# Coffee Blink Animation Parameters
COFFEE_BLINK_MIN_INTERVAL = 7.0
COFFEE_BLINK_MAX_INTERVAL = 15.0
COFFEE_BLINK_DURATION = 0.2     # seconds (how long the eyes stay closed)

# Smoke Animation Parameters
# Each dict: 
#   min_opacity, max_opacity, 
#   period (seconds for one pulse cycle), 
#   phase_offset (0 to 2*pi for variation),
#   base_x, base_y (top-left position of this smoke image on the canvas, relative to where coffee body will be)
#   You will need to carefully determine base_x and base_y for each smoke layer
#   to make it look like it's coming from the coffee cup.
#   These are offsets from the top-left of where coffee_body is pasted.
#   If coffee_body is centered, then these are offsets from that centered position's top-left.
smoke_params = {
    "smoke_1": {"min": 0.1, "max": 0.6, "period": 4.5, "phase": 0.0,        "base_x": 0, "base_y": -180}, # Example: Centered X, above coffee body
    "smoke_2": {"min": 0.05, "max": 0.5, "period": 6.0, "phase": np.pi / 2, "base_x": -30, "base_y": -200},# Example: Slightly left, higher
    "smoke_3": {"min": 0.15, "max": 0.7, "period": 3.5, "phase": np.pi,     "base_x": 30, "base_y": -170}, # Example: Slightly right, different height
}

# Output folder name for the Coffee character PNG sequence
COFFEE_SEQUENCE_OUTPUT_FOLDER = os.path.join(MAIN_OUTPUT_DIR, "coffee_character_with_smoke_blinks_rgba_frames")
os.makedirs(COFFEE_SEQUENCE_OUTPUT_FOLDER, exist_ok=True)

# --- Global variables for animation states ---
coffee_next_blink_time_global = 0.0 
coffee_blink_end_time_global = 0.0

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
    # Sine wave oscillates between -1 and 1. (sin(x)+1)/2 maps it to [0,1]
    normalized_oscillation = (math.sin((2 * math.pi * t / period) + phase_offset) + 1) / 2.0
    opacity = min_opacity + (max_opacity - min_opacity) * normalized_oscillation
    return max(0.0, min(1.0, opacity)) # Clamp between 0 and 1

# --- Frame Generation Function for FINAL COFFEE Layer ---
def make_final_coffee_character_frame(t, coffee_body_img, coffee_blink_img, smoke_images_dict, smoke_anim_params_dict):
    global coffee_next_blink_time_global, coffee_blink_end_time_global

    # Start with a new, fully transparent canvas for this frame
    current_frame_pil = Image.new('RGBA', CANVAS_SIZE, (0, 0, 0, 0)) 

    # --- Define Coffee Body Position ---
    # For this pre-render, we'll center the coffee body on the canvas.
    # All other elements (smoke, blink) will be positioned relative to this.
    if coffee_body_img:
        coffee_body_center_x = CANVAS_SIZE[0] // 2
        coffee_body_center_y = CANVAS_SIZE[1] // 2
        # Top-left position for coffee_body_img to be centered
        cb_paste_x = coffee_body_center_x - (coffee_body_img.width // 2)
        cb_paste_y = coffee_body_center_y - (coffee_body_img.height // 2)
    else: # Fallback if coffee body isn't loaded, though script should exit earlier
        cb_paste_x = 0
        cb_paste_y = 0
        logger.warning(f"Coffee body image not available for frame at t={t:.2f}s. Smoke/blink position might be off.")

    # 1. Paste Animated Smoke Layers (UNDER coffee body)
    for smoke_name, smoke_original_img in smoke_images_dict.items():
        if not smoke_original_img: 
            logger.debug(f"Skipping {smoke_name} for frame at t={t:.2f}s as it's not loaded.")
            continue
        
        params = smoke_anim_params_dict[smoke_name]
        opacity = get_animated_opacity(t, params["min"], params["max"], params["period"], params["phase"])
        
        smoke_to_animate = smoke_original_img.copy() 
        alpha_channel = smoke_to_animate.getchannel('A')
        clamped_opacity = max(0.0, min(1.0, opacity)) 
        
        modified_alpha_data = [int(p * clamped_opacity) for p in alpha_channel.getdata()]
        modified_alpha_channel = Image.new('L', alpha_channel.size)
        modified_alpha_channel.putdata(modified_alpha_data)
        smoke_to_animate.putalpha(modified_alpha_channel)
        
        # Calculate smoke paste position:
        # It's the coffee body's top-left + smoke's base_x/base_y offset
        smoke_paste_x = cb_paste_x + params["base_x"]
        smoke_paste_y = cb_paste_y + params["base_y"]
        
        current_frame_pil.paste(smoke_to_animate, (smoke_paste_x, smoke_paste_y), smoke_to_animate)
        # logger.debug(f"  Smoke '{smoke_name}' opacity: {opacity:.2f} at ({smoke_paste_x},{smoke_paste_y}) for t={t:.2f}s")

    # 2. Paste Coffee Body (on top of smoke)
    if coffee_body_img:
        current_frame_pil.paste(coffee_body_img, (cb_paste_x, cb_paste_y), coffee_body_img)

    # 3. Coffee Blink Logic (on top of coffee body)
    is_coffee_blinking_now = False
    if t >= coffee_blink_end_time_global: 
        if t >= coffee_next_blink_time_global: 
            is_coffee_blinking_now = True
            coffee_blink_end_time_global = t + COFFEE_BLINK_DURATION
            coffee_next_blink_time_global = coffee_blink_end_time_global + \
                                           random.uniform(COFFEE_BLINK_MIN_INTERVAL, COFFEE_BLINK_MAX_INTERVAL)
    elif t < coffee_blink_end_time_global and t >= (coffee_blink_end_time_global - COFFEE_BLINK_DURATION):
        is_coffee_blinking_now = True

    if is_coffee_blinking_now and coffee_blink_img:
        # Assuming blink image should be pasted at the same base position as coffee_body
        # if it's a full overlay of the face with closed eyes.
        # If blink_image is just the eyes, its paste position needs to be relative to coffee_body.
        current_frame_pil.paste(coffee_blink_img, (cb_paste_x, cb_paste_y), coffee_blink_img)
        # logger.debug(f"Coffee: Pasting blink image at t={t:.2f}s")
        
    return current_frame_pil 

# --- Main Rendering Logic ---
def render_coffee_character_sequence():
    global coffee_next_blink_time_global # Initialize for the first blink

    logger.info("Loading images for Coffee Character pre-render...")
    coffee_body_img_loaded = read_image_rgba(COFFEE_BODY_PATH, "Coffee Body")
    coffee_blink_img_loaded = read_image_rgba(COFFEE_BLINK_IMAGE_PATH, "Coffee Blink")
    smoke_images_loaded = { # Load smoke images into a dictionary
        "smoke_1": read_image_rgba(SMOKE_1_PATH, "Smoke 1"),
        "smoke_2": read_image_rgba(SMOKE_2_PATH, "Smoke 2"),
        "smoke_3": read_image_rgba(SMOKE_3_PATH, "Smoke 3"),
    }

    if not coffee_body_img_loaded: 
        logger.error("Coffee body image failed to load. Cannot render Coffee sequence.")
        return
    if not all(smoke_images_loaded.values()): # Check if any smoke image failed to load
        logger.warning("One or more smoke images failed to load. Smoke animation might be incomplete.")
    if not coffee_blink_img_loaded:
        logger.warning("Coffee blink image failed to load. Coffee character will not blink.")


    total_frames_to_render = int(TOTAL_DURATION * FPS)
    logger.info(f"Total frames to render for Coffee Character sequence: {total_frames_to_render} ({TOTAL_DURATION}s at {FPS} FPS)")
    logger.warning("RENDERING COFFEE CHARACTER SEQUENCE WILL TAKE A VERY LONG TIME AND CONSUME SIGNIFICANT DISK SPACE!")

    logger.info(f"Starting Coffee Character (smoke, body, blinks) animation pre-render to: {COFFEE_SEQUENCE_OUTPUT_FOLDER}")
    # Initialize first blink time
    coffee_next_blink_time_global = random.uniform(COFFEE_BLINK_MIN_INTERVAL / 3, COFFEE_BLINK_MAX_INTERVAL / 3) 
    
    for i in range(total_frames_to_render):
        t = i / FPS
        if i % (FPS * 30) == 0: # Log progress every 30 seconds of video time
            logger.info(f"Coffee Character Anim: Processing frame {i}/{total_frames_to_render} (t={t:.2f}s)")
        
        frame_pil = make_final_coffee_character_frame(t, 
                                                      coffee_body_img_loaded, 
                                                      coffee_blink_img_loaded, 
                                                      smoke_images_loaded, 
                                                      smoke_params)
        try:
            # Save as PNG to preserve transparency
            frame_pil.save(os.path.join(COFFEE_SEQUENCE_OUTPUT_FOLDER, f"coffee_char_frame_{i:05d}.png"))
        except Exception as e:
            logger.exception(f"Error saving Coffee Character frame {i}: {e}"); break 
    logger.info("Coffee Character animation pre-render finished.")


if __name__ == "__main__":
    confirm = input(f"This script will render {int(TOTAL_DURATION * FPS)} PNG frames for the Coffee Character sequence ({TOTAL_DURATION/60:.2f} minutes). This will take a very long time and a lot of disk space. Are you sure you want to proceed? (yes/no): ")
    if confirm.lower() == 'yes':
        render_coffee_character_sequence()
    else:
        logger.info("Pre-rendering cancelled by user.")
    
    logger.info("Coffee Character pre-render script finished.")
