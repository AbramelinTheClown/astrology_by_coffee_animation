import os
import logging # For robust logging
import traceback # For detailed error tracebacks
from PIL import Image
import numpy as np # Used by MoviePy and Librosa, aliased as np
import librosa
import librosa.display
import matplotlib.pyplot as plt # For visualization in generate_mouth_animation_frames
from moviepy import VideoClip, AudioFileClip


# --- Logger Setup ---
def setup_logger(log_file_path, level=logging.INFO):
    """Sets up a logger that outputs to both console and a file."""
    logger = logging.getLogger(__name__) 
    logger.setLevel(level)
    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    # Ensure the directory for the log file exists
    log_dir = os.path.dirname(log_file_path)
    if log_dir: # Check if log_dir is not an empty string (e.g. if log_file_path is just a filename)
        os.makedirs(log_dir, exist_ok=True)
    fh = logging.FileHandler(log_file_path, mode='w')
    fh.setLevel(level)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger

# --- Configuration & Paths ---
output_dir = r"D:\AI\astrology_by_coffee_v1\video\animation_output"
os.makedirs(output_dir, exist_ok=True)

log_file = os.path.join(output_dir, "animation_generation_nebbles_gaze.log") # New log file name
logger = setup_logger(log_file, level=logging.INFO)

logger.info("Starting animation script with Nebbles' directed gaze...")

audio_file_path = r"D:\AI\astrology_by_coffee_v1\audio\horoscope_Aquarius_2025-04-20.mp3"
background_path = r"D:\AI\astrology_by_coffee_v1\images\scene\coffee_house_back_stage.png"
smoke_1_path = r"D:\AI\astrology_by_coffee_v1\images\scene\smoke_1.png"
smoke_2_path = r"D:\AI\astrology_by_coffee_v1\images\scene\smoke_2.png"
smoke_3_path = r"D:\AI\astrology_by_coffee_v1\images\scene\smoke_3.png"
coffee_body_path = r"D:\AI\astrology_by_coffee_v1\images\scene\coffee_body.png"
mouth_mid_path = r"D:\AI\astrology_by_coffee_v1\images\scene\coffee_mouth_mid.png"
mouth_wide_path = r"D:\AI\astrology_by_coffee_v1\images\scene\coffee_mouth_wide.png"
blink_image_path = r"D:\AI\astrology_by_coffee_v1\images\scene\coffee_blinks.png"
nebbles_zodiac_path = r"D:\AI\astrology_by_coffee_v1\images\scene\nebbles_zodiac.png"
nebbles_body_path = r"D:\AI\astrology_by_coffee_v1\images\scene\nebbles_body.png"
nebbles_eyes_path = r"D:\AI\astrology_by_coffee_v1\images\scene\nebbles_eyes.png" 

fps = 24
threshold_silent_global = 0.03
threshold_mid_global = 0.15

# Nebbles eye movement parameters
# For default subtle movement
NEBBLES_DEFAULT_EYE_MAX_OFFSET_X = 2  # Reduced subtle movement
NEBBLES_DEFAULT_EYE_PERIOD_X = 4.0    
NEBBLES_DEFAULT_EYE_MAX_OFFSET_Y = 1  # Reduced subtle movement
NEBBLES_DEFAULT_EYE_PERIOD_Y = 5.5    

# For "looking up" pose
NEBBLES_LOOK_UP_Y_OFFSET = -10  # Pixels to shift eyes UP (negative Y)
NEBBLES_LOOK_UP_X_OFFSET = 0    # No horizontal shift when looking up (can be adjusted)
NEBBLES_LOOK_UP_HOLD_DURATION = 1.0 # Seconds to hold the "look up" pose


# --- Image Loading Function ---
def read_image_rgba(path):
    # ... (function remains the same) ...
    logger.debug(f"Attempting to read image: {path}")
    try:
        img = Image.open(path).convert('RGBA')
        logger.debug(f"Successfully loaded and converted image: {path}")
        return img
    except FileNotFoundError:
        logger.error(f"Image file not found at {path}. Returning a placeholder.")
        return Image.new('RGBA', (100, 100), (0, 0, 0, 0))
    except Exception as e:
        logger.exception(f"Error loading image at {path}. Returning a placeholder.")
        return Image.new('RGBA', (100, 100), (0, 0, 0, 0))

# --- Load All PIL Images ---
logger.info("Loading PIL images...")
# ... (pil_images dictionary loading remains the same) ...
pil_images = {
    "background": read_image_rgba(background_path),
    "smoke_1": read_image_rgba(smoke_1_path),
    "smoke_2": read_image_rgba(smoke_2_path),
    "smoke_3": read_image_rgba(smoke_3_path),
    "coffee_body": read_image_rgba(coffee_body_path),
    "mouth_mid": read_image_rgba(mouth_mid_path),
    "mouth_wide": read_image_rgba(mouth_wide_path),
    "blink_image": read_image_rgba(blink_image_path),
    "nebbles_zodiac": read_image_rgba(nebbles_zodiac_path),
    "nebbles_body": read_image_rgba(nebbles_body_path),
    "nebbles_eyes": read_image_rgba(nebbles_eyes_path)
}
logger.info("PIL images loading process complete.")

# --- Validate Background Image & Get Canvas Size ---
# ... (validation remains the same) ...
background_image_obj = pil_images.get("background")
if not (background_image_obj and hasattr(background_image_obj, 'size') and background_image_obj.size[0] > 0):
    logger.critical("Background image not loaded correctly or is empty. Exiting.")
    exit()
canvas_size = background_image_obj.size
logger.info(f"Background image validated. Canvas size set to: {canvas_size}")

# --- Mouth Animation Frame Generation Function (Same as before) ---
def generate_mouth_animation_frames(file_path_to_analyze, fps_audio=24,
                                   threshold_silent=0.05, threshold_mid=0.25,
                                   visualize_waveform=False):
    # ... (function remains the same) ...
    logger.info(f"Generating mouth animation frames for: {file_path_to_analyze} at {fps_audio} FPS")
    mouth_animation_indices = []
    try:
        logger.info(f"Loading audio data with Librosa from: {file_path_to_analyze}")
        y, sr = librosa.load(file_path_to_analyze, sr=None)
        duration = librosa.get_duration(y=y, sr=sr)
        logger.info(f"Librosa - Native Sampling rate (sr): {sr} Hz, Duration: {duration:.2f}s")

        num_video_frames = int(duration * fps_audio)
        if num_video_frames == 0:
            logger.warning("Calculated zero video frames for mouth sync.")
            return []
        logger.info(f"Total video frames for mouth sync: {num_video_frames}")

        samples_per_video_frame = int(sr / fps_audio)
        if samples_per_video_frame == 0:
            logger.warning("Calculated zero audio samples per video frame for mouth sync.")
            return []
        
        rms_per_video_frame = []
        for i in range(num_video_frames):
            start_sample = i * samples_per_video_frame
            end_sample = min(start_sample + samples_per_video_frame, len(y))
            audio_segment = y[start_sample:end_sample]
            if len(audio_segment) > 0:
                rms_per_video_frame.append(np.sqrt(np.mean(audio_segment**2)))
            else:
                rms_per_video_frame.append(0.0)
        
        if not rms_per_video_frame:
            logger.warning("No RMS values calculated for mouth sync.")
            return []

        max_rms = np.max(rms_per_video_frame)
        if max_rms == 0:
             normalized_rms_values = [0.0] * num_video_frames
        else:
            normalized_rms_values = [rms / max_rms for rms in rms_per_video_frame]

        for norm_rms in normalized_rms_values:
            if norm_rms < threshold_silent: mouth_animation_indices.append(0)
            elif norm_rms < threshold_mid: mouth_animation_indices.append(2)
            else: mouth_animation_indices.append(3)
        
        logger.info(f"Generated {len(mouth_animation_indices)} mouth animation frames.")

        if visualize_waveform:
            logger.info("Visualizing waveform and RMS for threshold tuning...")
            plt.figure(figsize=(15, 6))
            ax1 = plt.subplot(2, 1, 1); librosa.display.waveshow(y, sr=sr, alpha=0.7, ax=ax1)
            actual_file_name = os.path.basename(file_path_to_analyze)
            plt.title(f'Waveform of {actual_file_name}'); plt.ylabel('Amplitude')
            ax2 = plt.subplot(2, 1, 2, sharex=ax1)
            times = librosa.frames_to_time(np.arange(len(normalized_rms_values)), sr=sr, hop_length=samples_per_video_frame)
            min_len = min(len(times), len(normalized_rms_values))
            plt.plot(times[:min_len], normalized_rms_values[:min_len], label='Normalized RMS', color='r')
            plt.axhline(y=threshold_silent, color='g', linestyle='--', label=f'Silent Thresh ({threshold_silent})')
            plt.axhline(y=threshold_mid, color='b', linestyle='--', label=f'Mid Thresh ({threshold_mid})')
            plt.title('Normalized RMS Energy & Thresholds'); plt.xlabel('Time (s)')
            plt.ylabel('Normalized RMS'); plt.legend(); plt.grid(True)
            plt.tight_layout(); plt.show()
        return mouth_animation_indices
    except FileNotFoundError:
        logger.error(f"Audio file for analysis not found: {file_path_to_analyze}")
        return []
    except Exception as e:
        logger.exception(f"Error in generate_mouth_animation_frames for {file_path_to_analyze}:")
        return []

# --- Nebbles Eye Movement Function (MODIFIED) ---
def calculate_nebbles_eye_offset(t, current_video_duration):
    """
    Calculates Nebbles' eye offset. Eyes look up at 1/3 and 2/3 of video duration.
    Otherwise, performs a default subtle movement.
    """
    if current_video_duration <= 0: # Avoid division by zero if duration is not set
        return (0,0)

    trigger_1_start = current_video_duration / 3.0
    trigger_1_end = trigger_1_start + NEBBLES_LOOK_UP_HOLD_DURATION

    trigger_2_start = (2.0 * current_video_duration) / 3.0
    trigger_2_end = trigger_2_start + NEBBLES_LOOK_UP_HOLD_DURATION

    # Check for "look up" states
    if (trigger_1_start <= t < trigger_1_end) or \
       (trigger_2_start <= t < trigger_2_end):
        logger.debug(f"Nebbles: LOOKING UP at t={t:.2f}")
        return (NEBBLES_LOOK_UP_X_OFFSET, NEBBLES_LOOK_UP_Y_OFFSET)
    else:
        # Default subtle movement
        offset_x = NEBBLES_DEFAULT_EYE_MAX_OFFSET_X * np.sin(2 * np.pi * t / NEBBLES_DEFAULT_EYE_PERIOD_X)
        offset_y = NEBBLES_DEFAULT_EYE_MAX_OFFSET_Y * np.cos((2 * np.pi * t / NEBBLES_DEFAULT_EYE_PERIOD_Y) + (np.pi / 4))
        # logger.debug(f"Nebbles: DEFAULT eye movement at t={t:.2f}, offset=({int(round(offset_x))},{int(round(offset_y))})")
        return int(round(offset_x)), int(round(offset_y))


# --- Generate Mouth Animation Sequence ---
# ... (logic remains the same) ...
logger.info("Generating mouth animation sequence from audio...")
mouth_animation_sequence = generate_mouth_animation_frames(
    audio_file_path,
    fps_audio=fps,
    threshold_silent=threshold_silent_global,
    threshold_mid=threshold_mid_global,
    visualize_waveform=False 
)

if not mouth_animation_sequence:
    logger.warning("Failed to generate mouth animation sequence. Using static closed mouth fallback.")
    try:
        temp_audio_for_duration = AudioFileClip(audio_file_path)
        _duration = temp_audio_for_duration.duration
        temp_audio_for_duration.close()
        mouth_animation_sequence = [0] * int(_duration * fps)
        if not mouth_animation_sequence: mouth_animation_sequence = [0] * (5*fps) 
        logger.info(f"Fallback mouth sequence created with {len(mouth_animation_sequence)} closed frames.")
    except Exception as e:
        logger.exception("Error creating fallback mouth sequence. Using minimal fallback.")
        mouth_animation_sequence = [0] * (5*fps)

# --- Map mouth indices to PIL images for OVERLAYS ---
# ... (logic remains the same) ...
mouth_overlay_image_map = {
    2: pil_images["mouth_mid"],
    3: pil_images["mouth_wide"],
}
logger.debug(f"Mouth overlay image map created: {mouth_overlay_image_map}")

# --- OPTIMIZATION: Pre-composite Static Layers ---
# ... (logic remains the same, "nebbles_eyes" is already correctly excluded) ...
logger.info("Pre-compositing static layers...")
static_layer_render_order = [
    "background", "smoke_1", "smoke_2", "smoke_3",
    "nebbles_zodiac", "nebbles_body", 
    "coffee_body",
]
pre_composited_base_scene = Image.new('RGBA', canvas_size, (0,0,0,0))
for layer_name in static_layer_render_order:
    img_to_paste = pil_images.get(layer_name)
    if img_to_paste and hasattr(img_to_paste, 'size') and img_to_paste.size[0] > 0:
        logger.debug(f"  Pasting static layer: {layer_name}")
        pre_composited_base_scene.paste(img_to_paste, (0, 0), img_to_paste)
    else:
        logger.warning(f"  Skipping static layer {layer_name} as it's invalid or not found.")
logger.info("Static layers pre-composited.")


# --- Video Frame Creation Function (Optimized) ---
saved_debug_frames = 0
max_debug_frames_to_save = 0

# This global variable will be set after loading the main audio clip
# It's used by calculate_nebbles_eye_offset via create_pil_frame_final_rgb
VIDEO_DURATION_GLOBAL = 0.0 

def create_pil_frame_final_rgb(t):
    global saved_debug_frames
    # Access the global video duration
    global VIDEO_DURATION_GLOBAL 

    current_frame_pil_rgba = pre_composited_base_scene.copy()
    current_video_frame_num = int(t * fps)

    # Dynamic Mouth Overlay
    if current_video_frame_num < len(mouth_animation_sequence):
        mouth_shape_index = mouth_animation_sequence[current_video_frame_num]
        mouth_overlay_to_paste = mouth_overlay_image_map.get(mouth_shape_index)
        if mouth_overlay_to_paste: 
            if hasattr(mouth_overlay_to_paste, 'size') and mouth_overlay_to_paste.size[0] > 0:
                current_frame_pil_rgba.paste(mouth_overlay_to_paste, (0, 0), mouth_overlay_to_paste)
    
    # Dynamic Nebbles' Eyes
    nebbles_eyes_img = pil_images.get("nebbles_eyes")
    if nebbles_eyes_img and hasattr(nebbles_eyes_img, 'size') and nebbles_eyes_img.size[0] > 0:
        # Pass the actual video duration to the offset calculation function
        eye_offset_x, eye_offset_y = calculate_nebbles_eye_offset(t, VIDEO_DURATION_GLOBAL)
        paste_position = (eye_offset_x, eye_offset_y) # Base position is (0,0) for the eye layer
        current_frame_pil_rgba.paste(nebbles_eyes_img, paste_position, nebbles_eyes_img)
        # logger.debug(f"Nebbles eyes at t={t:.2f}, offset=({eye_offset_x},{eye_offset_y}), pasted at {paste_position}") # Can be too verbose
    else:
        logger.warning(f"Nebbles_eyes image invalid or not found at t={t:.2f}")

    # Dynamic Coffee Blink animation
    blink_interval = 3.5
    blink_duration = 0.15
    if (t % blink_interval) < blink_duration:
        blink_img = pil_images.get("blink_image")
        if blink_img and hasattr(blink_img, 'size') and blink_img.size[0] > 0:
            current_frame_pil_rgba.paste(blink_img, (0, 0), blink_img)

    current_frame_pil_rgb = current_frame_pil_rgba.convert('RGB')

    if t == 0 and saved_debug_frames < max_debug_frames_to_save:
        try:
            frame_filename = os.path.join(output_dir, f"debug_pil_frame_t_{t:.2f}.png")
            current_frame_pil_rgb.save(frame_filename)
            logger.info(f"Saved debug frame: {frame_filename}")
            saved_debug_frames += 1
        except Exception as e: logger.exception(f"Error saving debug frame at t={t:.2f}")

    return np.array(current_frame_pil_rgb)

# --- Load Main Audio for Video ---
logger.info(f"Loading main audio for video from: {audio_file_path}")
main_audio_clip = None
# VIDEO_DURATION_GLOBAL is set here
try:
    main_audio_clip = AudioFileClip(audio_file_path)
    VIDEO_DURATION_GLOBAL = main_audio_clip.duration 
    logger.info(f"Main audio loaded. Duration: {VIDEO_DURATION_GLOBAL:.2f}s")
except Exception as e:
    logger.exception(f"Error loading main audio: {audio_file_path}. Video will use fallback duration and no audio.")
    VIDEO_DURATION_GLOBAL = 5.0 # Fallback duration if audio fails








# --- Load Main Audio for Video ---
logger.info(f"Loading main audio for video from: {audio_file_path}")
main_audio_clip = None
video_duration = 5.0 
try:
    main_audio_clip = AudioFileClip(audio_file_path)
    video_duration = main_audio_clip.duration
    logger.info(f"Main audio loaded. Duration: {video_duration:.2f}s")
except Exception as e:
    logger.exception(f"Error loading main audio: {audio_file_path}. Video will use fallback duration and no audio.")

# --- Create and Write Video ---
expected_num_frames = int(video_duration * fps)
if len(mouth_animation_sequence) < expected_num_frames:
    logger.warning(f"Mouth animation sequence ({len(mouth_animation_sequence)} frames) is shorter than expected video frames ({expected_num_frames}). Padding with closed mouth.")
    mouth_animation_sequence.extend([0] * (expected_num_frames - len(mouth_animation_sequence)))
logger.info(f"Final mouth animation sequence length: {len(mouth_animation_sequence)}")


logger.info(f"Creating video clip with duration: {video_duration:.2f}s, canvas size: {canvas_size}, fps: {fps}")
video_clip_raw = VideoClip(create_pil_frame_final_rgb, duration=video_duration)


if main_audio_clip:
    logger.info("Attaching audio to the video clip.")
    final_clip = video_clip_raw.with_audio(main_audio_clip)
else:
    logger.warning("Main audio not loaded. Creating video without audio.")
    final_clip = video_clip_raw

output_video_path = os.path.join(output_dir, "logged_optimized_natural_closed_mouth_animation.mp4")
logger.info(f"Attempting to write video to: {output_video_path}")

try:
    final_clip.write_videofile(
        output_video_path,
        fps=fps,
        codec='libx264',
        remove_temp=True,
        threads=os.cpu_count() or 4,
        logger='bar', # MoviePy's progress bar
        preset='medium' 
    )
    logger.info(f"Final video saved successfully to {output_video_path}")
except Exception as e:
    logger.critical(f"FATAL: Error writing final video file to {output_video_path}:")
    logger.exception(e) # Logs the full traceback
finally:
    if main_audio_clip:
        try:
            main_audio_clip.close()
            logger.info("Main audio clip closed.")
        except Exception as e:
            logger.exception("Error closing main audio clip.")

logger.info("Script finished.")
