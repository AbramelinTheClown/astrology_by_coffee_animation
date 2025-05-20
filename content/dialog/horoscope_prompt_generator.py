# Filename: horoscope_prompt_generator.py
import json
import logging
import os
import argparse
from datetime import datetime, timezone
from pathlib import Path

LLM_MODEL_NAME = "mistral-small:latest"
RULING_PLANETS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Pluto",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Uranus", "Pisces": "Neptune"
}
ZODIAC_SIGNS = list(RULING_PLANETS.keys())

if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s-%(levelname)s [%(filename)s.%(funcName)s:%(lineno)d] - %(message)s',
                        handlers=[logging.StreamHandler()])

def find_newest_data_folder(base_astro_output_path: Path) -> Path | None:
    if not base_astro_output_path.is_dir():
        logging.error(f"Astro output base path not found: {base_astro_output_path}")
        return None
    try:
        subfolders = [f for f in base_astro_output_path.iterdir() if f.is_dir()]
        if not subfolders: logging.warning(f"No subfolders in {base_astro_output_path}"); return None
        subfolders.sort(key=lambda x: x.name, reverse=True)
        logging.info(f"Found newest astro data folder: {subfolders[0]}")
        return subfolders[0]
    except Exception as e: logging.error(f"Error finding newest astro data folder: {e}", exc_info=True); return None

def load_json_from_folder(folder_path: Path) -> dict | None:
    try:
        json_files = list(folder_path.glob("*.json"))
        if not json_files: logging.warning(f"No JSON files in {folder_path}"); return None
        with open(json_files[0], 'r', encoding='utf-8') as f: data = json.load(f)
        logging.info(f"Loaded JSON from {json_files[0]}")
        return data
    except Exception as e: logging.error(f"Error loading JSON from {folder_path}: {e}", exc_info=True); return None

def create_horoscope_prompt_from_template(
    prompt_template_str: str, astro_data: dict, target_zodiac_sign: str, profile_content: str = ""
) -> str:
    try:
        if target_zodiac_sign not in RULING_PLANETS:
            return f"Error: Invalid zodiac sign '{target_zodiac_sign}'"
        focus_planet = RULING_PLANETS[target_zodiac_sign]
        calc_meta = astro_data.get('calculation_metadata', {})
        time_utc_str = calc_meta.get('calculation_datetime_utc', datetime.now(timezone.utc).isoformat())
        try:
            if time_utc_str.endswith('Z'): dt_obj_utc = datetime.fromisoformat(time_utc_str[:-1] + '+00:00')
            else:
                dt_obj_utc = datetime.fromisoformat(time_utc_str)
                if dt_obj_utc.tzinfo is None: dt_obj_utc = dt_obj_utc.replace(tzinfo=timezone.utc)
            date_str = dt_obj_utc.strftime('%B %d, %Y')
        except ValueError:
            date_str = datetime.now(timezone.utc).strftime('%B %d, %Y')
            logging.warning(f"Bad time_utc: {time_utc_str}, using current date {date_str}.")
        pos_summary = [f"{n} in {d.get('sign','?')} {'(R)' if d.get('retrograde') else ''}."
                       for n,d in astro_data.get('celestial_bodies',{}).items() if isinstance(d,dict)]
        aspect_map = {"conjunction":"conjunct","opposition":"opposition","trine":"trine",
                      "square":"square","sextile":"sextile","semisextile":"semisextile","quincunx":"quincunx"}
        asp_summary = [f"{a.get('body1')} {aspect_map.get(a.get('aspect_type','').lower(),a.get('aspect_type'))} {a.get('body2')} ({a.get('angle_degrees',0):.0f}°)."
                       for a in astro_data.get('aspect_analysis',{}).get('aspects',[])[:5]] # Top 5 aspects
        data_narrative = (f"Today, {date_str}, for {target_zodiac_sign} (ruler: {focus_planet}):\n"
                          f"Placements: {' '.join(pos_summary) or 'General energies.'}\n"
                          f"Aspects: {' '.join(asp_summary) or 'Quiet dance.'}")
        effective_profile = profile_content.strip() or "Default Profile."
        format_values = {"LLM_MODEL_NAME":LLM_MODEL_NAME,"target_zodiac_sign":target_zodiac_sign,
                         "date_str":date_str,"data_narrative":data_narrative,
                         "focus_planet":focus_planet,"effective_profile":effective_profile}
        return prompt_template_str.format(**format_values).strip()
    except KeyError as e: return f"Error: Prompt template missing placeholder: {e}"
    except Exception as e: return f"Error creating prompt: {e}"

def generate_llm_input_prompt_file(
    loaded_astro_data: dict, target_zodiac_sign: str, prompt_template_abs_path_str: str,
    target_output_dir_str: str, profile_content_str: str
) -> str | None:
    prompt_template_filepath = Path(prompt_template_abs_path_str)
    if not prompt_template_filepath.is_file():
        logging.error(f"Template file not found: {prompt_template_filepath}"); return None
    try:
        with open(prompt_template_filepath, 'r', encoding='utf-8') as f: template_content = f.read()
    except Exception as e: logging.error(f"Error reading template {prompt_template_filepath}: {e}"); return None

    output_directory = Path(target_output_dir_str)
    try: output_directory.mkdir(parents=True, exist_ok=True)
    except Exception as e: logging.error(f"Could not create dir {output_directory}: {e}"); return None

    template_stem = prompt_template_filepath.stem
    if template_stem.lower().endswith("_prompt"): template_stem = template_stem[:-len("_prompt")]
    
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S%fZ")
    output_filename = f"{template_stem}_{timestamp}_{target_zodiac_sign}.txt"
    output_filepath = output_directory / output_filename
    
    horoscope_prompt = create_horoscope_prompt_from_template(
        template_content, loaded_astro_data, target_zodiac_sign, profile_content_str
    )
    if not horoscope_prompt.startswith("Error:"):
        try:
            with open(output_filepath, 'w', encoding='utf-8') as f: f.write(horoscope_prompt)
            msg = f"LLM Input Prompt: Saved for {target_zodiac_sign} to: {output_filepath}"
            logging.info(msg); print(msg)
            return str(output_filepath)
        except Exception as e: logging.error(f"LLM Input Prompt: Error saving to {output_filepath}: {e}")
    else: logging.error(f"LLM Input Prompt: Failed for {target_zodiac_sign}: {horoscope_prompt}")
    return None

def main_cli():
    parser = argparse.ArgumentParser(description="Generate Horoscope LLM Input Prompt")
    parser.add_argument("target_zodiac_sign", choices=ZODIAC_SIGNS)
    parser.add_argument("prompt_template_file", type=str, help="Path to prompt template.")
    parser.add_argument("target_output_dir", type=str, help="Exact directory to save output.")
    parser.add_argument("--project_base_path", type=str, default=str(Path().resolve()))
    parser.add_argument("--profile_content", type=str, default="Insightful profile.")
    args = parser.parse_args()
    project_base = Path(args.project_base_path).resolve()
    template_file = Path(args.prompt_template_file);
    if not template_file.is_absolute(): template_file=(project_base/template_file).resolve()
    target_out_dir = Path(args.target_output_dir);
    if not target_out_dir.is_absolute(): target_out_dir=(project_base/target_out_dir).resolve()

    astro_base = project_base / "content" / "astro" / "astro_output"
    newest_folder = find_newest_data_folder(astro_base)
    if not newest_folder: print(f"CLI Error: No astro data in {astro_base}"); return
    astro_data = load_json_from_folder(newest_folder)
    if not astro_data: print(f"CLI Error: Could not load astro data from {newest_folder}"); return
    
    profile = args.profile_content; prof_path_str = args.profile_content
    if os.path.sep in prof_path_str or prof_path_str.endswith(".txt"):
        prof_path = Path(prof_path_str)
        if not prof_path.is_absolute(): prof_path = (project_base / prof_path).resolve()
        if prof_path.is_file():
            try:
                with open(prof_path, 'r', encoding='utf-8') as pf: profile = pf.read()
                logging.info(f"CLI: Loaded profile from {prof_path}")
            except Exception as e: logging.warning(f"CLI: Error loading profile {prof_path}: {e}")
    
    generate_llm_input_prompt_file(astro_data, args.target_zodiac_sign, str(template_file),
                                   str(target_out_dir), profile)
if __name__ == "__main__":
    main_cli()