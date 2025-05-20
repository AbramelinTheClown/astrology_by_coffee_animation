import os
from PIL import Image
import numpy as np # For math functions like sin, pi
import logging
import random
import math # For math.sin

# --- Basic Logger Setup ---
def setup_simple_logger(log_file_path, level=logging.INFO):
    # Use a unique name for the logger to prevent conflicts if script is run multiple times/ways
    logger_name = os.path.basename(log_file_path).split('.')[0] + "_" + str(random.randint(1,10000))
    logger = logging.getLogger(logger_name) 
    logger.setLevel(level)
    if logger.hasHandlers(): # Clear existing handlers for this specific logger instance
        logger.handlers.clear()
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
    
    # Console Handler
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    # File Handler
    log_dir = os.path.dirname(log_file_path)
    if log_dir: 
        os.makedirs(log_dir, exist_ok=True)
    fh = logging.FileHandler(log_file_path, mode='w')
    fh.setLevel(level)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger

# --- Configuration ---
MAIN_OUTPUT_DIR = r"D:\AI\astrology_by_coffee_v1\video\char_sequences" 
os.makedirs(MAIN_OUTPUT_DIR, exist_ok=True)

LOG_FILE = os.path.join(MAIN_OUTPUT_DIR, "prerender_granular_layers_zodiac_left_v3.log") # New log name
logger = setup_simple_logger(LOG_FILE)

logger.info("Starting pre-render script for SEPARATE transparent animated layers (Zodiac Moved Further Left v3)...")

# Image Paths
COFFEE_BODY_PATH = r"D:\AI\astrology_by_coffee_v1\images\scene\coffee_body.png"
COFFEE_BLINK_IMAGE_PATH = r"D:\AI\astrology_by_coffee_v1\images\scene\coffee_blinks.png"
SMOKE_1_PATH = r"D:\AI\astrology_by_coffee_v1\images\scene\smoke_1.png"
SMOKE_2_PATH = r"D:\AI\astrology_by_coffee_v1\images\scene\smoke_2.png"
SMOKE_3_PATH = r"D:\AI\astrology_by_coffee_v1\images\scene\smoke_3.png"

ZODIAC_IMAGE_PATH = r"D:\AI\astrology_by_coffee_v1\images\scene\coffee_zodiac_resized_500x500.png"
NEBBLES_BODY_PATH = r"D:\AI\astrology_by_coffee_v1\images\scene\nebbles_body.png"
NEBBLES_EYES_IMAGE_PATH = r"D:\AI\astrology_by_coffee_v1\images\scene\nebbles_eyes.png"

# Animation Parameters
VIDEO_DURATION_MINUTES = 11
VIDEO_DURATION_SECONDS = 11
# For testing, uncomment below and comment out the full duration
# VIDEO_DURATION_MINUTES = 0
# VIDEO_DURATION_SECONDS = 5 # Short duration for testing
TOTAL_DURATION = (VIDEO_DURATION_MINUTES * 60) + VIDEO_DURATION_SECONDS
FPS = 24 

CANVAS_WIDTH = 1920 
CANVAS_HEIGHT = 1080
CANVAS_SIZE = (CANVAS_WIDTH, CANVAS_HEIGHT)

TEST_FRAME_TIME = 5.0

# Coffee Blink Animation Parameters
COFFEE_BLINK_MIN_INTERVAL = 7.0
COFFEE_BLINK_MAX_INTERVAL = 15.0
COFFEE_BLINK_DURATION = 0.2     

# Nebbles Eye Animation Parameters
NEBBLES_EYE_POSES = {"DEFAULT": (0, 0), "UP": (-8, -10), "DOWN": (0, 10)}
NEBBLES_ACTIVE_POSE_KEYS = ["UP", "DOWN"]
NEBBLES_POSE_HOLD_DURATION = 10.0  
NEBBLES_EVENT_SLOT_DURATION = 20.0 
NEBBLES_EYES_RELATIVE_OFFSET_X = 0 
NEBBLES_EYES_RELATIVE_OFFSET_Y = 0 


# Nebbles Body Placement Parameters (Offset from canvas center)
NEBBLES_BODY_CENTER_OFFSET_X = -20 
NEBBLES_BODY_CENTER_OFFSET_Y = 40 

# Zodiac Placement Parameters (Offset from canvas center)
# Original X offset was 205. Moved left by another 15px.
ZODIAC_CENTER_OFFSET_X = 205 - 15 # New X offset = 190
ZODIAC_CENTER_OFFSET_Y = 340 
ZODIAC_ROTATION_PERIOD = 30.0

# Smoke Animation Parameters
smoke_params = {
    "smoke_1": {"min": 0.1, "max": 0.6, "period": 4.5, "phase": 0.0,        "base_x": 0, "base_y": -30}, 
    "smoke_2": {"min": 0.05, "max": 0.5, "period": 6.0, "phase": np.pi / 2, "base_x": -30, "base_y": -50},
    "smoke_3": {"min": 0.15, "max": 0.7, "period": 3.5, "phase": np.pi,     "base_x": 30, "base_y": -20}, 
}

# Output folder names for PNG sequences
COFFEE_FINAL_ANIM_OUTPUT_FOLDER = os.path.join(MAIN_OUTPUT_DIR, "coffee_final_animation_rgba_frames")
NEBBLES_FINAL_ANIM_OUTPUT_FOLDER = os.path.join(MAIN_OUTPUT_DIR, "nebbles_final_animation_rgba_frames")
TEST_FRAMES_OUTPUT_FOLDER = os.path.join(MAIN_OUTPUT_DIR, "test_frames") 
os.makedirs(COFFEE_FINAL_ANIM_OUTPUT_FOLDER, exist_ok=True)
os.makedirs(NEBBLES_FINAL_ANIM_OUTPUT_FOLDER, exist_ok=True)
os.makedirs(TEST_FRAMES_OUTPUT_FOLDER, exist_ok=True)


# --- Global variables for animation states ---
coffee_next_blink_time_global = 0.0 
coffee_blink_end_time_global = 0.0
GLOBAL_Y_SHIFT_DOWN = 30 

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

# --- Nebbles Eye Animation Logic ---
def get_nebbles_eye_animation_offset(t, current_video_total_duration):
    if current_video_total_duration <= 0: 
        return NEBBLES_EYE_POSES["DEFAULT"]
    slot_index = int(t / NEBBLES_EVENT_SLOT_DURATION)
    time_in_slot = t % NEBBLES_EVENT_SLOT_DURATION
    if time_in_slot < NEBBLES_POSE_HOLD_DURATION: 
        if slot_index == 0: 
            return NEBBLES_EYE_POSES["DEFAULT"]
        else:
            random_generator = random.Random(slot_index) 
            chosen_active_pose_key = random_generator.choice(NEBBLES_ACTIVE_POSE_KEYS)
            return NEBBLES_EYE_POSES[chosen_active_pose_key]
    else: 
        return NEBBLES_EYE_POSES["DEFAULT"]

# --- Frame Generation Function for FINAL COFFEE Layer ---
def make_final_coffee_frame(t, coffee_body_img, coffee_blink_img, smoke_images_dict, smoke_anim_params_dict):
    global coffee_next_blink_time_global, coffee_blink_end_time_global 

    current_frame_pil = Image.new('RGBA', CANVAS_SIZE, (0, 0, 0, 0)) 
    cb_canvas_center_x = CANVAS_SIZE[0] // 2
    cb_canvas_center_y = CANVAS_SIZE[1] // 2
    
    if coffee_body_img:
        cb_paste_x = cb_canvas_center_x - (coffee_body_img.width // 2)
        cb_paste_y = (cb_canvas_center_y - (coffee_body_img.height // 2)) + GLOBAL_Y_SHIFT_DOWN
    else: 
        cb_paste_x = 0 
        cb_paste_y = 0 + GLOBAL_Y_SHIFT_DOWN 
        logger.warning(f"Coffee body image not available for frame at t={t:.2f}s. Smoke/blink position might be off.")

    for smoke_name, smoke_original_img in smoke_images_dict.items():
        if not smoke_original_img: continue
        params = smoke_anim_params_dict[smoke_name]
        opacity = get_animated_opacity(t, params["min"], params["max"], params["period"], params["phase"])
        smoke_to_animate = smoke_original_img.copy() 
        alpha_channel = smoke_to_animate.getchannel('A')
        clamped_opacity = max(0.0, min(1.0, opacity)) 
        modified_alpha_data = [int(p * clamped_opacity) for p in alpha_channel.getdata()]
        modified_alpha_channel = Image.new('L', alpha_channel.size)
        modified_alpha_channel.putdata(modified_alpha_data)
        smoke_to_animate.putalpha(modified_alpha_channel)
        smoke_paste_x = cb_paste_x + params["base_x"] 
        smoke_paste_y = cb_paste_y + params["base_y"]
        current_frame_pil.paste(smoke_to_animate, (smoke_paste_x, smoke_paste_y), smoke_to_animate)

    if coffee_body_img:
        current_frame_pil.paste(coffee_body_img, (cb_paste_x, cb_paste_y), coffee_body_img)

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
        current_frame_pil.paste(coffee_blink_img, (cb_paste_x, cb_paste_y), coffee_blink_img) 
        
    return current_frame_pil 

# --- Frame Generation Function for FINAL NEBBLES Layer (Placement Updated) ---
def make_final_nebbles_frame(t, zodiac_img, nebbles_body_img, nebbles_eyes_img, video_total_duration):
    current_frame_pil = Image.new('RGBA', CANVAS_SIZE, (0, 0, 0, 0))
    canvas_center_x = CANVAS_SIZE[0] // 2 
    canvas_center_y = CANVAS_SIZE[1] // 2 

    # 1. Spinning Zodiac - uses ZODIAC_CENTER_OFFSET_X/Y
    if zodiac_img:
        angle_degrees = -(t / ZODIAC_ROTATION_PERIOD) * 360; angle_degrees %= -360 
        resample_filter_rotate = Image.Resampling.BICUBIC if hasattr(Image, "Resampling") else Image.BICUBIC
        rotated_zodiac = zodiac_img.rotate(angle_degrees, resample=resample_filter_rotate, expand=False)
        
        target_zodiac_center_x = canvas_center_x + ZODIAC_CENTER_OFFSET_X 
        target_zodiac_center_y = canvas_center_y + ZODIAC_CENTER_OFFSET_Y 
        zodiac_paste_x = int(round(target_zodiac_center_x - rotated_zodiac.width / 2))
        zodiac_paste_y = int(round(target_zodiac_center_y - rotated_zodiac.height / 2))
        current_frame_pil.paste(rotated_zodiac, (zodiac_paste_x, zodiac_paste_y), rotated_zodiac)

    # 2. Nebbles Body - uses NEBBLES_BODY_CENTER_OFFSET_X/Y
    if nebbles_body_img:
        target_nebbles_body_center_x = canvas_center_x + NEBBLES_BODY_CENTER_OFFSET_X 
        target_nebbles_body_center_y = canvas_center_y + NEBBLES_BODY_CENTER_OFFSET_Y 
        
        nb_paste_x = int(round(target_nebbles_body_center_x - nebbles_body_img.width / 2))
        nb_paste_y = int(round(target_nebbles_body_center_y - nebbles_body_img.height / 2))
        current_frame_pil.paste(nebbles_body_img, (nb_paste_x, nb_paste_y), nebbles_body_img)

        # 3. Nebbles Eyes 
        if nebbles_eyes_img:
            eye_anim_offset_x, eye_anim_offset_y = get_nebbles_eye_animation_offset(t, video_total_duration)
            
            final_eye_paste_x = nb_paste_x + NEBBLES_EYES_RELATIVE_OFFSET_X + eye_anim_offset_x
            final_eye_paste_y = nb_paste_y + NEBBLES_EYES_RELATIVE_OFFSET_Y + eye_anim_offset_y
            
            current_frame_pil.paste(nebbles_eyes_img, (final_eye_paste_x, final_eye_paste_y), nebbles_eyes_img)
            
    return current_frame_pil

# --- Function to Render Test Frames ---
def render_test_frames(time_t, coffee_assets, nebbles_assets, video_duration_for_nebbles_eyes):
    global coffee_next_blink_time_global, coffee_blink_end_time_global 
    
    logger.info(f"Rendering test frames at t={time_t:.2f}s...")
    original_next_blink = coffee_next_blink_time_global
    original_blink_end = coffee_blink_end_time_global

    logger.info("Generating test frame for Coffee sequence...")
    test_coffee_frame = make_final_coffee_frame(time_t, 
                                                coffee_assets["body"], 
                                                coffee_assets["blink"],
                                                coffee_assets["smokes"],
                                                coffee_assets["smoke_params"])
    test_coffee_output_path = os.path.join(TEST_FRAMES_OUTPUT_FOLDER, f"test_coffee_frame_t{time_t:.1f}s_shifted_down.png")
    try:
        test_coffee_frame.save(test_coffee_output_path)
        logger.info(f"Saved Coffee test frame to: {test_coffee_output_path}")
    except Exception as e:
        logger.exception(f"Error saving Coffee test frame: {e}")

    coffee_next_blink_time_global = original_next_blink 
    coffee_blink_end_time_global = original_blink_end

    logger.info("Generating test frame for Nebbles sequence...")
    test_nebbles_frame = make_final_nebbles_frame(time_t,
                                                  nebbles_assets["zodiac"],
                                                  nebbles_assets["body"],
                                                  nebbles_assets["eyes"],
                                                  video_duration_for_nebbles_eyes) 
    test_nebbles_output_path = os.path.join(TEST_FRAMES_OUTPUT_FOLDER, f"test_nebbles_frame_t{time_t:.1f}s_zodiac_left_v2.png") # New test name
    try:
        test_nebbles_frame.save(test_nebbles_output_path)
        logger.info(f"Saved Nebbles test frame to: {test_nebbles_output_path}")
    except Exception as e:
        logger.exception(f"Error saving Nebbles test frame: {e}")
    logger.info("Test frame generation complete.")


# --- Main Execution Logic ---
if __name__ == "__main__":
    logger.info("Loading all images for potential test and full render...")
    coffee_body_img_loaded = read_image_rgba(COFFEE_BODY_PATH, "Coffee Body")
    coffee_blink_img_loaded = read_image_rgba(COFFEE_BLINK_IMAGE_PATH, "Coffee Blink")
    smoke_images_loaded = {
        "smoke_1": read_image_rgba(SMOKE_1_PATH, "Smoke 1"),
        "smoke_2": read_image_rgba(SMOKE_2_PATH, "Smoke 2"),
        "smoke_3": read_image_rgba(SMOKE_3_PATH, "Smoke 3"),
    }
    zodiac_img_loaded = read_image_rgba(ZODIAC_IMAGE_PATH, "Resized Zodiac") 
    nebbles_body_img_loaded = read_image_rgba(NEBBLES_BODY_PATH, "Nebbles Body")
    nebbles_eyes_img_loaded = read_image_rgba(NEBBLES_EYES_IMAGE_PATH, "Nebbles Eyes")

    coffee_assets_for_test = {
        "body": coffee_body_img_loaded,
        "blink": coffee_blink_img_loaded,
        "smokes": smoke_images_loaded,
        "smoke_params": smoke_params
    }
    nebbles_assets_for_test = {
        "zodiac": zodiac_img_loaded,
        "body": nebbles_body_img_loaded,
        "eyes": nebbles_eyes_img_loaded
    }

    coffee_next_blink_time_global = random.uniform(COFFEE_BLINK_MIN_INTERVAL / 3, COFFEE_BLINK_MAX_INTERVAL / 3) 
    logger.info(f"Initial Coffee blink (for test or full render) scheduled around t={coffee_next_blink_time_global:.2f}s")

    render_test_frames(TEST_FRAME_TIME, coffee_assets_for_test, nebbles_assets_for_test, TOTAL_DURATION)

    total_png_frames = int(TOTAL_DURATION * FPS) * 2 
    confirm = input(f"Test frames saved. This script will now render {total_png_frames} PNG frames ({TOTAL_DURATION/60:.2f} minutes per character sequence). This will take a VERY LONG TIME and a lot of disk space. Are you sure you want to proceed? (yes/no): ")
    
    if confirm.lower() == 'yes':
        logger.info("User confirmed. Starting full sequence rendering...")
        
        coffee_next_blink_time_global = random.uniform(COFFEE_BLINK_MIN_INTERVAL / 3, COFFEE_BLINK_MAX_INTERVAL / 3) 
        coffee_blink_end_time_global = 0.0 
        logger.info(f"Re-initialized Coffee blink (for full render) scheduled around t={coffee_next_blink_time_global:.2f}s")

        logger.info(f"Starting FINAL COFFEE (smoke, body, blinks) pre-render to: {COFFEE_FINAL_ANIM_OUTPUT_FOLDER}")
        for i in range(int(TOTAL_DURATION * FPS)):
            t = i / FPS
            if i % (FPS * 30) == 0: 
                logger.info(f"Coffee Final Anim: Processing frame {i}/{int(TOTAL_DURATION * FPS)} (t={t:.2f}s)")
            frame_pil = make_final_coffee_frame(t, coffee_body_img_loaded, coffee_blink_img_loaded, 
                                                smoke_images_loaded, smoke_params)
            try:
                frame_pil.save(os.path.join(COFFEE_FINAL_ANIM_OUTPUT_FOLDER, f"coffee_final_frame_{i:05d}.png"))
            except Exception as e:
                logger.exception(f"Error saving Coffee Final frame {i}: {e}"); break 
        logger.info("FINAL COFFEE animation pre-render finished.")

        logger.info(f"Starting FINAL NEBBLES (zodiac, body, eyes) pre-render to: {NEBBLES_FINAL_ANIM_OUTPUT_FOLDER}")
        for i in range(int(TOTAL_DURATION * FPS)):
            t = i / FPS
            if i % (FPS * 30) == 0: 
                logger.info(f"Nebbles Final Anim: Processing frame {i}/{int(TOTAL_DURATION * FPS)} (t={t:.2f}s)")
            frame_pil = make_final_nebbles_frame(t, zodiac_img_loaded, nebbles_body_img_loaded, 
                                                 nebbles_eyes_img_loaded, TOTAL_DURATION)
            try:
                frame_pil.save(os.path.join(NEBBLES_FINAL_ANIM_OUTPUT_FOLDER, f"nebbles_final_frame_{i:05d}.png"))
            except Exception as e:
                logger.exception(f"Error saving Nebbles Final frame {i}: {e}"); break
        logger.info("FINAL NEBBLES animation pre-render finished.")
    else:
        logger.info("Full pre-rendering cancelled by user.")
    
    logger.info("All pre-render sequences script finished.")
