#!/usr/bin/env python
"""
测试美食推荐模块的API接口
"""
import requests

BASE_URL = "http://localhost:8000"


def test_get_filters():
    """测试获取筛选条件接口"""
    print("\n=== 测试获取筛选条件接口 ===")
    response = requests.get(f"{BASE_URL}/api/restaurant/filters")
    data = response.json()
    print(f"状态码: {response.status_code}")
    print(f"响应数据: {data}")
    assert response.status_code == 200, "接口返回失败"
    assert "locations" in data, "缺少locations字段"
    assert "cuisines" in data, "缺少cuisines字段"
    assert "spice_levels" in data, "缺少spice_levels字段"
    print("✅ 测试通过")
    return data


def test_recommend_no_filter():
    """测试无筛选条件的推荐"""
    print("\n=== 测试无筛选条件的推荐 ===")
    response = requests.get(f"{BASE_URL}/api/restaurant/recommend")
    data = response.json()
    print(f"状态码: {response.status_code}")
    print(f"响应数据: {data}")
    assert response.status_code == 200, "接口返回失败"
    assert "id" in data, "缺少id字段"
    assert "name" in data, "缺少name字段"
    assert "location" in data, "缺少location字段"
    assert "cuisine" in data, "缺少cuisine字段"
    assert "spice_level" in data, "缺少spice_level字段"
    print("✅ 测试通过")
    return data


def test_recommend_with_filter():
    """测试有筛选条件的推荐"""
    print("\n=== 测试有筛选条件的推荐 ===")
    params = {
        "location": "Houhu",
        "cuisine": "Chinese",
        "spice_level": "Spicy"
    }
    response = requests.get(f"{BASE_URL}/api/restaurant/recommend", params=params)
    data = response.json()
    print(f"请求参数: {params}")
    print(f"状态码: {response.status_code}")
    print(f"响应数据: {data}")
    assert response.status_code == 200, "接口返回失败"
    print("✅ 测试通过")
    return data


def test_refresh():
    """测试刷新推荐接口"""
    print("\n=== 测试刷新推荐接口 ===")
    params = {
        "location": "Lushan",
        "cuisine": "Western",
        "spice_level": "None"
    }
    response = requests.get(f"{BASE_URL}/api/restaurant/refresh", params=params)
    data = response.json()
    print(f"请求参数: {params}")
    print(f"状态码: {response.status_code}")
    print(f"响应数据: {data}")
    assert response.status_code == 200, "接口返回失败"
    print("✅ 测试通过")
    return data


if __name__ == "__main__":
    print("开始测试美食推荐模块API...")
    
    try:
        # 测试获取筛选条件
        filters = test_get_filters()
        
        # 测试无筛选条件的推荐
        restaurant1 = test_recommend_no_filter()
        
        # 测试有筛选条件的推荐
        restaurant2 = test_recommend_with_filter()
        
        # 测试刷新推荐
        restaurant3 = test_refresh()
        
        print("\n" + "=" * 50)
        print("所有测试通过！✅")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
