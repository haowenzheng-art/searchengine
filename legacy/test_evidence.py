"""测试预设数据的证据链"""
from workflow_data import get_preset, PRESETS

print("="*60)
print("测试预设数据证据链")
print("="*60)

for key, name in PRESETS.items():
    data = get_preset(key)
    print(f"\n预设: {key}")
    print(f"  名称: {data.get('name')}")
    print(f"  证据链数量: {len(data.get('evidence_urls', []))}")
    if data.get('evidence_urls'):
        for i, e in enumerate(data['evidence_urls'], 1):
            print(f"    {i}. {e.get('title')}")
            print(f"       {e.get('url')}")
    else:
        print("    ⚠️ 没有证据链！")

print("\n" + "="*60)
