"""
火山引擎 API 客户端模块
使用 OpenAI 兼容接口调用火山引擎的 Claude 模型
"""
import os
import json
import requests
from typing import Dict, Any, Optional
from config import VOLCENGINE_API_KEY, BASE_URL, MODEL


class VolcEngineClient:
    """火山引擎 API 客户端"""

    def __init__(self):
        self.api_key = VOLCENGINE_API_KEY
        self.base_url = BASE_URL
        self.model = MODEL
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def chat_completion(self, messages: list, temperature: float = 0.7, max_tokens: int = 4000) -> Dict[str, Any]:
        """
        调用聊天补全接口

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}, ...]
            temperature: 温度参数
            max_tokens: 最大 token 数

        Returns:
            API 响应字典
        """
        # 尝试不同的 URL 格式
        urls_to_try = [
            self.base_url,
            f"{self.base_url}/chat/completions" if not self.base_url.endswith('/chat/completions') else self.base_url,
            f"{self.base_url.replace('/api/coding', '/api/v3')}/chat/completions" if '/api/coding' in self.base_url else None,
        ]

        # 过滤掉 None
        urls_to_try = [url for url in urls_to_try if url]

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        last_error = None
        for url in urls_to_try:
            try:
                print(f"   尝试 URL: {url}")
                response = requests.post(url, headers=self.headers, json=payload, timeout=120)
                response.raise_for_status()
                result = response.json()
                print(f"   ✓ API 请求成功")
                return result
            except requests.exceptions.RequestException as e:
                last_error = e
                print(f"   ✗ 请求失败: {e}")
                continue

        print(f"API 调用失败，所有 URL 都无法访问: {last_error}")
        return {"error": str(last_error)}

    def extract_json_from_response(self, response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        从 API 响应中提取 JSON 内容

        Args:
            response: API 响应字典

        Returns:
            提取的 JSON 数据，失败返回 None
        """
        try:
            if "error" in response:
                return None

            content = response["choices"][0]["message"]["content"]

            # 尝试直接解析 JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # 尝试提取 JSON 代码块
                if "```json" in content:
                    json_start = content.find("```json") + 7
                    json_end = content.find("```", json_start)
                    json_str = content[json_start:json_end].strip()
                    return json.loads(json_str)
                elif "```" in content:
                    json_start = content.find("```") + 3
                    json_end = content.find("```", json_start)
                    json_str = content[json_start:json_end].strip()
                    return json.loads(json_str)
                else:
                    # 尝试找到第一个 { 到最后一个 } 的内容
                    brace_start = content.find("{")
                    brace_end = content.rfind("}")
                    if brace_start != -1 and brace_end != -1:
                        json_str = content[brace_start:brace_end + 1].strip()
                        return json.loads(json_str)

            return None
        except Exception as e:
            print(f"提取 JSON 失败: {e}")
            return None


# 全局客户端实例
_client = None


def get_client() -> VolcEngineClient:
    """获取单例客户端"""
    global _client
    if _client is None:
        _client = VolcEngineClient()
    return _client


def analyze_workflow_with_llm(search_results: list, keyword: str) -> Dict[str, Any]:
    """
    使用 LLM 分析工作流

    Args:
        search_results: 搜索结果列表
        keyword: 搜索关键词

    Returns:
        分析结果字典
    """
    client = get_client()

    # 构建提示词
    prompt = build_analysis_prompt(search_results, keyword)

    messages = [
        {
            "role": "system",
            "content": "你是一个专业的业务流程分析师，擅长分析企业工作流并提出自动化改进方案。请用 JSON 格式输出分析结果。"
        },
        {
            "role": "user",
            "content": prompt
        }
    ]

    print(f"正在调用 LLM 分析工作流: {keyword}...")
    response = client.chat_completion(messages, temperature=0.7, max_tokens=4000)

    result = client.extract_json_from_response(response)

    if result is None:
        print("LLM 返回格式异常，使用预设数据...")
        from workflow_data import get_preset
        return get_preset(keyword)

    # 补充必要字段
    if "keyword" not in result:
        result["keyword"] = keyword
    if "generated_at" not in result:
        from datetime import datetime
        result["generated_at"] = datetime.now().isoformat()

    return result


def build_analysis_prompt(search_results: list, keyword: str) -> str:
    """
    构建分析提示词

    Args:
        search_results: 搜索结果列表
        keyword: 搜索关键词

    Returns:
        提示词字符串
    """
    # 整理搜索结果
    search_content = ""
    for i, result in enumerate(search_results[:10], 1):
        search_content += f"""
[{i}] {result.get('title', '无标题')}
    链接: {result.get('url', '')}
    摘要: {result.get('snippet', result.get('content', ''))[:300]}
"""

    prompt = f"""
请分析以下关于"{keyword}"的工作流信息，基于搜索结果提供专业分析。

## 搜索结果
{search_content}

## 任务
请分析这个工作流，并按照以下 JSON 格式输出分析结果：

{{
    "workflow_name": "{keyword}",
    "industry": "请填写所属行业",
    "trigger_condition": "请描述工作流的触发条件",
    "roles": ["角色1", "角色2", "角色3"],
    "systems": ["系统1", "系统2", "系统3"],
    "steps": [
        {{
            "step_number": 1,
            "description": "步骤描述",
            "role": "执行角色",
            "input": "输入内容",
            "output": "输出内容",
            "system": "使用系统",
            "estimated_duration_minutes": 30,
            "is_decision": false
        }}
    ],
    "pain_points": {{
        "manual_repetition": {{
            "description": "人工重复工作的描述",
            "step_numbers": [1, 2],
            "time_percentage": 30,
            "why_inefficient": "为什么低效"
        }},
        "information_movement": {{
            "description": "信息搬运的描述",
            "step_numbers": [2, 3],
            "time_percentage": 20,
            "why_inefficient": "为什么低效"
        }},
        "judgment_cost": {{
            "description": "判断成本的描述",
            "step_numbers": [3],
            "time_percentage": 15,
            "why_inefficient": "为什么低效"
        }},
        "communication_cost": {{
            "description": "沟通成本的描述",
            "step_numbers": [4],
            "time_percentage": 15,
            "why_inefficient": "为什么低效"
        }},
        "waiting_cost": {{
            "description": "等待成本的描述",
            "step_numbers": [5],
            "time_percentage": 10,
            "why_inefficient": "为什么低效"
        }},
        "audit_cost": {{
            "description": "审核成本的描述",
            "step_numbers": [6],
            "time_percentage": 10,
            "why_inefficient": "为什么低效"
        }}
    }},
    "agent_flow": {{
        "new_process_description": "Agent 介入后的新流程描述",
        "intervention_points": [
            {{
                "step_number": 1,
                "intervention_type": "完全自动/Agent辅助/必须人类确认",
                "description": "介入方式描述",
                "risk_control": "风险控制措施"
            }}
        ],
        "human_approval": [
            {{
                "step": 1,
                "reason": "需要人类确认的原因",
                "condition": "触发条件"
            }}
        ],
        "agent_value_proposition": [
            "价值主张1",
            "价值主张2"
        ],
        "product_solution": {{
            "product_name": "产品名称",
            "core_features": ["核心功能1", "核心功能2"],
            "user_stories": ["用户故事1", "用户故事2"],
            "tech_architecture": "技术架构描述"
        }},
        "mvp_plan": [
            {{
                "day": 1,
                "phase": "阶段名称",
                "task": "任务描述",
                "deliverable": "交付物",
                "success_metric": "成功指标",
                "owner": "负责人",
                "tools_used": "使用工具"
            }}
        ]
    }},
    "cost": {{
        "assumptions": [
            "假设1",
            "假设2"
        ],
        "current_cost_detail": {{
            "labor_cost_breakdown": [
                {{
                    "role": "角色",
                    "monthly_salary": 6000,
                    "hourly_cost": 35,
                    "time_per_application": 10,
                    "cost_per_application": 350,
                    "monthly_volume": 100,
                    "monthly_cost": 35000
                }}
            ],
            "total_monthly_cost": 100000,
            "total_annual_cost": 1200000
        }},
        "agent_cost_detail": {{
            "api_cost_per_unit": 0.5,
            "setup_cost": 50000,
            "maintenance_cost": 3000,
            "remaining_human_cost": {{
                "role": "角色",
                "headcount": 1,
                "monthly_cost": 8000
            }},
            "total_monthly_cost": 11500,
            "total_annual_cost": 138000
        }},
        "savings": {{
            "monthly_savings": 88500,
            "annual_savings": 1062000
        }},
        "roi": {{
            "break_even_months": 2,
            "first_year_roi": 680
        }}
    }},
    "evidence_urls": [
        {{
            "title": "证据标题",
            "url": "证据链接"
        }}
    ]
}}

## 要求
1. 基于搜索结果，尽量真实地描述这个工作流
2. steps 至少包含 4 个步骤，最多 10 个步骤
3. pain_points 至少分析 3 种低效原因
4. intervention_points 至少包含 2 个完全自动、2 个 Agent 辅助
5. mvp_plan 必须完整包含 7 天计划
6. cost 部分的计算要合理，有明确假设
7. evidence_urls 从搜索结果中选择 2-5 个最相关的

请直接输出 JSON，不要包含其他说明文字。
"""

    return prompt


if __name__ == "__main__":
    print("火山引擎 API 客户端测试")
    print(f"API 配置: {BASE_URL}")
    print(f"模型: {MODEL}")
    print()

    # 测试简单调用
    client = get_client()
    test_messages = [
        {
            "role": "user",
            "content": "你好，请用一句话介绍自己，用 JSON 格式输出 {\"message\": \"你的介绍\"}"
        }
    ]

    response = client.chat_completion(test_messages, max_tokens=200)
    print("测试响应:")
    print(json.dumps(response, ensure_ascii=False, indent=2))
