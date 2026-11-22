"""Sprawdza, które modele Gemini działają na darmowym kluczu (krótkie zapytanie testowe)."""
import json
import os
import time
import urllib.error

from .llm import API, _err_text, _req


def main():
    key = os.environ["GEMINI_API_KEY"]
    models = _req(f"{API}/models?pageSize=200", key).get("models", [])
    names = sorted(m["name"] for m in models if "generateContent" in m.get("supportedGenerationMethods", []))
    print("Dostępne:", ", ".join(n.split("/")[-1] for n in names))
    cands = [n for n in names if ("pro" in n or "flash" in n) and not any(
        x in n for x in ("image", "tts", "audio", "live", "embed", "learnlm", "nano", "computer"))]
    body = {"contents": [{"role": "user", "parts": [{"text": "Odpowiedz jednym słowem: OK"}]}]}
    for n in cands:
        t0 = time.time()
        try:
            out = _req(f"{API}/{n}:generateContent", key, body, timeout=60)
            txt = out["candidates"][0]["content"]["parts"][0]["text"].strip()[:20]
            print(f"OK   {n.split('/')[-1]}  {time.time() - t0:.1f}s  -> {txt}")
        except urllib.error.HTTPError as e:
            print(f"FAIL {n.split('/')[-1]}  {_err_text(e)}")
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {n.split('/')[-1]}  {str(e)[:100]}")
        time.sleep(2)


if __name__ == "__main__":
    main()
