# Filename: coffee_renderer.py
# Location: D:\AI\astrology_by_coffee_v1\content\animation\render_scripts\coffee_renderer.py

from PIL import Image
from moviepy import VideoClip, AudioFileClip, VideoFileClip
import numpy as np
from pathlib import Path
import logging
import os
from typing import Dict, Optional

# Ensure logs directory exists
LOG_DIR = Path(r"D:\AI\astrology_by_coffee_v1\logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s-%(levelname)s [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "coffee_renderer.log", mode='w')
    ]
)

# Mouth sizes (same as in render_orchestrator.py)
MOUTH_SIZES = {
    1: (40, 25),
    2: (50, 30),
    3: (65, 45),
    4: (70, 50),
    5: (75, 55)
}

# Mouth positions (same as in render_orchestrator.py, centered at 510, 880)
MOUTH_POSITIONS = {
    1: (490, 867),  # Size 40x25, center at (510, 880)
    2: (485, 865),  # Size 50x30, center at (510, 880)
    3: (477, 857),  # Size 65x45, center at (510, 880)
    4: (475, 855),  # Size 70x50, center at (510, 880)
    5: (472, 852)   # Size 75x55, center at (510, 880)
}

EXPECTED_RESOLUTION = (1080, 1920)  # YouTube Shorts resolution (vertical)




# Load the wheel and icon
wheel = Image.open("wheel.png").convert("RGBA")
icon = Image.open("zodiac_icon.png").convert("RGBA")

# Resize icon if needed
icon = icon.resize((wheel.width // 4, wheel.height // 4), Image.ANTIALIAS)

# Calculate center position
icon_pos = (
    (wheel.width - icon.width) // 2,
    (wheel.height - icon.height) // 2
)

# Paste the icon onto the wheel
composite = wheel.copy()
composite.paste(icon, icon_pos, icon)

# Save the composite image to use in animation
composite.save("wheel_with_icon.png")





def load_pil_image_rgba(image_path: Path, lipsync_idx: int) -> Image.Image:
    """Load an image, convert to RGBA, resize to the appropriate MOUTH_SIZE, with a fallback for missing files."""
    try:
        img = Image.open(image_path)
        img_rgba = img.convert("RGBA") if img.mode != "RGBA" else img
        mouth_size = MOUTH_SIZES.get(lipsync_idx, MOUTH_SIZES[1])  # Default to smallest if index not found
        img_rgba = img_rgba.resize(mouth_size, Image.Resampling.LANCZOS)
        has_transparency = img_rgba.getextrema()[-1][0] < 255
        if not has_transparency:
            logging.warning(f"Image {image_path} has no transparent pixels, which may obscure the video.")
        logging.debug(f"Loaded and resized image: {image_path}, Size: {img_rgba.size}, Has transparency: {has_transparency}")
        return img_rgba
    except FileNotFoundError:
        logging.warning(f"Asset image not found: {image_path}. Using placeholder.")
        return Image.new("RGBA", MOUTH_SIZES[1], (255, 0, 255, 255))
    except Exception as e:
        logging.error(f"Error loading asset image {image_path}: {e}")
        return Image.new("RGBA", MOUTH_SIZES[1], (255, 0, 0, 255))

def render_test_frame(
    t: float,
    base_frame_np: np.ndarray,
    mouth_to_paste_pil: Optional[Image.Image],
    output_path: Path
):
    """Render a test frame to verify mouth placement."""
    try:
        frame_pil = Image.fromarray(base_frame_np).convert("RGBA")
        if mouth_to_paste_pil:
            position = MOUTH_POSITIONS.get(lipsync_idx, MOUTH_POSITIONS[1])
            frame_pil.paste(mouth_to_paste_pil, position, mouth_to_paste_pil)
        frame_pil.convert("RGB").save(output_path)
        logging.info(f"Saved test frame: {output_path}")
    except Exception as e:
        logging.error(f"Error saving test frame {output_path}: {e}")

def render_coffee_from_video_template(
    mouth_sequence: list[int],
    character_mouth_assets_path: Path,
    video_template_path: Path,
    output_video_path: Path,
    fps: int,
    audio_path_for_final_video: str,
    lipsync_to_image_id: Dict[int, Optional[int]] = None
) -> bool:
    """Render a video by compositing mouth images onto a base video template."""
    logging.info(f"Rendering Coffee video using template '{video_template_path.name}' to '{output_video_path.name}'")

    # Load mouth images
    mouth_images_pil = {}
    for lipsync_idx, image_id in lipsync_to_image_id.items():
        if image_id is not None:
            mouth_img_filename = f"coffee_mouth_speak_{image_id}.png"
            mouth_img_path = character_mouth_assets_path / mouth_img_filename
            mouth_images_pil[lipsync_idx] = load_pil_image_rgba(mouth_img_path, lipsync_idx)
            logging.info(f"Loaded mouth image for index {lipsync_idx}: {mouth_img_path}")

    # Load audio
    try:
        main_audio_clip = AudioFileClip(audio_path_for_final_video)
        video_duration = main_audio_clip.duration
        logging.info(f"Audio loaded: {audio_path_for_final_video}, Duration: {video_duration:.2f}s")
        if video_duration <= 0:
            logging.error("Audio duration is zero or negative.")
            return False
    except Exception as e:
        logging.error(f"Could not load audio {audio_path_for_final_video}: {e}")
        return False

    # Load base video template
    try:
        base_video_template_clip = VideoFileClip(str(video_template_path), target_resolution=EXPECTED_RESOLUTION)
        logging.info(f"Video template loaded: {video_template_path}, Duration: {base_video_template_clip.duration:.2f}s, Resolution: {base_video_template_clip.size}")
        if base_video_template_clip.duration < video_duration:
            logging.warning(f"Video template duration ({base_video_template_clip.duration}s) is shorter than audio duration ({video_duration}s).")
        if base_video_template_clip.size != EXPECTED_RESOLUTION:
            logging.warning(f"Video resolution {base_video_template_clip.size} does not match expected {EXPECTED_RESOLUTION}.")
    except Exception as e:
        logging.error(f"Could not load video template {video_template_path}: {e}")
        return False

    def make_frame_pil(t):
        """Generate a video frame at time t by compositing a mouth image onto the base frame."""
        current_template_time = min(t, base_video_template_clip.duration - (1/fps))
        try:
            base_frame_np = base_video_template_clip.get_frame(current_template_time)
            if base_frame_np.shape[:2] != (EXPECTED_RESOLUTION[1], EXPECTED_RESOLUTION[0]):
                logging.warning(f"Base frame shape {base_frame_np.shape[:2]} does not match expected {EXPECTED_RESOLUTION}.")
        except Exception as e:
            logging.error(f"Error getting frame at time {current_template_time}: {e}")
            return np.zeros((EXPECTED_RESOLUTION[1], EXPECTED_RESOLUTION[0], 3), dtype=np.uint8)

        frame_pil = Image.fromarray(base_frame_np)
        if frame_pil.size != EXPECTED_RESOLUTION:
            logging.warning(f"Frame size {frame_pil.size} does not match expected {EXPECTED_RESOLUTION}. Resizing.")
            frame_pil = frame_pil.resize(EXPECTED_RESOLUTION, Image.Resampling.LANCZOS)
        frame_pil = frame_pil.convert("RGBA")
        frame_num = int(t * fps)
        if frame_num < len(mouth_sequence):
            lipsync_shape_idx = mouth_sequence[frame_num]
            image_id = lipsync_to_image_id.get(lipsync_shape_idx)
            mouth_img_path = (character_mouth_assets_path / f"coffee_mouth_speak_{image_id}.png") if image_id else None
            logging.debug(f"Frame {frame_num} (t={t:.2f}s): Lip-sync index {lipsync_shape_idx}, Image: {mouth_img_path or 'None (closed mouth)'}")
            if image_id is not None:
                mouth_to_paste_pil = mouth_images_pil.get(lipsync_shape_idx)
                if mouth_to_paste_pil:
                    position = MOUTH_POSITIONS.get(lipsync_shape_idx, MOUTH_POSITIONS[1])
                    try:
                        frame_pil.paste(mouth_to_paste_pil, position, mouth_to_paste_pil)
                        logging.debug(f"Pasted mouth image for index {lipsync_shape_idx}: {mouth_img_path} at {position}")
                    except Exception as e:
                        logging.warning(f"Could not paste mouth at frame {frame_num}: {e}")
        return np.array(frame_pil.convert("RGB"))

    # Create the final video clip
    try:
        video_clip = VideoClip(make_frame_pil, duration=video_duration)
        final_video_clip = video_clip.with_audio(main_audio_clip)
        final_video_clip.write_videofile(
            str(output_video_path),
            fps=fps,
            codec="libx264",
            audio_codec="aac",
            threads=os.cpu_count() or 2,
            preset="medium",
            ffmpeg_params=["-vf", f"scale={EXPECTED_RESOLUTION[0]}:{EXPECTED_RESOLUTION[1]}:force_original_aspect_ratio=disable"],
            logger="bar"
        )
        logging.info(f"Video successfully saved: {output_video_path}")
        success = True
    except Exception as e:
        logging.error(f"Error during video writing: {e}", exc_info=True)
        success = False
    finally:
        main_audio_clip.close()
        base_video_template_clip.close()
        video_clip.close() if 'video_clip' in locals() else None
        final_video_clip.close() if 'final_video_clip' in locals() else None

    return success