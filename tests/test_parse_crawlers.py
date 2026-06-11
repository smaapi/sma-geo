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

stats, total = parse([fixture], ua_list, ip_ranges)

check(total == 7, f"日志行数应为 7,实为 {total}")
check("GPTBot" in stats, "GPTBot 未命中")
check(sum(stats.get("GPTBot", {}).get("paths", {}).values()) == 3, "GPTBot 总命中应为 3")
check(stats.get("GPTBot", {}).get("verified") == 2, f"GPTBot 已验真应为 2(官方段 IP),实为 {stats.get('GPTBot', {}).get('verified')}")
check(stats.get("GPTBot", {}).get("ua_only") == 1, "GPTBot 仅 UA 匹配应为 1(伪装 IP 1.2.3.4)")
check("ClaudeBot" in stats, "ClaudeBot 未命中")
check(stats.get("ClaudeBot", {}).get("ua_only") == 1, "ClaudeBot 应记仅 UA 档(无官方段)")
check(not any("Chrome" in b or "Mozilla" in b for b in stats), "普通浏览器 UA 不应命中")
check(len(stats) == 2, f"应只命中 2 个 bot,实为 {sorted(stats)}")

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
