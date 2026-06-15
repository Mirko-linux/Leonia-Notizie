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
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- CONFIGURAZIONE LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def calcola_valutazione_potenziale(notizia, tutte_le_notizie):
    """
    Calcola il punteggio in stelle (da 1 a 5) basandosi su quante fonti
    parlano dello stesso argomento (parole chiave simili nel titolo).
    """
    titolo_target = (notizia.get('titolo', '') if isinstance(notizia, dict) else '').lower()
    if not titolo_target:
        return "⭐"
        
    # Estrae parole chiave significative (lunghe più di 4 caratteri)
    parole_chiave = [p for p in re.findall(r'\b\w{5,}\b', titolo_target)]
    if not parole_chiave:
        return "⭐"

    fonti_concordi = 1
    # Confronta con le altre notizie estratte nel ciclo attuale
    for altra in tutte_le_notizie:
        t_altra = (altra.get('titolo', '') if isinstance(altra, dict) else '').lower()
        if t_altra == titolo_target:
            continue
        # Se l'altro titolo contiene almeno 2 delle parole chiave, consideriamo la notizia correlata
        corrispondenze = sum(1 for pc in parole_chiave if pc in t_altra)
        if corrispondenze >= 2:
            fonti_concordi += 1

    # Cap a 5 stelle massimo
    stelle = min(fonti_concordi, 5)
    return "⭐" * stelle

def job_notiziario():
    """Funzione principale con invio sistematico su Telegraph, Audio e Calcolo Fonti."""
    ora_attuale = datetime.now().hour
    
    # 1. Verifica fascia operativa
    if not (config.FASCIA_ORARIA[0] <= ora_attuale <= config.FASCIA_ORARIA[1]):
        logging.info(f"Fuori fascia oraria operativa ({ora_attuale}:00). Riposo.")
        return

    logging.info(f"Avvio elaborazione delle ore {ora_attuale}:00")
    
    # 2. Recupero notizie
    try:
        notizie_raw = scraper.get_all_news()
    except Exception as e:
        logging.error(f"Errore durante lo scraping: {e}")
        return

    if not notizie_raw:
        logging.warning("Nessuna notizia recuperata dai siti.")
        return

    # 3. Logica Filtro Duplicati con il Canale Cassaforte
    notizie_da_inviare = []
    logging.info("Verifica duplicati tramite la cronologia del canale di log...")
    try:
        for notizia in notizie_raw:
            url = notizia.get('link') if isinstance(notizia, dict) else notizia
            titolo = notizia.get('titolo', 'Senza Titolo') if isinstance(notizia, dict) else url[:30]
            
            if not telegram_bot.controlla_duplicato_su_telegram(url):
                notizie_da_inviare.append(notizia)
                telegram_bot.salva_notizia_nel_log(url, titolo)
                time.sleep(0.2)
            else:
                logging.info(f"Notizia scartata (già inviata): {titolo[:30]}...")
    except Exception as e:
        logging.error(f"Errore filtraggio notizie: {e}. Procedo con fallback.")
        notizie_da_inviare = notizie_raw[:5]

    if not notizie_da_inviare:
        logging.info("Nessuna nuova notizia da pubblicare dopo il filtraggio.")
        return
    
    notizie_da_inviare = notizie_da_inviare[:5]

    # Calcolo della stella di valutazione per la notizia principale/rilevante
    valutazione_stelle = calcola_valutazione_potenziale(notizie_da_inviare[0], notizie_raw)

    # 4. Generazione Testo Esteso via IA (destinato a Telegraph e Audio)
    es_ora_speciale = (ora_attuale == 15)  # Spostato l'approfondimento speciale alle 15
    try:
        testo_ia_esteso, modello_usato = ai_engine.genera_testo(notizie_da_inviare, is_special=es_ora_speciale)
    except Exception as e:
        logging.error(f"Errore generazione testo IA: {e}")
        return

    if testo_ia_esteso and modello_usato:
        # Pulizia caratteri e tag
        testo_ia_esteso = re.sub(r'[^\x00-\x7fàèéìòùÀÈÉÌÒÙ⭐]+', '', testo_ia_esteso)
        testo_ia_esteso = re.sub(r'([a-z])([A-Z])', r'\1 \2', testo_ia_esteso)
        testo_ia_esteso = testo_ia_esteso.replace("</b>", "</b>\n")

        # Generazione Pagina Telegraph per TUTTE le edizioni
        try:
            tipo_notiziario = "APPROFONDIMENTO" if es_ora_speciale else "EDIZIONE"
            link_telegraph = ai_engine.crea_pagina_telegraph(
                titolo=f"{tipo_notiziario} LEONIA+ - ORE {ora_attuale}:00 del {datetime.now().strftime('%d/%m/%Y')}",
                contenuto_html=testo_ia_esteso
            )
        except Exception as e:
            logging.error(f"Errore creazione pagina Telegraph: {e}")
            link_telegraph = "#"

        # 5. Generazione Sintesi Breve per Telegram (Titolo + Breve riassunto)
        titolo_principale = notizie_da_inviare[0].get('titolo', 'Notizie dell\'ultima ora') if isinstance(notizie_da_inviare[0], dict) else 'Notizie Leonia+'
        
        if es_ora_speciale:
            msg_telegram = (
                f"🌟 <b>LEONIA+ APPROFONDIMENTO - ORE {ora_attuale}:00</b>\n\n"
                f"📌 <b>Focus su:</b> {titolo_principale}\n"
                f"📊 <b>Valutazione Potenziale:</b> {valutazione_stelle}\n\n"
                f"👉 L'analisi completa e dettagliata dello scenario è disponibile sulla nostra pagina dedicata.\n\n"
                f"🔗 <a href='{link_telegraph}'>LEGGI L'APPROFONDIMENTO COMPLETO</a>"
            )
        else:
            msg_telegram = (
                f"📢 <b>LEONIA+ NOTIZIE - ORE {ora_attuale}:00</b>\n\n"
                f"🔹 <b>Primo Piano:</b> {titolo_principale}\n"
                f"📊 <b>Valutazione Potenziale:</b> {valutazione_stelle}\n\n"
                f"📝 Abbiamo sintetizzato le 5 notizie più importanti del momento nel report esteso.\n\n"
                f"🔗 <a href='{link_telegraph}'>LEGGI IL REPORT SU TELEGRAPH</a>"
            )
        
        # Invio del testo sintetico con pin automatico
        telegram_bot.send_message_to_all(msg_telegram)
        logging.info(f"Messaggio sintetico inviato e fissato ({modello_usato}).")

        # 6. Generazione e Invio Audio (basato sul testo esteso)
        try:
            audio_file = audio_engine.genera_audio(testo_ia_esteso)
            if audio_file and os.path.exists(audio_file):
                didascalia = (
                    f"🎙 <b>Audio-Notiziario - Ore {ora_attuale}:00</b>\n\n"
                    f"🔗 <a href='{link_telegraph}'>Leggi il testo completo qui</a>"
                )
                telegram_bot.send_audio_to_all(audio_file, didascalia)
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

    # 2. Configura Nuovi Orari Richiesti
    # NOTIZIE: 8, 13, 18
    schedule.every().day.at("08:00").do(job_notiziario)
    schedule.every().day.at("13:00").do(job_notiziario)
    schedule.every().day.at("18:00").do(job_notiziario)
    
    # APPROFONDIMENTO: 15
    schedule.every().day.at("15:00").do(job_notiziario)

    logging.info("====================================")
    logging.info("   LEONIA+ NOTIZIE BOT AVVIATO      ")
    logging.info("====================================")

    # [RIMOZIONE TEST INIZIALE] Il bot ora non eseguirà job_notiziario() all'accensione

    # 3. LOOP INFINITO (Mantiene in vita l'applicazione su Render)
    while True:
        schedule.run_pending()
        time.sleep(1)