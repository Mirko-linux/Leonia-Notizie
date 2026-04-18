# Leonia+ Noticias

**Leonia+ Noticias** es un bot de Telegram de código abierto que, basado en inteligencia artificial generativa, resume 5 noticias de 5 fuentes autorizadas (ANSA, TGcom24, etc.) en italiano.

--
[🇮🇹 Volver al Italiano](../README.md)
--

## Funcionalidades

* **Agregación de múltiples fuentes**: Recupera noticias en tiempo real de diferentes fuentes mediante web scraping ético.

* **Impulsado por IA**: Utiliza modelos avanzados, a través del servicio Openrouter.com, para resumir las noticias.

* **Base de datos Redis**: Gestión de grupos registrados mediante una base de datos clave-valor para una máxima persistencia.

* **Horario de funcionamiento**: Activo solo durante el día (de 6:00 a 18:00, hora de Roma).

* **Editoriales vespertinos**: A las 18:00, genera un artículo en profundidad seleccionado por la IA y lo publica a través del servicio Telegra.ph.
* **Servicio de ping integrado**: Servidor interno de Flask para la vinculación de puertos a Render.

## Advertencias

Nuestro proyecto está dirigido por un desarrollador independiente de tan solo 17 años, por lo que es posible que encuentre errores, fallos o imprecisiones. En tales casos, le recomendamos enviar una solicitud de extracción, que será revisada lo antes posible.