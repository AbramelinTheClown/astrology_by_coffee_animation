import os
from PIL import Image
import numpy as np
from moviepy import *
import logging
import random # For choosing eye poses

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
OUTPUT_DIR = r"D:\AI\astrology_by_coffee_v1\video\final_renders" # Output directory for the final video
os.makedirs(OUTPUT_DIR, exist_ok=True)

LOG_FILE = os.path.join(OUTPUT_DIR, "render_full_video_nebbles_eyes.log")
logger = setup_simple_logger(LOG_FILE)

logger.info("Starting full video render with Nebbles animated eyes...")

# Paths
BASE_VIDEO_PATH = r"D:\AI\astrology_by_coffee_v1\video\final_renders\video_with_fade_overlay.mp4"
NEBBLES_EYES_IMAGE_PATH = r"D:\AI\astrology_by_coffee_v1\images\scene\nebbles_eyes.png"

# Nebbles Eye Animation Parameters (same as your test script)
NEBBLES_EYE_POSES = {
    "DEFAULT": (0, 0),
    "UP": (-8, -10),
    "DOWN": (0, 10)
}
NEBBLES_ACTIVE_POSE_KEYS = ["UP", "DOWN"]
NEBBLES_POSE_HOLD_DURATION = 10.0
NEBBLES_EVENT_SLOT_DURATION = 20.0 

# Video Output Parameters
# FPS will be taken from the base video
OUTPUT_VIDEO_FILENAME = "final_video_with_nebbles_animated_eyes.mp4"
OUTPUT_VIDEO_FILEPATH = os.path.join(OUTPUT_DIR, OUTPUT_VIDEO_FILENAME)

# --- Global variables for assets (loaded once) ---
base_video_clip_global = None
nebbles_eyes_img_global = None
video_total_duration_global = 0.0


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

# --- Nebbles Eye Animation Logic (MODIFIED FOR DEFAULT START) ---
def get_nebbles_eye_animation_offset(t, current_video_total_duration):
    if current_video_total_duration <= 0: 
        return NEBBLES_EYE_POSES["DEFAULT"]

    slot_index = int(t / NEBBLES_EVENT_SLOT_DURATION)
    time_in_slot = t % NEBBLES_EVENT_SLOT_DURATION

    if time_in_slot < NEBBLES_POSE_HOLD_DURATION: # This is the "active" part of a slot
        if slot_index == 0: # If it's the very first slot's "active" part
            logger.debug(f"t={t:.2f}s: Slot 0, Active Period -> Forcing DEFAULT pose for initial period.")
            return NEBBLES_EYE_POSES["DEFAULT"]
        else:
            # For other slots, proceed with random active pose
            random_generator = random.Random(slot_index) # Deterministic random based on slot
            chosen_active_pose_key = random_generator.choice(NEBBLES_ACTIVE_POSE_KEYS)
            # logger.debug(f"t={t:.2f}s: Slot {slot_index}, Active Pose: {chosen_active_pose_key}")
            return NEBBLES_EYE_POSES[chosen_active_pose_key]
    else: # This is the "default" part of a slot
        # logger.debug(f"t={t:.2f}s: Slot {slot_index}, Default Pose Period")
        return NEBBLES_EYE_POSES["DEFAULT"]

# --- Frame Processing Function for MoviePy ---
def make_video_frame(t):
    global base_video_clip_global, nebbles_eyes_img_global, video_total_duration_global

    base_video_frame_np = base_video_clip_global.get_frame(t)
    current_frame_pil = Image.fromarray(base_video_frame_np).convert('RGBA')

    if nebbles_eyes_img_global:
        nebbles_current_eye_offset = get_nebbles_eye_animation_offset(t, video_total_duration_global)
        final_paste_position = nebbles_current_eye_offset 
        current_frame_pil.paste(nebbles_eyes_img_global, final_paste_position, nebbles_eyes_img_global)
    
    final_frame_rgb_pil = current_frame_pil.convert('RGB')
    return np.array(final_frame_rgb_pil)


def render_full_video():
    global base_video_clip_global, nebbles_eyes_img_global, video_total_duration_global

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
        logger.error("Nebbles' eyes image could not be loaded. Video will be rendered without Nebbles' eyes overlay.")

    logger.info(f"Starting video processing. Output FPS: {output_fps}, Duration: {video_total_duration_global:.2f}s")

    try:
        logger.info("Creating new video clip with Nebbles' animated eyes overlay...")
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
