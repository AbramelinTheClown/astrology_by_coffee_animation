client = Client("http://127.0.0.1:7860/")
import os
import dotenv

os.dotenv()

NEBBLES_VOICE_CLONE= os.dotenv("NEBBLSE_VOICE_CLONE")

def get_f5tts(voice, refernce_txt, script,):
    
    client.predict(
    ref_audio_input=handle_file(voice),
    ref_text_input=refernce_txt,
    gen_text_input=script,
    remove_silence=False,
    randomize_seed=True,
    seed_input=722887908,
    cross_fade_duration_slider=0.15,
    nfe_slider=32,
    speed_slider=0.7,
    api_name="/basic_tts"
    )
    return(result)