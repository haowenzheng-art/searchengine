"""测试预设API返回的数据"""
from workflow_data import get_preset

print("测试预设数据:")
data = get_preset('recruitment')
print(f"名称: {data.get('name')}")
print(f"证据链数量: {len(data.get('evidence_urls', []))}")
print("\n证据链内容:")
for e in data.get('evidence_urls', []):
    print(f"  - {e.get('title')}: {e.get('url')}")

print("\n" + "="*60)
print("数据keys:", list(data.keys()))
