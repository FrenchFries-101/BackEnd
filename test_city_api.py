#!/usr/bin/env python
"""
测试城市信息模块的API接口
"""
import requests

BASE_URL = "http://localhost:8000"


def test_get_weather_current_month():
    """测试获取当前月份天气"""
    print("\n=== 测试获取当前月份天气 ===")
    response = requests.get(f"{BASE_URL}/api/city/weather")
    data = response.json()
    print(f"状态码: {response.status_code}")
    print(f"响应数据: {data}")
    assert response.status_code == 200, "接口返回失败"
    assert "month" in data, "缺少month字段"
    assert "description" in data, "缺少description字段"
    assert "icon_url" in data, "缺少icon_url字段"
    print("✅ 测试通过")
    return data


def test_get_weather_specific_month():
    """测试获取指定月份天气"""
    print("\n=== 测试获取指定月份天气 ===")
    for month in [3, 4, 5]:
        response = requests.get(f"{BASE_URL}/api/city/weather?month={month}")
        data = response.json()
        print(f"月份 {month}:")
        print(f"  状态码: {response.status_code}")
        print(f"  响应数据: {data}")
        assert response.status_code == 200, "接口返回失败"
        assert data["month"] == month, f"返回的月份不匹配，期望 {month}"
    print("✅ 测试通过")
    return data


def test_get_sights_default():
    """测试获取景点信息（默认返回3条）"""
    print("\n=== 测试获取景点信息（默认3条） ===")
    response = requests.get(f"{BASE_URL}/api/city/sights")
    data = response.json()
    print(f"状态码: {response.status_code}")
    print(f"返回数量: {len(data)}")
    for sight in data:
        print(f"  - {sight['title']}: {sight['description']}")
    assert response.status_code == 200, "接口返回失败"
    assert isinstance(data, list), "返回数据应该是列表"
    assert len(data) == 3, "默认应该返回3条数据"
    for sight in data:
        assert "title" in sight, "缺少title字段"
        assert "description" in sight, "缺少description字段"
    print("✅ 测试通过")
    return data


def test_get_sights_custom_limit():
    """测试获取景点信息（自定义数量）"""
    print("\n=== 测试获取景点信息（自定义数量） ===")
    for limit in [1, 2, 3]:
        response = requests.get(f"{BASE_URL}/api/city/sights?limit={limit}")
        data = response.json()
        print(f"限制数量 {limit}:")
        print(f"  状态码: {response.status_code}")
        print(f"  实际返回: {len(data)} 条")
        assert response.status_code == 200, "接口返回失败"
        assert len(data) == limit, f"返回数量不匹配，期望 {limit} 条"
    print("✅ 测试通过")
    return data


if __name__ == "__main__":
    print("开始测试城市信息模块API...")
    
    try:
        # 测试获取当前月份天气
        weather1 = test_get_weather_current_month()
        
        # 测试获取指定月份天气
        weather2 = test_get_weather_specific_month()
        
        # 测试获取景点信息（默认）
        sights1 = test_get_sights_default()
        
        # 测试获取景点信息（自定义）
        sights2 = test_get_sights_custom_limit()
        
        print("\n" + "=" * 50)
        print("所有测试通过！✅")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
