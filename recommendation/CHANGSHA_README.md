# 长沙城市信息模块 (Changsha City Info Module)

## 功能概述
提供长沙城市的天气信息和景点推荐功能，帮助用户了解长沙的天气状况和著名景点。

## 接口文档

### 1. 获取天气信息
**接口**: `GET /api/city/weather`

**功能**: 获取指定月份的天气信息，默认返回当前月份

**请求参数** (可选):
- `month`: 月份 (1-12)，默认返回当前月份

**响应示例**:
```json
{
  "month": 4,
  "description": "Rainy but warming up, enjoy spring flowers!",
  "icon_url": "static/icons/rain.gif"
}
```

**字段说明**:
- `month`: 月份
- `description`: 英文天气描述
- `icon_url`: 天气图标URL

**逻辑说明**:
1. 如果不指定月份，使用当前月份
2. 查询指定月份的天气信息
3. 如果没有找到，返回数据库中的第一条天气记录

### 2. 获取景点信息
**接口**: `GET /api/city/sights`

**功能**: 获取长沙城市景点信息

**请求参数** (可选):
- `limit`: 返回景点数量，默认3条，最小1条，最大100条

**响应示例**:
```json
[
  {
    "title": "Hunan Botanical Garden",
    "description": "Enjoy flowers and beautiful garden scenery",
    "icon_url": "static/icons/flower.gif",
    "image_url": "static/images/hunan_garden.png",
    "address": "Kaifu District, Changsha, Hunan",
    "copyright": "https://baike.baidu.com/item/%E6%B9%96%E5%8D%97%E7%9C%81%E6%A3%AE%E6%9E%97%E6%A4%8D%E7%89%A9%E5%9B%AD/6068095"
  },
  {
    "title": "Yuelu Mountain",
    "description": "Hiking, lake view, historical culture",
    "icon_url": "static/icons/mountain.gif",
    "image_url": "static/images/yuelu_mountain.png",
    "address": "Yuelu District, Changsha, Hunan",
    "copyright": "https://ibaotu.com/sucai/19434921.html"
  },
  {
    "title": "Orange Isle",
    "description": "Walking, sightseeing, night fireworks show",
    "icon_url": "static/icons/island.gif",
    "image_url": "static/images/juzizhou.png",
    "address": "Xiangjiang River, Changsha, Hunan",
    "copyright": "https://haowallpaper.com/homeViewLook/17690785630768512"
  }
]
```

**字段说明**:
- `title`: 景点名称（英文）
- `description`: 景点描述（英文）
- `icon_url`: 景点小图标URL
- `image_url`: 景点图片URL
- `address`: 景点地址（英文）
- `copyright`: 图片版权网址

## 数据库表结构

### 天气表 (city_weather)
```sql
CREATE TABLE city_weather (
    id INT PRIMARY KEY AUTO_INCREMENT,
    month INT NOT NULL,               -- 月份 3,4,5
    description VARCHAR(255) NOT NULL,-- 英文天气描述
    icon VARCHAR(100) NOT NULL        -- gif 或 icon 文件名
);
```

### 景点表 (city_sights)
```sql
CREATE TABLE city_sights (
    id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(100) NOT NULL,      -- 景点名称英文
    description VARCHAR(255) NOT NULL,-- 描述英文
    icon VARCHAR(100),                 -- 小 gif icon 文件
    image VARCHAR(255),                -- 图片文件路径
    address VARCHAR(255),              -- 地址英文
    copyright VARCHAR(255)             -- 图片版权网址
);
```

## 初始化数据

### 天气数据
- 3月: "Rainy season, watch out riding e-scooters!" + rain.gif
- 4月: "Rainy but warming up, enjoy spring flowers!" + rain.gif
- 5月: "Sunny and warm, perfect for outdoor activities!" + sunny.gif

### 景点数据
1. Hunan Botanical Garden - 湖南省植物园
2. Yuelu Mountain - 岳麓山
3. Orange Isle - 橘子洲

## 文件结构
```
recommendation/
├── changsha_models.py      # 数据库模型
├── changsha_schemas.py     # Pydantic 数据模型
├── changsha.py            # API 路由
└── changsha_seed.py       # 种子数据初始化
```

## 使用示例

### Python 请求示例
```python
import requests

# 获取当前月份天气
response = requests.get("http://localhost:8000/api/city/weather")
weather = response.json()

# 获取4月天气
response = requests.get("http://localhost:8000/api/city/weather?month=4")
weather = response.json()

# 获取景点信息（默认3条）
response = requests.get("http://localhost:8000/api/city/sights")
sights = response.json()

# 获取景点信息（自定义数量）
response = requests.get("http://localhost:8000/api/city/sights?limit=2")
sights = response.json()
```

### curl 请求示例
```bash
# 获取当前月份天气
curl http://localhost:8000/api/city/weather

# 获取指定月份天气
curl http://localhost:8000/api/city/weather?month=4

# 获取景点信息
curl http://localhost:8000/api/city/sights

# 获取指定数量的景点
curl http://localhost:8000/api/city/sights?limit=2
```

## 静态资源说明

### 需要准备以下静态文件：

#### 天气图标 (static/icons/)
- `rain.gif` - 雨天图标
- `sunny.gif` - 晴天图标

#### 景点资源 (static/icons/ 和 static/images/)
- `flower.gif` - 植物园图标
- `static/images/hunan_garden.png` - 植物园图片

- `mountain.gif` - 山岳图标
- `static/images/yuelu_mountain.png` - 岳麓山图片

- `island.gif` - 岛屿图标
- `static/images/juzizhou.png` - 橘子洲图片

## 数据库初始化

城市信息模块的数据库会在服务启动时自动初始化。如需手动初始化或重置数据，可以运行：

```bash
python init_city_db.py
```

该脚本会：
1. 创建 `city_weather` 和 `city_sights` 数据表
2. 初始化天气和景点的种子数据

## 测试

运行API测试脚本：

```bash
python test_city_api.py
```

测试内容包括：
- 获取当前月份天气
- 获取指定月份天气（3月、4月、5月）
- 获取景点信息（默认数量）
- 获取景点信息（自定义数量）

## 前端集成建议

1. **页面加载时**: 调用 `/api/city/weather` 获取当前月份天气
2. **季节切换时**: 调用 `/api/city/weather?month=X` 获取对应月份天气
3. **景点展示**: 调用 `/api/city/sights?limit=3` 获取景点列表
4. **显示天气图标**: 使用返回的 `icon_url` 显示天气动图
5. **显示景点**: 遍历景点列表，显示图片和描述
6. **版权信息**: 在使用景点图片时，显示 `copyright` 字段的版权链接

## 扩展说明

本模块位于 `recommendation/` 目录下，与美食推荐模块 (`restaurant.py`) 同级。

后续可以扩展：
- 添加更多月份的天气数据
- 添加更多景点信息
- 支持景点分类（自然风光、历史古迹等）
- 添加景点评分和评论功能
