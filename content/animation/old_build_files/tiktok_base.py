import os
from moviepy import VideoFileClip
import random
import logging
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
INPUT_VIDEO_PATH = r"D:\AI\astrology_by_coffee_v1\video\animation\youtube_base.mp4"
OUTPUT_DIR = r"D:\AI\astrology_by_coffee_v1\video\tiktok_renders" 
os.makedirs(OUTPUT_DIR, exist_ok=True)

LOG_FILE = os.path.join(OUTPUT_DIR, "center_crop_for_tiktok_v2.log") # New log name
logger = setup_simple_logger(LOG_FILE)

logger.info("Starting video center crop for TikTok script (v2 with .cropped method)...")

# TikTok Aspect Ratio
TIKTOK_ASPECT_RATIO_W = 9
TIKTOK_ASPECT_RATIO_H = 16

# Output Video Parameters
OUTPUT_VIDEO_FILENAME = "tiktok_base.mp4"
OUTPUT_VIDEO_FILEPATH = os.path.join(OUTPUT_DIR, OUTPUT_VIDEO_FILENAME)

def crop_video_for_tiktok(input_path, output_path):
    logger.info(f"Loading video for cropping: {input_path}")
    video = None # Initialize to ensure it's defined for finally block
    cropped_video = None # Initialize
    
    try:
        video = VideoFileClip(input_path)
        original_width = video.w
        original_height = video.h
        original_duration = video.duration
        original_fps = video.fps if video.fps else 24 

        logger.info(f"Original video loaded. Duration: {original_duration:.2f}s, Size: ({original_width}x{original_height}), FPS: {original_fps}")

        target_width = int(original_height * (TIKTOK_ASPECT_RATIO_W / TIKTOK_ASPECT_RATIO_H))

        if target_width >= original_width:
            logger.warning(f"Calculated target width ({target_width}) for TikTok is >= original width ({original_width}). "
                           "Original video may already be portrait or square. "
                           "Saving a copy without horizontal cropping.")
            cropped_video = video # Assign original video if no crop is needed
        else:
            crop_x_center = original_width / 2
            x1 = int(crop_x_center - (target_width / 2))
            x2 = int(crop_x_center + (target_width / 2))
            
            logger.info(f"Target TikTok width: {target_width}px (at original height {original_height}px).")
            logger.info(f"Cropping from x1={x1} to x2={x2}.")

            # Use the .cropped() method of the VideoClip object
            cropped_video = video.cropped(x1=x1, y1=0, x2=x2, y2=original_height)
            
            logger.info(f"Cropped video size: ({cropped_video.w}x{cropped_video.h})")


        logger.info(f"Attempting to write cropped TikTok video to: {output_path}")
        cropped_video.write_videofile(
            output_path,
            fps=original_fps, 
            codec='libx264',
            audio_codec='aac', 
            threads=os.cpu_count() or 2,
            logger='bar',
            preset='medium'
        )
        logger.info(f"Successfully saved cropped TikTok video to: {output_path}")

    except Exception as e:
        logger.critical(f"An error occurred while processing the video: {input_path}")
        logger.exception(e)
    finally:
        if video: 
            try:
                video.close()
                logger.info("Input video clip closed.")
            except Exception as e_close:
                logger.error(f"Error closing input video clip: {e_close}")
        # Only close cropped_video if it's a new object and not the same as video
        if cropped_video and cropped_video != video: 
             try:
                cropped_video.close()
                logger.info("Cropped video clip closed.")
             except Exception as e_close:
                logger.error(f"Error closing cropped video clip: {e_close}")


if __name__ == "__main__":
    logger.info("Starting video cropping process...")
    crop_video_for_tiktok(INPUT_VIDEO_PATH, OUTPUT_VIDEO_FILEPATH)
    logger.info("Video cropping script finished.")
