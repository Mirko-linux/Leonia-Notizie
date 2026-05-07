from gtts import gTTS
from pydub import AudioSegment
import os
import logging
import re

def genera_audio(testo, filename="news_finale.mp3"):
    """
    Trasforma il testo in audio MP3 con gestione percorsi assoluti.
    """
    # Determiniamo la cartella dove si trova fisicamente questo script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    path_sigla = os.path.join(BASE_DIR, "sigla.mp3")
    temp_voice = os.path.join(BASE_DIR, "voice_temp.mp3")
    output_path = os.path.join(BASE_DIR, filename)
    
    try:
        # --- 1. PULIZIA TESTO ---
        testo_pulito = re.sub(r'<[^>]+>', '', testo)
        testo_pulito = re.sub(r'http\S+|www\S+', '', testo_pulito)
        testo_pulito = testo_pulito.replace("⭐", "").replace("---", "")
        testo_pulito = " ".join(testo_pulito.split())

        if not testo_pulito.strip():
            logging.warning("Testo pulito vuoto, impossibile generare audio.")
            return None

        # --- 2. GENERAZIONE VOCE ---
        logging.info("Generazione voce con gTTS...")
        tts = gTTS(text=testo_pulito, lang='it')
        tts.save(temp_voice)

        # --- 3. INTEGRAZIONE SIGLA ---
        # Verifichiamo se il file esiste usando il percorso assoluto
        if os.path.exists(path_sigla):
            logging.info(f"Sigla trovata in: {path_sigla}. Unione in corso...")
            sigla = AudioSegment.from_mp3(path_sigla)
            voce = AudioSegment.from_mp3(temp_voice)
            
            pausa = AudioSegment.silent(duration=500)
            audio_completo = sigla + pausa + voce
            
            # Esportiamo l'audio finale
            audio_completo.export(output_path, format="mp3")
            
            if os.path.exists(temp_voice):
                os.remove(temp_voice)
                
            logging.info(f"Audio finale creato: {output_path}")
            return output_path
        else:
            logging.warning(f"Sigla NON trovata al percorso: {path_sigla}. Uso solo voce.")
            if os.path.exists(output_path):
                os.remove(output_path)
            os.rename(temp_voice, output_path)
            return output_path

    except Exception as e:
        logging.error(f"Errore critico audio: {e}")
        if os.path.exists(temp_voice):
            os.remove(temp_voice)
        return None