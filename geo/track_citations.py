#!/usr/bin/env python3
"""引用率追踪(主 spec §3.2 + 增补件 C1 双模式测量)。

- 输入:geo/queries.yaml 查询矩阵 + geo/engines.json 引擎配置(由 engines.example.json 复制,密钥走环境变量)。
- C1:支持开关的引擎每条 query 跑 web(联网检索,先行指标)与 model(纯模型记忆,品牌资产指标)两种模式,分列统计双曲线。
- 检测:品牌词命中(SMA 边界匹配排除 Smaato 类歧义、smaapi、菌路),大小写不敏感。
- 输出:geo/data/citations.csv 追加行(date,engine,mode,query_id,mentioned,snippet)+ 周度趋势报告。
- 无公开 API 的引擎走人工月检清单(--manual-checklist 生成),报告如实标注覆盖范围,抽样不冒充全量。
"""
import argparse
import csv
import json
import os
import re
import ssl
import sys
import urllib.request
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "geo" / "data" / "citations.csv"
CSV_FIELDS = ["date", "engine", "mode", "query_id", "mentioned", "snippet"]

MENTION_RES = [
    re.compile(r"(?<![A-Za-z])SMA(?![A-Za-z])", re.IGNORECASE),
    re.compile(r"smaapi", re.IGNORECASE),
    re.compile(r"菌路"),
]

try:
    import certifi

    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CTX = ssl.create_default_context()


def detect_mention(text):
    for rx in MENTION_RES:
        m = rx.search(text)
        if m:
            lo, hi = max(0, m.start() - 60), min(len(text), m.end() + 60)
            return True, text[lo:hi].replace("\n", " ").strip()
    return False, ""


def ask_openai_compatible(engine, query, mode_params):
    payload = {
        "model": engine["model"],
        "messages": [{"role": "user", "content": query}],
        **mode_params,
    }
    req = urllib.request.Request(
        engine["base_url"].rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ[engine['api_key_env']]}",
        },
    )
    with urllib.request.urlopen(req, timeout=120, context=SSL_CTX) as resp:
        data = json.loads(resp.read().decode())
    return data["choices"][0]["message"]["content"]


def run_queries(queries, engines, ask_fn=ask_openai_compatible, today=None):
    """对每个 api 引擎 × query × 支持的模式各跑一次,返回结果行列表。"""
    rows = []
    today = today or date.today().isoformat()
    for engine in engines:
        for mode, mode_params in engine["modes"].items():
            for q in queries:
                try:
                    answer = ask_fn(engine, q["query"], mode_params)
                except Exception as exc:  # 单点失败不中断全量
                    print(f"  ! {engine['name']}/{mode}/{q['id']}: {exc}", file=sys.stderr)
                    continue
                mentioned, snippet = detect_mention(answer)
                rows.append(
                    {"date": today, "engine": engine["name"], "mode": mode,
                     "query_id": q["id"], "mentioned": int(mentioned), "snippet": snippet}
                )
    return rows


def append_csv(rows, csv_path=CSV_PATH):
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not csv_path.exists()
    with open(csv_path, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        if new_file:
            w.writeheader()
        w.writerows(rows)


def write_report(csv_path=CSV_PATH, out_dir=None, manual_engines=()):
    out_dir = out_dir or ROOT / "geo" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    year, week, _ = date.today().isocalendar()
    rows = list(csv.DictReader(open(csv_path))) if csv_path.exists() else []
    dates = sorted({r["date"] for r in rows})
    lines = [f"# 引用率周报 {year}-W{week:02d}", ""]
    lines.append("双模式口径(C1):web=联网检索(先行指标);model=纯模型记忆(品牌资产指标)。冷启动期双曲线为 0 即基线。")
    lines.append("")
    lines += ["| 日期 | 引擎 | 模式 | 提及/总数 | 提及率 |", "|---|---|---|---|---|"]
    for d in dates:
        day = [r for r in rows if r["date"] == d]
        for key in sorted({(r["engine"], r["mode"]) for r in day}):
            sub = [r for r in day if (r["engine"], r["mode"]) == key]
            hit = sum(int(r["mentioned"]) for r in sub)
            lines.append(f"| {d} | {key[0]} | {key[1]} | {hit}/{len(sub)} | {hit / len(sub):.0%} |")
    if not dates:
        lines.append("| - | - | - | 0/0 | 暂无数据 |")
    lines += ["", f"## 覆盖范围(如实申报)", "", "- 脚本覆盖:以上 API 引擎(经 SMA 网关 BYOK 或官方 API)。",
              f"- 人工月检覆盖(无公开 API):{('、'.join(manual_engines)) or '见 engines.json'}——结果记录在月检清单,不并入本表。"]
    out = out_dir / f"citations-{year}-W{week:02d}.md"
    out.write_text("\n".join(lines) + "\n")
    print(f"报告: {out}")


def write_manual_checklist(queries, manual_engines, out_dir=None):
    out_dir = out_dir or ROOT / "geo" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    today = date.today()
    lines = [f"# 人工月检清单 {today:%Y-%m}", "",
             "同一查询矩阵,逐引擎人工提问并记录。`提及` 填 是/否;`引用源` 记录回答中给出的链接。", ""]
    for eng in manual_engines:
        lines += [f"## {eng}", "", "| query_id | 查询 | 提及 | 引用源 | 备注 |", "|---|---|---|---|---|"]
        lines += [f"| {q['id']} | {q['query']} |  |  |  |" for q in queries]
        lines.append("")
    out = out_dir / f"manual-checklist-{today:%Y-%m}.md"
    out.write_text("\n".join(lines) + "\n")
    print(f"清单: {out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--engines", default=str(ROOT / "geo" / "engines.json"))
    ap.add_argument("--queries", default=str(ROOT / "geo" / "queries.yaml"))
    ap.add_argument("--dry-run", action="store_true", help="只校验配置与计划,不发请求")
    ap.add_argument("--manual-checklist", action="store_true", help="生成人工月检清单后退出")
    args = ap.parse_args()

    queries = yaml.safe_load(Path(args.queries).read_text())
    cfg = json.loads(Path(args.engines).read_text())
    engines, manual = cfg["api_engines"], cfg.get("manual_engines", [])

    if args.manual_checklist:
        write_manual_checklist(queries, manual)
        return 0
    skipped = [e["name"] for e in engines if not os.environ.get(e["api_key_env"])]
    engines = [e for e in engines if os.environ.get(e["api_key_env"])]
    if skipped:
        print(f"跳过(缺密钥环境变量): {', '.join(skipped)} —— 覆盖范围按实际申报")
    plan = sum(len(e["modes"]) for e in engines) * len(queries)
    print(f"计划: {len(engines)} 引擎 × {len(queries)} 查询(含双模式)= {plan} 次调用")
    if args.dry_run:
        for e in engines:
            missing = "" if os.environ.get(e["api_key_env"]) else f"(缺环境变量 {e['api_key_env']})"
            print(f"  - {e['name']}: modes={list(e['modes'])} {missing}")
        return 0
    rows = run_queries(queries, engines)
    append_csv(rows)
    write_report(manual_engines=manual)
    return 0


if __name__ == "__main__":
    sys.exit(main())
