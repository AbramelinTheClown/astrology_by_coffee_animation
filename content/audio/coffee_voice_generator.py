# Filename: coffee_voice_generator.py
import os
import requests
import logging
from pathlib import Path
import argparse
import dotenv

# Resolve .env path relative to this script's assumed project structure
# D:/AI/astrology_by_coffee_v1/content/audio/coffee_voice_generator.py -> parents[2] is D:/AI/astrology_by_coffee_v1
project_root_for_env = Path(__file__).resolve().parents[2] 
dotenv.load_dotenv(dotenv_path=project_root_for_env / ".env")

DEFAULT_ORPHEUS_TTS_API_URL = os.getenv("ORPHEUS_TTS_API_URL", "http://localhost:5005/v1/audio/speech")
VOICE_MAPPINGS = {
    "coffee": os.getenv("COFFEE_VOICE_ID", "tara"),
    "nebbles": os.getenv("NEBBLES_VOICE_ID", "leo") # Though Nebbles might use a different system
}
if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s-%(levelname)s [%(filename)s.%(funcName)s:%(lineno)d] - %(message)s',
                        handlers=[logging.StreamHandler()])

def generate_speech_from_text(
    text_to_speak: str, voice_id: str,
    orpheus_api_url: str = DEFAULT_ORPHEUS_TTS_API_URL,
    output_filepath: Path = None, speed: float = 1.0, response_format: str = "wav"
) -> bool | bytes:
    if not text_to_speak.strip(): logging.error("Input text for TTS is empty."); return False
    payload = {"model":"orpheus","input":text_to_speak,"voice":voice_id,
               "response_format":response_format,"speed":speed}
    logging.info(f"Sending TTS request. Voice: {voice_id}, URL: {orpheus_api_url}")
    try:
        response = requests.post(orpheus_api_url, json=payload, timeout=180)
        response.raise_for_status()
        if response.headers.get('content-type')==f'audio/{response_format}':
            audio_content = response.content
            logging.info(f"Received audio (Size: {len(audio_content)} bytes).")
            if output_filepath:
                try:
                    output_filepath.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_filepath, 'wb') as f: f.write(audio_content)
                    logging.info(f"TTS Audio: Saved to: {output_filepath}"); print(f"TTS Audio: Saved to: {output_filepath}")
                    return True
                except Exception as e: logging.error(f"TTS Audio: Error saving to {output_filepath}: {e}"); return False
            else: return audio_content # Return raw bytes
        else: logging.error(f"Orpheus API bad response type: {response.headers.get('content-type')}"); return False
    except Exception as e: logging.error(f"Error with Orpheus TTS: {e}", exc_info=True); return False

def process_script_file_to_speech(
    ai_written_script_filepath_str: str, character_name: str,
    target_audio_output_dir_str: str, # Exact dated/char/type directory
    orpheus_api_url: str = DEFAULT_ORPHEUS_TTS_API_URL, speed: float = 1.0
) -> str | None: # Returns path to created audio file or None
    ai_script_filepath = Path(ai_written_script_filepath_str) # Assumed absolute
    if not ai_script_filepath.is_file():
        logging.error(f"AI-written script file not found: {ai_script_filepath}"); return None
    try:
        with open(ai_script_filepath, 'r', encoding='utf-8') as f: script_text = f.read()
        logging.info(f"Read AI script text from: {ai_script_filepath}")
    except Exception as e: logging.error(f"Error reading AI script {ai_script_filepath}: {e}"); return None

    voice_id = VOICE_MAPPINGS.get(character_name.lower())
    if not voice_id: logging.error(f"No voice ID for char: '{character_name}'. Mappings: {VOICE_MAPPINGS}"); return None

    output_audio_directory = Path(target_audio_output_dir_str) # Assumed absolute
    try: output_audio_directory.mkdir(parents=True, exist_ok=True)
    except Exception as e: logging.error(f"Could not create audio output dir {output_audio_directory}: {e}"); return None

    audio_filename = f"{ai_script_filepath.stem}.wav" # e.g., coffee_youtubeshort_..._Aries_script.wav
    output_audio_filepath = output_audio_directory / audio_filename

    success = generate_speech_from_text(script_text, voice_id, orpheus_api_url, output_audio_filepath, speed)
    return str(output_audio_filepath) if success else None

def main_cli():
    cli_project_base = Path(os.getenv("PROJECT_BASE_PATH", Path.cwd())).resolve()
    parser = argparse.ArgumentParser(description="Generate speech from AI script.")
    parser.add_argument("ai_script_file", type=str, help="Path to AI-generated .txt script.")
    parser.add_argument("character_name", type=str, choices=list(VOICE_MAPPINGS.keys()))
    parser.add_argument("target_audio_output_dir", type=str, help="Exact directory for output audio.")
    parser.add_argument("--project_base", type=str, default=str(cli_project_base))
    parser.add_argument("--api_url", type=str, default=DEFAULT_ORPHEUS_TTS_API_URL)
    parser.add_argument("--speed", type=float, default=1.0)
    args = parser.parse_args()

    project_base = Path(args.project_base).resolve() # Use resolved arg
    script_file = Path(args.ai_script_file);
    if not script_file.is_absolute(): script_file=(project_base/script_file).resolve()
    audio_out_dir = Path(args.target_audio_output_dir);
    if not audio_out_dir.is_absolute(): audio_out_dir=(project_base/audio_out_dir).resolve()
    
    process_script_file_to_speech(str(script_file), args.character_name, str(audio_out_dir),
                                  args.api_url, args.speed)
if __name__ == "__main__":
    main_cli()