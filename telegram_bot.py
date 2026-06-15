import requests
import config
import logging
import time
import os
import re

# --- CONFIGURAZIONE CANALE CASSAFORTE ---
# Recupera l'ID del canale privato usato come database storico
CANALE_LOG_ID = os.getenv("CANALE_LOG_ID")

# Variabile 'r' mantenuta a None per evitare crash se referenziata altrove
r = None

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

    return list(dict.fromkeys(lista))

# --- LOGICA DEL "CANALE CASSAFORTE" (DATABASE SU TELEGRAM) ---

def controlla_duplicato_su_telegram(url_notizia):
    """
    Legge gli ultimi 100 messaggi dal canale privato di log.
    Ritorna True se l'URL è già presente, altrimenti False.
    """
    if not CANALE_LOG_ID:
        logging.warning("CANALE CASSAFORTE: CANALE_LOG_ID non configurato. Salto il controllo duplicati.")
        return False

    url = f"https://api.telegram.org/bot{config.TOKEN}/getChatHistory"
    payload = {
        "chat_id": CANALE_LOG_ID,
        "limit": 100  # Controlla la cronologia delle ultime 100 notizie salvate
    }
    
    try:
        res = requests.post(url, json=payload, timeout=20)
        if res.status_code == 200:
            messaggi = res.json().get("result", [])
            for msg in messaggi:
                testo = msg.get("text", "")
                if url_notizia in testo:
                    return True  # Trovato! La notizia è un duplicato
        else:
            logging.error(f"CANALE CASSAFORTE: Errore getChatHistory: {res.text}")
    except Exception as e:
        logging.error(f"CANALE CASSAFORTE: Errore durante la lettura del log: {e}")
    
    return False

def salva_notizia_nel_log(url_notizia, titolo):
    """Invia l'URL e il titolo della notizia nel canale privato per tenerne traccia."""
    if not CANALE_LOG_ID:
        return False
        
    url = f"https://api.telegram.org/bot{config.TOKEN}/sendMessage"
    payload = {
        "chat_id": CANALE_LOG_ID,
        "text": f"LOG_DATA\nTitolo: {titolo}\nLink: {url_notizia}",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload, timeout=15)
        return True
    except Exception as e:
        logging.error(f"CANALE CASSAFORTE: Impossibile scrivere nel canale di log: {e}")
        return False

# --- FUNZIONI DI INVIO E FISSAGGIO ---

def pin_message(chat_id, message_id):
    """Fissa un messaggio specifico in una chat o canale."""
    url = f"https://api.telegram.org/bot{config.TOKEN}/pinChatMessage"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "disable_notification": True  # Silenzioso
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
        message_id = send_message(text, target_chat=full_id)
        if message_id:
            chat_id = full_id.split(":")[0] if ":" in str(full_id) else full_id
            pin_message(chat_id, message_id)
            
        time.sleep(0.5)
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
    """Mantenuta unicamente per retrocompatibilità moduli."""
    return False