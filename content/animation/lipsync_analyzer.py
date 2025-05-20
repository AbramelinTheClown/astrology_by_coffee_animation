# Filename: lipsync_analyzer.py
# Location: D:\AI\astrology_by_coffee_v1\content\animation\lipsync_analyzer.py
import librosa
import logging
import numpy as np
import librosa
import os
from pathlib import Path
from collections import Counter
from moviepy import AudioFileClip
import dotenv
import matplotlib
matplotlib.use('Agg')  # Set non-interactive backend
import matplotlib.pyplot as plt

# Load .env file
dotenv.load_dotenv(dotenv_path=Path(r"D:\AI\astrology_by_coffee_v1\.env"))

# Ensure logs directory exists
LOG_DIR = Path(r"D:\AI\astrology_by_coffee_v1\logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s-%(levelname)s [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "lipsync_analyzer.log", mode='w')
    ]
)

def generate_mouth_animation_frames(
    file_path_to_analyze: str,
    fps_audio: int = int(os.getenv("VIDEO_FPS", 24)),
    threshold_silent: float = float(os.getenv("LIPSYNC_THRESHOLD_SILENT", 0.02)),
    threshold_slight: float = float(os.getenv("LIPSYNC_THRESHOLD_SLIGHT", 0.12)),
    threshold_mid: float = float(os.getenv("LIPSYNC_THRESHOLD_MID", 0.25)),
    threshold_wider: float = float(os.getenv("LIPSYNC_THRESHOLD_WIDER", 0.33)),
    threshold_very_wide: float = float(os.getenv("LIPSYNC_THRESHOLD_VERY_WIDE", 0.65)),
    visualize_waveform: bool = True
) -> list[int]:
    logging.info(f"Analyzing audio for lip-sync: {file_path_to_analyze} at {fps_audio} FPS")
    mouth_animation_indices = []
    try:
        logging.info(f"Loading audio data with Librosa from: {file_path_to_analyze}")
        try:
            y, sr = librosa.load(file_path_to_analyze, sr=None, mono=True)
        except Exception as e:
            logging.error(f"Failed to load audio with Librosa: {e}", exc_info=True)
            raise
        duration = librosa.get_duration(y=y, sr=sr)
        logging.info(f"Librosa - Native SR: {sr} Hz, Duration: {duration:.2f}s")
        if sr != 44100:
            logging.warning(f"Audio sample rate is {sr} Hz, expected 44100 Hz. Resampling.")
            y = librosa.resample(y, orig_sr=sr, target_sr=44100)
            sr = 44100

        amplification_factor = 10.0
        y = y * amplification_factor
        logging.info(f"Applied amplification factor: {amplification_factor}")

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

        raw_rms_mean = np.mean(rms_per_video_frame)
        raw_rms_std = np.std(rms_per_video_frame)
        raw_rms_min = np.min(rms_per_video_frame)
        raw_rms_max = np.max(rms_per_video_frame)
        logging.info(f"Raw RMS stats: Mean={raw_rms_mean:.6f}, Std={raw_rms_std:.6f}, Min={raw_rms_min:.6f}, Max={raw_rms_max:.6f}")

        max_rms = np.max(rms_per_video_frame)
        if max_rms == 0:
            logging.info("Audio is silent. All mouth frames will be closed.")
            normalized_rms_values = [0.0] * num_video_frames
        else:
            normalized_rms_values = [rms / max_rms for rms in rms_per_video_frame]

        rms_mean = np.mean(normalized_rms_values)
        rms_std = np.std(normalized_rms_values)
        rms_min = np.min(normalized_rms_values)
        rms_max = np.max(normalized_rms_values)
        logging.info(f"Normalized RMS stats: Mean={rms_mean:.4f}, Std={rms_std:.4f}, Min={rms_min:.4f}, Max={rms_max:.4f}")
        logging.info(f"Thresholds: Silent={threshold_silent:.4f}, Slight={threshold_slight:.4f}, Mid={threshold_mid:.4f}, Wider={threshold_wider:.4f}, Very Wide={threshold_very_wide:.4f}")

        if visualize_waveform:
            logging.info("Generating waveform and RMS visualization")
            try:
                time_axis = np.linspace(0, duration, len(y))
                frame_times = np.linspace(0, duration, num_video_frames)

                plt.figure(figsize=(12, 8))
                plt.subplot(2, 1, 1)
                plt.plot(time_axis, y, label='Waveform', color='blue')
                plt.title('Audio Waveform')
                plt.xlabel('Time (s)')
                plt.ylabel('Amplitude')
                plt.grid(True)

                plt.subplot(2, 1, 2)
                plt.plot(frame_times, normalized_rms_values, label='Normalized RMS', color='orange')
                plt.axhline(y=threshold_silent, color='red', linestyle='--', label=f'Silent Threshold ({threshold_silent})')
                plt.axhline(y=threshold_slight, color='green', linestyle='--', label=f'Slight Threshold ({threshold_slight})')
                plt.axhline(y=threshold_mid, color='purple', linestyle='--', label=f'Mid Threshold ({threshold_mid})')
                plt.axhline(y=threshold_wider, color='brown', linestyle='--', label=f'Wider Threshold ({threshold_wider})')
                plt.axhline(y=threshold_very_wide, color='pink', linestyle='--', label=f'Very Wide Threshold ({threshold_very_wide})')
                plt.title('Normalized RMS per Frame')
                plt.xlabel('Time (s)')
                plt.ylabel('Normalized RMS')
                plt.legend()
                plt.grid(True)

                plot_filename = LOG_DIR / f"waveform_rms_{Path(file_path_to_analyze).stem}.png"
                plt.tight_layout()
                plt.savefig(plot_filename)
                plt.close()
                logging.info(f"Saved waveform and RMS plot to: {plot_filename}")
            except Exception as e:
                logging.error(f"Error generating waveform visualization: {e}", exc_info=True)
                raise

        mouth_animation_indices = []
        for norm_rms in normalized_rms_values:
            if norm_rms < threshold_silent:
                mouth_animation_indices.append(0)
            elif norm_rms < threshold_slight:
                mouth_animation_indices.append(1)
            elif norm_rms < threshold_mid:
                mouth_animation_indices.append(2)
            elif norm_rms < threshold_wider:
                mouth_animation_indices.append(3)
            elif norm_rms < threshold_very_wide:
                mouth_animation_indices.append(4)
            else:
                mouth_animation_indices.append(5)

        smoothed_indices = []
        window_size = 2
        half_window = window_size // 2
        for i in range(len(mouth_animation_indices)):
            start_idx = max(0, i - half_window)
            end_idx = min(len(mouth_animation_indices), i + half_window + 1)
            window = mouth_animation_indices[start_idx:end_idx]
            avg_idx = round(sum(window) / len(window))
            if i > 0:
                prev_idx = smoothed_indices[-1]
                if avg_idx > prev_idx + 2:
                    avg_idx = prev_idx + 2
                elif avg_idx < prev_idx - 2:
                    avg_idx = prev_idx - 2
            smoothed_indices.append(min(max(avg_idx, 0), 5))

        mouth_animation_indices = smoothed_indices
        logging.info(f"Applied smoothing with window size {window_size}")

        index_counts = Counter(mouth_animation_indices)
        total_frames = len(mouth_animation_indices)
        distribution = {k: f"{v} ({v/total_frames*100:.2f}%)" for k, v in index_counts.items()}
        logging.info(f"Mouth index distribution (after smoothing): {distribution} (0=closed, 1=slight, 2=mid, 3=wider, 4=wide, 5=very wide)")

        logging.debug(f"Returning sequence of length {len(mouth_animation_indices)}")
        return mouth_animation_indices

    except FileNotFoundError:
        logging.error(f"Audio file not found: {file_path_to_analyze}")
        return []
    except Exception as e:
        logging.error(f"Error in generate_mouth_animation_frames for {file_path_to_analyze}: {e}", exc_info=True)
        return []

def generate_mouth_animation_sequence(audio_file_path: str, fps: int = int(os.getenv("VIDEO_FPS", 24))) -> list[int]:
    """Wrapper function to generate mouth animation sequence."""
    logging.info(f"Generating mouth animation sequence from audio: {audio_file_path}")
    if not Path(audio_file_path).is_file():
        logging.error(f"Audio file not found: {audio_file_path}. Using fallback sequence of closed mouths.")
        try:
            temp_audio = AudioFileClip(audio_file_path)
            duration = temp_audio.duration
            temp_audio.close()
        except Exception:
            duration = 5.0
        num_frames = int(duration * fps)
        mouth_animation_sequence = [0] * (num_frames or 5 * fps)
        logging.info(f"Fallback sequence created with {len(mouth_animation_sequence)} closed frames.")
        return mouth_animation_sequence

    # Check audio duration before processing
    try:
        temp_audio = AudioFileClip(audio_file_path)
        duration = temp_audio.duration
        temp_audio.close()
        logging.info(f"Audio duration: {duration:.2f}s")
        if duration <= 0:
            logging.warning("Audio duration is 0. Using fallback sequence.")
            num_frames = int(5.0 * fps)  # Fallback to 5 seconds
            mouth_animation_sequence = [0] * num_frames
            logging.info(f"Fallback sequence created with {len(mouth_animation_sequence)} closed frames.")
            return mouth_animation_sequence
    except Exception as e:
        logging.error(f"Error checking audio duration: {e}", exc_info=True)
        num_frames = int(5.0 * fps)
        mouth_animation_sequence = [0] * num_frames
        logging.info(f"Fallback sequence created with {len(mouth_animation_sequence)} closed frames.")
        return mouth_animation_sequence

    mouth_animation_sequence = generate_mouth_animation_frames(
        file_path_to_analyze=audio_file_path,
        fps_audio=fps,
        visualize_waveform=True
    )
    logging.info(f"Returned sequence: {mouth_animation_sequence}")
    logging.info(f"Generated sequence length: {len(mouth_animation_sequence)}")
    logging.info(f"First 10 indices: {mouth_animation_sequence[:10]}")

    if not mouth_animation_sequence:
        logging.warning("Failed to generate mouth animation sequence. Using fallback.")
        num_frames = int(duration * fps)
        mouth_animation_sequence = [0] * (num_frames or 5 * fps)
        logging.info(f"Fallback sequence created with {len(mouth_animation_sequence)} closed frames.")
    else:
        logging.info("Successfully generated mouth animation sequence.")
    return mouth_animation_sequence