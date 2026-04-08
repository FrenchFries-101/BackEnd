# 美食推荐模块 (Restaurant Recommendation Module)

## 功能概述
提供美食推荐功能的API接口，支持按地点、风味、辣度进行筛选，并随机推荐餐馆。

## 接口文档

### 1. 获取筛选条件
**接口**: `GET /api/restaurant/filters`

**功能**: 获取所有可用的筛选选项

**响应示例**:
```json
{
  "locations": [
    {"value":"Houhu","label":"后湖小区","display":"Houhu District"},
    {"value":"Lushan","label":"麓山南路","display":"Lushan South Rd"},
    {"value":"Canteen","label":"学校食堂","display":"School Canteen"},
    {"value":"Tianma","label":"天马小区","display":"Tianma District"}
  ],
  "cuisines": [
    {"value":"Chinese","label":"中餐","display":"Chinese"},
    {"value":"Western","label":"西餐","display":"Western"},
    {"value":"Japanese","label":"日料","display":"Japanese"},
    {"value":"Korean","label":"韩餐","display":"Korean"},
    {"value":"FastFood","label":"快餐","display":"Fast Food"},
    {"value":"Others","label":"其他","display":"Others"}
  ],
  "spice_levels": [
    {"value":"None","label":"不辣","display":"None"},
    {"value":"Mild","label":"微辣","display":"Mild"},
    {"value":"Spicy","label":"辣","display":"Spicy"}
  ]
}
```

### 2. 随机推荐餐馆
**接口**: `GET /api/restaurant/recommend`

**功能**: 根据筛选条件随机推荐一条餐馆记录

**请求参数** (可选):
- `location`: 地点筛选 (如: "Houhu", "Lushan", "Canteen", "Tianma")
- `cuisine`: 风味筛选 (如: "Chinese", "Western", "Japanese", "Korean", "FastFood", "Others")
- `spice_level`: 辣度筛选 (如: "None", "Mild", "Spicy")

**响应示例**:
```json
{
  "id": 4,
  "name": "遇见牛肉钵火锅",
  "location": "Houhu",
  "cuisine": "Chinese",
  "spice_level": "Spicy"
}
```

**逻辑说明**:
1. 根据传入的筛选条件查询符合条件的餐馆
2. 随机返回一条记录 (SQL: ORDER BY RAND() LIMIT 1)
3. 如果筛选结果为空，返回数据库中的任意一条餐馆记录

### 3. 刷新推荐
**接口**: `GET /api/restaurant/refresh`

**功能**: 在当前筛选条件下刷新一条新的随机推荐

**请求参数**: 与 `/recommend` 相同

**响应格式**: 与 `/recommend` 相同

## 数据库表结构

```sql
CREATE TABLE restaurant (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,        -- 中文餐馆名字
    location VARCHAR(50) NOT NULL,     -- 地点英文值
    cuisine VARCHAR(50) NOT NULL,      -- 风味英文值
    spice_level VARCHAR(10) NOT NULL   -- 辣度英文值
);
```

## 字段对应表

### 地点
| 中文 | 英文存储值 | 前端显示英文 |
|------|-----------|------------|
| 后湖小区 | Houhu | Houhu District |
| 麓山南路 | Lushan | Lushan South Rd |
| 学校食堂 | Canteen | School Canteen |
| 天马小区 | Tianma | Tianma District |

### 风味
| 中文 | 英文存储值 | 前端显示英文 |
|------|-----------|------------|
| 中餐 | Chinese | Chinese |
| 西餐 | Western | Western |
| 日料 | Japanese | Japanese |
| 韩餐 | Korean | Korean |
| 快餐 | FastFood | Fast Food |
| 其他 | Others | Others |

### 辣度
| 中文 | 英文存储值 | 前端显示英文 |
|------|-----------|------------|
| 不辣 | None | None |
| 微辣 | Mild | Mild |
| 辣 | Spicy | Spicy |

## 文件结构
```
recommendation/
├── __init__.py           # 模块初始化
├── models.py             # 数据库模型
├── schemas.py            # Pydantic 数据模型
├── restaurant.py         # API 路由
└── seed.py              # 种子数据初始化
```

## 使用示例

### Python 请求示例
```python
import requests

# 获取筛选条件
response = requests.get("http://localhost:8000/api/restaurant/filters")
filters = response.json()

# 随机推荐（无筛选）
response = requests.get("http://localhost:8000/api/restaurant/recommend")
restaurant = response.json()

# 筛选推荐（后湖小区 + 中餐 + 辣）
response = requests.get("http://localhost:8000/api/restaurant/recommend?location=Houhu&cuisine=Chinese&spice_level=Spicy")
restaurant = response.json()
```

### 前端集成说明
1. 页面加载时调用 `/api/restaurant/filters` 获取所有筛选条件
2. 用户选择筛选条件后，调用 `/api/restaurant/recommend` 获取推荐
3. 点击"刷新推荐"时，调用 `/api/restaurant/refresh` 获取新的推荐

## 扩展说明
本模块位于 `recommendation` 目录下，后续可在此目录下添加：
- `changsha.py` - 长沙信息提供模块
- `dundee.py` - 邓迪信息提供模块

所有推荐类功能都统一在 `recommendation` 模块下管理。
