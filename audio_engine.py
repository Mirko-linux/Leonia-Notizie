from gtts import gTTS
from pydub import AudioSegment  # Necessario per unire sigla e voce
import os
import logging
import re

def genera_audio(testo, filename="news_finale.mp3"):
    """
    Trasforma il testo in audio MP3:
    1. Rimuove link e tag HTML (così non vengono letti).
    2. Genera la voce con gTTS.
    3. Incolla la 'sigla.mp3' all'inizio del file.
    """
    temp_voice = "voice_temp.mp3"
    
    try:
        # --- 1. PULIZIA TESTO PER LA LETTURA VOCALE ---
        # Rimuove i tag HTML (es: <b>, </b>)
        testo_pulito = re.sub(r'<[^>]+>', '', testo)
        
        # Rimuove i link (http, https, www) affinché non vengano compitati lettera per lettera
        testo_pulito = re.sub(r'http\S+|www\S+', '', testo_pulito)
        
        # Rimuove emoji (come ⭐) e separatori grafici (come ---)
        testo_pulito = testo_pulito.replace("⭐", "").replace("---", "")
        
        # Pulizia spazi extra
        testo_pulito = " ".join(testo_pulito.split())

        if not testo_pulito.strip():
            logging.warning("Testo pulito vuoto, impossibile generare audio.")
            return None

        # --- 2. GENERAZIONE VOCE ---
        logging.info("Generazione voce con gTTS...")
        tts = gTTS(text=testo_pulito, lang='it')
        tts.save(temp_voice)

        # --- 3. INTEGRAZIONE SIGLA ---
        if os.path.exists("sigla.mp3"):
            logging.info("Sigla.mp3 trovata. Unione audio in corso...")
            sigla = AudioSegment.from_mp3("sigla.mp3")
            voce = AudioSegment.from_mp3(temp_voice)
            
            # Crea una pausa di silenzio di 500ms (mezzo secondo) tra sigla e voce
            pausa = AudioSegment.silent(duration=500)
            
            # Unione: SIGLA + PAUSA + VOCE
            audio_completo = sigla + pausa + voce
            
            # Esporta il file finale
            audio_completo.export(filename, format="mp3")
            
            # Rimuove il file temporaneo della voce
            if os.path.exists(temp_voice):
                os.remove(temp_voice)
                
            logging.info(f"Audio finale creato con sigla: {filename}")
            return filename
        else:
            # Se la sigla manca, usa solo la voce generata
            logging.warning("Sigla.mp3 non trovata nella cartella. Genero audio solo voce.")
            if os.path.exists(filename):
                os.remove(filename)
            os.rename(temp_voice, filename)
            return filename

    except Exception as e:
        logging.error(f"Errore critico durante la generazione audio: {e}")
        # Pulizia in caso di errore per non lasciare file corrotti
        if os.path.exists(temp_voice):
            os.remove(temp_voice)
        return None