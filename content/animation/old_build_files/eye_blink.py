import os
from PIL import Image
import numpy as np
from moviepy import VideoFileClip, VideoClip 
import logging
import random 

# --- Basic Logger Setup ---
def setup_simple_logger(log_file_path, level=logging.INFO):
    logger = logging.getLogger(os.path.basename(log_file_path).split('.')[0])
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
OUTPUT_DIR = r"D:\AI\astrology_by_coffee_v1\video\final_renders" 
os.makedirs(OUTPUT_DIR, exist_ok=True)

LOG_FILE = os.path.join(OUTPUT_DIR, "render_full_video_all_animations.log") # New log name
logger = setup_simple_logger(LOG_FILE)

logger.info("Starting full video render with Nebbles eyes and Coffee blinks...")

# Paths
BASE_VIDEO_PATH = r"D:\AI\astrology_by_coffee_v1\video\zodiac_animation_final_tests\spinning_zodiac_on_prerender_full_length.mp4"
NEBBLES_EYES_IMAGE_PATH = r"D:\AI\astrology_by_coffee_v1\images\scene\nebbles_eyes.png"
COFFEE_BLINK_IMAGE_PATH = r"D:\AI\astrology_by_coffee_v1\images\scene\coffee_blinks.png" # Added

# Nebbles Eye Animation Parameters
NEBBLES_EYE_POSES = {
    "DEFAULT": (0, 0),
    "UP": (-8, -10),
    "DOWN": (0, 10)
}
NEBBLES_ACTIVE_POSE_KEYS = ["UP", "DOWN"]
NEBBLES_POSE_HOLD_DURATION = 10.0  
NEBBLES_EVENT_SLOT_DURATION = 20.0 

# Coffee Blink Animation Parameters
COFFEE_BLINK_MIN_INTERVAL = 7.0  # seconds
COFFEE_BLINK_MAX_INTERVAL = 15.0 # seconds
COFFEE_BLINK_DURATION = 0.2     # seconds (how long the eyes stay closed)

# Video Output Parameters
OUTPUT_VIDEO_FILENAME = "final_video_all_animations.mp4" # New output name
OUTPUT_VIDEO_FILEPATH = os.path.join(OUTPUT_DIR, OUTPUT_VIDEO_FILENAME)

# --- Global variables for assets & animation states (loaded/initialized once) ---
base_video_clip_global = None
nebbles_eyes_img_global = None
coffee_blink_img_global = None # For Coffee's blink image
video_total_duration_global = 0.0

# Coffee Blink State
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

# --- Nebbles Eye Animation Logic ---
def get_nebbles_eye_animation_offset(t, current_video_total_duration):
    # ... (this function remains the same as in the artifact) ...
    if current_video_total_duration <= 0: 
        return NEBBLES_EYE_POSES["DEFAULT"]
    slot_index = int(t / NEBBLES_EVENT_SLOT_DURATION)
    time_in_slot = t % NEBBLES_EVENT_SLOT_DURATION
    if time_in_slot < NEBBLES_POSE_HOLD_DURATION: 
        if slot_index == 0: 
            logger.debug(f"t={t:.2f}s: Nebbles Slot 0, Active Period -> Forcing DEFAULT pose.")
            return NEBBLES_EYE_POSES["DEFAULT"]
        else:
            random_generator = random.Random(slot_index) 
            chosen_active_pose_key = random_generator.choice(NEBBLES_ACTIVE_POSE_KEYS)
            return NEBBLES_EYE_POSES[chosen_active_pose_key]
    else: 
        return NEBBLES_EYE_POSES["DEFAULT"]

# --- Frame Processing Function for MoviePy ---
def make_video_frame(t):
    global base_video_clip_global, nebbles_eyes_img_global, coffee_blink_img_global
    global video_total_duration_global
    global coffee_next_blink_time_global, coffee_blink_end_time_global

    base_video_frame_np = base_video_clip_global.get_frame(t)
    current_frame_pil = Image.fromarray(base_video_frame_np).convert('RGBA')

    # --- Coffee Blink Logic ---
    is_coffee_blinking_now = False
    if t >= coffee_blink_end_time_global: # If previous blink ended or first frame
        if t >= coffee_next_blink_time_global: # Time for a new blink
            logger.debug(f"Coffee: Starting blink at t={t:.2f}s")
            is_coffee_blinking_now = True
            coffee_blink_end_time_global = t + COFFEE_BLINK_DURATION
            # Schedule the next blink AFTER this one ends
            coffee_next_blink_time_global = coffee_blink_end_time_global + \
                                           random.uniform(COFFEE_BLINK_MIN_INTERVAL, COFFEE_BLINK_MAX_INTERVAL)
            logger.debug(f"Coffee: Blink ends at {coffee_blink_end_time_global:.2f}s, next blink scheduled around {coffee_next_blink_time_global:.2f}s")
    elif t < coffee_blink_end_time_global and t >= (coffee_blink_end_time_global - COFFEE_BLINK_DURATION):
        # This condition ensures we are currently within an active blink period
        # that was initiated by a previous frame's check.
        is_coffee_blinking_now = True

    if is_coffee_blinking_now and coffee_blink_img_global:
        # Assuming coffee_blink_img_global is a full-frame overlay with transparency
        # and the closed eyes are positioned correctly within it to align with Coffee.
        current_frame_pil.paste(coffee_blink_img_global, (0, 0), coffee_blink_img_global)
        logger.debug(f"Coffee: Pasting blink image at t={t:.2f}s")


    # --- Nebbles Eye Logic ---
    if nebbles_eyes_img_global:
        nebbles_current_eye_offset = get_nebbles_eye_animation_offset(t, video_total_duration_global)
        final_paste_position = nebbles_current_eye_offset 
        current_frame_pil.paste(nebbles_eyes_img_global, final_paste_position, nebbles_eyes_img_global)
    
    final_frame_rgb_pil = current_frame_pil.convert('RGB')
    return np.array(final_frame_rgb_pil)


def render_full_video():
    global base_video_clip_global, nebbles_eyes_img_global, coffee_blink_img_global
    global video_total_duration_global
    global coffee_next_blink_time_global # Initialize for the first blink

    logger.info(f"Loading base video: {BASE_VIDEO_PATH}")
    try:
        base_video_clip_global = VideoFileClip(BASE_VIDEO_PATH)
        video_total_duration_global = base_video_clip_global.duration
        output_fps = base_video_clip_global.fps if base_video_clip_global.fps else 24 
        logger.info(f"Base video loaded. Duration: {video_total_duration_global:.2f}s, FPS: {output_fps}")
    except Exception as e:
        logger.critical(f"Failed to load base video: {BASE_VIDEO_PATH}")
        logger.exception(e)
        return

    logger.info(f"Loading Nebbles' eyes image: {NEBBLES_EYES_IMAGE_PATH}")
    nebbles_eyes_img_global = read_image_rgba(NEBBLES_EYES_IMAGE_PATH, "Nebbles' Eyes Image")
    if not nebbles_eyes_img_global:
        logger.warning("Nebbles' eyes image could not be loaded. Nebbles eyes will not be animated.")

    logger.info(f"Loading Coffee blink image: {COFFEE_BLINK_IMAGE_PATH}")
    coffee_blink_img_global = read_image_rgba(COFFEE_BLINK_IMAGE_PATH, "Coffee Blink Image")
    if not coffee_blink_img_global:
        logger.warning("Coffee blink image could not be loaded. Coffee character will not blink.")

    # Initialize first blink time
    coffee_next_blink_time_global = random.uniform(COFFEE_BLINK_MIN_INTERVAL / 2, COFFEE_BLINK_MAX_INTERVAL / 2) # Start with a slightly shorter initial wait
    logger.info(f"Initial Coffee blink scheduled around t={coffee_next_blink_time_global:.2f}s")


    logger.info(f"Starting video processing. Output FPS: {output_fps}, Duration: {video_total_duration_global:.2f}s")

    try:
        logger.info("Creating new video clip with all animations...")
        processed_video_clip = VideoClip(make_video_frame, duration=video_total_duration_global)

        if base_video_clip_global.audio:
            logger.info("Assigning audio from base video to the new clip.")
            processed_video_clip = processed_video_clip.set_audio(base_video_clip_global.audio)
        else:
            logger.info("Base video has no audio track.")

        logger.info(f"Attempting to write final video to: {OUTPUT_VIDEO_FILEPATH}")
        processed_video_clip.write_videofile(
            OUTPUT_VIDEO_FILEPATH,
            fps=output_fps,
            codec='libx264',
            audio_codec='aac', 
            threads=os.cpu_count() or 2,
            logger='bar', 
            preset='medium' 
        )
        logger.info(f"Successfully saved processed video to: {OUTPUT_VIDEO_FILEPATH}")

    except Exception as e:
        logger.critical("An error occurred during video processing or writing:")
        logger.exception(e)
    finally:
        if base_video_clip_global:
            try:
                base_video_clip_global.close()
                logger.info("Base video clip closed.")
            except Exception as e_close:
                logger.error(f"Error closing base video clip: {e_close}")

if __name__ == "__main__":
    render_full_video()
    logger.info("Full video render script finished.")
