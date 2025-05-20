import os
from PIL import Image
import numpy as np
from moviepy import VideoFileClip, VideoClip # Added VideoClip
import logging

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
OUTPUT_DIR = r"D:\AI\astrology_by_coffee_v1\video\final_renders" # Directory for final video
os.makedirs(OUTPUT_DIR, exist_ok=True)

LOG_FILE = os.path.join(OUTPUT_DIR, "video_with_fade_overlay.log")
logger = setup_simple_logger(LOG_FILE)

logger.info("Starting video overlay script...")

# Paths
BASE_VIDEO_PATH = r"D:\AI\astrology_by_coffee_v1\video\final_renders\final_video_all_animations.mp4"
FADE_IMAGE_PATH = r"D:\AI\astrology_by_coffee_v1\images\scene\fade_block.png" # Updated path

# Parameters for the fade overlay
FADE_IMAGE_PASTE_POSITION = (0, -95) # Top-left coordinates (X, Y) to paste the fade_block.png

# Output Video Parameters
FPS = 24 # Assuming the base video's FPS, or set as desired for output
OUTPUT_VIDEO_FILENAME = "video_with_fade_overlay.mp4"
OUTPUT_VIDEO_FILEPATH = os.path.join(OUTPUT_DIR, OUTPUT_VIDEO_FILENAME)


# --- Helper Function ---
def read_image_rgba(path, image_description="Image"):
    logger.debug(f"Reading {image_description}: {path}")
    try:
        img = Image.open(path).convert('RGBA') # Ensure RGBA for transparency
        logger.info(f"Successfully loaded {image_description}: {path} (Size: {img.size})")
        return img
    except FileNotFoundError:
        logger.error(f"{image_description} file not found: {path}")
        return None
    except Exception as e:
        logger.exception(f"Error loading {image_description} {path}: {e}")
        return None

# --- Global variables for assets (to be loaded once) ---
base_video_clip_global = None
fade_img_global = None

def process_video_with_overlay():
    global base_video_clip_global, fade_img_global # Allow modification of global variables

    logger.info(f"Loading base video: {BASE_VIDEO_PATH}")
    try:
        base_video_clip_global = VideoFileClip(BASE_VIDEO_PATH)
        logger.info(f"Base video loaded. Duration: {base_video_clip_global.duration:.2f}s, Size: {base_video_clip_global.size}, FPS: {base_video_clip_global.fps}")
    except Exception as e:
        logger.critical(f"Failed to load base video: {BASE_VIDEO_PATH}")
        logger.exception(e)
        return

    logger.info(f"Loading fade image: {FADE_IMAGE_PATH}")
    fade_img_global = read_image_rgba(FADE_IMAGE_PATH, "Fade Image")

    if not fade_img_global:
        logger.error("Fade image could not be loaded. Cannot proceed with overlay.")
        if base_video_clip_global:
            base_video_clip_global.close()
        return

    # Determine output FPS: use base video's FPS if available, otherwise default
    output_fps = base_video_clip_global.fps if base_video_clip_global.fps else FPS
    video_duration = base_video_clip_global.duration

    logger.info(f"Starting video processing. Output FPS: {output_fps}, Duration: {video_duration:.2f}s")

    # Define the function to generate each frame
    def make_frame(t):
        # Get current frame from the base video
        # MoviePy's get_frame handles time correctly within the clip's duration
        video_frame_np = base_video_clip_global.get_frame(t)
        # Convert NumPy array (video frame) to PIL Image and ensure RGBA for pasting
        current_frame_pil = Image.fromarray(video_frame_np).convert('RGBA')

        # Paste the fade image
        # Using fade_img_global as its own mask to handle its transparency correctly
        current_frame_pil.paste(fade_img_global, FADE_IMAGE_PASTE_POSITION, fade_img_global)
        
        # Convert final PIL Image back to RGB NumPy array for MoviePy (libx264 expects RGB)
        final_frame_rgb_pil = current_frame_pil.convert('RGB')
        return np.array(final_frame_rgb_pil)

    # Create the new video clip by applying the make_frame function
    try:
        logger.info("Creating new video clip with overlay...")
        processed_video_clip = VideoClip(make_frame, duration=video_duration)

        # Write the final video file
        logger.info(f"Attempting to write final video to: {OUTPUT_VIDEO_FILEPATH}")
        processed_video_clip.write_videofile(
            OUTPUT_VIDEO_FILEPATH,
            fps=output_fps,
            codec='libx264',
            audio=True, # Preserve audio from the base video clip
            # audio_codec='aac', # Usually good for mp4
            threads=os.cpu_count() or 2,
            logger='bar', # MoviePy's progress bar
            preset='medium' # 'ultrafast', 'fast', 'medium', 'slow', 'veryslow'
        )
        logger.info(f"Successfully saved processed video to: {OUTPUT_VIDEO_FILEPATH}")

    except Exception as e:
        logger.critical("An error occurred during video processing or writing:")
        logger.exception(e)
    finally:
        # Important: Close the video file clip when done
        if base_video_clip_global:
            try:
                base_video_clip_global.close()
                logger.info("Base video clip closed.")
            except Exception as e_close:
                logger.error(f"Error closing base video clip: {e_close}")
        # No need to close processed_video_clip as it's generated in memory and used by write_videofile


if __name__ == "__main__":
    process_video_with_overlay()
    logger.info("Video overlay script finished.")
