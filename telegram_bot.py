import requests
import config
import logging
import time
import os
import redis # Assicurati che sia nel requirements.txt
import re

# --- CONFIGURAZIONE DATABASE REDIS ---
REDIS_URL = os.getenv("REDIS_URL")
CHIAVE_REDIS_GRUPPI = "lista_gruppi"

# Inizializzazione globale di 'r'
r = None

if REDIS_URL:
    try:
        # Configurazione corretta per Redis 8.0.0 (rimosso ssl_cert_reqs che causava il crash)
        r = redis.from_url(
            REDIS_URL, 
            decode_responses=True,
            retry_on_timeout=True,
            socket_connect_timeout=15,
            socket_keepalive=True
        )
        # Test di connessione immediato
        r.ping()
        logging.info("DATABASE: Collegato a Redis con successo.")
    except Exception as e:
        logging.error(f"DATABASE: Errore connessione Redis: {e}")
        r = None 

# --- GESTIONE DESTINATARI ---

def get_lista_gruppi():
    """Recupera la lista unica da Variabili d'ambiente e Canale principale."""
    lista = [str(config.CHAT_ID)] 
    
    gruppi_env = os.getenv("GRUPPI_ID")
    if gruppi_env:
        ids_da_env = [g.strip() for g in gruppi_env.split(",") if g.strip()]
        lista.extend(ids_da_env)
        logging.info(f"CONFIG: Caricati {len(ids_da_env)} gruppi da Environment.")

    if r:
        try:
            gruppi_redis = r.smembers(CHIAVE_REDIS_GRUPPI)
            lista.extend(list(gruppi_redis))
        except:
            pass

    return list(dict.fromkeys(lista))

# --- FUNZIONI DI INVIO E FISSAGGIO ---

def pin_message(chat_id, message_id):
    """Fissa un messaggio specifico in una chat o canale."""
    url = f"https://api.telegram.org/bot{config.TOKEN}/pinChatMessage"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "disable_notification": True  # Fissa in modo silenzioso per non spammare
    }
    try:
        res = requests.post(url, json=payload, timeout=15)
        if res.status_code == 200:
            logging.info(f"FISSATO: Messaggio {message_id} fissato con successo nella chat {chat_id}")
            return True
        else:
            logging.warning(f"FISSATO: Impossibile fissare il messaggio nella chat {chat_id}. Risposta: {res.text}")
            return False
    except Exception as e:
        logging.error(f"Errore durante il fissaggio del messaggio in {chat_id}: {e}")
        return False

def send_message(text, target_chat=None):
    """Invia a una singola chat gestendo i Topic. Ritorna il message_id se ha successo."""
    if not text: return None
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
        if res.status_code == 200:
            data = res.json()
            # Estraiamo l'ID del messaggio appena inviato
            return data.get("result", {}).get("message_id")
        return None
    except Exception as e:
        logging.error(f"Errore invio testo a {chat_id}: {e}")
        return None

def send_message_to_all(text):
    """Invia il notiziario a tutti e fissa automaticamente l'articolo."""
    destinatari = get_lista_gruppi()
    logging.info(f"INVIO: Inizio distribuzione e fissaggio a {len(destinatari)} chat.")
    
    for full_id in destinatari:
        # 1. Invia il messaggio e ottieni il suo ID
        message_id = send_message(text, target_chat=full_id)
        
        # 2. Se l'invio ha avuto successo, lo fissa in alto
        if message_id:
            # Estrae il chat_id pulito senza l'id del topic (perché pinChatMessage vuole solo l'ID della chat)
            chat_id = full_id.split(":")[0] if ":" in str(full_id) else full_id
            pin_message(chat_id, message_id)
            
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