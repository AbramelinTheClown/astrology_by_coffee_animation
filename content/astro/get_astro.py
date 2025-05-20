# Filename: get_astro.py
import pathlib
import datetime
import json
import logging
import os
import numpy as np
from skyfield.api import load, Loader
from skyfield import __version__ as skyfield_version

# --- Base Directory Paths ---
BASE_PROJECT_DIR = pathlib.Path().resolve() # Assumes script is run with CWD as project root

# --- Log File Setup (relative to BASE_PROJECT_DIR) ---
log_filename = BASE_PROJECT_DIR / 'content' / 'astro' / 'log' / 'astrology_media_generation.log'
log_filename.parent.mkdir(parents=True, exist_ok=True)

# Basic logging config - main_get_astro_logic might reconfigure if needed for file handler
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s-%(levelname)s [%(module)s.%(funcName)s:%(lineno)d] - %(message)s',
                    handlers=[logging.StreamHandler()]) # Default to stream, file handler in function

SKYFIELD_DATA_DIR = BASE_PROJECT_DIR / "content" / "astro" / "skyfield_data"
EPHEMERIS_FILE = 'de421.bsp'

current_run_time_aware_utc = datetime.datetime.now(datetime.timezone.utc)
datetime_string_for_dirs = current_run_time_aware_utc.strftime("%Y-%m-%d_%H%M%S")
current_run_time_filename_str = current_run_time_aware_utc.strftime('%Y%m%d_%H%M')

PLANET_KEYS = {
    'sun': 'SUN', 'moon': 'MOON', 'mercury': 'MERCURY BARYCENTER', 'venus': 'VENUS BARYCENTER',
    'mars': 'MARS BARYCENTER', 'jupiter': 'JUPITER BARYCENTER', 'saturn': 'SATURN BARYCENTER',
    'uranus': 'URANUS BARYCENTER', 'neptune': 'NEPTUNE BARYCENTER', 'pluto': 'PLUTO BARYCENTER',
    'ceres': 'CERES', 'pallas': 'PALLAS', 'juno': 'JUNO', 'vesta': 'VESTA', 'chiron': 'CHIRON',
    'north_node': 'NODE'
}
ZODIAC_SIGNS_LIST = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
                'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']
ZODIAC_ABBR = ['Ari', 'Tau', 'Gem', 'Can', 'Leo', 'Vir',
               'Lib', 'Sco', 'Sag', 'Cap', 'Aqu', 'Pis']
EXALTATIONS = {
    'Sun': 'Aries', 'Moon': 'Taurus', 'Mercury': 'Virgo', 'Venus': 'Pisces',
    'Mars': 'Capricorn', 'Jupiter': 'Cancer', 'Saturn': 'Libra'
}
ASPECT_DEFINITIONS = {
    'Conjunction': (0, 10), 'Semisextile': (30, 2), 'Sextile': (60, 6),
    'Square': (90, 8), 'Trine': (120, 8), 'Quincunx': (150, 2),
    'Opposition': (180, 10)
}

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.float32, np.float64)): return float(obj)
        if isinstance(obj, (np.int32, np.int64)): return int(obj)
        if isinstance(obj, np.bool_): return bool(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        return super().default(obj)

def get_zodiac_sign_and_abbr(longitude_degrees):
    lon_norm = longitude_degrees % 360.0
    sign_index = int(lon_norm / 30)
    return ZODIAC_SIGNS_LIST[sign_index], ZODIAC_ABBR[sign_index]

def degrees_to_dms_string(longitude_degrees, sign_abbr):
    lon_norm = longitude_degrees % 360.0
    degree_in_sign = lon_norm % 30.0
    deg = int(degree_in_sign)
    minute_float = (degree_in_sign - deg) * 60
    mnt = int(minute_float)
    sec_float = (minute_float - mnt) * 60
    sec = int(round(sec_float));
    if sec == 60: sec = 0; mnt += 1
    if mnt == 60: mnt = 0; deg += 1
    return f"{deg:02d}° {sign_abbr} {mnt:02d}' {sec:02d}\""

def calculate_moon_phase(sun_lon, moon_lon):
    angle = (moon_lon - sun_lon + 360) % 360
    if angle < 22.5 or angle >= 337.5: return 'New Moon'
    elif 22.5 <= angle < 67.5: return 'Waxing Crescent'
    elif 67.5 <= angle < 112.5: return 'First Quarter'
    elif 112.5 <= angle < 157.5: return 'Waxing Gibbous'
    elif 157.5 <= angle < 202.5: return 'Full Moon'
    elif 202.5 <= angle < 247.5: return 'Waning Gibbous'
    elif 247.5 <= angle < 292.5: return 'Last Quarter'
    else: return 'Waning Crescent'

def get_celestial_body_data(aware_datetime_utc, skyfield_loader):
    ts = skyfield_loader.timescale()
    t = ts.from_datetime(aware_datetime_utc)
    eph = skyfield_loader(EPHEMERIS_FILE)
    earth = eph['EARTH']
    celestial_bodies_data = {}
    raw_longitudes = {}
    for body_key_lower, skyfield_name in PLANET_KEYS.items():
        body_name_capitalized = body_key_lower.replace('_', ' ').title()
        try: celestial_body_obj = eph[skyfield_name]
        except Exception as e: logging.error(f"Err load '{skyfield_name}': {e}"); continue
        astrometric = earth.at(t).observe(celestial_body_obj)
        _, ecliptic_lon, _ = astrometric.ecliptic_latlon()
        current_longitude_degrees = ecliptic_lon.degrees
        sign, sign_abbr = get_zodiac_sign_and_abbr(current_longitude_degrees)
        longitude_dms_str = degrees_to_dms_string(current_longitude_degrees, sign_abbr)
        exalted = EXALTATIONS.get(body_name_capitalized) == sign
        retrograde = False
        if body_key_lower == 'north_node': retrograde = True
        elif body_key_lower not in ['sun', 'moon']:
            dt_plus_1 = aware_datetime_utc + datetime.timedelta(minutes=1)
            t_plus_1 = ts.from_datetime(dt_plus_1)
            lon_plus_1 = earth.at(t_plus_1).observe(celestial_body_obj).ecliptic_latlon()[1].degrees
            delta_lon = (lon_plus_1 - current_longitude_degrees + 180) % 360 - 180
            retrograde = delta_lon < 0
        celestial_bodies_data[body_name_capitalized] = {
            'longitude_decimal': round(current_longitude_degrees,6), 'longitude_dms': longitude_dms_str,
            'sign': sign, 'retrograde': retrograde, 'exalted': exalted
        }
        raw_longitudes[body_name_capitalized] = current_longitude_degrees
        if body_key_lower == 'north_node':
            sn_lon = (current_longitude_degrees + 180.0) % 360.0
            sn_sign,sn_abbr = get_zodiac_sign_and_abbr(sn_lon)
            celestial_bodies_data['South Node'] = {
                'longitude_decimal':round(sn_lon,6), 'longitude_dms':degrees_to_dms_string(sn_lon,sn_abbr),
                'sign': sn_sign, 'retrograde':True,'exalted':False
            }
            raw_longitudes['South Node'] = sn_lon
    if 'Sun' in raw_longitudes and 'Moon' in raw_longitudes:
        moon_phase = calculate_moon_phase(raw_longitudes['Sun'], raw_longitudes['Moon'])
        if 'Moon' in celestial_bodies_data: celestial_bodies_data['Moon']['phase'] = moon_phase
    return celestial_bodies_data, raw_longitudes

def calculate_aspects(celestial_bodies_data, raw_longitudes):
    aspects_list = []
    body_names = list(raw_longitudes.keys())
    for i in range(len(body_names)):
        for j in range(i + 1, len(body_names)):
            b1,b2=body_names[i],body_names[j];lon1,lon2=raw_longitudes[b1],raw_longitudes[b2]
            diff=abs(lon1-lon2);sep=min(diff,360.0-diff)
            for name,(angle,orb) in ASPECT_DEFINITIONS.items():
                if abs(sep-angle)<=orb and b1 in celestial_bodies_data and b2 in celestial_bodies_data:
                    aspects_list.append({'body1':b1,'body2':b2,'aspect_type':name,
                                         'angle_degrees':round(sep,2),'orb_degrees':round(abs(sep-angle),2),
                                         'sign1':celestial_bodies_data[b1]['sign'],'sign2':celestial_bodies_data[b2]['sign']})
                    break
    return aspects_list

def calculate_midpoints(raw_longitudes):
    midpoints_data = {}
    body_names = list(raw_longitudes.keys())
    for i in range(len(body_names)):
        for j in range(i + 1, len(body_names)):
            b1,b2=body_names[i],body_names[j];lon1,lon2=raw_longitudes[b1],raw_longitudes[b2]
            mid_raw=(lon1+lon2)/2.0;
            if abs(lon1-lon2)>180: mid_raw=(lon1+lon2+360)/2.0
            mid_lon=mid_raw%360.0;sign,abbr=get_zodiac_sign_and_abbr(mid_lon)
            midpoints_data[f"{b1}/{b2}"]={'longitude_decimal':round(mid_lon,6),
                                          'longitude_dms':degrees_to_dms_string(mid_lon,abbr),'sign':sign}
    return midpoints_data

def calculate_arabic_parts(raw_longitudes, asc_lon_placeholder=0.0):
    arabic_parts_data = {}
    if 'Sun' in raw_longitudes and 'Moon' in raw_longitudes:
        pof_lon=(asc_lon_placeholder+raw_longitudes['Moon']-raw_longitudes['Sun']+360)%360.0
        sign,abbr=get_zodiac_sign_and_abbr(pof_lon)
        arabic_parts_data['Part of Fortune']={'longitude_decimal':round(pof_lon,6),
                                             'longitude_dms':degrees_to_dms_string(pof_lon,abbr),'sign':sign,
                                             'formula_note':"Asc+Moon-Sun (Asc placeholder used)"}
    return arabic_parts_data

def main_get_astro_logic():
    # Ensure logging file handler is set up with absolute path for robustness
    for handler in logging.root.handlers[:]: logging.root.removeHandler(handler) # Clear existing
    file_handler = logging.FileHandler(str(log_filename), mode='w')
    formatter = logging.Formatter('%(asctime)s-%(levelname)s [%(module)s.%(funcName)s:%(lineno)d] - %(message)s')
    file_handler.setFormatter(formatter)
    logging.getLogger().addHandler(file_handler)
    logging.getLogger().addHandler(logging.StreamHandler()) # Also log to console
    logging.getLogger().setLevel(logging.INFO)

    logging.info(f"main_get_astro_logic started. Skyfield: {skyfield_version}. Project Base: {BASE_PROJECT_DIR}")
    try:
        SKYFIELD_DATA_DIR.mkdir(parents=True, exist_ok=True)
        skyfield_loader = Loader(str(SKYFIELD_DATA_DIR), verbose=True)
        eph_path = SKYFIELD_DATA_DIR / EPHEMERIS_FILE
        if not eph_path.exists(): logging.info(f"Downloading {EPHEMERIS_FILE} to {SKYFIELD_DATA_DIR}...")
        skyfield_loader(EPHEMERIS_FILE)
        logging.info(f"Ephemeris {EPHEMERIS_FILE} ready in {SKYFIELD_DATA_DIR}")
    except Exception as e: logging.critical(f"Skyfield Loader init failed: {e}", exc_info=True); raise

    try:
        celestial_data, raw_lons = get_celestial_body_data(current_run_time_aware_utc, skyfield_loader)
        aspects = calculate_aspects(celestial_data, raw_lons)
        midpoints = calculate_midpoints(raw_lons)
        arabic_parts = calculate_arabic_parts(raw_lons)
        output_data = {
            "calculation_metadata": {"calculation_datetime_utc":current_run_time_aware_utc.isoformat(),
                                     "ephemeris_file_used":EPHEMERIS_FILE,"skyfield_version":skyfield_version},
            "celestial_bodies":celestial_data,
            "aspect_analysis":{"aspects":aspects,
                               "orb_settings_used":{n:f"{a}°(orb±{o}°)" for n,(a,o) in ASPECT_DEFINITIONS.items()}},
            "derived_points":{"midpoints":midpoints,"arabic_parts":arabic_parts}
        }
        output_dir = BASE_PROJECT_DIR/"content"/"astro"/"astro_output"/datetime_string_for_dirs
        output_dir.mkdir(parents=True, exist_ok=True)
        output_fn = output_dir/f"astrological_data_v2_{current_run_time_filename_str}.json"
        logging.info(f"Saving astro data to: {output_fn}")
        with open(output_fn, 'w') as f: json.dump(output_data, f, cls=NumpyEncoder, indent=4)
        logging.info("Astro data saved."); print(f"SUCCESS (get_astro): Data saved to {output_fn}")
        return True
    except Exception as e:
        logging.error(f"Processing/saving astro data failed: {e}", exc_info=True)
        print(f"ERROR (get_astro): Processing failed. Log: {log_filename}. Err: {e}")
        return False

if __name__ == "__main__":
    logging.info(f"get_astro.py direct execution started.")
    if main_get_astro_logic():
        logging.info("get_astro.py direct execution finished successfully.")
    else:
        logging.error("get_astro.py direct execution failed."); exit(1)