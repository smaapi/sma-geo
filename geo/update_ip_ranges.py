#!/usr/bin/env python3
"""拉取各厂商官方公布的爬虫 IP 段,vendor 进 geo/data/ip-ranges/(增补件 C2)。

数据组织方式参考 CrawlerScope:每 bot 一份 JSON + manifest 溯源。
更新流程:重跑本脚本 → diff 审查 → commit。无官方段的 bot 不在此列,监测时归"仅 UA 匹配"档。
"""
import json
import ssl
import urllib.request
from datetime import date
from pathlib import Path

try:
    import certifi

    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CTX = ssl.create_default_context()

SOURCES = {
    "GPTBot": "https://openai.com/gptbot.json",
    "OAI-SearchBot": "https://openai.com/searchbot.json",
    "ChatGPT-User": "https://openai.com/chatgpt-user.json",
    "PerplexityBot": "https://www.perplexity.ai/perplexitybot.json",
    "Perplexity-User": "https://www.perplexity.ai/perplexity-user.json",
}

OUT_DIR = Path(__file__).resolve().parent / "data" / "ip-ranges"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for bot, url in SOURCES.items():
        req = urllib.request.Request(url, headers={"User-Agent": "sma-geo-ip-range-updater"})
        with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        prefixes = [p.get("ipv4Prefix") or p.get("ipv6Prefix") for p in data.get("prefixes", [])]
        prefixes = [p for p in prefixes if p]
        out = OUT_DIR / f"{bot}.json"
        out.write_text(json.dumps({"bot": bot, "source": url, "prefixes": prefixes}, indent=2) + "\n")
        manifest[bot] = {"file": out.name, "source": url, "prefixCount": len(prefixes), "fetched": date.today().isoformat()}
        print(f"{bot}: {len(prefixes)} prefixes")
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
