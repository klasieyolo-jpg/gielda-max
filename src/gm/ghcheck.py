"""Sprawdza GitHub Models (darmowe GPT) z tokenem Actions."""
import json
import os
import urllib.error
import urllib.request

H = {"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}", "Content-Type": "application/json",
     "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}


def req(url, body=None):
    r = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, headers=H)
    with urllib.request.urlopen(r, timeout=60) as x:
        raw = x.read().decode(errors="replace")
        print("  HTTP", x.status, x.url, "|", raw[:300].replace("\n", " "))
        return json.loads(raw)


try:
    cat = req("https://models.github.ai/catalog/models")
    print("KATALOG TYP:", type(cat).__name__, str(cat)[:200])
    lst = cat if isinstance(cat, list) else cat.get("models", cat.get("data", []))
    ids = [m.get("id", m.get("name", "")) for m in lst]
    print("KATALOG:", ", ".join(i for i in ids if i.startswith("openai/")))
except Exception as e:  # noqa: BLE001
    body = e.read().decode()[:300] if hasattr(e, "read") else ""
    print("KATALOG BŁĄD", repr(e)[:200], body)
    ids = []
for m in [i for i in ids if i.startswith("openai/")][:12] or ["openai/gpt-4.1-mini", "openai/gpt-4o-mini"]:
    try:
        out = req("https://models.github.ai/inference/chat/completions",
                  {"model": m, "messages": [{"role": "user", "content": "Odpowiedz jednym słowem: OK"}]})
        print("OK  ", m, out["choices"][0]["message"]["content"][:20])
    except Exception as e:  # noqa: BLE001
        body = e.read().decode()[:200] if hasattr(e, "read") else ""
        print("FAIL", m, repr(e)[:150], body)
