import requests
import config
import logging
import time
import os
import redis

# --- CONFIGURAZIONE DATABASE ---
GRUPPI_FILE = "gruppi.txt"
REDIS_URL = os.getenv("REDIS_URL")
CHIAVE_REDIS = "lista_gruppi" # Nome unico per la tabella dei gruppi

r = None
if REDIS_URL:
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        logging.info("DATABASE: Collegato a Redis (Modalità Render)")
    except Exception as e:
        logging.error(f"DATABASE: Errore connessione Redis: {e}")

def registra_gruppo(chat_id):
    """Salva l'ID su Redis e su file locale."""
    chat_id = str(chat_id)
    if r:
        try:
            r.sadd(CHIAVE_REDIS, chat_id)
            logging.info(f"REGISTRAZIONE: Gruppo {chat_id} salvato su Redis.")
        except Exception as e:
            logging.error(f"Errore Redis: {e}")
    
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
    """Recupera la lista unica da Redis e File."""
    lista = [str(config.CHAT_ID)] # Canale ufficiale
    
    if r:
        try:
            gruppi_redis = r.smembers(CHIAVE_REDIS)
            lista.extend(list(gruppi_redis))
        except Exception as e:
            logging.error(f"Errore recupero Redis: {e}")
            
    if os.path.exists(GRUPPI_FILE):
        try:
            with open(GRUPPI_FILE, "r") as f:
                lista.extend([g.strip() for g in f.read().splitlines() if g.strip()])
        except Exception as e:
            logging.error(f"Errore recupero file: {e}")

    return list(dict.fromkeys(lista))

def send_message_to_all(text):
    """Invia il testo a tutti."""
    destinatari = get_lista_gruppi()
    for chat_id in destinatari:
        send_message(text, target_chat=chat_id)
        time.sleep(0.3) # Piccola pausa anti-flood

def send_audio_to_all(audio_path, caption):
    """Invia l'audio a tutti i gruppi usando la STESSA LISTA del testo."""
    destinatari = get_lista_gruppi()
    success = True
    
    url = f"https://api.telegram.org/bot{config.TOKEN}/sendAudio" # Usa lo stesso token
    
    for group_id in destinatari:
        try:
            with open(audio_path, 'rb') as audio:
                files = {'audio': audio}
                data = {
                    'chat_id': group_id, 
                    'caption': caption, 
                    'parse_mode': 'HTML'
                }
                res = requests.post(url, files=files, data=data, timeout=30)
                if res.status_code != 200:
                    logging.error(f"Errore API invio audio a {group_id}: {res.text}")
        except Exception as e:
            logging.error(f"Errore invio audio a {group_id}: {e}")
            success = False
    return success

def send_message(text, target_chat=None):
    """Invia a una singola chat."""
    if not text: return False
    chat_id = target_chat if target_chat else config.CHAT_ID
    url = f"https://api.telegram.org/bot{config.TOKEN}/sendMessage"
    
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        res = requests.post(url, json=payload, timeout=25)
        return res.status_code == 200
    except Exception as e:
        logging.error(f"Errore invio a {chat_id}: {e}")
        return False