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

def send_message(text, target_chat=None):
    if not text: return False
    full_id = str(target_chat if target_chat else config.CHAT_ID)
    
    # Gestione Topic: separa l'ID dal Topic ID se presente (es. -100123:555)
    thread_id = None
    if ":" in full_id:
        chat_id, thread_id = full_id.split(":")
    else:
        chat_id = full_id

    url = f"https://api.telegram.org/bot{config.TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": text, 
        "parse_mode": "HTML",
        "message_thread_id": thread_id  # Telegram lo ignora se è None
    }
    
    try:
        res = requests.post(url, json=payload, timeout=25)
        return res.status_code == 200
    except Exception as e:
        logging.error(f"Errore invio testo a {chat_id}: {e}")
        return False

def send_audio_to_all(audio_path, caption):
    destinatari = get_lista_gruppi()
    url = f"https://api.telegram.org/bot{config.TOKEN}/sendAudio"
    
    for full_id in destinatari:
        # Logica Topic anche per l'audio
        thread_id = None
        if ":" in str(full_id):
            chat_id, thread_id = str(full_id).split(":")
        else:
            chat_id = full_id

        try:
            with open(audio_path, 'rb') as audio:
                files = {'audio': audio}
                data = {
                    'chat_id': chat_id, 
                    'caption': caption, 
                    'parse_mode': 'HTML',
                    'message_thread_id': thread_id
                }
                requests.post(url, files=files, data=data, timeout=120)
                logging.info(f"Audio inviato a {chat_id} (Topic: {thread_id})")
        except Exception as e:
            logging.error(f"Errore audio a {chat_id}: {e}")