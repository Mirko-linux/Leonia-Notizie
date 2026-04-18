import schedule
import time
from datetime import datetime
import logging
import re
import threading
import os
from flask import Flask

# Import dei moduli locali
import scraper
import ai_engine
import telegram_bot
import config
import audio_engine  

# --- CONFIGURAZIONE FLASK (WEB SERVER PER RENDER) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Leonia+ Notizie Bot is running!"

def run_flask():
    # Render assegna una porta dinamica tramite la variabile PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- CONFIGURAZIONE LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- LOGICA DEL BOT ---
def job_notiziario():
    """Funzione principale con filtro anti-duplicati e Audio-Notiziario."""
    ora_attuale = datetime.now().hour
    
    # Verifica fascia operativa
    if config.FASCIA_ORARIA[0] <= ora_attuale <= config.FASCIA_ORARIA[1]:
        logging.info(f"Avvio elaborazione notiziario delle ore {ora_attuale}:00")
        
        notizie_raw = scraper.get_all_news()
        if not notizie_raw:
            logging.warning("Nessuna notizia recuperata.")
            return

        # --- LOGICA FILTRO DUPLICATI ---
        notizie_da_inviare = []
        for notizia in notizie_raw:
            url = notizia.get('link')
            
            # Controlliamo se l'URL è già presente nel set "news_sent" su Redis
            if not telegram_bot.r.sismember("news_sent", url):
                notizie_da_inviare.append(notizia)
                telegram_bot.r.sadd("news_sent", url)
            else:
                logging.info(f"Notizia già inviata in precedenza: {notizia.get('titolo')[:30]}...")

        # Scadenza memoria news (24 ore)
        telegram_bot.r.expire("news_sent", 86400)

        if not notizie_da_inviare:
            logging.info("Nessuna nuova notizia da pubblicare. Salto il job.")
            return
        
        # Limite a 5 notizie per non sovraccaricare il TTS
        notizie_da_inviare = notizie_da_inviare[:5]

        # --- GENERAZIONE TESTO IA ---
        es_ora_speciale = (ora_attuale == 18)
        testo_ia, modello_usato = ai_engine.genera_testo(notizie_da_inviare, is_special=es_ora_speciale)
        
        if testo_ia and modello_usato:
            # Pulizia automatica testo
            testo_ia = re.sub(r'[^\x00-\x7fàèéìòùÀÈÉÌÒÙ⭐]+', '', testo_ia)
            testo_ia = re.sub(r'([a-z])([A-Z])', r'\1 \2', testo_ia)
            testo_ia = testo_ia.replace("</b>", "</b>\n")

            # --- INVIO TESTO ---
            if es_ora_speciale:
                link_art = ai_engine.crea_pagina_telegraph(
                    titolo=f"Approfondimento Leonia+ - {datetime.now().strftime('%d/%m/%Y')}",
                    contenuto_html=testo_ia
                )
                msg = f"<b>LEONIA+ APPROFONDIMENTO</b>\n\n<a href='{link_art}'>🔗 LEGGI L'ARTICOLO</a>"
            else:
                msg = f"<b>LEONIA+ NOTIZIE - ORE {ora_attuale}:00</b>\n\n{testo_ia}\n\n<i>Di Leonia+ Notizie</i>"
            
            telegram_bot.send_message_to_all(msg)
            logging.info(f"Messaggio testuale inviato con modello {modello_usato}")

            # --- GENERAZIONE E INVIO AUDIO ---
            audio_file = audio_engine.genera_audio(testo_ia)
            
            if audio_file:
                didascalia = f"🎙 <b>Audio-Notiziario - Ore {ora_attuale}:00</b>"
                telegram_bot.send_audio_to_all(audio_file, didascalia)
                
                # PULIZIA DISCO (Cruciale per Render)
                if os.path.exists(audio_file):
                    os.remove(audio_file)
                    logging.info("File audio temporaneo rimosso correttamente per risparmiare spazio.")

# --- AVVIO E SCHEDULAZIONE ---
if __name__ == "__main__":
    # 1. Avvia Flask in un thread separato
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    logging.info("Web Server Flask avviato (Port-binding attivo)")

    # 2. Configura Schedule
    schedule.every().hour.at(":00").do(job_notiziario)

    logging.info("====================================")
    logging.info("   LEONIA+ NOTIZIE BOT AVVIATO      ")
    logging.info("====================================")

    # 3. Test iniziale (esegue il job appena acceso il bot)
    try:
        job_notiziario()
    except Exception as e:
        logging.error(f"Errore test iniziale: {e}")

    # 4. Loop Infinito
    while True:
        schedule.run_pending()
        time.sleep(1)