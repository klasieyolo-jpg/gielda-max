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
        return json.loads(x.read().decode())


try:
    cat = req("https://models.github.ai/catalog/models")
    ids = [m["id"] for m in cat]
    print("KATALOG:", ", ".join(i for i in ids if i.startswith("openai/")))
except urllib.error.HTTPError as e:
    print("KATALOG BŁĄD", e.code, e.read().decode()[:300])
    ids = []
for m in [i for i in ids if i.startswith("openai/")][:12] or ["openai/gpt-4.1-mini", "openai/gpt-4o-mini"]:
    try:
        out = req("https://models.github.ai/inference/chat/completions",
                  {"model": m, "messages": [{"role": "user", "content": "Odpowiedz jednym słowem: OK"}]})
        print("OK  ", m, out["choices"][0]["message"]["content"][:20])
    except urllib.error.HTTPError as e:
        print("FAIL", m, e.code, e.read().decode()[:200])
