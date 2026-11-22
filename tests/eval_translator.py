"""Script de evaluación y benchmark de latencia para translator.py (skill: eval-wow-translator)."""

from __future__ import annotations

from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.translator import WoWTranslator


def run_evaluation() -> int:
    translator = WoWTranslator()
    time.sleep(0.6)  # Permite que el hilo de warmup precargue los modelos locales en segundo plano
    if translator.provider == "local":
        mode = f"Local Offline ({translator.model})"
    elif translator._client is not None:
        mode = f"Gemini API (live | {translator.model})"
    else:
        mode = "Fallback Offline / Glosario"
    print(f"=== Evaluación de WoWTranslator ({mode}) ===\n")

    incoming_tests = [
        "is that it myu %^&* bugge dwhen i DCs",
        "wait sec, healer oom, dont pull",
        "mb, fat fingered blink",
    ]
    outgoing_tests = [
        "esperen un poco que estoy sin mana",
        "me pegó un lagazo terrible, perdón",
        "¿alguien necesita este ítem o le doy codicia?",
    ]

    latencies: list[float] = []
    failures = 0

    print("--- Pruebas EN -> ES (Entrada) ---")
    for text in incoming_tests:
        start = time.perf_counter()
        result = translator.translate_incoming(text)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        latencies.append(elapsed_ms)
        has_bad_format = "\n" in result or (
            result.startswith('"') and result.endswith('"')
        )
        status = "PASS" if (elapsed_ms < 700.0 and not has_bad_format) else "FAIL"
        if status == "FAIL":
            failures += 1
        print(f"[{status}] ({elapsed_ms:6.1f} ms) {text!r}\n       -> {result!r}")

    print("\n--- Pruebas ES -> EN (Salida) ---")
    for text in outgoing_tests:
        start = time.perf_counter()
        result = translator.translate_outgoing(text)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        latencies.append(elapsed_ms)
        has_bad_format = "\n" in result or (
            result.startswith('"') and result.endswith('"')
        )
        status = "PASS" if (elapsed_ms < 700.0 and not has_bad_format) else "FAIL"
        if status == "FAIL":
            failures += 1
        print(f"[{status}] ({elapsed_ms:6.1f} ms) {text!r}\n       -> {result!r}")

    avg_ms = sum(latencies) / len(latencies) if latencies else 0.0
    print(f"\nLatencia promedio: {avg_ms:.2f} ms (Objetivo < 600 ms)")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(run_evaluation())
