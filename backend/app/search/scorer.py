"""三层证据评分架构.

Layer 1: 规则过滤 (0 成本, 砍 60-70% 明显垃圾)
Layer 2: LLM 粗筛 (Haiku, $0.001/次, 只对 Layer 1 通过的 URL 评分)
Layer 3: LLM 复评 (Sonnet, $0.01/次, 只对 Layer 2 边界 case 4-6 分复评)

设计原则:
1. 不静默 fallback - LLM 失败抛异常, 不悄悄返回低分
2. 强制结构化输出 - 用 tool_use 强制 JSON schema, 不靠 prompt 自觉
3. thinking 优先 - LLM 先输出 reason 再输出 score, 避免先打分再编理由
4. 否定例明确 - prompt 里明确首页/歧义命中 = 低分
"""
from __future__ import annotations

from urllib.parse import urlparse

from pydantic import BaseModel, Field

from app.agent.llm import get_current_llm
from app.core.logging import get_logger

log = get_logger(__name__)


# ============ Layer 1: 规则过滤 ============

# 招聘行业 SEO 农场 + 招聘导航站 (主页一定不进流程文章评估)
_HOMEPAGE_DOMAINS = {
    "zhaopin.com",
    "zhipin.com",
    "51job.com",
    "liepin.com",
    "lagou.com",
    "zhaopin.com.cn",
    "jobui.com",
    "kanzhun.com",
    "jobsdb.com",
    "monster.com.cn",
    "chinahr.com",
    "528.com.cn",
    "zpb.cc",
}

# 政府网站通常不是流程文章来源 (除非 query 明确要政策法规)
_GOV_DOMAINS = {"gov.cn", "mohrss.gov.cn", "changshu.gov.cn"}

# 招聘相关关键词 - 用于歧义命中检测
_RECRUITMENT_HOME_KEYWORDS = {"招聘", "求职", "找工作", "招人", "hire", "jobs", "career"}


def _get_registered_domain(netloc: str) -> str:
    """从 netloc 提取注册域名 (去掉子域名).

    例如: www.zhaopin.com -> zhaopin.com
          m.zhaopin.com -> zhaopin.com
          zhaopin.com -> zhaopin.com
    """
    # 去掉端口
    host = netloc.split(":")[0]
    # 去掉 www. / m. / mobile. 前缀
    if host.startswith("www."):
        host = host[4:]
    elif host.startswith("m.") or host.startswith("mobile."):
        host = host.split(".", 1)[1] if "." in host else host

    # 处理 .com.cn / .gov.cn 这种二级 TLD
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in ("com", "gov", "org", "net", "edu") and parts[-1] in ("cn", "hk", "tw"):
        return ".".join(parts[-3:])

    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host


def _is_homepage(url: str) -> bool:
    """判断 URL 是否是网站首页.

    首页 path 是空、/、/index.html、/index.php 等.
    """
    try:
        parsed = urlparse(url)
        path = parsed.path.lower().rstrip("/")
        if path in ("", "/", "/index.html", "/index.php", "/index.htm", "/default.html"):
            return True
        # path 段数 < 2 视为可疑 (频道页或首页)
        segments = [s for s in path.split("/") if s]
        if len(segments) < 2:
            return True
        return False
    except Exception:
        return False


def _is_recruitment_site_homepage(url: str, query: str) -> bool:
    """检测招聘网站首页 (zhaopin.com 等).

    query 含招聘关键词 + URL 域名是招聘网站 = 几乎肯定是首页而非流程文章.
    """
    try:
        parsed = urlparse(url)
        domain = _get_registered_domain(parsed.netloc)
        if domain in _HOMEPAGE_DOMAINS:
            # 招聘网站首页 - 直接拒绝
            if _is_homepage(url):
                return True
            # 即使不是首页, 招聘网站的内页也通常是职位列表页, 不是流程文章
            # 但留一层: 如果 path 很深 (>2 段), 可能是文章页, 让 LLM 评估
            segments = [s for s in parsed.path.split("/") if s]
            if len(segments) < 2:
                return True
        return False
    except Exception:
        return False


def _is_disambiguation(url: str, query: str) -> bool:
    """检测歧义命中 - URL 域名与 query 行业无关.

    例如: query 是中文流程, 但 URL 是英文首页或政府招聘网.
    """
    try:
        parsed = urlparse(url)
        domain = _get_registered_domain(parsed.netloc)
        # 政府网站 + 招聘 query, 但 URL 看起来是事业单位招聘公告而非流程文章
        if domain in _GOV_DOMAINS:
            # 检查 path 是否含 "公告" "通知" 这类页面路径
            path_lower = parsed.path.lower()
            if any(kw in path_lower for kw in ["notice", "announcement", "gonggao", "公告"]):
                return True
        return False
    except Exception:
        return False


def rule_filter(url: str, snippet: str, query: str) -> tuple[bool, str, str | None]:
    """Layer 1: 规则过滤.

    Returns:
        (passed, reason, layer1_label)
        - passed=True: 通过规则, 进 Layer 2 LLM 评估
        - passed=False: 被规则拒绝, 不进 LLM (省 token)
        - layer1_label: "homepage" / "disambiguation" / "recruitment_home" / None
    """
    if _is_recruitment_site_homepage(url, query):
        return False, f"招聘网站首页或职位列表页 (域名在黑名单: {_get_registered_domain(urlparse(url).netloc)})", "recruitment_home"

    if _is_homepage(url):
        return False, f"网站首页 (path 段数 < 2)", "homepage"

    if _is_disambiguation(url, query):
        return False, f"政府公告类页面, 非流程文章", "disambiguation"

    return True, "passed rule filter", None


# ============ Layer 2: LLM 粗筛 ============

class LLMScorerOutput(BaseModel):
    """LLM 评分的强制结构化输出."""
    score: float = Field(ge=0.0, le=10.0)
    reason: str = Field(description="判断理由, 先输出此字段再打分")
    is_homepage: bool = False
    is_disambiguation: bool = False


_SCORE_PROMPT = """你是证据相关度评估器. 评估 URL 与查询的相关度 (0-10分).

判定标准:
- score >= 7: 真实的流程文章/分析文章, 内容与 query 直接相关
- score 4-6: 部分相关, 内容有但不够深入或不是流程本身
- score <= 3: 首页/导航页/职位列表/SEO聚合页, 与流程无关

明确否定例:
1. 招聘网站首页 (zhaopin.com / 51job.com / liepin.com 等根域名) = score 0
2. URL 域名与 query 行业无关 = score <= 2
3. URL path 很浅 (只有 1 段) 通常是频道页 = score <= 3
4. 标题含"找工作/求职/招聘信息"等是职位列表, 非流程 = score <= 2

明确正例:
1. URL path 深 (>= 3 段), 标题含"流程/步骤/方案/详解"等 = 可能 score >= 7
2. snippet 描述具体步骤或方法论 = score >= 7
3. 域名是行业博客/知乎/搜狐/简书等内容平台 = 倾向 score >= 5

思维链: 先输出 reason 字段分析, 再输出 score.
"""


async def score_with_llm(
    url: str,
    snippet: str,
    query: str,
    title: str | None = None,
    *,
    tier: str = "haiku",
) -> LLMScorerOutput:
    """Layer 2/3: 用 LLM 评分.

    Args:
        tier: haiku (粗筛) 或 sonnet (复评)
    """
    from app.agent.tools._llm_helper import call_llm_for_json

    title_str = f"标题: {title}\n" if title else ""
    user_content = (
        f"查询: {query}\n\n"
        f"URL: {url}\n"
        f"{title_str}"
        f"摘要: {snippet}\n\n"
        f"评估此 URL 是否是讲 '{query}' 流程的真实文章."
    )
    result = await call_llm_for_json(
        tier=tier,
        system=_SCORE_PROMPT,
        user_content=user_content,
        output_schema=LLMScorerOutput,
        tool_name="score_evidence_response",
        temperature=0.0,
    )
    return LLMScorerOutput.model_validate(result)


# ============ 三层 orchestrator ============

async def score_evidence(
    url: str,
    snippet: str,
    query: str,
    title: str | None = None,
) -> tuple[float, str, bool, bool, int]:
    """三层评分入口.

    Returns:
        (score, reason, is_homepage, is_disambiguation, score_layer)
        score_layer: 1=rule, 2=haiku, 3=sonnet
    """
    # Layer 1: 规则过滤
    passed, rule_reason, layer1_label = rule_filter(url, snippet, query)
    if not passed:
        # 规则拒绝, 直接给低分, 不调 LLM
        label_map = {
            "homepage": (2.0, True, False),
            "recruitment_home": (1.0, True, False),
            "disambiguation": (2.0, False, True),
        }
        score, is_home, is_disamb = label_map.get(layer1_label or "", (2.0, False, False))
        log.info(
            "score_layer1_rejected",
            url=url,
            label=layer1_label,
            score=score,
            reason=rule_reason,
        )
        return score, rule_reason, is_home, is_disamb, 1

    # Layer 2: Haiku 粗筛
    try:
        layer2 = await score_with_llm(url, snippet, query, title, tier="haiku")
    except Exception as e:
        # LLM 失败 - 不静默 fallback, 抛异常让 orchestrator 处理
        log.error("score_layer2_failed", url=url, error=str(e))
        raise RuntimeError(f"Layer 2 LLM scoring failed: {e}") from e

    log.info(
        "score_layer2_done",
        url=url,
        score=layer2.score,
        reason=layer2.reason[:80],
        is_homepage=layer2.is_homepage,
    )

    # Layer 3: 边界 case (4-6 分) 复评
    if 4.0 <= layer2.score <= 6.0:
        try:
            layer3 = await score_with_llm(url, snippet, query, title, tier="sonnet")
            log.info(
                "score_layer3_done",
                url=url,
                score=layer3.score,
                reason=layer3.reason[:80],
                prev_score=layer2.score,
            )
            return layer3.score, layer3.reason, layer3.is_homepage, layer3.is_disambiguation, 3
        except Exception as e:
            # Layer 3 失败, 用 Layer 2 结果 (不阻断, 但记日志)
            log.warning(
                "score_layer3_failed_using_layer2",
                url=url,
                error=str(e),
                fallback_score=layer2.score,
            )
            return layer2.score, layer2.reason, layer2.is_homepage, layer2.is_disambiguation, 2

    # Layer 2 高分或低分, 直接用
    return layer2.score, layer2.reason, layer2.is_homepage, layer2.is_disambiguation, 2
