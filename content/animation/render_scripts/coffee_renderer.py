# Filename: coffee_renderer.py
# Location: D:\AI\astrology_by_coffee_v1\content\animation\render_scripts\coffee_renderer.py

from PIL import Image
from moviepy import VideoClip, AudioFileClip, VideoFileClip # Ensure moviepy classes are imported directly
import numpy as np
from pathlib import Path
import logging
import os
from typing import Dict, Optional, List # Added List for mouth_sequence type hint

# Ensure logs directory exists
LOG_DIR = Path(r"D:\AI\astrology_by_coffee_v1\logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging
# Consider using 'a' mode for FileHandler if running in a batch to append logs
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s-%(levelname)s [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "coffee_renderer.log", mode='w') 
    ]
)
logger = logging.getLogger(__name__) # Use a module-specific logger

# Mouth sizes (reduced by 25%)
MOUTH_SIZES = {
    1: (40, 25),
    2: (50, 30),
    3: (65, 45),
    4: (70, 50),
    5: (75, 55)
}

# Mouth positions (top-left, calculated to center pivot at (510, 880) for each mouth size)
# These positions assume the video resolution is EXPECTED_RESOLUTION (1080, 1920)
# And the mouth is being placed relative to a character centered around these coordinates.
MOUTH_POSITIONS = {
    1: (540, 860),  # Example: For a mouth of size MOUTH_SIZES[1], this is its top-left on a 1080x1920 frame
    2: (540, 860),
    3: (535, 860),
    4: (535, 860),
    5: (535, 860)
}

EXPECTED_RESOLUTION = (1080, 1920)  # YouTube Shorts resolution (width, height)

def load_pil_image_rgba(image_path: Path, lipsync_idx_for_size: int) -> Image.Image: # Renamed lipsync_idx for clarity
    """Load an image, convert to RGBA, resize to the appropriate MOUTH_SIZE, with a fallback for missing files."""
    try:
        img = Image.open(image_path)
        img_rgba = img.convert("RGBA") if img.mode != "RGBA" else img
        
        # Get the mouth size based on the lipsync_idx_for_size (which maps to MOUTH_SIZES keys)
        mouth_size = MOUTH_SIZES.get(lipsync_idx_for_size, MOUTH_SIZES[1])  # Default to smallest if index not found
        
        img_rgba = img_rgba.resize(mouth_size, Image.Resampling.LANCZOS)
        
        # Check for actual transparency (alpha values less than 255)
        # This is a basic check; a more robust check might involve checking if all alpha values are 255.
        has_transparency = False
        if img_rgba.mode == 'RGBA':
            alpha_channel = img_rgba.getchannel('A')
            if alpha_channel.getextrema()[0] < 255: # min alpha is less than 255
                has_transparency = True
        
        if not has_transparency:
            logger.warning(f"Image {image_path} (resized to {mouth_size}) might not have effective transparency, which could obscure the video.")
        
        logger.debug(f"Loaded and resized image: {image_path}, Target Size for index {lipsync_idx_for_size}: {mouth_size}, Final Image Size: {img_rgba.size}, Has transparency: {has_transparency}")
        return img_rgba
    except FileNotFoundError:
        logger.warning(f"Asset image not found: {image_path}. Using pink placeholder.")
        # Use the determined mouth_size for the placeholder as well
        placeholder_size = MOUTH_SIZES.get(lipsync_idx_for_size, MOUTH_SIZES[1])
        return Image.new("RGBA", placeholder_size, (255, 0, 255, 255)) # Pink placeholder
    except Exception as e:
        logger.error(f"Error loading asset image {image_path}: {e}", exc_info=True)
        # Use the determined mouth_size for the placeholder as well
        placeholder_size = MOUTH_SIZES.get(lipsync_idx_for_size, MOUTH_SIZES[1])
        return Image.new("RGBA", placeholder_size, (255, 0, 0, 255)) # Red placeholder for other errors

def render_test_frame( # This function seems for debugging, ensure it's called correctly if used
    t: float, # time, not used in this function as written
    base_frame_np: np.ndarray,
    mouth_to_paste_pil: Optional[Image.Image],
    lipsync_idx_for_position: int, # Added missing parameter
    output_path: Path
):
    """Render a test frame to verify mouth placement."""
    try:
        frame_pil = Image.fromarray(base_frame_np).convert("RGBA")
        if mouth_to_paste_pil:
            # Get position based on the lipsync_idx that determines mouth shape/size
            position = MOUTH_POSITIONS.get(lipsync_idx_for_position, MOUTH_POSITIONS[1])
            frame_pil.paste(mouth_to_paste_pil, position, mouth_to_paste_pil)
        
        # Save as RGB
        frame_pil.convert("RGB").save(output_path)
        logger.info(f"Saved test frame: {output_path}")
    except Exception as e:
        logger.error(f"Error saving test frame {output_path}: {e}", exc_info=True)

def render_coffee_from_video_template(
    mouth_sequence: List[int], # Corrected type hint
    character_mouth_assets_path: Path,
    video_template_path: Path,
    output_video_path: Path,
    fps: int,
    audio_path_for_final_video: str,
    lipsync_to_image_id: Dict[int, Optional[int]] # This maps lipsync_shape_idx to an image_id (number in filename)
) -> bool:
    """Render a video by compositing mouth images onto a base video template."""
    logger.info(f"Rendering Coffee video using template '{video_template_path.name}' to '{output_video_path.name}'")

    # Load mouth images, keyed by lipsync_shape_idx
    mouth_images_pil: Dict[int, Image.Image] = {}
    if lipsync_to_image_id: # Ensure it's not None
        for lipsync_shape_idx, image_id_in_filename in lipsync_to_image_id.items():
            if image_id_in_filename is not None: # 0 or None might mean closed mouth, handled by not pasting
                mouth_img_filename = f"coffee_mouth_speak_{image_id_in_filename}.png"
                mouth_img_path = character_mouth_assets_path / mouth_img_filename
                # Pass lipsync_shape_idx to load_pil_image_rgba because MOUTH_SIZES is keyed by it
                mouth_images_pil[lipsync_shape_idx] = load_pil_image_rgba(mouth_img_path, lipsync_shape_idx)
                logger.info(f"Loaded mouth image for lipsync_shape_idx {lipsync_shape_idx} (image_id {image_id_in_filename}): {mouth_img_path}")
            else:
                logger.info(f"Lipsync_shape_idx {lipsync_shape_idx} maps to no image (image_id is None), representing closed mouth.")
    else:
        logger.warning("lipsync_to_image_id mapping is None. No mouth images will be loaded.")


    # Load audio
    main_audio_clip = None
    try:
        main_audio_clip = AudioFileClip(audio_path_for_final_video)
        video_duration = main_audio_clip.duration
        logger.info(f"Audio loaded: {audio_path_for_final_video}, Duration: {video_duration:.2f}s")
        if video_duration <= 0:
            logger.error("Audio duration is zero or negative.")
            if main_audio_clip: main_audio_clip.close()
            return False
    except Exception as e:
        logger.error(f"Could not load audio {audio_path_for_final_video}: {e}", exc_info=True)
        if main_audio_clip: main_audio_clip.close()
        return False

    # Load base video template
    base_video_template_clip = None
    try:
        base_video_template_clip = VideoFileClip(str(video_template_path), target_resolution=EXPECTED_RESOLUTION)
        logger.info(f"Video template loaded: {video_template_path}, Duration: {base_video_template_clip.duration:.2f}s, Resolution: {base_video_template_clip.size}")
        
        if base_video_template_clip.duration < video_duration:
            logger.warning(f"Video template duration ({base_video_template_clip.duration:.2f}s) is shorter than audio duration ({video_duration:.2f}s). Video will be truncated to audio duration.")
        
        # MoviePy's target_resolution should handle this, but good to verify
        if base_video_template_clip.size != EXPECTED_RESOLUTION:
            logger.warning(f"Video template resolution {base_video_template_clip.size} does not match expected {EXPECTED_RESOLUTION}. MoviePy's target_resolution should adjust this.")
    
    except Exception as e:
        logger.error(f"Could not load video template {video_template_path}: {e}", exc_info=True)
        if main_audio_clip: main_audio_clip.close()
        if base_video_template_clip: base_video_template_clip.close()
        return False

    first_frame_test_done = False # Flag to render only one test frame

    def make_frame_pil(t):
        nonlocal first_frame_test_done # To modify the flag
        """Generate a video frame at time t by compositing a mouth image onto the base frame."""
        
        # Ensure we don't try to get a frame beyond the template's actual duration
        # Subtract a tiny amount to avoid issues at the exact end frame
        current_template_time = min(t, base_video_template_clip.duration - (1.0/fps if base_video_template_clip.duration > 0 else 0) )
        
        try:
            base_frame_np = base_video_template_clip.get_frame(current_template_time)
        except Exception as e:
            # If reading a frame fails, log and return a black frame of expected shape
            logger.error(f"Error getting frame from base_video_template_clip at time {current_template_time:.4f} (original t={t:.4f}): {e}", exc_info=True)
            return np.zeros((EXPECTED_RESOLUTION[1], EXPECTED_RESOLUTION[0], 3), dtype=np.uint8) # Ensure H, W, C order

        # Convert NumPy array (H, W, C) to PIL Image (W, H)
        frame_pil = Image.fromarray(base_frame_np) # This should be RGB from get_frame

        # Ensure frame_pil is at the EXPECTED_RESOLUTION (W, H)
        if frame_pil.size != EXPECTED_RESOLUTION:
            logger.warning(f"Frame (from template at {current_template_time:.2f}s) size {frame_pil.size} does not match expected {EXPECTED_RESOLUTION}. Resizing.")
            frame_pil = frame_pil.resize(EXPECTED_RESOLUTION, Image.Resampling.LANCZOS)
        
        # Convert to RGBA for pasting transparent mouths
        frame_pil = frame_pil.convert("RGBA")
        
        frame_num = int(t * fps)
        
        if frame_num < len(mouth_sequence):
            lipsync_shape_idx = mouth_sequence[frame_num] # This is the key for MOUTH_SIZES and MOUTH_POSITIONS
            
            # lipsync_to_image_id maps this shape_idx to the number in the filename (e.g., coffee_mouth_speak_1.png -> image_id=1)
            # We need mouth_images_pil to be keyed by lipsync_shape_idx as well.
            mouth_to_paste_pil = mouth_images_pil.get(lipsync_shape_idx)
            
            if mouth_to_paste_pil:
                # Position also needs to be based on lipsync_shape_idx
                position = MOUTH_POSITIONS.get(lipsync_shape_idx, MOUTH_POSITIONS[1]) # Default if not found
                try:
                    frame_pil.paste(mouth_to_paste_pil, position, mouth_to_paste_pil) # Use mouth's alpha as mask
                    # logger.debug(f"Frame {frame_num} (t={t:.2f}s): Pasted mouth for lipsync_shape_idx {lipsync_shape_idx} at {position}")
                except Exception as e:
                    logger.warning(f"Could not paste mouth image (for lipsync_shape_idx {lipsync_shape_idx}) at frame {frame_num}: {e}", exc_info=True)
            # else:
                # logger.debug(f"Frame {frame_num} (t={t:.2f}s): No mouth image for lipsync_shape_idx {lipsync_shape_idx} (closed mouth).")
        # else:
            # logger.debug(f"Frame {frame_num} (t={t:.2f}s): Frame number exceeds mouth_sequence length. No mouth displayed.")

        # For debugging: Save the first processed frame with a mouth (if any)
        # if not first_frame_test_done and mouth_to_paste_pil:
        #     test_output_dir = LOG_DIR / "test_frames"
        #     test_output_dir.mkdir(parents=True, exist_ok=True)
        #     render_test_frame(t, np.array(frame_pil.convert("RGB")), mouth_to_paste_pil, lipsync_shape_idx, test_output_dir / f"test_frame_{frame_num}_time_{t:.2f}.png")
        #     first_frame_test_done = True
            
        return np.array(frame_pil.convert("RGB")) # Return as RGB NumPy array

    # Create the final video clip
    video_clip = None
    final_video_clip_obj = None # Renamed to avoid conflict with VideoFileClip import
    success = False
    try:
        logger.info(f"Creating VideoClip with duration: {video_duration:.2f}s, FPS: {fps}")
        video_clip = VideoClip(make_frame_pil, duration=video_duration)
        
        logger.info("Setting audio for the video clip.")
        final_video_clip_obj = video_clip.with_audio(main_audio_clip) # Use set_audio, not with_audio for VideoClip
        
        logger.info(f"Writing final video to: {output_video_path}")
        final_video_clip_obj.write_videofile(
            str(output_video_path),
            fps=fps,
            codec="libx264",
            audio_codec="aac",
            threads=os.cpu_count() or 2, # Use available CPUs or default to 2
            preset="medium", # 'medium' is a good balance. 'ultrafast' is faster but lower quality. 'slower' is better quality but slower.
            # REMOVED ffmpeg_params for scaling, as make_frame_pil should handle resolution.
            # ffmpeg_params=["-vf", f"scale={EXPECTED_RESOLUTION[0]}:{EXPECTED_RESOLUTION[1]}:force_original_aspect_ratio=disable"],
            logger="bar" # Progress bar
        )
        logger.info(f"Video successfully saved: {output_video_path}")
        success = True
    except Exception as e:
        logger.error(f"Error during video clip creation or writing: {e}", exc_info=True)
        success = False
    finally:
        # Ensure all clips are closed to release resources
        if main_audio_clip:
            main_audio_clip.close()
            logger.debug("Closed main_audio_clip.")
        if base_video_template_clip:
            base_video_template_clip.close()
            logger.debug("Closed base_video_template_clip.")
        if video_clip: # This is the VideoClip instance
            video_clip.close()
            logger.debug("Closed video_clip (the VideoClip object).")
        if final_video_clip_obj: # This is the clip with audio
            final_video_clip_obj.close()
            logger.debug("Closed final_video_clip_obj (clip with audio).")

    return success

