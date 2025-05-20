import os
from PIL import Image
import logging

# --- Basic Logger Setup ---
def setup_simple_logger(log_level=logging.INFO):
    """Sets up a simple console logger."""
    logger = logging.getLogger("ImageResizerCompositorScript") # Updated logger name
    logger.setLevel(log_level)

    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    return logger

logger = setup_simple_logger()

# --- Configuration ---
# Input for resizing
ZODIAC_IMAGE_PATH = r"D:\AI\astrology_by_coffee_v1\images\scene\coffee_zodiac.png"
TARGET_ZODIAC_SIZE = (500, 500) # Target width and height for the zodiac image


NEBBLES_BODY_IMAGE_PATH = r"D:\AI\astrology_by_coffee_v1\images\scene\nebbles_body.png"
# Offset for the zodiac image from the center
ZODIAC_CENTER_OFFSET_X = 205# Pixels to shift right from center
ZODIAC_CENTER_OFFSET_Y = 310   # Pixels to shift down from center (0 for no vertical shift from center)


def load_image_for_compositing(path, image_description="Image"):
    """Loads an image and ensures it's RGBA for compositing."""
    logger.debug(f"Loading {image_description} from: {path}")
    if not os.path.exists(path):
        logger.error(f"{image_description} not found: {path}")
        return None
    try:
        img = Image.open(path)
        if img.mode != 'RGBA':
            img = img.convert('RGBA') # Ensure alpha channel for proper pasting
        logger.info(f"Successfully loaded {image_description}: {path} (Size: {img.size}, Mode: {img.mode})")
        return img
    except Exception as e:
        logger.exception(f"Error loading {image_description} from {path}:")
        return None

def process_images_and_composite(zodiac_input_path, zodiac_output_size, 
                                 background_path, coffee_body_path, nebbles_body_path):
    """
    Resizes the zodiac image, then composites it with other images onto a background,
    centering the zodiac image on the background with an additional offset.
    Saves the resized zodiac and the final composited image.
    """
    logger.info(f"Processing zodiac image: {zodiac_input_path}")

    resized_zodiac_path = None # Path to the successfully resized zodiac image

    if not os.path.exists(zodiac_input_path):
        logger.error(f"Input zodiac image not found: {zodiac_input_path}")
        return

    try:
        # 1. Resize the Zodiac Image
        zodiac_img_orig = Image.open(zodiac_input_path)
        logger.info(f"Original zodiac image size: {zodiac_img_orig.size} | Mode: {zodiac_img_orig.mode}")

        try:
            resample_filter = Image.Resampling.LANCZOS
        except AttributeError: 
            resample_filter = Image.LANCZOS
            
        resized_zodiac_img = zodiac_img_orig.resize(zodiac_output_size, resample_filter)
        logger.info(f"Resized zodiac image to: {resized_zodiac_img.size}")

        directory = os.path.dirname(zodiac_input_path)
        filename, extension = os.path.splitext(os.path.basename(zodiac_input_path))
        output_filename_resized_zodiac = f"{filename}_resized_{zodiac_output_size[0]}x{zodiac_output_size[1]}{extension}"
        resized_zodiac_path = os.path.join(directory, output_filename_resized_zodiac)

        resized_zodiac_img.save(resized_zodiac_path)
        logger.info(f"Successfully saved resized zodiac image to: {resized_zodiac_path}")

    except Exception as e:
        logger.exception(f"An error occurred while resizing or saving the zodiac image from {zodiac_input_path}:")
        return # Stop if zodiac resizing fails

    # 2. Proceed to Compositing if zodiac image was successfully resized and saved
    if not resized_zodiac_path:
        logger.error("Cannot proceed with compositing as resized zodiac path is not available.")
        return

    logger.info("Starting compositing process...")

    # Load all images for compositing, ensuring they are RGBA
    bg_img = load_image_for_compositing(background_path, "Background")
    coffee_img = load_image_for_compositing(coffee_body_path, "Coffee Body")
    # Load the *newly resized* zodiac image for compositing
    zodiac_comp_img = load_image_for_compositing(resized_zodiac_path, "Resized Zodiac") 
    nebbles_img = load_image_for_compositing(nebbles_body_path, "Nebbles Body")

    if not bg_img:
        logger.error("Background image is essential for compositing and was not loaded. Aborting.")
        return

    # Create the canvas, starting with the background
    # The canvas size will be determined by the background image
    final_canvas = bg_img.copy() # Start with the background
    logger.info(f"Compositing canvas created with size: {final_canvas.size}")

    # Paste Coffee Body onto the background
    # Assuming (0,0) paste for coffee body. Adjust coordinates if needed.
    if coffee_img:
        logger.info("Pasting Coffee Body...")
        final_canvas.paste(coffee_img, (0, 0), coffee_img) 
    else:
        logger.warning("Coffee Body image not loaded. Skipping its paste.")

    # Paste Resized Zodiac, centering it on the final_canvas with an offset
    if zodiac_comp_img:
        logger.info("Calculating position to center Resized Zodiac with offset...")
        canvas_width, canvas_height = final_canvas.size
        zodiac_width, zodiac_height = zodiac_comp_img.size

        # Calculate top-left coordinates for pasting to center the zodiac image
        center_x = (canvas_width - zodiac_width) // 2
        center_y = (canvas_height - zodiac_height) // 2
        
        # Apply the additional offset
        paste_x = center_x + ZODIAC_CENTER_OFFSET_X
        paste_y = center_y + ZODIAC_CENTER_OFFSET_Y 
        
        logger.info(f"Pasting Resized Zodiac at ({paste_x}, {paste_y}) (center-offset).")
        final_canvas.paste(zodiac_comp_img, (paste_x, paste_y), zodiac_comp_img)
    else:
        logger.warning("Resized Zodiac image not loaded. Skipping its paste.")
    
    # Paste Nebbles Body onto the current canvas
    # Assuming (0,0) paste for Nebbles. Adjust coordinates if needed.
    if nebbles_img:
        logger.info("Pasting Nebbles Body...")
        final_canvas.paste(nebbles_img, (0, 0), nebbles_img)
    else:
        logger.warning("Nebbles Body image not loaded. Skipping its paste.")

    # Save the final composited image
    try:
        # Output path for the composited image will be in the same directory as the zodiac image
        composited_output_path = os.path.join(os.path.dirname(zodiac_input_path), COMPOSITED_OUTPUT_FILENAME)
        final_canvas.save(composited_output_path)
        logger.info(f"Successfully saved final composited image to: {composited_output_path}")
    except Exception as e:
        logger.exception("An error occurred while saving the final composited image:")


if __name__ == "__main__":
    logger.info("Starting image processing and compositing script...")
    process_images_and_composite(
        ZODIAC_IMAGE_PATH, 
        TARGET_ZODIAC_SIZE,
        BACKGROUND_IMAGE_PATH,
        COFFEE_BODY_IMAGE_PATH,
        NEBBLES_BODY_IMAGE_PATH
    )
    logger.info("Image processing and compositing script finished.")