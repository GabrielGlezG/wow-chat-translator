---
name: eval-wow-translator
description: Evalúa y calibra el motor de traducción local offline (MarianMT / CTranslate2 int8) para mensajes de World of Warcraft (EN->ES y ES->EN), validando latencia ultra baja (<50ms), enmascarado de hipervínculos, jerga gamer y formato limpio sin comillas ni explicaciones.
---

# Evaluador de Traductor Gamer Local (WoW)

## Objetivo
Garantizar que `src/translator.py` traduzca en tiempo real de forma 100% offline mediante CTranslate2 con latencia menor a 60ms, interpretando la jerga de WoW y preservando los códigos de color e ítems del cliente.

## Instrucciones

1. Ejecuta la batería de pruebas de evaluación contra `WoWTranslator`:
   - `python tests/eval_translator.py`
   - O mediante pytest: `pytest tests/test_pipeline.py`
2. Casos de prueba requeridos:
   - **EN -> ES (Entrada):**
     - `"is that it myu %^&* bugge dwhen i DCs"` -> Debe interpretar la desconexión (`DC`) y el bug, sin traducción rota literal.
     - `"wait sec, healer oom, dont pull"` -> Debe reconocer `oom` (sin maná) y `pull` (pulear).
     - `"mb, fat fingered blink"` -> `"mala mía, apreté traslación/blink por error"`.
     - Links de ítems y marcas: `"focus {skull} on |cffa335ee|Hitem:19019...|h[Thunderfury]|h|r"` -> Debe preservar los tokens de WoW intactos.
   - **ES -> EN (Salida):**
     - `"esperen un poco que estoy sin mana"` -> `"wait a sec, oom"`.
     - `"me pegó un lagazo terrible, perdón"` -> `"sorry, huge lag spike"`.
     - `"¿alguien necesita este ítem o le doy codicia?"` -> `"anyone need this or greed?"`.
3. Verificaciones de calidad:
   - **Latencia:** Menor a 60ms en CPU promedio.
   - **Formato:** Salida en una sola línea, sin comillas envolventes innecesarias, sin notas ni explicaciones.
   - **100% Offline:** Inferencia local sin dependencias de red ni llamadas a APIs externas.
