# Filename: ai_script_writer.py
import os
import json
import requests
import logging
from pathlib import Path
import argparse
import dotenv

dotenv.load_dotenv()

DEFAULT_OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://l27.0.0.1:11434/api/generate")
DEFAULT_OLLAMA_MODEL = os.getenv("DEFAULT_OLLAMA_MODEL", "mistral-small:latest")

if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s-%(levelname)s [%(filename)s.%(funcName)s:%(lineno)d] - %(message)s',
                        handlers=[logging.StreamHandler()])

def generate_from_ollama(
    prompt_text: str, ollama_model_name: str,
    ollama_api_url: str = DEFAULT_OLLAMA_API_URL, stream: bool = False
) -> str | None:
    payload = {"model": ollama_model_name, "prompt": prompt_text, "stream": stream}
    logging.info(f"Sending prompt to Ollama. Model: {ollama_model_name}, URL: {ollama_api_url}")
    try:
        response = requests.post(ollama_api_url, json=payload, timeout=300) # 5 min timeout
        response.raise_for_status()
        if stream:
            full_response = ""
            for line in response.iter_lines():
                if line:
                    try:
                        json_line = json.loads(line.decode('utf-8'))
                        full_response += json_line.get("response", "")
                        if json_line.get("done"): break
                    except json.JSONDecodeError: logging.warning(f"Ollama stream JSON decode error: {line}")
            generated_text = full_response
        else:
            response_data = response.json(); generated_text = response_data.get("response")
        if generated_text: logging.info(f"Ollama response received (len: {len(generated_text)})."); return generated_text.strip()
        else: logging.error(f"Ollama response empty/no 'response' field. Response: {response.text[:300]}"); return None
    except requests.exceptions.Timeout: logging.error(f"Ollama request timeout at {ollama_api_url}", exc_info=True); return None
    except requests.exceptions.RequestException as e: logging.error(f"Ollama connection error at {ollama_api_url}: {e}", exc_info=True); return None
    except Exception as e: logging.error(f"Ollama generation error: {e}", exc_info=True); return None

def process_prompt_file_to_ollama(
    llm_prompt_filepath_str: str, ollama_model_name: str, target_output_dir_str: str,
    ollama_api_url: str = DEFAULT_OLLAMA_API_URL, output_filename_suffix: str = "_script"
) -> str | None:
    llm_prompt_filepath = Path(llm_prompt_filepath_str) # Assumed absolute
    if not llm_prompt_filepath.is_file():
        logging.error(f"LLM input prompt file not found: {llm_prompt_filepath}"); return None
    try:
        with open(llm_prompt_filepath, 'r', encoding='utf-8') as f: prompt_text = f.read()
        logging.info(f"Read LLM input prompt from: {llm_prompt_filepath}")
    except Exception as e: logging.error(f"Error reading LLM input prompt {llm_prompt_filepath}: {e}"); return None

    generated_script_text = generate_from_ollama(prompt_text, ollama_model_name, ollama_api_url)
    if generated_script_text:
        output_directory = Path(target_output_dir_str) # Assumed absolute
        try: output_directory.mkdir(parents=True, exist_ok=True)
        except Exception as e: logging.error(f"Could not create AI script dir {output_directory}: {e}"); return None
        
        output_filename = f"{llm_prompt_filepath.stem}{output_filename_suffix}{llm_prompt_filepath.suffix}"
        final_output_filepath = output_directory / output_filename
        try:
            with open(final_output_filepath, 'w', encoding='utf-8') as f: f.write(generated_script_text)
            msg = f"AI-Written Script: Saved to: {final_output_filepath}"
            logging.info(msg); print(msg)
            return str(final_output_filepath)
        except Exception as e: logging.error(f"AI-Written Script: Error saving to {final_output_filepath}: {e}")
    else: logging.error(f"AI-Written Script: Failed from Ollama for prompt: {llm_prompt_filepath.name}")
    return None

def main_cli():
    parser = argparse.ArgumentParser(description="Generate AI script via Ollama.")
    parser.add_argument("llm_prompt_file", type=str, help="Path to LLM input prompt .txt file.")
    parser.add_argument("target_output_dir", type=str, help="Exact directory for Ollama-generated script.")
    parser.add_argument("--model", type=str, default=DEFAULT_OLLAMA_MODEL)
    parser.add_argument("--api_url", type=str, default=DEFAULT_OLLAMA_API_URL)
    parser.add_argument("--suffix", type=str, default="_script")
    parser.add_argument("--project_base_path", type=str, default=str(Path().resolve()))
    args = parser.parse_args()
    project_base = Path(args.project_base_path).resolve()
    prompt_file = Path(args.llm_prompt_file);
    if not prompt_file.is_absolute(): prompt_file=(project_base/prompt_file).resolve()
    out_dir = Path(args.target_output_dir);
    if not out_dir.is_absolute(): out_dir=(project_base/out_dir).resolve()
    process_prompt_file_to_ollama(str(prompt_file), args.model, str(out_dir), args.api_url, args.suffix)

if __name__ == "__main__":
    main_cli()