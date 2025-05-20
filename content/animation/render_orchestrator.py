# Filename: render_orchestrator.py
# Location: D:\AI\astrology_by_coffee_v1\content\animation\render_orchestrator.py

import logging
import re
import os
from pathlib import Path
from typing import List, Dict, Optional
from .lipsync_analyzer import generate_mouth_animation_sequence
from .render_scripts.coffee_renderer import render_coffee_from_video_template
from .wheel_animator import integrate_rolling_wheel
from moviepy import *

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s-%(levelname)s [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Define the project base path
PROJECT_BASE_PATH = Path(r"D:\AI\astrology_by_coffee_v1")

# Video template paths
VIDEO_TEMPLATE_WIDESCREEN = PROJECT_BASE_PATH / "content" / "animation" / "video" / "prerendered" / "astrologyByCoffee" / "astrologByCoffee_widescreen.mp4"
VIDEO_TEMPLATE_MOBILE = PROJECT_BASE_PATH / "content" / "animation" / "video" / "prerendered" / "astrologyByCoffee" / "astrologyByCoffee_mobile.mp4"

# Select the active video template
ACTIVE_VIDEO_TEMPLATE = VIDEO_TEMPLATE_MOBILE

def get_mouth_image_ids(mouth_assets_path: Path) -> List[int]:
    """Scan the mouth assets directory and extract IDs from image filenames."""
    if not mouth_assets_path.is_dir():
        logging.error(f"Mouth assets directory not found: {mouth_assets_path}")
        return []

    pattern = r"coffee_mouth_speak_(\d+)\.png"
    image_ids = []

    for file_path in mouth_assets_path.glob("*.png"):
        match = re.match(pattern, file_path.name)
        if match:
            try:
                image_id = int(match.group(1))
                image_ids.append(image_id)
                logging.debug(f"Found mouth image: {file_path} with ID: {image_id}")
            except ValueError:
                logging.warning(f"Invalid ID in filename: {file_path.name}")
                continue

    image_ids.sort()
    logging.info(f"Found mouth images with IDs: {image_ids}")
    return image_ids

def render_video_for_task(
    batch_date_str: str,
    character_name: str,
    video_type: str,
    zodiac_sign: str,
    source_script_stem: str
) -> bool:
    """Render a video for a given task, including lip-sync and rolling wheel graphic."""
    logging.info(f"Rendering video for {character_name} - {video_type} - {zodiac_sign} (Batch: {batch_date_str})")

    # Construct audio file path
    audio_dir = PROJECT_BASE_PATH / "content" / "audio" / "voice" / "voice_output" / batch_date_str / character_name.lower() / video_type.lower()
    audio_filename = f"{source_script_stem}.wav"
    audio_path = audio_dir / audio_filename
    if not audio_path.is_file():
        logging.error(f"Audio file not found: {audio_path}")
        return False

    # Generate mouth animation sequence
    fps = int(os.getenv("VIDEO_FPS", 24))
    mouth_sequence = generate_mouth_animation_sequence(str(audio_path), fps=fps)
    if mouth_sequence is None:
        logging.error("Failed to generate mouth animation sequence.")
        return False

    # Set character-specific assets
    if character_name.lower() == "coffee":
        mouth_assets_path = PROJECT_BASE_PATH / "content" / "animation" / "images" / "scenes" / "astrology_by_coffee" / "coffee" / "mouth"
        video_template_path = ACTIVE_VIDEO_TEMPLATE
    else:
        logging.error(f"Rendering not implemented for character: {character_name}")
        return False

    # Verify assets
    if not video_template_path.is_file():
        logging.error(f"Video template not found: {video_template_path}")
        return False
    if not mouth_assets_path.is_dir():
        logging.error(f"Mouth assets directory not found: {mouth_assets_path}")
        return False

    # Dynamically load mouth images
    image_ids = get_mouth_image_ids(mouth_assets_path)
    if not image_ids:
        logging.warning("No mouth images found; using default closed mouth.")
        lipsync_to_image_id = {0: None}
    else:
        lipsync_to_image_id = {0: None}
        for i, image_id in enumerate(image_ids, start=1):
            lipsync_to_image_id[i] = image_id
            logging.info(f"Mapping lip-sync index {i} to mouth image: coffee_mouth_speak_{image_id}.png at {mouth_assets_path / f'coffee_mouth_speak_{image_id}.png'}")
        max_lipsync_index = max(mouth_sequence, default=0)
        if max_lipsync_index >= len(lipsync_to_image_id):
            logging.warning(f"Lip-sync indices exceed available images ({max_lipsync_index} vs {len(lipsync_to_image_id)}). Truncating.")
            mouth_sequence = [min(idx, len(lipsync_to_image_id) - 1) for idx in mouth_sequence]

    logging.info(f"Lip-sync to image ID mapping: {lipsync_to_image_id}")

    # Construct output video path
    final_videos_dated_root = PROJECT_BASE_PATH / "content" / "animation" / "video" / "final_video" / batch_date_str
    output_dir = PROJECT_BASE_PATH / "content" /"video" /final_videos_dated_root / character_name.lower() / video_type.lower()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_filename = f"{source_script_stem}_final_{batch_date_str}.mp4"
    output_video_path = output_dir / output_filename

    # Render the video with lip-sync using the existing renderer
    success = render_coffee_from_video_template(
        mouth_sequence=mouth_sequence,
        character_mouth_assets_path=mouth_assets_path,
        video_template_path=video_template_path,
        output_video_path=output_video_path,
        fps=fps,
        audio_path_for_final_video=str(audio_path),
        lipsync_to_image_id=lipsync_to_image_id
    )

    if not success:
        logging.error(f"Failed to render video with lip-sync: {output_video_path}")
        return False

    # Load the rendered video as a base clip
    base_clip = VideoFileClip(str(output_video_path))

    # Integrate the rolling wheel graphic over the base clip
    #integrate_rolling_wheel(zodiac_sign, base_clip, str(output_video_path),str(PROJECT_BASE_PATH))

    logging.info(f"Successfully rendered video with wheel graphic for {zodiac_sign}: {output_video_path}")
    return True