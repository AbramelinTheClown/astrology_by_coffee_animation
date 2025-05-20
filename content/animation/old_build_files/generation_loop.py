import os
from pathlib import Path
import dotenv # pip install python-dotenv

# horoscope_prompt_generator.py should be in the same directory or Python path
from content.dialog.horoscope_prompt_generator import (
    generate_single_prompt_file,
    ZODIAC_SIGNS,
    find_newest_data_folder,
    load_json_from_folder
)

dotenv.load_dotenv()

# These environment variables should now point to the PATH of your prompt template files
# e.g., COFFEE_YOUTUBESHORT_PROMPT_TEMPLATE="./prompt_templates/youtube_default.txt"
YOUTUBE_SHORT_TEMPLATE_PATH = os.getenv("COFFEE_YOUTUBESHORT_PROMPT_TEMPLATE")
TIKTOK_TEMPLATE_PATH = os.getenv("COFFEE_TIKTOK_PROMPT_TEMPLATE")

DEFAULT_PROJECT_BASE_PATH = "D:/AI/astrology_by_coffee_v1"
PROJECT_BASE_PATH = os.getenv("PROJECT_BASE_PATH", DEFAULT_PROJECT_BASE_PATH)
DEFAULT_PROFILE = "Insightful, wise, and slightly mysterious, with a dash of cosmic humor."
PROFILE_CONTENT_OR_PATH = os.getenv("ASTROLOGER_PROFILE", DEFAULT_PROFILE)

def run_astro_data_generation_placeholder():
    print("\nAttempting to run astrological data generation (getAstro)...")
    try:
        from content.astro import get_astro 
        if hasattr(get_astro, 'getAstro') and callable(get_astro.getAstro):
            print("Calling get_astro.getAstro()...")
            get_astro.getAstro()
        elif hasattr(get_astro, 'main') and callable(get_astro.main):
            print("Calling get_astro.main()...")
            get_astro.main()
        else:
            print("Could not find 'getAstro' or 'main' in content.astro.get_astro.")
        print("Astrological data generation process presumed complete.\n")
    except ImportError:
        print("Failed to import 'content.astro.get_astro'. Ensure correct structure and PYTHONPATH.")
        print("Skipping astro data generation. Ensure data is already present.\n")
    except Exception as e:
        print(f"An error occurred during astrological data generation: {e}\n")

def main_loop():
    print("--- Starting Horoscope Prompt Generation Batch (Modular Templates) ---")
    run_astro_data_generation_placeholder()

    project_base_path_obj = Path(PROJECT_BASE_PATH)
    astro_input_base_dir = project_base_path_obj / "content" / "astro" / "astro_output"

    print(f"Looking for newest astrological data in: {astro_input_base_dir}")
    newest_astro_data_folder = find_newest_data_folder(astro_input_base_dir)
    if not newest_astro_data_folder:
        print("Error: Could not find the newest astro data folder. Halting batch.")
        return
    
    astro_data_for_batch = load_json_from_folder(newest_astro_data_folder)
    if not astro_data_for_batch:
        print(f"Error: Could not load astro data from {newest_astro_data_folder}. Halting batch.")
        return
    print(f"Successfully loaded astrological data from {newest_astro_data_folder} for this batch run.")
    print("-" * 20)

    actual_profile_content = PROFILE_CONTENT_OR_PATH
    try:
        profile_path = Path(PROFILE_CONTENT_OR_PATH)
        if profile_path.is_file() and profile_path.suffix.lower() == ".txt":
            with open(profile_path, 'r', encoding='utf-8') as pf:
                actual_profile_content = pf.read()
            print(f"Loaded astrologer profile from: {profile_path}")
    except Exception:
        print(f"Using astrologer profile as string: '{PROFILE_CONTENT_OR_PATH[:50]}...'")
        pass
    print("-" * 20)

    if not YOUTUBE_SHORT_TEMPLATE_PATH and not TIKTOK_TEMPLATE_PATH:
        print("Error: No prompt template paths found in environment variables.")
        print("Please set COFFEE_YOUTUBESHORT_PROMPT_TEMPLATE and/or COFFEE_TIKTOK_PROMPT_TEMPLATE in your .env file.")
        return

    for sign in ZODIAC_SIGNS:
        print(f"\n>>> Processing for Zodiac Sign: {sign} <<<")
        
        if YOUTUBE_SHORT_TEMPLATE_PATH:
            print(f"  Generating YouTube Short prompt using template: '{YOUTUBE_SHORT_TEMPLATE_PATH}'...")
            generate_single_prompt_file(
                loaded_astro_data=astro_data_for_batch,
                target_zodiac_sign=sign,
                config_filename_str=YOUTUBE_SHORT_TEMPLATE_PATH, # This is the path to the template
                project_base_path_str=PROJECT_BASE_PATH,
                profile_content_str=actual_profile_content
            )
        else:
            print("  COFFEE_YOUTUBESHORT_PROMPT_TEMPLATE not set. Skipping YouTube Short prompt.")

        if TIKTOK_TEMPLATE_PATH:
            print(f"  Generating TikTok prompt using template: '{TIKTOK_TEMPLATE_PATH}'...")
            generate_single_prompt_file(
                loaded_astro_data=astro_data_for_batch,
                target_zodiac_sign=sign,
                config_filename_str=TIKTOK_TEMPLATE_PATH, # This is the path to the template
                project_base_path_str=PROJECT_BASE_PATH,
                profile_content_str=actual_profile_content
            )
        else:
            print("  COFFEE_TIKTOK_PROMPT_TEMPLATE not set. Skipping TikTok prompt.")
        
    print("\n--- Horoscope Prompt Generation Batch Finished ---")

if __name__ == "__main__":
    main_loop()