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
    """Funzione principale eseguita ogni ora."""
    ora_attuale = datetime.now().hour
    
    if config.FASCIA_ORARIA[0] <= ora_attuale <= config.FASCIA_ORARIA[1]:
        logging.info(f"Avvio elaborazione notiziario delle ore {ora_attuale}:00")
        
        notizie_raw = scraper.get_all_news()
        if not notizie_raw:
            logging.warning("Nessuna notizia recuperata. Salto l'invio.")
            return

        es_ora_speciale = (ora_attuale == 18)
        testo_ia, modello_usato = ai_engine.genera_testo(notizie_raw, is_special=es_ora_speciale)
        
        if testo_ia and modello_usato:
            # --- 1. PULIZIA EMOJI E CARATTERI ---
            testo_ia = re.sub(r'[^\x00-\x7fàèéìòùÀÈÉÌÒÙ⭐]+', '', testo_ia)

            testo_ia = re.sub(r'([a-z])([A-Z])', r'\1 \2', testo_ia)
            testo_ia = testo_ia.replace("</b>", "</b>\n")

            if "Valutazione:" in testo_ia and "⭐" not in testo_ia:
                testo_ia = testo_ia.replace("Valutazione:", "Valutazione: ⭐⭐⭐")
            if es_ora_speciale:
                link_approfondimento = ai_engine.crea_pagina_telegraph(
                    titolo=f"Approfondimento Leonia+ - {datetime.now().strftime('%d/%m/%Y')}",
                    contenuto_html=testo_ia
                )
                
                if link_approfondimento:
                    messaggio_per_invio = (
                        f"<b>LEONIA+ APPROFONDIMENTO</b>\n\n"
                        f"Leggi l'articolo completo qui:\n"
                        f"<a href='{link_approfondimento}'>🔗 CLICCA PER APRIRE</a>\n\n"
                        f"<i>Di Leonia+ Notizie</i>\n[Modello IA: {modello_usato}]"
                    )
                else:
                    messaggio_per_invio = f"<b>LEONIA+ APPROFONDIMENTO</b>\n\n{testo_ia}\n\n<i>Di Leonia+ Notizie</i>"
            else:
                header = f"<b>LEONIA+ NOTIZIE - ORE {ora_attuale}:00</b>"
                firma = f"\n\n<i>Di Leonia+ Notizie</i>\n[Modello IA: {modello_usato}]"
                messaggio_per_invio = f"{header}\n\n{testo_ia}{firma}"
            
            successo = telegram_bot.send_message_to_all(messaggio_per_invio)
            if successo:
                logging.info(f"Notiziario inviato con successo tramite {modello_usato}.")
            else:
                logging.error("Errore durante l'invio multiplo.")
        else:
            logging.error("L'IA non ha restituito contenuti validi.")
    else:
        logging.info(f"Ora attuale ({ora_attuale}:00) fuori fascia operativa.")

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