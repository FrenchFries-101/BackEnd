#!/usr/bin/env python
"""测试API返回的实际数据格式"""
import requests
import json

BASE_URL = "http://localhost:8000"

print("=== 测试天气API ===")
response = requests.get(f"{BASE_URL}/api/city/weather")
print(f"状态码: {response.status_code}")
data = response.json()
print(f"返回数据: {json.dumps(data, indent=2, ensure_ascii=False)}")
print(f"icon_url: {data['icon_url']}")
print(f"完整URL应该是: {BASE_URL}/{data['icon_url']}")
print()

print("=== 测试景点API ===")
response = requests.get(f"{BASE_URL}/api/city/sights")
print(f"状态码: {response.status_code}")
sights = response.json()
print(f"返回数据: {json.dumps(sights, indent=2, ensure_ascii=False)}")
print()

if sights:
    first_sight = sights[0]
    print(f"第一个景点:")
    print(f"  icon_url: {first_sight['icon_url']}")
    print(f"  完整URL: {BASE_URL}/{first_sight['icon_url']}")
    print(f"  image_url: {first_sight['image_url']}")
    print(f"  完整URL: {BASE_URL}/{first_sight['image_url']}")
