from gtts import gTTS
import os
import logging
import re

def genera_audio(testo, filename="news.mp3"):
    """
    Trasforma il testo in audio MP3.
    Rimuove i tag HTML per evitare che la voce legga 'bi chiusura bi'.
    """
    try:
        # Pulizia profonda per la lettura vocale
        testo_pulito = testo.replace("<b>", "").replace("</b>", "")
        testo_pulito = testo_pulito.replace("🔗 Fonte:", " Fonte: ")
        testo_pulito = testo_pulito.replace("---", "")
        # Rimuove le stelle per non far leggere 'stella stella stella'
        testo_pulito = testo_pulito.replace("⭐", "") 
        
        logging.info("Generazione file audio in corso...")
        tts = gTTS(text=testo_pulito, lang='it')
        tts.save(filename)
        return filename
    except Exception as e:
        logging.error(f"Errore generazione audio gTTS: {e}")
        return None