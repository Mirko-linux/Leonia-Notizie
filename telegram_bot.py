import requests
import config
import logging
import time
import os
import redis

# --- CONFIGURAZIONE DATABASE ---
GRUPPI_FILE = "gruppi.txt"
REDIS_URL = os.getenv("REDIS_URL")

# Connessione Redis (solo se presente la variabile, tipico di Render)
r = None
if REDIS_URL:
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        logging.info("DATABASE: Collegato a Redis (Modalità Render)")
    except Exception as e:
        logging.error(f"DATABASE: Errore connessione Redis: {e}")

def registra_gruppo(chat_id):
    """Salva l'ID su Redis (se disponibile) o su file locale."""
    chat_id = str(chat_id)
    # 1. Salva su Redis (Render)
    if r:
        try:
            r.sadd("lista_gruppi", chat_id)
            logging.info(f"REGISTRAZIONE: Gruppo {chat_id} salvato su Redis.")
        except Exception as e:
            logging.error(f"Errore Redis: {e}")
    
    # 2. Salva sempre anche su file (per backup locale)
    try:
        if not os.path.exists(GRUPPI_FILE):
            open(GRUPPI_FILE, "w").close()
        with open(GRUPPI_FILE, "r") as f:
            gruppi = f.read().splitlines()
        if chat_id not in gruppi:
            with open(GRUPPI_FILE, "a") as f:
                f.write(chat_id + "\n")
            logging.info(f"REGISTRAZIONE: Gruppo {chat_id} salvato su file locale.")
    except Exception as e:
        logging.error(f"Errore file locale: {e}")

def get_lista_gruppi():
    """Recupera la lista da Redis o File. Il canale principale è sempre incluso."""
    lista = [config.CHAT_ID] # Canale ufficiale Leonia+
    
    # Recupera da Redis
    if r:
        try:
            gruppi_redis = r.smembers("lista_gruppi")
            lista.extend(list(gruppi_redis))
        except Exception as e:
            logging.error(f"Errore recupero Redis: {e}")
            
    # Recupera da File (se esiste)
    if os.path.exists(GRUPPI_FILE):
        try:
            with open(GRUPPI_FILE, "r") as f:
                lista.extend([g.strip() for g in f.read().splitlines() if g.strip()])
        except Exception as e:
            logging.error(f"Errore recupero file: {e}")

    # Rimuove duplicati e pulisce spazi
    return list(dict.fromkeys(lista))

def send_message_to_all(text):
    """Invia il report a tutti i destinatari registrati."""
    destinatari = get_lista_gruppi()
    num = len(destinatari)
    
    # Anti-spam: se più di 20 gruppi, aspetta 1.1s, altrimenti 0.2s
    attesa = 1.1 if num > 20 else 0.2
    
    logging.info(f"INVIO MULTIPLO: Inizio invio a {num} chat...")
    
    for i, chat_id in enumerate(destinatari):
        send_message(text, target_chat=chat_id)
        if i < num - 1:
            time.sleep(attesa)
    return True

def send_audio_to_all(audio_path, caption):
    """Invia il file audio a tutti i gruppi registrati."""
    groups = r.smembers("telegram_groups")
    success = True
    
    for group_id in groups:
        try:
            url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendAudio"
            with open(audio_path, 'rb') as audio:
                files = {'audio': audio}
                data = {
                    'chat_id': group_id, 
                    'caption': caption, 
                    'parse_mode': 'HTML'
                }
                requests.post(url, files=files, data=data)
        except Exception as e:
            logging.error(f"Errore invio audio a {group_id}: {e}")
            success = False
    return success

def send_message(text, target_chat=None):
    """Invia a una singola chat con gestione HTML e messaggi lunghi."""
    if not text: return False
    chat_id = target_chat if target_chat else config.CHAT_ID
    url = f"https://api.telegram.org/bot{config.TOKEN}/sendMessage"
    MAX_LENGTH = 3900

    if len(text) <= MAX_LENGTH:
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        try:
            res = requests.post(url, json=payload, timeout=25)
            if res.status_code == 429: # Flood limit
                wait = res.json().get('parameters', {}).get('retry_after', 5)
                time.sleep(wait)
                res = requests.post(url, json=payload, timeout=25)
            
            if res.status_code != 200:
                # Fallback testo semplice
                payload.pop("parse_mode")
                res = requests.post(url, json=payload, timeout=25)
            return res.status_code == 200
        except Exception as e:
            logging.error(f"Errore invio a {chat_id}: {e}")
            return False
    else:
        # Messaggio lungo: divide e invia senza HTML per sicurezza
        parts = [text[i:i+MAX_LENGTH] for i in range(0, len(text), MAX_LENGTH)]
        for idx, part in enumerate(parts):
            p_load = {"chat_id": chat_id, "text": f"({idx+1}/{len(parts)})\n\n{part}"}
            requests.post(url, json=p_load, timeout=25)
            time.sleep(1)
        return True