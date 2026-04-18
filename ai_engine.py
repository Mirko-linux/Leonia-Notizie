import requests
import json
import config
from telegraph import Telegraph

# --- LISTE MODELLI ---
MODELLI_NORMAL = [
    "openai/gpt-oss-120b:free",
    "openai/gpt-oss-20b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nvidia/nemotron-3-nano-30b-a3b:free"
]

MODELLI_APPROFONDIMENTO = [
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nvidia/nemotron-3-nano-30b-a3b:free", 
    "openai/gpt-oss-120b:free",
    "openai/gpt-oss-20b:free"
]

def crea_pagina_telegraph(titolo, contenuto_html):
    try:
        telegraph = Telegraph()
        telegraph.create_account(short_name='LeoniaPlus')
        response = telegraph.create_page(
            title=titolo,
            html_content=contenuto_html.replace('\n', '<br>'),
            author_name="Leonia+ Notizie",
            author_url="https://t.me/leonia_plus_notizie"
        )
        return response['url']
    except Exception as e:
        print(f"Errore Telegra.ph: {e}")
        return None

def genera_testo(dati_raw, is_special=False):
    lista_modelli = MODELLI_APPROFONDIMENTO if is_special else MODELLI_NORMAL
    
    # --- COSTRUZIONE PROMPT ---
    if is_special:
        prompt = f"""
        AGISCI COME UN CAPOREDATORE GIORNALISTICO DI ALTO LIVELLO.
        Analizza questi dati: {dati_raw}
        
        COMPITO:
        1. Scegli la notizia più importante.
        2. Scrivi un editoriale approfondito (minimo 300 parole).
        3. Valuta la rilevanza globale con le stelle: ⭐⭐⭐⭐⭐.
        
        Sii analitico e serio. Non inventare fatti.
        """
    else:
        prompt = f"""
        AGISCI COME UN GIORNALISTA PROFESSIONISTA.
        Dati: {dati_raw}
        
        REGOLE TASSATIVE DI FORMATTAZIONE:
        1. Seleziona le 5 notizie più importanti.
        2. Per ogni notizia usa ESATTAMENTE questo schema:
        
        <b>TITOLO IN MAIUSCOLO</b>
        [Testo del riassunto: 3 frasi chiare, separate e ben spaziate.]
        
        🔗 Fonte: [URL]
        Valutazione: ⭐⭐⭐ (Scegli da 1 a 5 stelle)
        ---
        
        3. SPAZIATURA: Lascia SEMPRE una riga vuota tra il titolo <b> e il testo del riassunto.
        4. NO EMOJI: Non usare emoji nel testo, usa SOLO le stelle ⭐ nella riga valutazione.
        5. NO PAROLE ATTACCATE: Controlla bene che i nomi propri e i verbi siano separati da spazi.
        """

    headers = {
        "Authorization": f"Bearer {config.AI_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/MirkoDonato/LeoniaPlus",
    }

    # --- CICLO DI FALLBACK CON TIMEOUT 90s ---
    for modello in lista_modelli:
        data = {
            "model": modello,
            "messages": [
                {"role": "system", "content": "Sei un giornalista esperto. Scrivi in italiano perfetto, rispetta gli spazi tra le parole e usa correttamente i tag HTML <b>."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.4 # Più bassa per evitare "allucinazioni" di formattazione
        }
        
        try:
            print(f"Tentativo con modello: {modello}...")
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                data=json.dumps(data),
                timeout=90 # Impostato a 90 secondi come richiesto
            )
            
            if response.status_code == 200:
                risultato = response.json()
                testo = risultato['choices'][0]['message']['content']
                print(f"Successo con {modello}!")
                return testo, modello 
            else:
                print(f"Modello {modello} errore {response.status_code}. Prossimo...")
                continue
                
        except Exception as e:
            print(f"Errore tecnico con {modello}: {e}")
            continue
            
    return None, None