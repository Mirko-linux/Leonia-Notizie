import requests
import config
import logging
import time
import os
import redis # Assicurati che sia nel requirements.txt
import re

# --- CONFIGURAZIONE DATABASE REDIS ---
# Su Render assicurati che la variabile si chiami REDIS_URL
REDIS_URL = os.getenv("REDIS_URL")
CHIAVE_REDIS_GRUPPI = "lista_gruppi"

# Inizializzazione globale di 'r' per evitare l'AttributeError nel main.py
r = None

if REDIS_URL:
    try:
        # Configurazione con parametri di retry e SSL per Render
        r = redis.from_url(
            REDIS_URL, 
            decode_responses=True,
            retry_on_timeout=True,
            socket_connect_timeout=15,
            socket_keepalive=True,
            ssl_cert_reqs=None # Risolve spesso il "Connection closed by server"
        )
        # Test di connessione immediato
        r.ping()
        logging.info("DATABASE: Collegato a Redis con successo.")
    except Exception as e:
        logging.error(f"DATABASE: Errore connessione Redis: {e}")
        r = None # Se fallisce, r rimane None e il main.py userà il Fallback

# --- GESTIONE DESTINATARI ---

def get_lista_gruppi():
    """Recupera la lista unica da Variabili d'ambiente e Canale principale."""
    # 1. Canale ufficiale dal file config
    lista = [str(config.CHAT_ID)] 
    
    # 2. Recupera dalla variabile d'ambiente su Render (GRUPPI_ID)
    gruppi_env = os.getenv("GRUPPI_ID")
    if gruppi_env:
        ids_da_env = [g.strip() for g in gruppi_env.split(",") if g.strip()]
        lista.extend(ids_da_env)
        logging.info(f"CONFIG: Caricati {len(ids_da_env)} gruppi da Environment.")

    # 3. Recupera gruppi salvati dinamicamente su Redis (se presente)
    if r:
        try:
            gruppi_redis = r.smembers(CHIAVE_REDIS_GRUPPI)
            lista.extend(list(gruppi_redis))
        except:
            pass

    # Rimuove duplicati (es. se lo stesso ID è in config e in env)
    return list(dict.fromkeys(lista))

# --- FUNZIONI DI INVIO ---

def send_message(text, target_chat=None):
    """Invia a una singola chat gestendo i Topic (ID:TopicID)."""
    if not text: return False
    full_id = str(target_chat if target_chat else config.CHAT_ID)
    
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
        "message_thread_id": thread_id
    }
    
    try:
        res = requests.post(url, json=payload, timeout=25)
        return res.status_code == 200
    except Exception as e:
        logging.error(f"Errore invio testo a {chat_id}: {e}")
        return False

def send_message_to_all(text):
    """Invia il notiziario a tutti i destinatari registrati."""
    destinatari = get_lista_gruppi()
    logging.info(f"INVIO: Inizio distribuzione a {len(destinatari)} chat.")
    
    for chat_id in destinatari:
        send_message(text, target_chat=chat_id)
        time.sleep(0.5) # Protezione anti-flood
    return True

def send_audio_to_all(audio_path, caption):
    """Invia il file audio a tutti i gruppi con timeout esteso per file pesanti."""
    destinatari = get_lista_gruppi()
    url = f"https://api.telegram.org/bot{config.TOKEN}/sendAudio"
    
    for full_id in destinatari:
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
                # Timeout a 120s per caricamenti lenti su Render
                res = requests.post(url, files=files, data=data, timeout=120)
                if res.status_code == 200:
                    logging.info(f"Audio inviato con successo a {chat_id}")
        except Exception as e:
            logging.error(f"Errore invio audio a {chat_id}: {e}")
    return True

def registra_gruppo(chat_id):
    """Salva un nuovo gruppo su Redis (attivato da /start)."""
    if r:
        try:
            r.sadd(CHIAVE_REDIS_GRUPPI, str(chat_id))
            logging.info(f"DATABASE: Nuovo gruppo registrato: {chat_id}")
            return True
        except:
            return False
    return False