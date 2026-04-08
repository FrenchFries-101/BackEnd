import urllib.request
import urllib.error
import json

BASE_URL = "http://localhost:8000/api/restaurant"

def test_api():
    print("=" * 60)
    print("测试餐厅推荐API")
    print("=" * 60)
    print()

    # 测试1: Houhu + Western（应该返回404）
    print("测试1: Houhu + Western（数据库中没有这个组合）")
    print("-" * 60)
    try:
        params = urllib.parse.urlencode({"location": "Houhu", "cuisine": "Western"})
        url = f"{BASE_URL}/recommend?{params}"
        req = urllib.request.Request(url)

        try:
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                print(f"状态码: {response.status}")
                print(f"返回数据: {data}")
                if data.get("location") != "Houhu" or data.get("cuisine") != "Western":
                    print(f"❌ 错误：返回的餐厅不符合筛选条件！")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"✅ 状态码: {e.code}（符合预期，没有符合条件的餐厅）")
                print(f"错误信息: {e.read().decode()}")
            else:
                print(f"❌ HTTP错误: {e.code}")
        except Exception as e:
            print(f"❌ 错误: {e}")
    except Exception as e:
        print(f"请求失败: {e}")

    print()
    print("测试2: Houhu + Chinese（应该返回Houhu的中餐厅）")
    print("-" * 60)
    try:
        params = urllib.parse.urlencode({"location": "Houhu", "cuisine": "Chinese"})
        url = f"{BASE_URL}/recommend?{params}"
        req = urllib.request.Request(url)

        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            print(f"状态码: {response.status}")
            print(f"返回数据: {data}")
            if data.get("location") == "Houhu" and data.get("cuisine") == "Chinese":
                print(f"✅ 正确：返回的餐厅符合筛选条件")
            else:
                print(f"❌ 错误：返回的餐厅不符合筛选条件！")
    except Exception as e:
        print(f"请求失败: {e}")

    print()
    print("测试3: Houhu + FastFood（应该返回404）")
    print("-" * 60)
    try:
        params = urllib.parse.urlencode({"location": "Houhu", "cuisine": "FastFood"})
        url = f"{BASE_URL}/recommend?{params}"
        req = urllib.request.Request(url)

        try:
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                print(f"状态码: {response.status}")
                print(f"返回数据: {data}")
                if data.get("location") != "Houhu" or data.get("cuisine") != "FastFood":
                    print(f"❌ 错误：返回的餐厅不符合筛选条件！")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"✅ 状态码: {e.code}（符合预期，没有符合条件的餐厅）")
                print(f"错误信息: {e.read().decode()}")
            else:
                print(f"❌ HTTP错误: {e.code}")
    except Exception as e:
        print(f"请求失败: {e}")

    print()
    print("=" * 60)

if __name__ == "__main__":
    test_api()
