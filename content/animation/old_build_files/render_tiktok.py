import os
from PIL import Image
import numpy as np
from moviepy import ImageSequenceClip, AudioFileClip, VideoClip 
import logging
import random
import glob # For checking files in a directory

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
MAIN_INPUT_DIR = r"D:\AI\astrology_by_coffee_v1\video\transparent_prerenders_granular"
TIKTOK_OUTPUT_DIR = r"D:\AI\astrology_by_coffee_v1\video\tiktok_renders" 
TEST_FRAMES_DIR = os.path.join(TIKTOK_OUTPUT_DIR, "test_frames_tiktok_center_crop") 
os.makedirs(TIKTOK_OUTPUT_DIR, exist_ok=True)
os.makedirs(TEST_FRAMES_DIR, exist_ok=True)


LOG_FILE = os.path.join(TIKTOK_OUTPUT_DIR, "tiktok_video_compositing_center_crop_v2.log") # New log name
logger = setup_simple_logger(LOG_FILE)

logger.info("Starting TikTok video compositing script with CENTER CROP (v2 with improved loading)...")

# Paths to Pre-rendered PNG Sequences
COFFEE_SEQUENCE_FOLDER = os.path.join(MAIN_INPUT_DIR, "coffee_final_animation_rgba_frames")
NEBBLES_SEQUENCE_FOLDER = os.path.join(MAIN_INPUT_DIR, "nebbles_final_animation_rgba_frames")
AUDIO_FILE_PATH = r"D:\AI\astrology_by_coffee_v1\audio\horoscope_Aquarius_2025-04-20.mp3"

# TikTok Video Parameters
TIKTOK_CANVAS_WIDTH = 1080
TIKTOK_CANVAS_HEIGHT = 1920
TIKTOK_CANVAS_SIZE = (TIKTOK_CANVAS_WIDTH, TIKTOK_CANVAS_HEIGHT)
TIKTOK_BACKGROUND_COLOR = (20, 20, 30) 
FPS = 24 

# Pre-render Dimensions (assuming your sequences are 1920x1080)
PRE_RENDER_ORIGINAL_WIDTH = 1920
PRE_RENDER_ORIGINAL_HEIGHT = 1080

# Layer Positioning on the TikTok canvas (Y position from the top)
COFFEE_LAYER_Y_POS = 300             
NEBBLES_LAYER_Y_POS = 800            

# Test Frame Time
TEST_FRAME_TIME_SECONDS = 5.0 

# Video Output
OUTPUT_VIDEO_FILENAME = "final_tiktok_video_9x16_center_crop.mp4" 
OUTPUT_VIDEO_FILEPATH = os.path.join(TIKTOK_OUTPUT_DIR, OUTPUT_VIDEO_FILENAME)

# --- Global variables ---
coffee_clip_global = None
nebbles_clip_global = None
audio_clip_global = None
video_total_duration_global = 0.0
center_crop_box_for_prerender = None 

# --- Helper function to load image sequence safely ---
def load_image_sequence_safely(folder_path, fps, sequence_name="Image Sequence"):
    logger.info(f"Attempting to load {sequence_name} from: {folder_path}")
    if not os.path.isdir(folder_path):
        logger.error(f"{sequence_name} folder not found: {folder_path}")
        return None
    
    # Check for PNG files specifically, as that's what the pre-render script creates
    image_files = sorted(glob.glob(os.path.join(folder_path, "*.png")))
    
    if not image_files:
        logger.error(f"No PNG files found in {sequence_name} folder: {folder_path}")
        return None
    
    logger.info(f"Found {len(image_files)} PNG files in {folder_path}. Attempting to create ImageSequenceClip.")
    try:
        # Pass the explicit list of found files to ImageSequenceClip
        clip = ImageSequenceClip(image_files, fps=fps)
        logger.info(f"{sequence_name} loaded successfully. Duration: {clip.duration:.2f}s")
        return clip
    except IndexError: # Should be caught by the check above, but as a failsafe
        logger.error(f"IndexError during ImageSequenceClip creation for {folder_path}. This typically means the sequence was empty or unreadable by MoviePy.")
        return None
    except Exception as e:
        logger.error(f"Failed to load {sequence_name} from: {folder_path}")
        logger.exception(e)
        return None

# --- Frame Generation Function for TikTok Video ---
def make_tiktok_frame(t, current_coffee_clip, current_nebbles_clip):
    global center_crop_box_for_prerender 

    if TIKTOK_BACKGROUND_COLOR:
        tiktok_frame_pil = Image.new('RGB', TIKTOK_CANVAS_SIZE, TIKTOK_BACKGROUND_COLOR)
        tiktok_frame_pil = tiktok_frame_pil.convert('RGBA') 
    else:
        tiktok_frame_pil = Image.new('RGBA', TIKTOK_CANVAS_SIZE, (0,0,0,0))

    # Process Coffee Layer
    if current_coffee_clip and t < current_coffee_clip.duration:
        coffee_frame_np = current_coffee_clip.get_frame(t)
        coffee_pil_original_size = Image.fromarray(coffee_frame_np).convert('RGBA')
        
        if center_crop_box_for_prerender:
            coffee_cropped_pil = coffee_pil_original_size.crop(center_crop_box_for_prerender)
        else: 
            coffee_cropped_pil = coffee_pil_original_size 
        
        paste_x_coffee = 0 
        paste_y_coffee = COFFEE_LAYER_Y_POS
        tiktok_frame_pil.paste(coffee_cropped_pil, (paste_x_coffee, paste_y_coffee), coffee_cropped_pil)

    # Process Nebbles Layer
    if current_nebbles_clip and t < current_nebbles_clip.duration:
        nebbles_frame_np = current_nebbles_clip.get_frame(t)
        nebbles_pil_original_size = Image.fromarray(nebbles_frame_np).convert('RGBA')

        if center_crop_box_for_prerender:
            nebbles_cropped_pil = nebbles_pil_original_size.crop(center_crop_box_for_prerender)
        else: 
            nebbles_cropped_pil = nebbles_pil_original_size

        paste_x_nebbles = 0
        paste_y_nebbles = NEBBLES_LAYER_Y_POS
        tiktok_frame_pil.paste(nebbles_cropped_pil, (paste_x_nebbles, paste_y_nebbles), nebbles_cropped_pil)

    final_frame_rgb_pil = tiktok_frame_pil.convert('RGB')
    return np.array(final_frame_rgb_pil)

# --- Function to Render Test Frames ---
def render_tiktok_test_frames(time_t, current_crop_box):
    logger.info(f"Rendering TikTok test frames at t={time_t:.2f}s with crop box: {current_crop_box}")
    
    temp_coffee_clip = None
    temp_nebbles_clip = None

    try:
        temp_coffee_clip = load_image_sequence_safely(COFFEE_SEQUENCE_FOLDER, FPS, "Coffee Sequence (Test)")
        temp_nebbles_clip = load_image_sequence_safely(NEBBLES_SEQUENCE_FOLDER, FPS, "Nebbles Sequence (Test)")

        # 1. Coffee Test Frame
        if temp_coffee_clip and time_t < temp_coffee_clip.duration:
            coffee_test_canvas = Image.new('RGBA', TIKTOK_CANVAS_SIZE, (0,0,0,0)) 
            coffee_frame_np = temp_coffee_clip.get_frame(time_t)
            coffee_pil_original = Image.fromarray(coffee_frame_np).convert('RGBA')
            if current_crop_box:
                coffee_cropped_pil = coffee_pil_original.crop(current_crop_box)
            else:
                coffee_cropped_pil = coffee_pil_original
            
            paste_x_coffee = 0 
            paste_y_coffee = COFFEE_LAYER_Y_POS
            coffee_test_canvas.paste(coffee_cropped_pil, (paste_x_coffee, paste_y_coffee), coffee_cropped_pil)
            coffee_test_path = os.path.join(TEST_FRAMES_DIR, f"test_coffee_tiktok_cropped_t{time_t:.1f}s.png")
            coffee_test_canvas.save(coffee_test_path)
            logger.info(f"Saved Coffee test frame (cropped) to: {coffee_test_path}")
        elif not temp_coffee_clip:
            logger.warning("Coffee sequence not loaded for test frame generation.")


        # 2. Nebbles Test Frame
        if temp_nebbles_clip and time_t < temp_nebbles_clip.duration:
            nebbles_test_canvas = Image.new('RGBA', TIKTOK_CANVAS_SIZE, (0,0,0,0)) 
            nebbles_frame_np = temp_nebbles_clip.get_frame(time_t)
            nebbles_pil_original = Image.fromarray(nebbles_frame_np).convert('RGBA')
            if current_crop_box:
                nebbles_cropped_pil = nebbles_pil_original.crop(current_crop_box)
            else:
                nebbles_cropped_pil = nebbles_pil_original

            paste_x_nebbles = 0
            paste_y_nebbles = NEBBLES_LAYER_Y_POS
            nebbles_test_canvas.paste(nebbles_cropped_pil, (paste_x_nebbles, paste_y_nebbles), nebbles_cropped_pil)
            nebbles_test_path = os.path.join(TEST_FRAMES_DIR, f"test_nebbles_tiktok_cropped_t{time_t:.1f}s.png")
            nebbles_test_canvas.save(nebbles_test_path)
            logger.info(f"Saved Nebbles test frame (cropped) to: {nebbles_test_path}")
        elif not temp_nebbles_clip:
            logger.warning("Nebbles sequence not loaded for test frame generation.")


        # 3. Composite Test Frame (with background)
        if temp_coffee_clip and temp_nebbles_clip : # Only if both clips are available
            logger.info("Generating composite test frame for TikTok...")
            composite_frame_np = make_tiktok_frame(time_t, temp_coffee_clip, temp_nebbles_clip) 
            composite_frame_pil = Image.fromarray(composite_frame_np) 
            composite_test_path = os.path.join(TEST_FRAMES_DIR, f"test_composite_tiktok_cropped_frame_t{time_t:.1f}s.png")
            composite_frame_pil.save(composite_test_path)
            logger.info(f"Saved Composite TikTok test frame to: {composite_test_path}")
        else:
            logger.warning("Skipping composite test frame as one or both character sequences failed to load.")


    except Exception as e:
        logger.exception("Error during test frame generation:")
    finally:
        if temp_coffee_clip: temp_coffee_clip.close()
        if temp_nebbles_clip: temp_nebbles_clip.close()
    logger.info("Test frame generation finished.")


# --- Main Compositing Logic ---
def composite_for_tiktok():
    global coffee_clip_global, nebbles_clip_global, audio_clip_global, video_total_duration_global
    global center_crop_box_for_prerender

    crop_target_width = TIKTOK_CANVAS_WIDTH 
    if PRE_RENDER_ORIGINAL_WIDTH < crop_target_width:
        logger.error(f"Pre-render width ({PRE_RENDER_ORIGINAL_WIDTH}) is less than TikTok canvas width ({crop_target_width}). Cannot perform center crop as intended.")
        return 

    crop_x_offset = (PRE_RENDER_ORIGINAL_WIDTH - crop_target_width) // 2
    center_crop_box_for_prerender = (crop_x_offset, 0, crop_x_offset + crop_target_width, PRE_RENDER_ORIGINAL_HEIGHT)
    logger.info(f"Calculated center crop box for {PRE_RENDER_ORIGINAL_WIDTH}x{PRE_RENDER_ORIGINAL_HEIGHT} pre-renders: {center_crop_box_for_prerender}")
    logger.info(f"Cropped pre-render layer size will be: {crop_target_width}x{PRE_RENDER_ORIGINAL_HEIGHT}")

    render_tiktok_test_frames(TEST_FRAME_TIME_SECONDS, center_crop_box_for_prerender)

    confirm = input(f"Test frames saved to '{TEST_FRAMES_DIR}'. Please review them. Proceed with full TikTok video render? (yes/no): ")
    if confirm.lower() != 'yes':
        logger.info("Full TikTok video rendering cancelled by user."); return

    coffee_clip_global = load_image_sequence_safely(COFFEE_SEQUENCE_FOLDER, FPS, "Coffee Sequence (Main)")
    if not coffee_clip_global: return # Stop if essential clip fails

    nebbles_clip_global = load_image_sequence_safely(NEBBLES_SEQUENCE_FOLDER, FPS, "Nebbles Sequence (Main)")
    if not nebbles_clip_global: # Stop if essential clip fails
        if coffee_clip_global: coffee_clip_global.close()
        return

    logger.info(f"Loading audio from: {AUDIO_FILE_PATH}")
    try:
        audio_clip_global = AudioFileClip(AUDIO_FILE_PATH)
        logger.info(f"Audio loaded. Duration: {audio_clip_global.duration:.2f}s")
    except Exception as e:
        logger.error(f"Failed to load audio: {AUDIO_FILE_PATH}. Video will be silent.")
        logger.exception(e) # audio_clip_global will remain None

    durations = [coffee_clip_global.duration, nebbles_clip_global.duration]
    if audio_clip_global: durations.append(audio_clip_global.duration)
    
    video_total_duration_global = min(d for d in durations if d is not None and d > 0) 
    if video_total_duration_global == float('inf') or video_total_duration_global <= 0 : 
        video_total_duration_global = max(coffee_clip_global.duration, nebbles_clip_global.duration, 0) 
        if video_total_duration_global <= 0:
            logger.error("Could not determine a valid video duration. Aborting."); return

    logger.info(f"Final video duration will be: {video_total_duration_global:.2f}s")
    logger.info(f"Starting TikTok video processing. Output FPS: {FPS}")

    try:
        logger.info("Creating final TikTok video clip...")
        final_video_clip = VideoClip(lambda t: make_tiktok_frame(t, coffee_clip_global, nebbles_clip_global), 
                                     duration=video_total_duration_global)

        if audio_clip_global:
            logger.info("Assigning audio to the final clip.")
            final_video_clip = final_video_clip.set_audio(audio_clip_global.subclip(0, video_total_duration_global))
        else:
            logger.info("No audio track will be added.")

        logger.info(f"Attempting to write final TikTok video to: {OUTPUT_VIDEO_FILEPATH}")
        final_video_clip.write_videofile(
            OUTPUT_VIDEO_FILEPATH, fps=FPS, codec='libx264', audio_codec='aac', 
            threads=os.cpu_count() or 2, logger='bar', preset='medium' 
        )
        logger.info(f"Successfully saved final TikTok video to: {OUTPUT_VIDEO_FILEPATH}")

    except Exception as e:
        logger.critical("An error occurred during TikTok video processing or writing:")
        logger.exception(e)
    finally:
        if coffee_clip_global: coffee_clip_global.close()
        if nebbles_clip_global: nebbles_clip_global.close()
        if audio_clip_global: audio_clip_global.close()
        logger.info("MoviePy clips closed.")

if __name__ == "__main__":
    composite_for_tiktok()
    logger.info("TikTok video compositing script finished.")
