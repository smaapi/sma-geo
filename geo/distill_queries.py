#!/usr/bin/env python3
"""蒸馏式查询扩展(addendum 02v2 §C-2 取精版):生成"企业采购者会怎么问 AI"的同义变体候选。

原则:生成只扩问法,不造需求;候选输出到 docs/internal/ 供人工筛选,绝不自动入库;
矩阵上限 40 条由人工筛选时执行。生成走 SMA 网关(此处是生成任务,白标不影响)。
用法:source .env && python3 geo/distill_queries.py [--per-query 2] [--only-money]
"""
import argparse
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "geo"))
from track_citations import ask_openai_compatible  # noqa: E402

ENGINE = {"model": "sma-domestic-fast", "base_url": "https://demo.smaapi.com/v1", "api_key_env": "SMA_API_KEY"}

PROMPT = (
    "你是企业采购研究员。给定一条企业用户可能在 AI 搜索里输入的查询,生成 {n} 条同义变体:"
    "保持同一采购/使用意图,只改变问法(口语化、场景化、角色化均可),不引入原查询没有的新需求,"
    "不出现具体厂商承诺词。每行一条,不编号,不解释。\n原查询:{q}"
)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--per-query", type=int, default=2)
    ap.add_argument("--only-money", action="store_true", default=True)
    args = ap.parse_args()

    queries = yaml.safe_load((ROOT / "geo" / "queries.yaml").read_text())
    targets = [q for q in queries if not args.only_money or q.get("weight") == "money"]
    lines = [f"# 蒸馏查询候选 {date.today()} —— 人工筛选后方可入库(上限 40 条,含权重与 intent 标注)", ""]
    for q in targets:
        try:
            raw = ask_openai_compatible(ENGINE, PROMPT.format(n=args.per_query, q=q["query"]), {})
        except Exception as exc:
            print(f"  ! {q['id']}: {exc}", file=sys.stderr)
            continue
        variants = [l.strip().lstrip("-•1234567890. ") for l in raw.splitlines() if l.strip()][: args.per_query]
        lines.append(f"## {q['id']}({q['intent']}/{q.get('weight')}): {q['query']}")
        lines += [f"- [ ] {v}" for v in variants]
        lines.append("")
        print(f"{q['id']}: {len(variants)} 候选")
    out = ROOT / "docs" / "internal" / f"query-distill-candidates-{date.today()}.md"
    out.write_text("\n".join(lines) + "\n")
    print(f"候选清单: {out}")


if __name__ == "__main__":
    main()
