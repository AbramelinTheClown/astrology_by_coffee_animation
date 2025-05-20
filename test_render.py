import sys
import os
from pathlib import Path  # Move this import earlier
import logging  # Already present

# Define LOG_DIR before using it in logging configuration
LOG_DIR = Path(r"D:\AI\astrology_by_coffee_v1\logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s-%(levelname)s [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "test_render.log", mode='w')
    ]
)

# Existing imports (unchanged)
from content.animation.lipsync_analyzer import generate_mouth_animation_sequence
import random
from PIL import Image
import numpy as np
from moviepy import *
from typing import Dict, Optional

project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)
print("Added to sys.path:", project_root)
# Configuration
PROJECT_BASE_PATH = Path(r"D:\AI\astrology_by_coffee_v1")
AUDIO_PATH = PROJECT_BASE_PATH / "content" / "audio" / "voice" / "voice_output" / "2025-05-17" / "coffee" / "youtubeshort" / "coffee_youtubeshort_20250517_220411618932Z_Aries_script.wav"
MOUTH_ASSETS_PATH = PROJECT_BASE_PATH / "content" / "animation" / "images" / "scenes" / "astrology_by_coffee" / "coffee" / "mouth"
VIDEO_TEMPLATE_PATH = PROJECT_BASE_PATH / "content" / "animation" / "video" / "prerendered" / "astrologyByCoffee" / "astrologyByCoffee_mobile.mp4"
OUTPUT_DIR = PROJECT_BASE_PATH / "content" / "animation" / "video" / "final_video" / "2025-05-17" / "coffee" / "youtubeshort"
OUTPUT_VIDEO_PATH = OUTPUT_DIR / "coffee_youtubeshort_20250517_220411618932Z_Aries_script_final_2025-05-17.mp4"
FPS = 24
NUM_TEST_FRAMES = 5
EXPECTED_RESOLUTION = (1080, 1920)  # YouTube Shorts resolution (vertical)

# Mouth sizes (reduced by 25%)
MOUTH_SIZES = {
    1: (40, 25),
    2: (50, 30),
    3: (65, 45),
    4: (70, 50),
    5: (75, 55)
}

# Mouth positions (adjusted: up by 75% of height, right by 25% of width from center at (540, 960))
# Mouth positions (top-left, calculated to center pivot at (510, 880) for each mouth size)
MOUTH_POSITIONS = {
    1: (540, 860),  # Size 32x20, center at (510, 880)
    2: (540, 860),  # Size 63x40, center at (510, 880)
    3: (535, 860),  # Size 95x60, center at (510, 880)
    4: (535, 860), # Size 127x80, center at (510, 880)
    5: (535, 860)   # Size 158x100, center at (510, 880)
}
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

def get_mouth_image_ids(mouth_assets_path: Path) -> list[int]:
    """Scan the mouth assets directory and extract IDs from image filenames."""
    if not mouth_assets_path.is_dir():
        logging.error(f"Mouth assets directory not found: {mouth_assets_path}")
        return []
    pattern = r"coffee_mouth_speak_(\d+)\.png"
    image_ids = []
    for file_path in mouth_assets_path.glob("*.png"):
        import re
        match = re.match(pattern, file_path.name)
        if match:
            try:
                image_id = int(match.group(1))
                image_ids.append(image_id)
                logging.debug(f"Found mouth image: {file_path} with ID: {image_id}")
            except ValueError:
                logging.warning(f"Invalid ID in filename: {file_path.name}")
    image_ids.sort()
    logging.info(f"Found mouth images with IDs: {image_ids}")
    return image_ids

def render_test_frame(
    t: float,
    base_frame_np: np.ndarray,
    mouth_to_paste_pil: Optional[Image.Image],
    lipsync_idx: int,
    output_path: Path
):
    """Render a test frame to verify mouth placement."""
    try:
        logging.debug(f"Base frame shape: {base_frame_np.shape}")
        frame_pil = Image.fromarray(base_frame_np)
        if frame_pil.size != EXPECTED_RESOLUTION:
            logging.warning(f"Frame size {frame_pil.size} does not match expected {EXPECTED_RESOLUTION}. Resizing.")
            frame_pil = frame_pil.resize(EXPECTED_RESOLUTION, Image.Resampling.LANCZOS)
        frame_pil = frame_pil.convert("RGBA")
        if mouth_to_paste_pil:
            position = MOUTH_POSITIONS.get(lipsync_idx, MOUTH_POSITIONS[1])
            logging.debug(f"Pasting mouth image of size {mouth_to_paste_pil.size} at {position}")
            frame_pil.paste(mouth_to_paste_pil, position, mouth_to_paste_pil)
        frame_pil.convert("RGB").save(output_path)
        logging.info(f"Saved test frame: {output_path}")
    except Exception as e:
        logging.error(f"Error saving test frame {output_path}: {e}")



def test_render():
    """Test render random frames and optionally render the full video, bypassing TTS and LLM."""
    logging.info("Starting test render for Aries youtubeshort video")

    # Verify assets
    if not AUDIO_PATH.is_file():
        logging.error(f"Audio file not found: {AUDIO_PATH}")
        return
    if not VIDEO_TEMPLATE_PATH.is_file():
        logging.error(f"Video template not found: {VIDEO_TEMPLATE_PATH}")
        return
    if not MOUTH_ASSETS_PATH.is_dir():
        logging.error(f"Mouth assets directory not found: {MOUTH_ASSETS_PATH}")
        return

    # Load audio duration
    try:
        audio_clip = AudioFileClip(str(AUDIO_PATH))
        video_duration = audio_clip.duration
        logging.info(f"Audio loaded: {AUDIO_PATH}, Duration: {video_duration:.2f}s")
    except Exception as e:
        logging.error(f"Could not load audio {AUDIO_PATH}: {e}")
        return
    finally:
        audio_clip.close()

    # Generate mouth animation sequence
    mouth_sequence = generate_mouth_animation_sequence(str(AUDIO_PATH), fps=FPS)
    if not mouth_sequence:
        logging.error("Failed to generate mouth animation sequence")
        return
    logging.info(f"Generated {len(mouth_sequence)} mouth animation indices")

    # Load mouth images
    image_ids = get_mouth_image_ids(MOUTH_ASSETS_PATH)
    if not image_ids:
        logging.warning("No mouth images found; using default closed mouth.")
        lipsync_to_image_id = {0: None}
    else:
        lipsync_to_image_id = {0: None}
        for i, image_id in enumerate(image_ids, start=1):  # Map indices 1-5 to image_ids
            lipsync_to_image_id[i] = image_id
            logging.info(f"Mapping lip-sync index {i} to mouth image: coffee_mouth_speak_{image_id}.png at {MOUTH_ASSETS_PATH / f'coffee_mouth_speak_{image_id}.png'}")
        max_lipsync_index = max(mouth_sequence, default=0)
        if max_lipsync_index >= len(lipsync_to_image_id):
            logging.warning(f"Lip-sync indices exceed available images ({max_lipsync_index} vs {len(lipsync_to_image_id)}). Truncating.")
            mouth_sequence = [min(idx, len(lipsync_to_image_id) - 1) for idx in mouth_sequence]
    logging.info(f"Lip-sync to image ID mapping: {lipsync_to_image_id}")

    mouth_images_pil = {}
    for lipsync_idx, image_id in lipsync_to_image_id.items():
        if image_id is not None:
            mouth_img_filename = f"coffee_mouth_speak_{image_id}.png"
            mouth_img_path = MOUTH_ASSETS_PATH / mouth_img_filename
            mouth_images_pil[lipsync_idx] = load_pil_image_rgba(mouth_img_path, lipsync_idx)
            logging.info(f"Loaded mouth image for index {lipsync_idx}: {mouth_img_path}")

    # Load video template
    try:
        base_video_template_clip = VideoFileClip(str(VIDEO_TEMPLATE_PATH), target_resolution=EXPECTED_RESOLUTION)
        logging.info(f"Video template loaded: {VIDEO_TEMPLATE_PATH}, Duration: {base_video_template_clip.duration:.2f}s, Resolution: {base_video_template_clip.size}")
        if base_video_template_clip.size != EXPECTED_RESOLUTION:
            logging.warning(f"Video resolution {base_video_template_clip.size} does not match expected {EXPECTED_RESOLUTION}.")
    except Exception as e:
        logging.error(f"Could not load video template {VIDEO_TEMPLATE_PATH}: {e}")
        return

    # Generate random test frame times
    test_frame_times = sorted([random.uniform(0, video_duration) for _ in range(NUM_TEST_FRAMES)])
    logging.info(f"Selected test frame times: {test_frame_times}")

    # Render test frames
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for t in test_frame_times:
        frame_num = int(t * FPS)
        if frame_num >= len(mouth_sequence):
            logging.warning(f"Frame {frame_num} (t={t:.2f}s) exceeds mouth sequence length {len(mouth_sequence)}. Skipping.")
            continue
        lipsync_shape_idx = mouth_sequence[frame_num]
        image_id = lipsync_to_image_id.get(lipsync_shape_idx)
        mouth_img_path = (MOUTH_ASSETS_PATH / f"coffee_mouth_speak_{image_id}.png") if image_id else None
        logging.debug(f"Test frame at t={t:.2f}s (frame {frame_num}): Lip-sync index {lipsync_shape_idx}, Image: {mouth_img_path or 'None (closed mouth)'}")

        try:
            base_frame_np = base_video_template_clip.get_frame(min(t, base_video_template_clip.duration - (1/FPS)))
            if base_frame_np.shape[:2] != (EXPECTED_RESOLUTION[1], EXPECTED_RESOLUTION[0]):
                logging.warning(f"Base frame shape {base_frame_np.shape[:2]} does not match expected {EXPECTED_RESOLUTION}.")
        except Exception as e:
            logging.error(f"Error getting frame at time {t:.2f}s: {e}")
            continue

        render_test_frame(t, base_frame_np, mouth_images_pil.get(lipsync_shape_idx) if image_id else None, lipsync_shape_idx, OUTPUT_DIR / f"test_frame_t_{t:.1f}_idx_{lipsync_shape_idx}.png")

    base_video_template_clip.close()

    # Prompt for full render
    print(f"\nTest frames saved to: {OUTPUT_DIR}")
    print("Please review the test frames to verify mouth animations, proportions, and state balance.")
    confirm = input("Proceed with full video render? (yes/no): ")
    if confirm.lower() != 'yes':
        logging.info("Full video rendering cancelled by user.")
        return

    # Full render
    logging.info("Starting full video render")
    try:
        audio_clip = AudioFileClip(str(AUDIO_PATH))
        base_video_template_clip = VideoFileClip(str(VIDEO_TEMPLATE_PATH), target_resolution=EXPECTED_RESOLUTION)

        def make_frame_pil(t):
            current_template_time = min(t, base_video_template_clip.duration - (1/FPS))
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
            frame_num = int(t * FPS)
            if frame_num < len(mouth_sequence):
                lipsync_shape_idx = mouth_sequence[frame_num]
                image_id = lipsync_to_image_id.get(lipsync_shape_idx)
                mouth_img_path = (MOUTH_ASSETS_PATH / f"coffee_mouth_speak_{image_id}.png") if image_id else None
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

        video_clip = VideoClip(make_frame_pil, duration=video_duration)
        final_video_clip = video_clip.with_audio(audio_clip)
        final_video_clip.write_videofile(
            str(OUTPUT_VIDEO_PATH),
            fps=FPS,
            codec="libx264",
            audio_codec="aac",
            threads=os.cpu_count() or 2,
            preset="medium",
            ffmpeg_params=["-vf", f"scale={EXPECTED_RESOLUTION[0]}:{EXPECTED_RESOLUTION[1]}:force_original_aspect_ratio=disable"],
            logger="bar"
        )
        logging.info(f"Video successfully saved: {OUTPUT_VIDEO_PATH}")
    except Exception as e:
        logging.error(f"Error during video writing: {e}", exc_info=True)
    finally:
        audio_clip.close()
        base_video_template_clip.close()

if __name__ == "__main__":
    test_render()