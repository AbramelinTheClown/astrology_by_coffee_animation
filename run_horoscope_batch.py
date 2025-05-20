import os
import sys
from pathlib import Path
import dotenv
from datetime import datetime, timezone
import subprocess # Keep for get_astro
import logging
import importlib.util # For more detailed import diagnostics
import re # For sanitizing description

# Load environment variables from .env file
dotenv.load_dotenv()

# --- Determine Project Base Path ---
env_project_base_path = os.getenv("PROJECT_BASE_PATH")
if env_project_base_path:
    PROJECT_BASE_PATH = Path(env_project_base_path).resolve()
else:
    PROJECT_BASE_PATH = Path(__file__).resolve().parent 

# --- Configure Logging ---
if not logging.getLogger().hasHandlers():
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s-%(levelname)s [%(filename)s:%(lineno)d] - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
            # logging.FileHandler(PROJECT_BASE_PATH / "horoscope_batch.log")
        ]
    )
logging.info(f"Using PROJECT_BASE_PATH: {PROJECT_BASE_PATH}")
print(f"Using PROJECT_BASE_PATH: {PROJECT_BASE_PATH}")

# --- Configure Temporary Directory ---
try:
    temp_dir = PROJECT_BASE_PATH / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True) 
    os.environ['TMPDIR'] = str(temp_dir)
    os.environ['TEMP'] = str(temp_dir)
    os.environ['TMP'] = str(temp_dir)
    logging.info(f"Set TMPDIR/TEMP/TMP environment variables to: {temp_dir}")
    print(f"Attempting to use temporary directory: {temp_dir}")
except Exception as e_temp:
    logging.warning(f"Could not set custom temporary directory: {e_temp}")
    print(f"Warning: Could not set custom temporary directory: {e_temp}")


# --- Adjust sys.path for local module imports ---
if str(PROJECT_BASE_PATH) not in sys.path:
    sys.path.insert(0, str(PROJECT_BASE_PATH))

api_dir = PROJECT_BASE_PATH / "api"
if api_dir.exists() and str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))
    (api_dir / "__init__.py").touch(exist_ok=True)
    logging.info(f"Ensured 'api' directory is in sys.path and has __init__.py: {api_dir}")


# --- Imports from our custom modules ---
try:
    from content.dialog.horoscope_prompt_generator import (
        generate_llm_input_prompt_file, ZODIAC_SIGNS,
        find_newest_data_folder, load_json_from_folder
    )
    from content.dialog.ai_script_writer import process_prompt_file_to_ollama
    from content.audio.coffee_voice_generator import process_script_file_to_speech
    from content.animation.render_orchestrator import render_video_for_task 
except ImportError as e:
    logging.error(f"Failed to import one or more custom modules from 'content': {e}", exc_info=True)
    logging.error("Please ensure all __init__.py files are present in 'content' and its subdirectories, "
                  "and that the modules exist at the correct paths.")
    sys.exit("Critical import error. Exiting.")


# --- YouTube Upload Function Import ---
logging.info(f"Current sys.path before attempting to import 'upload_to_social': {sys.path}") 
expected_uploader_path = api_dir / "upload_to_social.py" 
logging.info(f"Expecting 'upload_to_social.py' at: {expected_uploader_path}") 
logging.info(f"Does '{expected_uploader_path}' exist? {expected_uploader_path.exists()}") 

uploader_module_name = "upload_to_social" 
uploader_spec = None
logging.info(f"Attempting importlib.util.find_spec for module name: '{uploader_module_name}'") 
try:
    uploader_spec = importlib.util.find_spec(uploader_module_name)
    if uploader_spec is None:
        logging.error(f"Importlib: Could not find the module spec for '{uploader_module_name}'. "
                      f"Python cannot locate the file or it's not recognizable as a module. "
                      f"Checked paths: {sys.path}")
    else:
        logging.info(f"Importlib: Found module spec for '{uploader_module_name}'. Location: {uploader_spec.origin}")
except Exception as e_spec:
    logging.error(f"Importlib: Error trying to find spec for '{uploader_module_name}': {e_spec}", exc_info=True)

YOUTUBE_UPLOAD_ENABLED_FROM_IMPORT = False 
actual_youtube_upload_function = None 

try:
    logging.info(f"Attempting: from {uploader_module_name} import upload_to_youtube")
    from upload_to_social import upload_to_youtube as actual_youtube_upload_function
    YOUTUBE_UPLOAD_ENABLED_FROM_IMPORT = True 
    logging.info("Successfully imported YouTube upload function from upload_to_social.py.")
except ImportError as e:
    logging.info("DEBUG: Entered ImportError exception block for 'upload_to_social'.") 
    logging.error(f"Could not import 'upload_to_youtube' from '{uploader_module_name}' (expected in 'api' directory). "
                  f"YouTube uploads will be disabled. Error: {e}", exc_info=True) 
    def actual_youtube_upload_function_placeholder(*args, **kwargs): 
        logging.critical("actual_youtube_upload_function IS NOT AVAILABLE due to import error! Upload will be skipped.")
        print("CRITICAL ERROR: YouTube upload function could not be imported. Upload will be skipped.")
        return None
    actual_youtube_upload_function = actual_youtube_upload_function_placeholder

except Exception as e_other: 
    logging.info("DEBUG: Entered other Exception block for 'upload_to_social' import.") 
    logging.error(f"An unexpected error occurred during import of '{uploader_module_name}': {e_other}", exc_info=True)
    def actual_youtube_upload_function_placeholder_other(*args, **kwargs): 
        logging.critical("actual_youtube_upload_function IS NOT AVAILABLE due to an unexpected import error! Upload will be skipped.")
        print("CRITICAL ERROR: YouTube upload function could not be imported due to an unexpected error. Upload will be skipped.")
        return None
    actual_youtube_upload_function = actual_youtube_upload_function_placeholder_other


# --- Helper to resolve paths from .env relative to PROJECT_BASE_PATH ---
def get_resolved_path_from_env(env_var_name: str, default_relative_path: str | None = None) -> str | None:
    path_str = os.getenv(env_var_name)
    if not path_str and default_relative_path:
        path_str = default_relative_path
    
    if path_str:
        path_obj = Path(path_str)
        return str(path_obj.resolve() if path_obj.is_absolute() else (PROJECT_BASE_PATH / path_obj).resolve())
    return None

# --- Load Configuration Paths ---
COFFEE_YTSHORT_INPUT_PROMPT_TEMPLATE = get_resolved_path_from_env("COFFEE_YOUTUBESHORT_PROMPT_TEMPLATE")
GET_ASTRO_SCRIPT_ABS_PATH_STR = get_resolved_path_from_env("GET_ASTRO_SCRIPT_PATH", "get_astro.py")

# --- Load Model Configuration ---
DEFAULT_OLLAMA_MODEL = os.getenv("DEFAULT_OLLAMA_MODEL", "mistral:latest")
COFFEE_OLLAMA_MODEL = os.getenv("COFFEE_OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)

# --- Load Profile Configuration ---
DEFAULT_PROFILE_TEXT = "Insightful, wise, and slightly mysterious, with a dash of cosmic humor."
ASTROLOGER_PROFILE_CONFIG_STR = os.getenv("ASTROLOGER_PROFILE", DEFAULT_PROFILE_TEXT)
COFFEE_PROFILE_CONFIG_STR = os.getenv("COFFEE_PROFILE", ASTROLOGER_PROFILE_CONFIG_STR)

# --- YouTube Upload Specific Configuration (Informational) ---
YOUTUBE_DEFAULT_PRIVACY_STATUS_FROM_ENV = os.getenv("YOUTUBE_DEFAULT_PRIVACY_STATUS", "public") 
YOUTUBE_CLIENT_SECRETS_PATH_FROM_ENV = get_resolved_path_from_env("YOUTUBE_CLIENT_SECRETS_JSON_PATH", "api/client_secrets.json")

# --- Configuration for Deleting Video After Upload ---
DELETE_VIDEO_AFTER_UPLOAD = os.getenv("DELETE_VIDEO_AFTER_UPLOAD", "True").lower() == "true"
if DELETE_VIDEO_AFTER_UPLOAD:
    logging.info("Local videos will be deleted after successful upload attempt.")
else:
    logging.info("Local videos will NOT be deleted after upload.")


def run_get_astro_script_func():
    print("\nAttempting to run astrological data generation (get_astro.py)...")
    if not GET_ASTRO_SCRIPT_ABS_PATH_STR:
        logging.error("GET_ASTRO_SCRIPT_PATH not defined in .env or as default. Cannot run get_astro.py.")
        return False
    
    get_astro_script_path = Path(GET_ASTRO_SCRIPT_ABS_PATH_STR)
    if not get_astro_script_path.is_file():
        logging.error(f"get_astro.py not found at the specified path: {get_astro_script_path}.")
        return False
    
    try:
        python_exe = sys.executable
        logging.info(f"Executing: {python_exe} {get_astro_script_path}")
        print(f"Executing: {python_exe} {get_astro_script_path}")
        process = subprocess.run(
            [python_exe, str(get_astro_script_path)],
            capture_output=True, text=True, check=False, cwd=str(PROJECT_BASE_PATH)
        )
        if process.returncode == 0:
            logging.info("get_astro.py executed successfully.")
            if process.stdout: logging.info(f"get_astro.py STDOUT: {process.stdout.strip()}")
            if process.stderr: logging.warning(f"get_astro.py STDERR: {process.stderr.strip()}")
            print("get_astro.py executed successfully.")
            return True
        else:
            logging.error(f"get_astro.py failed with return code {process.returncode}.")
            if process.stdout: logging.error(f"get_astro.py STDOUT: {process.stdout.strip()}")
            if process.stderr: logging.error(f"get_astro.py STDERR: {process.stderr.strip()}")
            print(f"Error: get_astro.py failed (RC:{process.returncode}). Check logs.")
            return False
    except Exception as e:
        logging.error(f"An unexpected error occurred while running get_astro.py: {e}", exc_info=True)
        print(f"Unexpected error running get_astro.py: {e}")
        return False

def load_profile(config_str: str) -> str:
    is_path_like = (os.path.sep in config_str or config_str.endswith(".txt")) and len(config_str) < 260
    if is_path_like:
        path = Path(config_str)
        if not path.is_absolute(): path = (PROJECT_BASE_PATH / path).resolve()
        if path.is_file() and path.suffix.lower() == ".txt":
            try:
                with open(path, 'r', encoding='utf-8') as f: content = f.read().strip()
                logging.info(f"Successfully loaded profile from text file: {path}")
                print(f"Loaded profile from: {path}")
                return content
            except Exception as e:
                logging.warning(f"Could not load profile from file {path} (Error: {e}). Using string as profile.")
        else:
            logging.info(f"Profile path '{config_str}' not a valid .txt file or not found. Using string as profile.")
    logging.info(f"Using profile as direct string: '{config_str[:70]}...'")
    return config_str

def main_loop():
    current_time = datetime.now(timezone.utc)
    batch_date_str = current_time.strftime("%Y-%m-%d") 
    logging.info(f"--- Starting Full Horoscope Generation Pipeline (Batch Date: {batch_date_str}) ---")
    print(f"--- Starting Full Horoscope Generation Pipeline (Batch Date: {batch_date_str}) ---")

    if not run_get_astro_script_func():
        logging.warning("Astro data generation failed/skipped. Attempting to use existing data.")

    astro_input_base_dir = PROJECT_BASE_PATH / "content" / "astro" / "astro_output"
    newest_astro_data_folder = find_newest_data_folder(astro_input_base_dir)
    if not newest_astro_data_folder:
        logging.critical(f"CRITICAL: No astro data folder found under {astro_input_base_dir}. Halting batch.")
        print(f"Error: No astro data folder found. Halting.")
        return
    
    astro_data_for_batch = load_json_from_folder(newest_astro_data_folder)
    if not astro_data_for_batch:
        logging.critical(f"CRITICAL: Could not load astro data from {newest_astro_data_folder}. Halting batch.")
        print(f"Error: Could not load astro data. Halting.")
        return
    
    calc_datetime_utc = astro_data_for_batch.get('calculation_metadata', {}).get('calculation_datetime_utc', 'N/A')
    logging.info(f"Using astro data from {newest_astro_data_folder} (data timestamp: {calc_datetime_utc}).")
    print(f"Using astro data from {newest_astro_data_folder}")

    coffee_profile_text = load_profile(COFFEE_PROFILE_CONFIG_STR)
    print("-" * 20)

    llm_prompts_dated_root = PROJECT_BASE_PATH / "content" / "dialog" / "dialog_output" / batch_date_str
    ai_scripts_dated_root = PROJECT_BASE_PATH / "content" / "dialog" / "generated_scripts" / batch_date_str
    audio_voices_dated_root = PROJECT_BASE_PATH / "content" / "audio" / "voice" / "voice_output" / batch_date_str
    final_videos_base_dir = PROJECT_BASE_PATH / "content" / "animation" / "video" / "final_video" 
    final_videos_dated_root = final_videos_base_dir / batch_date_str

    character_pipelines = {
        "Coffee": {
            "profile_text": coffee_profile_text, 
            "ollama_model": COFFEE_OLLAMA_MODEL,
            "templates": {
                "youtubeshort": COFFEE_YTSHORT_INPUT_PROMPT_TEMPLATE,
            },
            "use_orpheus_tts": True, 
            "do_render": True,
            "upload_to_youtube": True 
        }
    }

    for char_name, char_config in character_pipelines.items():
        if char_name != "Coffee": 
            logging.info(f"Skipping character: {char_name} as per current focus.")
            continue

        logging.info(f"Starting pipeline for character: {char_name}")
        print(f"\n=== Pipeline for: {char_name} ===")
        char_profile_to_use = char_config["profile_text"]
        char_ollama_model_to_use = char_config["ollama_model"]

        for video_type, template_abs_path_str in char_config["templates"].items():
            if video_type != "youtubeshort": 
                logging.info(f"Skipping video type '{video_type}' for {char_name} as per current focus.")
                continue

            if not template_abs_path_str:
                logging.info(f"No template for {char_name}-{video_type}. Skipping.")
                print(f"   No template for {char_name}-{video_type}. Skipping.")
                continue
            
            template_path_obj = Path(template_abs_path_str)
            if not template_path_obj.is_file():
                logging.warning(f"Template MISSING: {template_path_obj}. Skipping {char_name}-{video_type}.")
                print(f"   Warning: Template MISSING: {template_path_obj}. Skipping.")
                continue
            
            logging.info(f"Processing format: {video_type} for {char_name}")
            print(f"\n   -- Format: {video_type} --")
            
            char_video_type_lc = f"{char_name.lower()}/{video_type.lower()}" 
            current_llm_input_prompt_dir = llm_prompts_dated_root / char_video_type_lc
            current_ai_script_dir = ai_scripts_dated_root / char_video_type_lc
            current_audio_dir = audio_voices_dated_root / char_video_type_lc
            current_final_video_output_dir = final_videos_dated_root / char_name.lower() / video_type.lower()


            for sign in ZODIAC_SIGNS:
                logging.info(f"Processing Sign: {sign} for {char_name} - {video_type}")
                print(f"\n     Processing {sign} for {char_name} - {video_type}...")
                
                llm_input_prompt_filepath_str = None
                ai_written_script_filepath_str = None
                audio_filepath_for_render = None
                rendered_video_filepath = None
                ai_script_stem = None 

                # --- Stage 1: Generate LLM Input Prompt ---
                try:
                    print(f"       1. Generating LLM input prompt (template: '{template_path_obj.name}')...")
                    llm_input_prompt_filepath_str = generate_llm_input_prompt_file(
                        loaded_astro_data=astro_data_for_batch, target_zodiac_sign=sign,
                        prompt_template_abs_path_str=str(template_path_obj),
                        target_output_dir_str=str(current_llm_input_prompt_dir),
                        profile_content_str=char_profile_to_use
                    )
                    if not llm_input_prompt_filepath_str:
                        logging.error(f"FAIL Stage 1 (LLM Prompt): {char_name}-{video_type}-{sign}. Skipping.")
                        print(f"       Error: Failed Stage 1 for {sign}. Skipping.")
                        continue
                except Exception as e:
                    logging.error(f"Exception in Stage 1 (LLM Prompt) for {char_name}-{video_type}-{sign}: {e}", exc_info=True)
                    print(f"       Error: Exception in Stage 1 for {sign}. Skipping.")
                    continue
                
                # --- Stage 2: Generate AI Script (Ollama) ---
                try:
                    print(f"       2. Generating AI script (model: {char_ollama_model_to_use})...")
                    ai_written_script_filepath_str = process_prompt_file_to_ollama(
                        llm_prompt_filepath_str=llm_input_prompt_filepath_str,
                        ollama_model_name=char_ollama_model_to_use,
                        target_output_dir_str=str(current_ai_script_dir)
                    )
                    if not ai_written_script_filepath_str:
                        logging.error(f"FAIL Stage 2 (AI Script): {char_name}-{video_type}-{sign}. Skipping.")
                        print(f"       Error: Failed Stage 2 for {sign}. Skipping.")
                        continue
                    ai_script_stem = Path(ai_written_script_filepath_str).stem 
                except Exception as e:
                    logging.error(f"Exception in Stage 2 (AI Script) for {char_name}-{video_type}-{sign}: {e}", exc_info=True)
                    print(f"       Error: Exception in Stage 2 for {sign}. Skipping.")
                    continue
                
                # --- Stage 3: Generate TTS Audio ---
                if char_config["use_orpheus_tts"]:
                    try:
                        print(f"       3. Generating TTS audio for {char_name}...")
                        audio_filepath_for_render = process_script_file_to_speech(
                            ai_written_script_filepath_str=ai_written_script_filepath_str,
                            character_name=char_name,
                            target_audio_output_dir_str=str(current_audio_dir)
                        )
                        if not audio_filepath_for_render:
                            logging.error(f"FAIL Stage 3 (TTS): {char_name}-{video_type}-{sign}. No audio file path returned.")
                            print(f"       Error: Failed Stage 3 (TTS) for {sign}.")
                            if char_name.lower() == "coffee": 
                                logging.warning("Skipping rendering for Coffee due to TTS failure.")
                                print("       Skipping rendering for Coffee due to TTS failure.")
                                continue 
                        else:
                            logging.info(f"SUCCESS Stage 3 (TTS): Audio at {audio_filepath_for_render}")
                    except Exception as e:
                        logging.error(f"Exception in Stage 3 (TTS) for {char_name}-{video_type}-{sign}: {e}", exc_info=True)
                        print(f"       Error: Exception in Stage 3 (TTS) for {sign}. Skipping.")
                        if char_name.lower() == "coffee": continue 
                else: 
                    logging.info(f"TTS for {char_name} handled separately or not required. Skipping Orpheus TTS.")
                    print(f"       3. TTS for {char_name} handled separately or not required.")

                # --- Stage 4: Video Rendering ---
                if char_config.get("do_render", False):
                    if char_config["use_orpheus_tts"] and not audio_filepath_for_render:
                        logging.warning(f"Skipping rendering for {char_name}-{video_type}-{sign} due to missing audio from Stage 3.")
                        print(f"       4. Skipping rendering for {sign} due to missing audio.")
                    elif not ai_script_stem or not ai_written_script_filepath_str or not Path(ai_written_script_filepath_str).exists(): 
                        logging.warning(f"Skipping rendering for {char_name}-{video_type}-{sign} due to missing AI script or stem. Script path: {ai_written_script_filepath_str}, Stem: {ai_script_stem}")
                        print(f"       4. Skipping rendering for {sign} due to missing AI script or stem.")
                    else:
                        try:
                            print(f"       4. Orchestrating Video Rendering for {sign}...")
                            render_output = render_video_for_task(
                                batch_date_str=batch_date_str,
                                character_name=char_name,
                                video_type=video_type,
                                zodiac_sign=sign,
                                source_script_stem=ai_script_stem 
                            )
                            
                            if isinstance(render_output, (str, Path)) and Path(render_output).is_file():
                                rendered_video_filepath = str(render_output)
                                logging.info(f"SUCCESS Stage 4 (Video Rendering): Video explicitly returned at {rendered_video_filepath}")
                                print(f"       Video rendered successfully: {rendered_video_filepath}")
                            elif render_output is True: 
                                expected_video_filename = f"{ai_script_stem}_final_{batch_date_str}.mp4" 
                                potential_video_path = current_final_video_output_dir / expected_video_filename
                                logging.info(f"Render task returned True. Checking for video at: {potential_video_path}")
                                if potential_video_path.is_file():
                                    rendered_video_filepath = str(potential_video_path)
                                    logging.info(f"SUCCESS Stage 4 (Video Rendering): Video found at presumed path {rendered_video_filepath}")
                                    print(f"       Video rendered successfully (found at presumed path): {rendered_video_filepath}")
                                else:
                                    logging.error(f"FAIL Stage 4: Render task returned True, but video NOT FOUND at presumed path {potential_video_path} for {char_name}-{video_type}-{sign}.")
                                    print(f"       Error: Video rendering reported success, but file not found for {sign} at {potential_video_path}.")
                            else: 
                                logging.error(f"FAIL Stage 4 (Video Rendering): {char_name}-{video_type}-{sign}. Render task did not indicate success or return a valid path. Output: {render_output}")
                                print(f"       Error: Failed Stage 4 (Video Rendering) for {sign}. Output: {render_output}")
                        except Exception as e:
                            logging.error(f"Exception in Stage 4 (Video Rendering) for {char_name}-{video_type}-{sign}: {e}", exc_info=True)
                            print(f"       Error: Exception in Stage 4 for {sign}. Skipping subsequent stages for this item.")
                else: 
                    logging.info(f"Rendering for {char_name} disabled or handled separately.")
                    print(f"       4. Rendering for {char_name} disabled or handled separately.")

                # --- Stage 5: YouTube Upload & Cleanup ---
                should_attempt_upload = YOUTUBE_UPLOAD_ENABLED_FROM_IMPORT and char_config.get("upload_to_youtube", False)

                if should_attempt_upload:
                    if rendered_video_filepath and Path(rendered_video_filepath).is_file():
                        print(f"       5. Uploading video for {sign} to YouTube...")
                        logging.info(f"Attempting YouTube upload for: {rendered_video_filepath}")
                        
                        # --- Title (Emoji removed) ---
                        video_title = f"Only {sign}'s Grasp This! Daily Horoscope Short #Shorts"
                        if len(video_title) > 100: 
                            video_title = video_title[:97] + "..."
                        
                        # --- Description Sanitization and Logging ---
                        script_content_for_desc = "Daily horoscope reading." # Default
                        try:
                            if ai_written_script_filepath_str and Path(ai_written_script_filepath_str).exists():
                                with open(ai_written_script_filepath_str, 'r', encoding='utf-8') as f_script:
                                    script_text = f_script.read()
                                    first_paragraph = script_text.split('\n\n')[0]
                                    
                                    # Enhanced Sanitization: Keep alphanumeric, common punctuation, space, newline.
                                    # Replace multiple spaces with a single space.
                                    sanitized_paragraph = re.sub(r'[^\w\s.,!?"\'\-#:;()\n]', '', first_paragraph) 
                                    sanitized_paragraph = re.sub(r'\s+', ' ', sanitized_paragraph).strip()

                                    max_script_desc_len = 4500 
                                    if len(sanitized_paragraph) > max_script_desc_len:
                                        script_content_for_desc = sanitized_paragraph[:max_script_desc_len] + "..."
                                    else:
                                        script_content_for_desc = sanitized_paragraph
                            else:
                                logging.warning(f"AI script file not found or path is None ({ai_written_script_filepath_str}), using default description.")
                        except Exception as e_read_script:
                            logging.warning(f"Could not read or process AI script ({ai_written_script_filepath_str}) for description: {e_read_script}")
                        
                        video_description_parts = [
                            f"{char_name}'s daily horoscope for {sign} on {batch_date_str}.\n\n",
                            f"{script_content_for_desc}\n\n",
                            "Discover your fortune for the day!\n\n",
                            f"#Horoscope #{sign} #{char_name} #{video_type} #Astrology #{batch_date_str.replace('-', '')}"
                        ]
                        if video_type.lower() == "youtubeshort": 
                            video_description_parts.append(" #Shorts")
                        
                        video_description = "".join(video_description_parts)

                        max_total_desc_len = 4990 
                        if len(video_description) > max_total_desc_len:
                            video_description = video_description[:max_total_desc_len] + "..."
                        
                        logging.info(f"Attempting to upload with DESCRIPTION (length {len(video_description)}):\n----BEGIN DESCRIPTION----\n{video_description}\n----END DESCRIPTION----")
                        # --- End Description Handling ---

                        video_tags = [
                            char_name.lower(), "horoscope", sign.lower(), video_type.lower(),
                            "astrology", "dailyhoroscope", batch_date_str
                        ]
                        if video_type.lower() == "youtubeshort":
                            video_tags.extend(["shorts", "ytshorts"]) 
                        
                        upload_call_succeeded = False 
                        try:
                            print(f"       Calling actual_youtube_upload_function with: \n"
                                  f"         File: {rendered_video_filepath}\n"
                                  f"         Title: {video_title}\n"
                                  f"         Desc (length): {len(video_description)}\n" 
                                  f"         Tags: {video_tags}")

                            if not callable(actual_youtube_upload_function):
                                logging.error("actual_youtube_upload_function is not callable! This should not happen if import succeeded or placeholder was defined.")
                                raise TypeError("Upload function is not callable")

                            youtube_video_id_or_none = actual_youtube_upload_function(
                                file_path=str(rendered_video_filepath), 
                                title=video_title,
                                description=video_description, 
                                tags=video_tags
                            )
                            upload_call_succeeded = True 

                            if youtube_video_id_or_none: 
                                logging.info(f"SUCCESS Stage 5 (YouTube Upload): {char_name}-{video_type}-{sign}. Video ID: {youtube_video_id_or_none}")
                                print(f"       Successfully uploaded to YouTube. Video ID: {youtube_video_id_or_none}")
                            else: 
                                logging.info(f"Stage 5 (YouTube Upload): Call to actual_youtube_upload_function completed for {char_name}-{video_type}-{sign}. "
                                             f"Check console for upload status and ID from upload_to_social.py.")
                                print(f"       YouTube upload call completed for {sign}. Check console for status from upload script.")

                        except Exception as e_upload:
                            upload_call_succeeded = False 
                            logging.error(f"FAIL Stage 5 (YouTube Upload): An error occurred during the upload call for {char_name}-{video_type}-{sign}. Error: {e_upload}", exc_info=True)
                            print(f"       Error: Failed Stage 5 (YouTube Upload) for {sign} due to an exception: {e_upload}")
                        
                        if upload_call_succeeded and DELETE_VIDEO_AFTER_UPLOAD:
                            try:
                                os.remove(rendered_video_filepath)
                                logging.info(f"Successfully deleted local video file: {rendered_video_filepath}")
                                print(f"       Successfully deleted local video: {Path(rendered_video_filepath).name}")
                            except OSError as e_delete:
                                logging.error(f"Error deleting local video file {rendered_video_filepath}: {e_delete}", exc_info=True)
                                print(f"       Error deleting local video {Path(rendered_video_filepath).name}: {e_delete}")
                        elif DELETE_VIDEO_AFTER_UPLOAD and not upload_call_succeeded:
                            logging.warning(f"Skipping deletion of {rendered_video_filepath} because the upload call itself failed.")
                            print(f"       Skipping deletion of local video due to upload call failure.")
                    
                    elif not rendered_video_filepath:
                        logging.warning(f"YouTube upload and cleanup skipped for {char_name}-{video_type}-{sign}: Video was not successfully rendered or path not available from Stage 4.")
                        print(f"       5. YouTube upload & cleanup skipped: Video not rendered/path missing from Stage 4.")
                    elif not Path(rendered_video_filepath).is_file(): 
                        logging.warning(f"YouTube upload and cleanup skipped for {char_name}-{video_type}-{sign}: Rendered video file not found at {rendered_video_filepath}.")
                        print(f"       5. YouTube upload & cleanup skipped: Rendered video file not found.")
                
                elif char_config.get("upload_to_youtube", False): 
                    if not YOUTUBE_UPLOAD_ENABLED_FROM_IMPORT:
                         logging.warning(f"YouTube upload and cleanup skipped for {char_name}-{video_type}-{sign}: YouTube upload module was not imported successfully.")
                         print(f"       5. YouTube upload & cleanup skipped: Upload module not available (import failed).")

            logging.info(f"Completed processing all signs for {char_name} - {video_type}")
        logging.info(f"Finished all video types for character: {char_name}")

    logging.info("--- Full Horoscope Generation Pipeline Finished ---")
    print("\n--- Full Horoscope Generation Pipeline Finished ---")

if __name__ == "__main__":
    main_loop()
