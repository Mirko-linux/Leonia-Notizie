# Leonia+ Notizie

**Leonia+ Notizie** è un bot telegram open source che, basandosi su intelligenza artificiale generativa, riassume 5 notizie desunte  da 5 fonti autorevoli (ANSA, TGcom24...) in lingua italiana.

---

### Lingue disponibili / Available Languages
Selezione la tua lingua per leggere la documentazione:

| Lingua | Bandiera | Documento |
| :--- | :---: | :--- |
| **Italiano** | 🇮🇹 | *Sei già qui* |
| **English** | 🇬🇧 | [Read in English](./docs/README_EN.md) |
| **Español** | 🇪🇸 | [Leer en Español](./docs/README_ES.md) |
| **Français** | 🇫🇷 | [Lire en Français](./docs/README_FR.md) |
| **Deutsch** | 🇩🇪 | [Auf Deutsch lesen](./docs/README_DE.md) |

---

## Caratteristiche 

* **Aggregazione di diverse fonti**: Recupera notizie in tempo reale da diverse fonti tramite web scraping etico.
* **Powered by AI**: Utilizza modelli avanzati, tramite il servizio Openrouter.com, per riassumere le notizie.
* **Database Redis**: Gestione dei gruppi registrati tramite database Key-Value per la massima persistenza.
* **Fascia Operativa**: è attivo solo nella fase giornaliera (dalle 6:00 alle 18:00, secondo il fuso orario di Roma).
* **Editoriali Serali**: Alle 18:00 genera un approfondimento a scelta dall'AI e lo pubblica usando il servizio Telegra.ph.
* **Servizio di ping integrato**: Server Flask interno per il port-binding su Render.

## Avvertenze

Il nostro progetto è portato avanti da uno sviluppatore indipendente di soli 17 anni, di conseguenza errori, bug e qualche imprecisione potrebbero non essere rari. In tal caso si consiglia di effettuare una pull request che verrà esaminata il più presto possibile