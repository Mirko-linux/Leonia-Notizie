import schedule
import time
from datetime import datetime
import logging
import re

# Import dei moduli locali
import scraper
import ai_engine
import telegram_bot
import config

# Configurazione del logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def job_notiziario():
    """Funzione principale eseguita ogni ora."""
    ora_attuale = datetime.now().hour
    
    # Verifica fascia operativa (6-21) configurata in config.py
    if config.FASCIA_ORARIA[0] <= ora_attuale <= config.FASCIA_ORARIA[1]:
        logging.info(f"Avvio elaborazione notiziario delle ore {ora_attuale}:00")
        
        # 1. Recupero notizie (Titoli + Link + Fonte)
        notizie_raw = scraper.get_all_news()
        
        if not notizie_raw:
            logging.warning("Nessuna notizia recuperata dagli scraper. Salto l'invio.")
            return

        # 2. Controllo se è l'ora dell'approfondimento (ore 18)
        es_ora_speciale = (ora_attuale == 18)
        
        # 3. Generazione testo tramite IA
        testo_ia, modello_usato = ai_engine.genera_testo(notizie_raw, is_special=es_ora_speciale)
        
        if testo_ia and modello_usato:
            # --- PULIZIA EMOJI E CARATTERI SPECIALI ---
            # Teniamo lettere accentate italiane, numeri e punteggiatura, rimuoviamo emoji
            testo_ia = re.sub(r'[^\x00-\x7fàèéìòùÀÈÉÌÒÙ]+', '', testo_ia)

            if es_ora_speciale:
                # --- CASO 18:00: PUBBLICAZIONE SU TELEGRA.PH ---
                logging.info("Generazione pagina Telegra.ph per approfondimento...")
                
                link_approfondimento = ai_engine.crea_pagina_telegraph(
                    titolo=f"Approfondimento Leonia+ - {datetime.now().strftime('%d/%m/%Y')}",
                    contenuto_html=testo_ia
                )
                
                if link_approfondimento:
                    messaggio_per_invio = (
                        f"<b>LEONIA+ APPROFONDIMENTO</b>\n\n"
                        f"Oggi analizziamo i fatti salienti con un editoriale dedicato.\n\n"
                        f"Leggi l'articolo completo qui:\n"
                        f"<a href='{link_approfondimento}'>🔗 CLICCA PER APRIRE L'APPROFONDIMENTO</a>\n\n"
                        f"<i>Di Leonia+ Notizie</i>\n[Modello IA: {modello_usato}]"
                    )
                else:
                    logging.error("Fallimento creazione pagina Telegra.ph. Invio come testo normale.")
                    messaggio_per_invio = f"<b>LEONIA+ APPROFONDIMENTO</b>\n\n{testo_ia}\n\n<i>Di Leonia+ Notizie</i>\n[Modello IA: {modello_usato}]"
            
            else:
                # --- CASO ORARIO: MESSAGGIO DIRETTO ---
                header = f"<b>LEONIA+ NOTIZIE - ORE {ora_attuale}:00</b>"
                firma = f"\n\n<i>Di Leonia+ Notizie</i>\n[Modello IA: {modello_usato}]"
                messaggio_per_invio = f"{header}\n\n{testo_ia}{firma}"
            
            # 5. Invio effettivo a tutti i gruppi registrati
            successo = telegram_bot.send_message_to_all(messaggio_per_invio)
            
            if successo:
                logging.info(f"Notiziario inviato con successo a tutte le chat tramite {modello_usato}.")
            else:
                logging.error("Errore durante l'invio multiplo a Telegram.")
        else:
            logging.error("L'IA non ha restituito contenuti validi.")
    else:
        logging.info(f"Ora attuale ({ora_attuale}:00) fuori fascia operativa. Bot in standby.")

# --- SCHEDULAZIONE E AVVIO ---

schedule.every().hour.at(":00").do(job_notiziario)

logging.info("====================================")
logging.info("   LEONIA+ NOTIZIE BOT AVVIATO      ")
logging.info(f"   Operativo dalle {config.FASCIA_ORARIA[0]} alle {config.FASCIA_ORARIA[1]} ")
logging.info("====================================")
logging.info("Bot in ascolto. In attesa del prossimo job schedulato...")

# Esecuzione test iniziale di avvio
try:
    logging.info("Esecuzione test iniziale di avvio...")
    job_notiziario()
except Exception as e:
    logging.error(f"Errore critico durante il test iniziale: {e}")

# Loop infinito
while True:
    schedule.run_pending()
    time.sleep(10)