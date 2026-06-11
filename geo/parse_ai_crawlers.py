#!/usr/bin/env python3
"""AI 爬虫访问监测(主 spec §3.1 + 增补件 C2 IP 段验真)。

输入:nginx/Caddy combined 格式访问日志(支持 glob 与 .gz)。
匹配:UA 清单 = config/robots.json(vendored)+ config/cn-bots.json,与 robots.txt 同源。
验真:对公布官方 IP 段的 bot(见 geo/data/ip-ranges/),来源 IP 落在段内记"已验真",
     否则记"仅 UA 匹配"(疑似伪装);未公布段的 bot 统一记"仅 UA 匹配(无官方段)"。
输出:geo/reports/crawlers-<YYYY>-W<WW>.md 周报 + 同名 .csv。
部署后建议 cron:每周一 `python3 geo/parse_ai_crawlers.py --logs '/var/log/caddy/*.log*'`。
"""
import argparse
import csv
import glob
import gzip
import ipaddress
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_RE = re.compile(r'^(\S+) \S+ \S+ \[([^\]]+)\] "(\S+) (\S+)[^"]*" (\d{3}) \S+ "[^"]*" "([^"]*)"')
TIME_FMT = "%d/%b/%Y:%H:%M:%S %z"
# UA 中的厂商 URL 段(如 +https://openai.com/gptbot)在匹配前剥离,防其域名误命中清单条目(REVIEW r3 D2)
UA_URL_RE = re.compile(r"\+https?://\S+")


def compile_bot_patterns(ua_list):
    """边界匹配:名称前后不得是字母数字(名称内空格/连字符按字面)。"""
    return [
        (b, re.compile(r"(?<![A-Za-z0-9])" + re.escape(b) + r"(?![A-Za-z0-9])", re.IGNORECASE))
        for b in ua_list
    ]


def load_ua_list():
    upstream = json.loads((ROOT / "config" / "robots.json").read_text())
    cn = json.loads((ROOT / "config" / "cn-bots.json").read_text())["bots"]
    cn_uas = [b["ua"] if isinstance(b, dict) else b for b in cn]
    # 大小写不敏感去重,保留上游原始大小写;排序确定化(REVIEW r3 D2)
    merged = {}
    for ua in list(upstream.keys()) + cn_uas:
        merged.setdefault(ua.lower(), ua)
    return sorted(merged.values(), key=lambda b: (-len(b), b.lower()))


def load_ip_ranges():
    ranges = {}
    manifest_path = ROOT / "geo" / "data" / "ip-ranges" / "manifest.json"
    if not manifest_path.exists():
        return ranges
    manifest = json.loads(manifest_path.read_text())
    for bot, meta in manifest.items():
        data = json.loads((manifest_path.parent / meta["file"]).read_text())
        ranges[bot] = [ipaddress.ip_network(p) for p in data["prefixes"]]
    return ranges


def iter_lines(patterns):
    for pattern in patterns:
        for path in sorted(glob.glob(pattern)):
            opener = gzip.open if path.endswith(".gz") else open
            with opener(path, "rt", errors="replace") as fh:
                yield from fh


def parse(patterns, ua_list, ip_ranges):
    stats = {}  # bot -> {paths: {path: count}, verified, ua_only, first, last}
    total_lines = 0
    bot_patterns = compile_bot_patterns(ua_list)
    for line in iter_lines(patterns):
        total_lines += 1
        m = LOG_RE.match(line)
        if not m:
            continue
        ip_str, time_str, _method, path, _status, ua = m.groups()
        ua_clean = UA_URL_RE.sub("", ua)
        bot = next((b for b, rx in bot_patterns if rx.search(ua_clean)), None)
        if bot is None:
            continue
        entry = stats.setdefault(bot, {"paths": {}, "verified": 0, "ua_only": 0, "first": None, "last": None})
        entry["paths"][path] = entry["paths"].get(path, 0) + 1
        try:
            ts = datetime.strptime(time_str, TIME_FMT)
            entry["first"] = min(entry["first"] or ts, ts)
            entry["last"] = max(entry["last"] or ts, ts)
        except ValueError:
            pass
        if bot in ip_ranges:
            try:
                ok = any(ipaddress.ip_address(ip_str) in net for net in ip_ranges[bot])
            except ValueError:
                ok = False
            entry["verified" if ok else "ua_only"] += 1
        else:
            entry["ua_only"] += 1
    return stats, total_lines


def write_reports(stats, total_lines, ip_ranges, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    year, week, _ = date.today().isocalendar()
    base = out_dir / f"crawlers-{year}-W{week:02d}"
    fmt = lambda ts: ts.strftime("%Y-%m-%d %H:%M %z") if ts else "-"

    with open(f"{base}.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["bot", "path", "count", "verified_hits", "ua_only_hits", "first_seen", "last_seen", "ranges_published"])
        for bot, e in sorted(stats.items()):
            for path, count in sorted(e["paths"].items(), key=lambda kv: -kv[1]):
                w.writerow([bot, path, count, e["verified"], e["ua_only"], fmt(e["first"]), fmt(e["last"]), bot in ip_ranges])

    lines = [f"# AI 爬虫周报 {year}-W{week:02d}", "", f"- 解析日志行: {total_lines}", f"- 命中 AI 爬虫: {len(stats)} 个", ""]
    if stats:
        lines += ["| Bot | 总命中 | 已验真 | 仅 UA 匹配 | 官方段 | 首次 | 最近 |", "|---|---|---|---|---|---|---|"]
        for bot, e in sorted(stats.items(), key=lambda kv: -sum(kv[1]["paths"].values())):
            total = sum(e["paths"].values())
            lines.append(f"| {bot} | {total} | {e['verified']} | {e['ua_only']} | {'有' if bot in ip_ranges else '无(仅 UA 档)'} | {fmt(e['first'])} | {fmt(e['last'])} |")
        lines += ["", "## 热门路径(每 bot 前 5)", ""]
        for bot, e in sorted(stats.items()):
            tops = sorted(e["paths"].items(), key=lambda kv: -kv[1])[:5]
            lines.append(f"- **{bot}**: " + ", ".join(f"`{p}`×{c}" for p, c in tops))
    else:
        lines.append("本周无 AI 爬虫命中(冷启动期属预期)。")
    lines += ["", "> 已验真 = 来源 IP 落在厂商公布段内;仅 UA 匹配 = UA 命中但 IP 不在段内(疑似伪装)或厂商未公布段。"]
    Path(f"{base}.md").write_text("\n".join(lines) + "\n")
    print(f"报告: {base}.md / {base}.csv")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--logs", nargs="+", required=True, help="访问日志 glob(支持 .gz)")
    ap.add_argument("--out-dir", default=str(ROOT / "geo" / "reports"))
    args = ap.parse_args()
    stats, total = parse(args.logs, load_ua_list(), load_ip_ranges())
    write_reports(stats, total, load_ip_ranges(), Path(args.out_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
