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

def job_notiziario():
    """Funzione principale con protezione anti-crash e gestione database."""
    ora_attuale = datetime.now().hour
    
    # 1. Verifica fascia operativa
    if not (config.FASCIA_ORARIA[0] <= ora_attuale <= config.FASCIA_ORARIA[1]):
        logging.info(f"Fuori fascia oraria operativa ({ora_attuale}:00). Riposo.")
        return

    logging.info(f"Avvio elaborazione notiziario delle ore {ora_attuale}:00")
    
    # 2. Recupero notizie
    try:
        notizie_raw = scraper.get_all_news()
    except Exception as e:
        logging.error(f"Errore durante lo scraping: {e}")
        return

    if not notizie_raw:
        logging.warning("Nessuna notizia recuperata dai siti.")
        return

    # 3. Logica Filtro Duplicati con Protezione Anti-Crash
    notizie_da_inviare = []
    
    # Controlliamo se la connessione Redis esiste
    if telegram_bot.r is not None:
        try:
            for notizia in notizie_raw:
                # Gestione robusta: notizia può essere dict o str (per sicurezza)
                url = notizia.get('link') if isinstance(notizia, dict) else notizia
                
                if not telegram_bot.r.sismember("news_sent", url):
                    notizie_da_inviare.append(notizia)
                    telegram_bot.r.sadd("news_sent", url)
                else:
                    titolo = notizia.get('titolo', 'Senza Titolo')[:30] if isinstance(notizia, dict) else url[:30]
                    logging.info(f"Notizia già inviata: {titolo}...")
            
            # Scadenza memoria 24h
            telegram_bot.r.expire("news_sent", 86400)
        except Exception as e:
            logging.error(f"Errore database Redis durante il filtro: {e}. Procedo senza filtro.")
            notizie_da_inviare = notizie_raw[:5] # Fallback: prendi le prime 5
    else:
        logging.warning("Redis non collegato! Invio notizie senza controllo duplicati.")
        notizie_da_inviare = notizie_raw[:5]

    if not notizie_da_inviare:
        logging.info("Nessuna nuova notizia da pubblicare dopo il filtraggio.")
        return
    
    # Limitiamo sempre a 5 per non sovraccaricare l'IA e il TTS
    notizie_da_inviare = notizie_da_inviare[:5]

    # 4. Generazione Testo IA
    es_ora_speciale = (ora_attuale == 18)
    try:
        testo_ia, modello_usato = ai_engine.genera_testo(notizie_da_inviare, is_special=es_ora_speciale)
    except Exception as e:
        logging.error(f"Errore generazione testo IA: {e}")
        return

    if testo_ia and modello_usato:
        # Pulizia e formattazione
        testo_ia = re.sub(r'[^\x00-\x7fàèéìòùÀÈÉÌÒÙ⭐]+', '', testo_ia)
        testo_ia = re.sub(r'([a-z])([A-Z])', r'\1 \2', testo_ia)
        testo_ia = testo_ia.replace("</b>", "</b>\n")

        # 5. Invio Messaggio Testuale
        if es_ora_speciale:
            try:
                link_art = ai_engine.crea_pagina_telegraph(
                    titolo=f"Approfondimento Leonia+ - {datetime.now().strftime('%d/%m/%Y')}",
                    contenuto_html=testo_ia
                )
                msg = f"<b>LEONIA+ APPROFONDIMENTO</b>\n\n<a href='{link_art}'>🔗 LEGGI L'ARTICOLO</a>"
            except Exception as e:
                logging.error(f"Errore creazione pagina Telegraph: {e}")
                msg = f"<b>LEONIA+ NOTIZIE - ORE {ora_attuale}:00</b>\n\n{testo_ia}"
        else:
            msg = f"<b>LEONIA+ NOTIZIE - ORE {ora_attuale}:00</b>\n\n{testo_ia}\n\n<i>Di Leonia+ Notizie</i>"
        
        telegram_bot.send_message_to_all(msg)
        logging.info(f"Messaggio inviato con successo ({modello_usato}).")

        # 6. Generazione e Invio Audio
        try:
            audio_file = audio_engine.genera_audio(testo_ia)
            if audio_file and os.path.exists(audio_file):
                didascalia = f"🎙 <b>Audio-Notiziario - Ore {ora_attuale}:00</b>"
                telegram_bot.send_audio_to_all(audio_file, didascalia)
                
                # Pulizia immediata
                os.remove(audio_file)
                logging.info("File audio rimosso correttamente.")
        except Exception as e:
            logging.error(f"Errore durante la fase audio: {e}")

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