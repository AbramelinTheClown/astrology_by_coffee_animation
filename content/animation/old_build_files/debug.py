# Filename: lipsync_analyzer.py
# Location: D:\AI\astrology_by_coffee_v1\content\animation\lipsync_analyzer.py

import logging
import numpy as np
import librosa
import os
from pathlib import Path
import matplotlib.pyplot as plt
from moviepy.editor import AudioFileClip
import dotenv

# Load .env file
dotenv.load_dotenv(dotenv_path=Path(r"D:\AI\astrology_by_coffee_v1\.env"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s-%(levelname)s [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[logging.StreamHandler()]
)

def generate_mouth_animation_frames(
    file_path_to_analyze: str,
    fps_audio: int = 24,
    threshold_silent: float = float(os.getenv("LIPSYNC_THRESHOLD_SILENT", 0.03)),
    threshold_mid: float = float(os.getenv("LIPSYNC_THRESHOLD_MID", 0.15)),
    visualize_waveform: bool = False
) -> list[int]:
    """
    Generate mouth animation frame indices based on audio energy.

    Args:
        file_path_to_analyze (str): Path to the audio file.
        fps_audio (int): Frames per second for video.
        threshold_silent (float): RMS threshold for silent (closed mouth).
        threshold_mid (float): RMS threshold for mid-level mouth movement.
        visualize_waveform (bool): If True, display waveform and RMS plot.

    Returns:
        list[int]: List of mouth animation indices (0=closed, 2=mid, 3=wide).
    """
    logging.info(f"Analyzing audio for lip-sync: {file_path_to_analyze} at {fps_audio} FPS")
    mouth_animation_indices = []
    try:
        logging.info(f"Loading audio data with Librosa from: {file_path_to_analyze}")
        y, sr = librosa.load(file_path_to_analyze, sr=None)
        duration = librosa.get_duration(y=y, sr=sr)
        logging.info(f"Librosa - Native SR: {sr} Hz, Duration: {duration:.2f}s")

        num_video_frames = int(duration * fps_audio)
        if num_video_frames == 0:
            logging.warning("Calculated zero video frames. Audio might be too short or FPS too low.")
            return []
        logging.info(f"Total video frames for lip-sync: {num_video_frames}")

        samples_per_video_frame = int(sr / fps_audio)
        if samples_per_video_frame == 0:
            logging.warning("Calculated zero audio samples per frame. FPS might be too high.")
            return []
        logging.debug(f"Audio samples per video frame: {samples_per_video_frame}")

        rms_per_video_frame = []
        for i in range(num_video_frames):
            start_sample = i * samples_per_video_frame
            end_sample = min(start_sample + samples_per_video_frame, len(y))
            audio_segment = y[start_sample:end_sample]
            if len(audio_segment) > 0:
                rms = np.sqrt(np.mean(audio_segment**2))
                rms_per_video_frame.append(rms)
            else:
                rms_per_video_frame.append(0.0)

        if not rms_per_video_frame:
            logging.warning("No RMS values calculated for lip-sync.")
            return []

        max_rms = np.max(rms_per_video_frame)
        if max_rms == 0:
            logging.info("Audio is silent. All mouth frames will be closed.")
            normalized_rms_values = [0.0] * num_video_frames
        else:
            normalized_rms_values = [rms / max_rms for rms in rms_per_video_frame]
        logging.debug(f"Normalized RMS values (first 10): {normalized_rms_values[:10]}")

        for norm_rms in normalized_rms_values:
            if norm_rms < threshold_silent:
                mouth_animation_indices.append(0)  # Closed mouth
            elif norm_rms < threshold_mid:
                mouth_animation_indices.append(2)  # Mid mouth
            else:
                mouth_animation_indices.append(3)  # Wide mouth

        logging.info(f"Generated {len(mouth_animation_indices)} mouth animation frame indices for {file_path_to_analyze}.")
        return mouth_animation_indices

    except FileNotFoundError:
        logging.error(f"Audio file not found: {file_path_to_analyze}")
        return []
    except Exception as e:
        logging.error(f"Error in generate_mouth_animation_frames for {file_path_to_analyze}: {e}", exc_info=True)
        return []

def generate_mouth_animation_sequence(audio_file_path: str, fps: int = 24) -> list[int]:
    """
    Wrapper function to generate mouth animation sequence.

    Args:
        audio_file_path (str): Path to the audio file.
        fps (int): Frames per second for video.

    Returns:
        list[int]: List of mouth animation indices, or None if failed.
    """
    logging.info(f"Generating mouth animation sequence from audio: {audio_file_path}")
    mouth_animation_sequence = generate_mouth_animation_frames(
        file_path_to_analyze=audio_file_path,
        fps_audio=fps,
        visualize_waveform=False
    )

    if not mouth_animation_sequence:
        logging.warning("Failed to generate mouth animation sequence. Using fallback.")
        try:
            temp_audio = AudioFileClip(audio_file_path)
            duration = temp_audio.duration
            temp_audio.close()
            num_frames = int(duration * fps)
            mouth_animation_sequence = [0] * (num_frames or 5 * fps)  # Fallback to 5s if zero
            logging.info(f"Fallback sequence created with {len(mouth_animation_sequence)} closed frames.")
        except Exception as e:
            logging.error(f"Error creating fallback sequence: {e}", exc_info=True)
            mouth_animation_sequence = [0] * (5 * fps)
    return mouth_animation_sequence