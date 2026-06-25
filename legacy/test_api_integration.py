"""
测试火山引擎 API 集成
"""
import sys
import os

print("="*60)
print("  测试火山引擎 API 集成")
print("="*60)

# 测试 1: 检查配置
print("\n[1/4] 检查配置...")
try:
    from config import VOLCENGINE_API_KEY, BASE_URL, MODEL
    print(f"   API Key: {VOLCENGINE_API_KEY[:20]}..." if VOLCENGINE_API_KEY else "   API Key: [未设置]")
    print(f"   Base URL: {BASE_URL}")
    print(f"   Model: {MODEL}")
    print("   ✓ 配置加载成功")
except Exception as e:
    print(f"   ✗ 配置加载失败: {e}")
    sys.exit(1)

# 测试 2: 测试 LLM 客户端
print("\n[2/4] 测试 LLM 客户端...")
try:
    from llm_client import get_client
    client = get_client()

    # 简单测试
    test_messages = [
        {"role": "user", "content": "请用 JSON 格式回复: {\"message\": \"你好，世界!\"}"}
    ]

    print("   发送测试请求...")
    response = client.chat_completion(test_messages, max_tokens=100)

    if "error" in response:
        print(f"   ✗ API 请求失败: {response['error']}")
    else:
        print(f"   ✓ API 请求成功")
        content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
        print(f"   响应内容: {content[:100]}...")

except Exception as e:
    print(f"   ✗ LLM 客户端测试失败: {e}")
    import traceback
    traceback.print_exc()

# 测试 3: 测试搜索
print("\n[3/4] 测试网络搜索...")
try:
    from bing_search import search_bing
    results = search_bing("企业招聘流程", num_results=3)
    print(f"   ✓ 搜索成功，获得 {len(results)} 个结果")
    for r in results:
        print(f"   - {r.get('title', '无标题')[:40]}...")
except Exception as e:
    print(f"   ✗ 搜索测试失败: {e}")

# 测试 4: 测试完整 Agent (预设模式)
print("\n[4/4] 测试完整 Agent (预设模式)...")
try:
    import agent_enhanced as agent
    result = agent.run_full_agent("招聘筛选流程", use_real_llm=False)
    if result:
        print(f"   ✓ Agent 运行成功")
        print(f"   工作流名称: {result.get('workflow_name', '未知')}")
        print(f"   行业: {result.get('industry', '未知')}")
    else:
        print(f"   ✗ Agent 运行失败")
except Exception as e:
    print(f"   ✗ Agent 测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("  测试完成！")
print("="*60)
