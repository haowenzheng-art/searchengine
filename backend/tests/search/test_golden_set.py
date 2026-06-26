"""黄金集测试 - 验证三层评分准确率.

CI 必跑, 准确率 < 85% 阻断 PR.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.search.scorer import score_evidence

GOLDEN_SET_PATH = Path(__file__).parent.parent / "golden_set" / "evidence_scores.jsonl"
ACCURACY_THRESHOLD = 0.85  # 85% 准确率阻断
SCORE_TOLERANCE = 1.0  # 误差 <= 1 视为正确


def load_golden_set() -> list[dict]:
    """加载黄金集测试用例."""
    cases = []
    with GOLDEN_SET_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            cases.append(json.loads(line))
    return cases


@pytest.mark.parametrize(
    "case",
    load_golden_set(),
    ids=lambda c: f"{c['expected_label']}:{c['url'][:40]}",
)
@pytest.mark.asyncio
async def test_golden_set_evidence_scoring(case, session_factory):
    """对每个黄金集用例跑三层评分, 验证 score 误差 <= 1."""
    score, reason, is_home, is_disamb, layer = await score_evidence(
        url=case["url"],
        snippet=case["snippet"],
        query=case["query"],
        title=case.get("title"),
    )
    expected = case["expected_score"]
    diff = abs(score - expected)
    assert diff <= SCORE_TOLERANCE, (
        f"\nURL: {case['url']}\n"
        f"Query: {case['query']}\n"
        f"Expected: {expected} ({case['expected_label']})\n"
        f"Got: {score} (layer {layer})\n"
        f"Diff: {diff} > tolerance {SCORE_TOLERANCE}\n"
        f"Reason: {reason[:200]}\n"
        f"Expected reason: {case['reason']}"
    )


@pytest.mark.asyncio
async def test_golden_set_overall_accuracy(session_factory):
    """整体准确率 >= 85% 才通过."""
    cases = load_golden_set()
    correct = 0
    failures: list[str] = []

    for case in cases:
        try:
            score, reason, is_home, is_disamb, layer = await score_evidence(
                url=case["url"],
                snippet=case["snippet"],
                query=case["query"],
                title=case.get("title"),
            )
            if abs(score - case["expected_score"]) <= SCORE_TOLERANCE:
                correct += 1
            else:
                failures.append(
                    f"{case['url'][:60]} | expected={case['expected_score']} got={score} (layer {layer})"
                )
        except Exception as e:
            failures.append(f"{case['url'][:60]} | EXCEPTION: {e}")

    accuracy = correct / len(cases)
    failure_report = "\n".join(failures[:10])  # 只显示前 10 个失败
    assert accuracy >= ACCURACY_THRESHOLD, (
        f"Golden set accuracy {accuracy:.2%} < {ACCURACY_THRESHOLD:.0%} threshold\n"
        f"Failures ({len(failures)}):\n{failure_report}"
    )
