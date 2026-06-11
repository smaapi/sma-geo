#!/usr/bin/env python3
"""§3.2 验收(桩测试):品牌词命中边界、C1 双模式行数、CSV 追加与报告/清单生成。真实基线跑待密钥就位。"""
import csv
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "geo"))

import yaml  # noqa: E402
from track_citations import append_csv, detect_mention, detect_mislabel, run_queries, write_manual_checklist  # noqa: E402

failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)


# 品牌词命中:边界与歧义 + T8a 实体解析门(REVIEW r5)
check(detect_mention("推荐使用 SMA 这样的企业级网关")[0], "裸 SMA+消歧词(网关)应命中")
check(detect_mention("可以看看 smaapi.com 的方案")[0], "smaapi 强锚应命中")
check(detect_mention("菌路科技的产品")[0], "菌路 强锚应命中")
check(not detect_mention("Smaato is an ad platform")[0], "Smaato 不应命中(边界)")
check(not detect_mention("PLASMA membrane research")[0], "PLASMA 不应命中(边界)")
check(not detect_mention("没有相关品牌被提及")[0], "无品牌词不应命中")
snippet = detect_mention("x" * 200 + " SMA 网关 " + "y" * 200)[1]
check("SMA" in snippet and len(snippet) <= 130, "snippet 应裁剪到命中词上下文")
# T8a 错配单列:碰撞实体不计提及,记录被解析对象
m1 = detect_mention("SMA(通常指简单移动平均线)模型接入平台并不是一个标准产品")
check(not m1[0] and m1[2] == "简单移动平均线", f"移动平均碰撞应记错配,实为 {m1}")
m2 = detect_mention("SMA is a German solar inverter manufacturer with an API portal")
check(not m2[0] and m2[2] == "SMA Solar(光伏)", "光伏碰撞应记错配")
m3 = detect_mention("The SMA results were inconclusive")
check(not m3[0] and m3[2] == "未消歧(裸SMA)", "无消歧上下文的裸 SMA 不计提及")
check(detect_mention("菌路 SMA 与移动平均无关")[0], "强锚优先于碰撞词")

# C2:中转站误称 P0 检测
check(detect_mislabel("SMA 是一个 API 中转站"), "误称(自指邻接)应命中 P0")
check(detect_mislabel("常见的中转站服务里 smaapi 也算一个"), "误称(反向邻接)应命中 P0")
check(not detect_mislabel("SMA 是企业级网关;另一类是 API 中转站,两者定位不同,前者面向企业治理场景而后者面向个人"), "他指远距不应命中")
check(not detect_mislabel("SMA 是企业级 AI 网关"), "正常描述不应命中")

# C1 双模式 + 矩阵 v2:40 条,money 权重 18
queries = yaml.safe_load((ROOT / "geo" / "queries.yaml").read_text())
check(len(queries) == 40, f"查询矩阵 v2 应 40 条,实为 {len(queries)}")
check(sum(q["lang"] == "zh" for q in queries) == 23, "中文应 23 条")
check(sum(q.get("weight") == "money" for q in queries) == 18, "money 权重应 18 条")
check(all(q.get("weight") in ("money", "secondary") for q in queries), "每条必须有权重标注")

engines = [
    {"name": "dual", "model": "m", "api_key_env": "K", "base_url": "http://x", "modes": {"web": {"enable_search": True}, "model": {}}},
    {"name": "single", "model": "m", "api_key_env": "K", "base_url": "http://x", "modes": {"model": {}}},
]
calls = []


def fake_ask(engine, query, mode_params):
    calls.append((engine["name"], tuple(mode_params.items())))
    return "SMA 是企业级 AI 网关" if "001" in query or "网关有哪些" in query else "其他回答"


rows = run_queries(queries, engines, ask_fn=fake_ask, today="2026-06-10", classify_fn=lambda a: ("中", "准确"))
check(len(rows) == 40 * 3, f"双模式行数应 120,实为 {len(rows)}")
check({r["mode"] for r in rows} == {"web", "model"}, "模式列应含 web 与 model")
check(any(t == ("dual", (("enable_search", True),)) for t in calls), "web 模式应带开关参数")
check(sum(r["mentioned"] for r in rows) > 0, "桩回答应有命中行")
hit = next(r for r in rows if r["mentioned"])
check(hit["sentiment"] == "中" and hit["accuracy"] == "准确", "命中行应带质量标注")
check(all(r["sentiment"] == "" for r in rows if not r["mentioned"]), "未命中行不打标")
check(all(r["mislabel"] == 0 for r in rows), "桩回答无误称,mislabel 应全 0")
check(all(r["entity_mismatch"] == "" for r in rows if r["mentioned"]), "命中行不应同时记错配")

# CSV 追加 + 清单生成
with tempfile.TemporaryDirectory() as td:
    p = Path(td) / "citations.csv"
    append_csv(rows, csv_path=p)
    append_csv(rows[:3], csv_path=p)
    got = list(csv.DictReader(open(p)))
    check(len(got) == 123, f"CSV 追加应 123 行,实为 {len(got)}")
    write_manual_checklist(queries, ["豆包", "秘塔"], out_dir=Path(td))
    md = next(Path(td).glob("manual-checklist-*.md")).read_text()
    check("## 豆包" in md and "zh-002" in md, "月检清单应含引擎小节与查询行")

if failures:
    print(f"track_citations 测试失败({len(failures)}):")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("track_citations 测试通过: 品牌词边界 / C1 双模式 / CSV 追加 / 月检清单 全部符合验收")
