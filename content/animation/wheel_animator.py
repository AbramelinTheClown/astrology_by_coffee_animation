# File: D:\AI\astrology_by_coffee_v1\content\animation\wheel_animator.py
import os
import logging
from pathlib import Path
from PIL import Image, ImageDraw

logger_wheel_init = logging.getLogger("WheelAnimatorInit") # For initialization logging

MOVIEPY_AVAILABLE = False
VideoFileClip, ImageClip, CompositeVideoClip = None, None, None # Pre-define for global scope within module

try:
    logger_wheel_init.info(f"Attempting to import MoviePy components (target version ~2.1.1) in wheel_animator.py...")
    
    # Correct imports for MoviePy 2.0+ (like your version 2.1.1)
    from moviepy import (
        VideoFileClip,
        ImageClip,
        CompositeVideoClip
    )
    # The .rotate() method is directly available on clips, so no specific fx import for rotation.
    
    import moviepy # To access __version__
    logger_wheel_init.info(f"MoviePy version confirmed: {moviepy.__version__}") # Should show 2.1.1
    
    logger_wheel_init.info("MoviePy components imported successfully in wheel_animator.py.")
    MOVIEPY_AVAILABLE = True
except ImportError as e:
    logger_wheel_init.error(f"Failed to import MoviePy components in wheel_animator.py. Error: {e}", exc_info=True)
    print(f"CRITICAL WARNING: MoviePy failed to import in wheel_animator.py: {e}")
except Exception as e_gen:
    logger_wheel_init.error(f"An unexpected error occurred during MoviePy import in wheel_animator.py: {e_gen}", exc_info=True)
    print(f"CRITICAL WARNING: Unexpected error importing MoviePy in wheel_animator.py: {e_gen}")

# --- Basic Logger Setup ---
def setup_simple_logger(log_level=logging.INFO, logger_name="WheelAnimator"):
    logger_instance = logging.getLogger(logger_name)
    if logger_instance.hasHandlers():
        logger_instance.handlers.clear()
    logger_instance.setLevel(log_level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s [%(filename)s:%(lineno)d] - %(message)s')
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    ch.setFormatter(formatter)
    logger_instance.addHandler(ch)
    logger_instance.propagate = False
    return logger_instance

logger = setup_simple_logger() # Main logger for this module's functions


def create_rolling_wheel_clip(
    zodiac_sign: str,
    video_duration: float,
    roll_duration: float = 2.0,
    final_pos_x: int = 33,
    final_pos_y: int = 160,
    icon_scale_factor: float = 1,
    ongoing_rotation_speed: float = -30.0, # degrees per second
    base_path_str: str = r"D:\AI\astrology_by_coffee_v1"
) -> 'ImageClip | None': 
    
    if not MOVIEPY_AVAILABLE or ImageClip is None:
        logger.error("MoviePy's ImageClip is not available. Cannot create rolling wheel clip.")
        return None

    base_path = Path(base_path_str)
    zodiac_sign_lower = zodiac_sign.lower()

    wheel_filename = "zodiac_300.png" 
    wheel_path = base_path / "content" / "animation" / "images" / "scenes" / "astrology_by_coffee" / "props" / wheel_filename
    icon_filename = f"icons8-{zodiac_sign_lower}-100.png" 
    icon_path = base_path / "content" / "animation" / "images" / "scenes" / "astrology_by_coffee" / "set" / "purple_zodiac" / icon_filename
    default_icon_filename = r"D:\AI\astrology_by_coffee_v1\content\animation\images\scenes\astrology_by_coffee\nebbles\concept\coffee_and_nebbles__screen_logo.png"
    default_icon_path = base_path / "content" / "animation" / "images" / "scenes" / "astrology_by_coffee" / "set" / "purple_zodiac" / default_icon_filename
    
    temp_dir = base_path / "temp/temp_frames_wheel_animator" 
    temp_dir.mkdir(parents=True, exist_ok=True)
    composited_image_path = temp_dir / f"wheel_with_{zodiac_sign_lower}_icon.png"

    try:
        logger.debug(f"Attempting to load wheel image from: {wheel_path}")
        if not wheel_path.is_file():
            logger.warning(f"Wheel image not found: {wheel_path}. Creating placeholder.")
            placeholder_wheel = Image.new('RGBA', (300, 300), (0,0,0,0)) 
            draw = ImageDraw.Draw(placeholder_wheel)
            draw.ellipse((10,10,290,290), outline="purple", width=20) 
            placeholder_wheel.save(wheel_path)

        with Image.open(wheel_path).convert("RGBA") as wheel_img_pil:
            actual_icon_path_to_load = icon_path
            if not icon_path.is_file():
                logger.debug(f"Icon for {zodiac_sign} ('{icon_filename}') not found at {icon_path}.")
                if default_icon_path.is_file():
                    logger.debug(f"Using default icon: {default_icon_path}")
                    actual_icon_path_to_load = default_icon_path
                else:
                    logger.warning(f"Default icon ('{default_icon_filename}') not found at: {default_icon_path}. Creating placeholder default icon.")
                    placeholder_default = Image.new('RGBA', (100,100), (100,100,100,128)) 
                    draw = ImageDraw.Draw(placeholder_default)
                    draw.text((10,40), "DEF", fill="white") 
                    placeholder_default.save(default_icon_path)
                    actual_icon_path_to_load = default_icon_path 
            
            if actual_icon_path_to_load.is_file(): 
                with Image.open(actual_icon_path_to_load).convert("RGBA") as icon_img_pil:
                    icon_width = int(wheel_img_pil.width * icon_scale_factor)
                    icon_height = int(wheel_img_pil.height * icon_scale_factor)
                    try: 
                        resample_filter = Image.Resampling.LANCZOS
                    except AttributeError: 
                        resample_filter = Image.LANCZOS
                    icon_resized = icon_img_pil.resize((icon_width, icon_height), resample_filter)
                    
                    icon_pos_x = (wheel_img_pil.width - icon_resized.width) // 2
                    icon_pos_y = (wheel_img_pil.height - icon_resized.height) // 2
                    wheel_img_pil.paste(icon_resized, (icon_pos_x, icon_pos_y), icon_resized) 
            else:
                logger.warning(f"No icon (specific or default) could be loaded for the wheel for {zodiac_sign}.")
            
            wheel_img_pil.save(composited_image_path)
            logger.debug(f"Saved composited wheel image for {zodiac_sign} to: {composited_image_path}")

    except Exception as e:
        logger.exception(f"Pillow image processing error for zodiac wheel '{zodiac_sign}':")
        return None


    try:
        # Corrected: Use set_duration()
        img_clip = ImageClip(str(composited_image_path)).with_duration(video_duration)
    except e:
        print(type(video_duration))
        print(type(img_clip))

    # Corrected: Use .w and .h for width and height for MoviePy clips
    # These are usually aliases for clip.size[0] and clip.size[1]
    if img_clip.w is None or img_clip.h is None: # Check if dimensions are loaded
        logger.error(f"ImageClip for {composited_image_path} has no dimensions (w,h). Cannot proceed.")
        # Attempt to load them if using an older way or if they are not immediately available
        # This might happen if the image file is problematic or MoviePy defers loading.
        # Forcing a read of a frame can sometimes populate these:
        try:
            img_clip.get_frame(0) # Try to read the first frame to ensure size is loaded
            if img_clip.w is None or img_clip.h is None: # Check again
                 logger.error(f"Still no dimensions after get_frame(0). ImageClip size: {img_clip.size}")
                 # Fallback to size attribute if w/h are None but size is populated
                 if img_clip.size and len(img_clip.size) == 2:
                     logger.info(f"Using img_clip.size[0] and img_clip.size[1] as fallback.")
                     start_x, start_y = -img_clip.size[0], -img_clip.size[1]
                 else:
                     return None # Cannot determine dimensions
            else:
                 start_x, start_y = -img_clip.w, -img_clip.h
        except Exception as ex_size:
            logger.exception(f"Error trying to get dimensions for ImageClip {composited_image_path}: {ex_size}")
            return None
    else:
        start_x, start_y = -img_clip.w, -img_clip.h

    end_x, end_y = final_pos_x, final_pos_y

    def position_func(t): 
        if t < 0: return (int(start_x), int(start_y))
        if t < roll_duration:
            progress = t / roll_duration
            current_x = start_x + (end_x - start_x) * progress
            current_y = start_y + (end_y - start_y) * progress
            return (int(current_x), int(current_y))
        else:
            return (int(end_x), int(end_y))

    def rotation_func(t): 
        if t < 0: return 0
        if t < roll_duration:
            return -360 * (t / roll_duration) 
        else:
            time_after_roll = t - roll_duration
            return -360 + (ongoing_rotation_speed * time_after_roll)

    animated_wheel_clip = (img_clip
                           .with_position(position_func)
                           .rotated(rotation_func, resample='bicubic')) 
    
    logger.info(f"Animated wheel clip for {zodiac_sign} created successfully.")
    return animated_wheel_clip


def integrate_rolling_wheel(
    zodiac_sign: str,
    base_clip: 'VideoFileClip', 
    final_output_path_str: str, 
    project_base_path_str: str  
) -> bool:

    if not MOVIEPY_AVAILABLE or CompositeVideoClip is None or VideoFileClip is None:
        logger.error("MoviePy (CompositeVideoClip or VideoFileClip) is not available. Cannot integrate rolling wheel.")
        return False

    logger.info(f"Integrating rolling wheel for {zodiac_sign} onto video, outputting to {final_output_path_str}")

    if base_clip.duration is None:
        logger.error("Base clip (received as argument) has no duration. Cannot determine duration for wheel animation.")
        return False
    video_duration = base_clip.duration

    wheel_animation_clip = create_rolling_wheel_clip(
        zodiac_sign=zodiac_sign,
        video_duration=video_duration,
        base_path_str=project_base_path_str
    )

    if wheel_animation_clip is None:
        logger.error(f"Failed to create rolling wheel animation for {zodiac_sign}. Wheel will not be added.")
        return False 

    final_video = CompositeVideoClip(
        [base_clip, wheel_animation_clip], 
        size=base_clip.size 
    )

    try:
        logger.info(f"Writing final video with integrated wheel to: {final_output_path_str}")
        final_video.write_videofile(
            final_output_path_str,
            codec="libx264", 
            fps=base_clip.fps if base_clip.fps else 24, 
            threads=os.cpu_count() or 4, 
            logger='bar' 
        )
        logger.info(f"Successfully integrated wheel and saved video to {final_output_path_str}")
        return True
    except Exception as e:
        logger.exception(f"Error writing final video with integrated wheel: {e}")
        return False
    finally:
        if 'final_video' in locals() and final_video: final_video.close()
        if wheel_animation_clip: wheel_animation_clip.close()
