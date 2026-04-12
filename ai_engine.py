import requests
import json
import config
from telegraph import Telegraph

# --- LISTE MODELLI SCELTE DA TE ---
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
        
        # Creazione della pagina
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
    """
    Genera il testo del notiziario o dell'approfondimento.
    Ritorna una tupla: (testo_generato, nome_modello_usato)
    """
    lista_modelli = MODELLI_APPROFONDIMENTO if is_special else MODELLI_NORMAL
    
    # --- COSTRUZIONE PROMPT DETTAGLIATO ---
    if is_special:
        prompt = f"""
        AGISCI COME UN CAPOREDATORE GIORNALISTICO DI ALTO LIVELLO.
        Analizza questi dati: {dati_raw}
        
        COMPITO:
        1. Scegli la notizia più importante tra quelle fornite.
        2. Scrivi un editoriale approfondito (minimo 300 parole).
        3. Stile: Professionale, impeccabile, senza errori grammaticali o di battitura.
        4. Includi in fondo al testo il link della fonte originale trovato nei dati.
        5. Valuta la rilevanza globale della notizia con un punteggio da ⭐ a ⭐⭐⭐⭐⭐.
        
        Sii analitico e serio. Non inventare fatti non presenti nei dati.
        """
    else:
        prompt = f"""
        AGISCI COME UN GIORNALISTA DI UN TELEGIORNALE NAZIONALE.
        Dati forniti: {dati_raw}
        
        REGOLE RIGIDE:
        1. Seleziona le 5 notizie più rilevanti.
        2. Per ogni notizia scrivi un riassunto esauriente e dettagliato (almeno 4-5 frasi).
        3. Sii preciso: non confondere luoghi, nomi o date. Controlla la coerenza tra titolo e contenuto.
        4. "NON usare emoji nel testo, AD ECCEZIONE delle stelle (⭐) per la valutazione finale di ogni notizia.".
        5. Inserisci il link alla fonte originale (presente nei dati) alla fine di ogni paragrafo della notizia.
        6. Aggiungi un punteggio di rilevanza da ⭐ a ⭐⭐⭐⭐⭐ per ogni notizia.
        7. Sii estremamente sintetico. Riassumi ogni notizia in massimo 3 o 4 frasi brevi e incisive. Non superare i 2500 caratteri totali per l'intero messaggio
        8. Non inventare informazioni non presenti nei dati, ma sii dettagliato e completo con ciò che hai.
        9. Usa lo stile HTML invece del Markdown per garantire compatibilità con Telegram e mantenere la formattazione.
        
        FORMATO RICHIESTO PER OGNI NOTIZIA:
        [TITOLO IN GRASSETTO]
        [Testo del riassunto lungo e dettagliato...]
        🔗 Fonte: [Link]
        Valutazione: [Stelle]
        ---
        """

    headers = {
        "Authorization": f"Bearer {config.AI_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/MirkoDonato/LeoniaPlus",
    }

    # --- CICLO DI FALLBACK ---
    for modello in lista_modelli:
        data = {
            "model": modello,
            "messages": [
                {"role": "system", "content": "Sei un giornalista esperto, preciso e impeccabile."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.5 # Media per bilanciare creatività e precisione
        }
        
        try:
            print(f"Tentativo con modello: {modello}...")
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                data=json.dumps(data),
                timeout=60 # Aumentato a 60 per editoriali lunghi
            )
            
            if response.status_code == 200:
                risultato = response.json()
                testo = risultato['choices'][0]['message']['content']
                print(f"Successo con {modello}!")
                return testo, modello 
            else:
                print(f"Modello {modello} non disponibile (Errore {response.status_code}).")
                continue
                
        except Exception as e:
            print(f"Errore tecnico con {modello}: {e}")
            continue
            
    return None, None # Se falliscono tutti