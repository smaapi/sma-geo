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
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_RE = re.compile(r'^(\S+) \S+ \S+ \[([^\]]+)\] "(\S+) (\S+)[^"]*" (\d{3}) (\S+) "[^"]*" "([^"]*)"')
TIME_FMT = "%d/%b/%Y:%H:%M:%S %z"


def parse_line(line):
    """单行解析:支持 nginx combined 与 Caddy JSON 两种格式(r10 批次 D1)。"""
    line = line.strip()
    if line.startswith("{"):
        try:
            d = json.loads(line)
        except ValueError:
            return None
        req = d.get("request", {})
        ua = (req.get("headers", {}).get("User-Agent") or [""])[0]
        ts = None
        if "ts" in d:
            try:
                ts = datetime.fromtimestamp(float(d["ts"]), tz=timezone.utc)
            except (ValueError, OSError):
                ts = None
        return {"ip": req.get("client_ip") or req.get("remote_ip", ""), "time": ts,
                "path": req.get("uri", ""), "status": int(d.get("status", 0) or 0),
                "bytes": int(d.get("size", 0) or 0), "host": req.get("host", "-"), "ua": ua}
    m = LOG_RE.match(line)
    if not m:
        return None
    ip, time_str, _method, path, status, size, ua = m.groups()
    try:
        ts = datetime.strptime(time_str, TIME_FMT)
    except ValueError:
        ts = None
    return {"ip": ip, "time": ts, "path": path, "status": int(status),
            "bytes": int(size) if size.isdigit() else 0, "host": "-", "ua": ua}
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
    """bot -> {paths/status/hosts: Counter, bytes, verified, ua_only, first, last}(r10 D1 维度)。"""
    stats = {}
    total_lines = 0
    bot_patterns = compile_bot_patterns(ua_list)
    for line in iter_lines(patterns):
        total_lines += 1
        rec = parse_line(line)
        if rec is None:
            continue
        ua_clean = UA_URL_RE.sub("", rec["ua"])
        bot = next((b for b, rx in bot_patterns if rx.search(ua_clean)), None)
        if bot is None:
            continue
        entry = stats.setdefault(bot, {"paths": Counter(), "status": Counter(), "hosts": Counter(),
                                       "bytes": 0, "verified": 0, "ua_only": 0, "first": None, "last": None})
        entry["paths"][rec["path"]] += 1
        entry["status"][f"{rec['status'] // 100}xx"] += 1
        entry["hosts"][rec["host"]] += 1
        entry["bytes"] += rec["bytes"]
        if rec["time"]:
            entry["first"] = min(entry["first"] or rec["time"], rec["time"])
            entry["last"] = max(entry["last"] or rec["time"], rec["time"])
        if bot in ip_ranges:
            try:
                ok = any(ipaddress.ip_address(rec["ip"]) in net for net in ip_ranges[bot])
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

    # 分表(r10 D1):bot 级一行一 bot(无重复计数),path 级单列明细
    with open(f"{base}-bots.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["bot", "total_hits", "verified_hits", "ua_only_hits", "s2xx", "s3xx", "s4xx", "s5xx",
                    "bytes", "hosts", "first_seen", "last_seen", "ranges_published"])
        for bot, e in sorted(stats.items(), key=lambda kv: -sum(kv[1]["paths"].values())):
            w.writerow([bot, sum(e["paths"].values()), e["verified"], e["ua_only"],
                        e["status"].get("2xx", 0), e["status"].get("3xx", 0), e["status"].get("4xx", 0), e["status"].get("5xx", 0),
                        e["bytes"], ";".join(sorted(e["hosts"])), fmt(e["first"]), fmt(e["last"]), bot in ip_ranges])
    with open(f"{base}-paths.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["bot", "path", "count"])
        for bot, e in sorted(stats.items()):
            for path, count in sorted(e["paths"].items(), key=lambda kv: -kv[1]):
                w.writerow([bot, path, count])

    lines = [f"# AI 爬虫周报 {year}-W{week:02d}", "", f"- 解析日志行: {total_lines}", f"- 命中 AI 爬虫: {len(stats)} 个", ""]
    if stats:
        lines += ["| Bot | 总命中 | 已验真 | 仅 UA | 2xx/3xx/4xx/5xx | 流量 | 官方段 | 首次 | 最近 |", "|---|---|---|---|---|---|---|---|---|"]
        for bot, e in sorted(stats.items(), key=lambda kv: -sum(kv[1]["paths"].values())):
            total = sum(e["paths"].values())
            sc = "/".join(str(e["status"].get(k, 0)) for k in ("2xx", "3xx", "4xx", "5xx"))
            lines.append(f"| {bot} | {total} | {e['verified']} | {e['ua_only']} | {sc} | {e['bytes'] // 1024}KB | {'有' if bot in ip_ranges else '无'} | {fmt(e['first'])} | {fmt(e['last'])} |")
        lines += ["", "## 热门路径(每 bot 前 5)", ""]
        for bot, e in sorted(stats.items()):
            tops = e["paths"].most_common(5)
            lines.append(f"- **{bot}**: " + ", ".join(f"`{p}`×{c}" for p, c in tops))
    else:
        lines.append("本周无 AI 爬虫命中(冷启动期属预期)。")
    # r11 §3-1:仅 UA 档观察阈值——周命中 >100 或非公开路径探测 → 观察级备注(不告警不门禁)
    PROBE_RE = __import__("re").compile(r"^/(console|admin|api/internal|\.env|wp-|\.git|phpmyadmin)", __import__("re").IGNORECASE)
    observations = []
    for bot, e in stats.items():
        total = sum(e["paths"].values())
        probes = [p for p in e["paths"] if PROBE_RE.match(p)]
        if total > 100 and e["verified"] == 0:
            observations.append(f"- {bot}: 周命中 {total} 且零验真,超观察阈值(>100)")
        if probes:
            observations.append(f"- {bot}: 探测非公开路径 {sorted(probes)[:5]}")
    if observations:
        lines += ["", "## 观察级备注(仅 UA 档伪装流量,r11 §3-1 阈值)", ""] + observations
    lines += ["", "> 已验真 = 来源 IP 落在厂商公布段内;仅 UA 匹配 = UA 命中但 IP 不在段内(疑似伪装)或厂商未公布段——此列固定保留为伪装流量观察位(r11 裁定)。",
              "> 计数口径:bot 级表一行一 bot,verified/ua_only 为请求级计数;path 明细见 -paths.csv,不与 bot 表混算。"]
    Path(f"{base}.md").write_text("\n".join(lines) + "\n")
    print(f"报告: {base}.md / {base}-bots.csv / {base}-paths.csv")


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
