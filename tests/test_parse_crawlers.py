#!/usr/bin/env python3
"""§3.1 验收:样例日志正确区分 GPTBot 与普通 UA;C2 验真分档正确;空日志不报错。"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "geo"))

from parse_ai_crawlers import load_ip_ranges, load_ua_list, parse, write_reports  # noqa: E402

failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)


ua_list = load_ua_list()
ip_ranges = load_ip_ranges()
fixture = str(ROOT / "tests" / "fixtures" / "sample-access.log")

# D2 守卫:合并清单无大小写重复;排序确定(REVIEW r3)
lower = [u.lower() for u in ua_list]
check(len(lower) == len(set(lower)), "UA 清单存在大小写不敏感重复")
check(ua_list == sorted(ua_list, key=lambda b: (-len(b), b.lower())), "UA 清单排序非确定")
check("OpenAI" in ua_list and "GPTBot" in ua_list, "歧义对 OpenAI/GPTBot 应同时在清单中(回归前提)")

stats, total = parse([fixture], ua_list, ip_ranges)

# D2 回归:GPTBot 行的厂商 URL(+https://openai.com/gptbot)不得误记入 OpenAI 名下
check("OpenAI" not in stats, "厂商 URL 误命中 OpenAI(D2 根因复现)")

check(total == 7, f"日志行数应为 7,实为 {total}")
check("GPTBot" in stats, "GPTBot 未命中")
check(sum(stats.get("GPTBot", {}).get("paths", {}).values()) == 3, "GPTBot 总命中应为 3")
check(stats.get("GPTBot", {}).get("verified") == 2, f"GPTBot 已验真应为 2(官方段 IP),实为 {stats.get('GPTBot', {}).get('verified')}")
check(stats.get("GPTBot", {}).get("ua_only") == 1, "GPTBot 仅 UA 匹配应为 1(伪装 IP 1.2.3.4)")
check("ClaudeBot" in stats, "ClaudeBot 未命中")
check(stats.get("ClaudeBot", {}).get("ua_only") == 1, "ClaudeBot 应记仅 UA 档(无官方段)")
check(not any("Chrome" in b or "Mozilla" in b for b in stats), "普通浏览器 UA 不应命中")
check(len(stats) == 2, f"应只命中 2 个 bot,实为 {sorted(stats)}")

# r10 D1:Caddy JSON 格式混合解析 + 新维度
fixture_caddy = str(ROOT / "tests" / "fixtures" / "sample-access-caddy.log")
stats2, total2 = parse([fixture, fixture_caddy], ua_list, ip_ranges)
check(total2 == 10, f"混合日志行数应 10,实为 {total2}")
g = stats2.get("GPTBot", {})
check(sum(g.get("paths", {}).values()) == 4, "混合解析 GPTBot 总命中应 4(nginx 3 + caddy 1)")
check(g.get("verified") == 3, f"混合解析已验真应 3,实为 {g.get('verified')}")
check(g.get("status", {}).get("2xx") == 4, "GPTBot 2xx 计数应 4")
check(g.get("bytes", 0) > 0, "bytes 应聚合")
check("www.smaapi.com" in g.get("hosts", {}), "caddy host 维度应记录")

with tempfile.TemporaryDirectory() as td2:
    from parse_ai_crawlers import write_reports as _wr
    _wr(stats2, total2, ip_ranges, __import__("pathlib").Path(td2))
    import pathlib as _pl
    check(any(_pl.Path(td2).glob("crawlers-*-bots.csv")), "应产出 bot 级分表")
    check(any(_pl.Path(td2).glob("crawlers-*-paths.csv")), "应产出 path 级分表")

# r11 §3-1:观察阈值(>100 零验真 / 非公开路径探测)
from collections import Counter as _C
synth = {
    "GPTBot": {"paths": _C({f"/p{i}": 1 for i in range(120)}), "status": _C({"2xx": 120}), "hosts": _C({"www.smaapi.com": 120}), "bytes": 1, "verified": 0, "ua_only": 120, "first": None, "last": None},
    "ClaudeBot": {"paths": _C({"/console/index.html": 2, "/": 1}), "status": _C({"4xx": 3}), "hosts": _C(), "bytes": 0, "verified": 0, "ua_only": 3, "first": None, "last": None},
}
with tempfile.TemporaryDirectory() as td3:
    _wr(synth, 123, ip_ranges, __import__("pathlib").Path(td3))
    md = next(__import__("pathlib").Path(td3).glob("crawlers-*.md")).read_text()
    check("观察级备注" in md and "超观察阈值" in md, "高命中零验真应触发观察备注")
    check("/console/index.html" in md, "非公开路径探测应列入备注")

# 空日志不报错
with tempfile.TemporaryDirectory() as td:
    empty = Path(td) / "empty.log"
    empty.write_text("")
    s2, t2 = parse([str(empty)], ua_list, ip_ranges)
    check(s2 == {} and t2 == 0, "空日志应零命中且不报错")
    write_reports(s2, t2, ip_ranges, Path(td) / "reports")
    check(any(Path(td, "reports").glob("crawlers-*.md")), "空日志也应产出周报")
    # 不存在的 glob 不报错
    s3, _ = parse([str(Path(td) / "nope-*.log")], ua_list, ip_ranges)
    check(s3 == {}, "无匹配 glob 应零命中且不报错")

if failures:
    print(f"parse_ai_crawlers 测试失败({len(failures)}):")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("parse_ai_crawlers 测试通过: UA 区分 / C2 验真分档 / 空日志容错 全部符合验收")
