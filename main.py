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

# --- CONFIGURAZIONE FLASK (WEB SERVER PER RENDER) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Leonia+ Notizie Bot is running!"

def run_flask():
    # Render assegna una porta dinamica tramite la variabile PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- LOGICA DEL BOT ---
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def job_notiziario():
    """Funzione principale con filtro anti-duplicati."""
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
                # Aggiungiamo l'URL alla memoria
                telegram_bot.r.sadd("news_sent", url)
            else:
                logging.info(f"Notizia già inviata in precedenza: {notizia.get('titolo')[:30]}...")

        # Facciamo scadere la lista degli URL ogni 24 ore per non riempire Redis all'infinito
        telegram_bot.r.expire("news_sent", 86400)

        # Se dopo il filtro non ci sono notizie nuove, ci fermiamo qui
        if not notizie_da_inviare:
            logging.info("Nessuna nuova notizia da pubblicare. Salto il job.")
            return
        
        # Prendiamo solo le prime 5 se ce ne sono troppe
        notizie_da_inviare = notizie_da_inviare[:5]
        # -------------------------------

        es_ora_speciale = (ora_attuale == 18)
        testo_ia, modello_usato = ai_engine.genera_testo(notizie_da_inviare, is_special=es_ora_speciale)
        
        if testo_ia and modello_usato:
            # Pulizia e formattazione (Regex per spazi e caratteri)
            testo_ia = re.sub(r'[^\x00-\x7fàèéìòùÀÈÉÌÒÙ⭐]+', '', testo_ia)
            testo_ia = re.sub(r'([a-z])([A-Z])', r'\1 \2', testo_ia)
            testo_ia = testo_ia.replace("</b>", "</b>\n")

            if es_ora_speciale:
                # Logica Telegra.ph per le 18:00
                link_art = ai_engine.crea_pagina_telegraph(
                    titolo=f"Approfondimento Leonia+ - {datetime.now().strftime('%d/%m/%Y')}",
                    contenuto_html=testo_ia
                )
                msg = f"<b>LEONIA+ APPROFONDIMENTO</b>\n\n<a href='{link_art}'>🔗 LEGGI L'ARTICOLO</a>"
            else:
                msg = f"<b>LEONIA+ NOTIZIE - ORE {ora_attuale}:00</b>\n\n{testo_ia}\n\n<i>Di Leonia+ Notizie</i>"
            
            telegram_bot.send_message_to_all(msg)
            logging.info(f"Notiziario inviato con {len(notizie_da_inviare)} nuove notizie.")

# --- AVVIO E SCHEDULAZIONE ---
if __name__ == "__main__":
    # 1. Avvia Flask in un thread separato
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True # Il thread si chiude se il programma principale si chiude
    flask_thread.start()
    logging.info("Web Server Flask avviato (Porta 10000 o assegnata da Render)")

    # 2. Configura Schedule
    schedule.every().hour.at(":00").do(job_notiziario)

    logging.info("====================================")
    logging.info("   LEONIA+ NOTIZIE BOT AVVIATO      ")
    logging.info("====================================")

    # 3. Test iniziale (opzionale)
    try:
        job_notiziario()
    except Exception as e:
        logging.error(f"Errore test iniziale: {e}")

    # 4. Loop Infinito
    while True:
        schedule.run_pending()
        time.sleep(10)