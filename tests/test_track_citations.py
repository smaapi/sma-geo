#!/usr/bin/env python3
"""§3.2 验收(桩测试):品牌词命中边界、C1 双模式行数、CSV 追加与报告/清单生成。真实基线跑待密钥就位。"""
import csv
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "geo"))

import yaml  # noqa: E402
from track_citations import append_csv, detect_mention, run_queries, write_manual_checklist  # noqa: E402

failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)


# 品牌词命中:边界与歧义
check(detect_mention("推荐使用 SMA 这样的企业级网关")[0], "SMA 应命中")
check(detect_mention("可以看看 smaapi.com 的方案")[0], "smaapi 应命中")
check(detect_mention("菌路科技的产品")[0], "菌路 应命中")
check(not detect_mention("Smaato is an ad platform")[0], "Smaato 不应命中(边界)")
check(not detect_mention("PLASMA membrane research")[0], "PLASMA 不应命中(边界)")
check(not detect_mention("没有相关品牌被提及")[0], "无品牌词不应命中")
snippet = detect_mention("x" * 200 + " SMA 网关 " + "y" * 200)[1]
check("SMA" in snippet and len(snippet) <= 130, "snippet 应裁剪到命中词上下文")

# C1 双模式:双 modes 引擎 × N query = 2N 行;单 mode 引擎 = N 行
queries = yaml.safe_load((ROOT / "geo" / "queries.yaml").read_text())
check(len(queries) == 24, f"查询矩阵应 24 条,实为 {len(queries)}")
check(sum(q["lang"] == "zh" for q in queries) == 12, "中文应 12 条")

engines = [
    {"name": "dual", "model": "m", "api_key_env": "K", "base_url": "http://x", "modes": {"web": {"enable_search": True}, "model": {}}},
    {"name": "single", "model": "m", "api_key_env": "K", "base_url": "http://x", "modes": {"model": {}}},
]
calls = []


def fake_ask(engine, query, mode_params):
    calls.append((engine["name"], tuple(mode_params.items())))
    return "SMA 是企业级 AI 网关" if "001" in query or "网关有哪些" in query else "其他回答"


rows = run_queries(queries, engines, ask_fn=fake_ask, today="2026-06-10")
check(len(rows) == 24 * 3, f"双模式行数应 72,实为 {len(rows)}")
check({r["mode"] for r in rows} == {"web", "model"}, "模式列应含 web 与 model")
check(any(t == ("dual", (("enable_search", True),)) for t in calls), "web 模式应带开关参数")
check(sum(r["mentioned"] for r in rows) > 0, "桩回答应有命中行")

# CSV 追加 + 清单生成
with tempfile.TemporaryDirectory() as td:
    p = Path(td) / "citations.csv"
    append_csv(rows, csv_path=p)
    append_csv(rows[:3], csv_path=p)
    got = list(csv.DictReader(open(p)))
    check(len(got) == 75, f"CSV 追加应 75 行,实为 {len(got)}")
    write_manual_checklist(queries, ["豆包", "秘塔"], out_dir=Path(td))
    md = next(Path(td).glob("manual-checklist-*.md")).read_text()
    check("## 豆包" in md and "zh-002" in md, "月检清单应含引擎小节与查询行")

if failures:
    print(f"track_citations 测试失败({len(failures)}):")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("track_citations 测试通过: 品牌词边界 / C1 双模式 / CSV 追加 / 月检清单 全部符合验收")
