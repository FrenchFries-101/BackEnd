# 后端接口说明

seed_data.py脚本是用测试的单词做数据库初始化用的，后面有了真实的单词词库和听力材料就换掉；
requirement.txt里是测试这些函数必须的依赖，pip install -r requirements.txt  一键安装；
models.py是单词和听力题相关数据库初始化的代码（左÷啊左÷），记得部署到本地的数据库；
database.py一个纯粹调用数据库的接口，被routers\listening.py、routers\word.py调用，无其他内容。

---
下面是listening和word_list的后端函数，实现在routers\listening.py、routers\word.py中

## 单词模块

单词功能是两级分类结构，调用顺序一般是：先拿一级分类，再拿二级分类，最后拿单词列表。

**获取一级分类** get_categories()

不需要传任何参数，直接调用，返回所有一级分类的名称列表，比如：

```json
["Academic Subject", "Academic English"]
```

---

**获取二级分类** get_subcategories(category: str,)

传一个 `category` 参数（就是上一步拿到的某个一级分类名称），返回该分类下所有二级分类，比如传 `Academic Subject` 会得到：

```json
["Mathematics", "Computer Science", "Civil Engineering", "Mechanical Engineering"]
```

如果传了一个不存在的分类名，会返回 404。

---

**获取单词列表** get_words(category: str, subcategory: str,)

传 `category` 和 `subcategory` 两个参数，返回该分类下所有单词，每个单词包含英文词条和对应释义，比如：

```json
[
  { "english": "derivative", "chinese": "rate of change of a function" },
  { "english": "matrix", "chinese": "rectangular array of numbers" }
]
```

分类下没有单词，或者分类名写错了，会返回 404。

---

## 听力模块

听力功能对应剑桥雅思真题，用户的操作路径是：选册数 → 选 Test → 选 Section → 练习 → 提交分数。接口设计也按这个流程来。

**获取可用册数** get_cambridge_list()

不需要参数，返回数据库里有材料的剑雅册数列表：

```json
[5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
```

---

**获取 Test 列表** get_tests(cambridge_id: int, user_id: int,)

传 `cambridge_id`（册数）和 `user_id`（用户 ID），返回该册所有 Test 的信息。除了 Test 编号和总 Section 数，还会带上这个用户已完成了几个 Section，方便前端展示进度。

```json
[
  { "test_id": 1, "total_sections": 4, "completed_sections": 2 },
  { "test_id": 2, "total_sections": 4, "completed_sections": 0 }
]
```

---

**获取 Section 列表** get_sections(cambridge_id: int, test_id: int,)

传 `cambridge_id` 和 `test_id`，返回该 Test 下所有 Section 的编号和主题名称：

```json
[
  { "section_number": 1, "section_name": "Recommendation for local facilities" },
  { "section_number": 2, "section_name": "Pottery workshop introduction" }
]
```

---

**获取练习材料** get_listening_material(cambridge_id: int, test_id: int, section_id: int,)

传 `cambridge_id`、`test_id`、`section_id`（Section 编号，1 到 4），返回该 Section 的音频路径、题目图片路径，以及完整答案：

```json
{
  "audio": "media/audio/cambridge15_test1_section1.mp3",
  "image": "media/images/cambridge15_test1_section1.png",
  "answers": {
    "1": "A",
    "2": "museum",
    "3": "Tuesday"
  }
}
```

前端用 `audio` 路径播放录音，用 `image` 路径展示题目图片，`answers` 在用户点"查看答案"时展示。

---

**提交分数** submit_score(body: SubmitScoreRequest,)

用户做完题、对完答案后，手动输入答对的题数提交。请求体是 JSON 格式，需要包含册数、Test 编号、Section 编号、答对题数，以及用户 ID：

```json
{
  "cambridge_id": 15,
  "test_id": 1,
  "section_id": 2,
  "score": 8,
  "user_id": 1
}
```

提交成功返回 `{ "status": "success" }`。每次提交都会单独存一条记录，同一个 Section 可以多次练习、多次提交，历史记录都会保留。

---

## 上线前需要准备的东西

### 听力音频和题目图片

目前数据库里存的文件路径都是占位的，真正跑起来需要把实际文件放进来。在项目根目录下建一个 `media` 文件夹，里面分 `audio` 和 `images` 两个子文件夹，文件按下面的规则命名：

- 音频：`cambridge{册数}_test{T}_section{S}.mp3`
- 图片：`cambridge{册数}_test{T}_section{S}.png`

比如剑雅 15 第 2 套 Test 第 3 个 Section，对应的文件就叫 `cambridge15_test2_section3.mp3` 和 `cambridge15_test2_section3.png`，放进去之后接口返回的路径就能对上。

### 真实单词数据

现在 seed 进去的单词是随手造的测试数据。换成真实词表的步骤很简单：把数据整理成下面这个格式，替换掉 `seed_data.py` 里的 `WORDS` 列表，然后重新跑一遍 `python seed_data.py` 就行：

```python
("一级分类", "二级分类", "英文词条", "中文释义"),
```

### 真实答案数据

每个 Section 的答案目前也是占位的。真实答案需要按题号填进去，同样是在 `seed_data.py` 里对应位置修改，然后重新跑 seed 脚本刷新数据库。

---

## 美食推荐模块

美食推荐功能提供基于地点、风味、辣度的智能餐馆推荐服务。

### 获取筛选条件

**接口**: `GET /api/restaurant/filters`

**说明**: 获取所有可用的筛选选项，包括地点、风味、辣度三个维度。

**返回示例**:

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

**字段说明**:
- `value`: 英文存储值，用于后端查询
- `label`: 中文名称，用于前端显示
- `display`: 英文显示文本，用于前端英文界面

---

### 随机推荐餐馆

**接口**: `GET /api/restaurant/recommend`

**说明**: 根据筛选条件随机推荐一家餐馆。

**请求参数** (全部可选):
- `location`: 地点筛选 (可选值: Houhu, Lushan, Canteen, Tianma)
- `cuisine`: 风味筛选 (可选值: Chinese, Western, Japanese, Korean, FastFood, Others)
- `spice_level`: 辣度筛选 (可选值: None, Mild, Spicy)

**请求示例**:

```bash
# 无筛选条件，随机推荐
GET /api/restaurant/recommend

# 按地点筛选
GET /api/restaurant/recommend?location=Houhu

# 多条件筛选
GET /api/restaurant/recommend?location=Houhu&cuisine=Chinese&spice_level=Spicy
```

**返回示例**:

```json
{
  "id": 4,
  "name": "遇见牛肉钵火锅",
  "location": "Houhu",
  "cuisine": "Chinese",
  "spice_level": "Spicy"
}
```

**字段说明**:
- `id`: 餐馆ID
- `name`: 餐馆中文名称
- `location`: 地点（英文存储值）
- `cuisine`: 风味（英文存储值）
- `spice_level`: 辣度（英文存储值）

**逻辑说明**:
1. 根据传入的筛选条件查询符合条件的餐馆
2. 使用 `ORDER BY RAND() LIMIT 1` 随机返回一条记录
3. 如果筛选结果为空，返回数据库中的任意一条餐馆记录
4. 所有筛选参数都是可选的，可以单独使用或组合使用

---

### 刷新推荐

**接口**: `GET /api/restaurant/refresh`

**说明**: 在当前筛选条件下刷新，获取新的随机推荐。

**请求参数**: 与 `/recommend` 相同

**返回格式**: 与 `/recommend` 相同

**使用场景**: 用户想要在相同筛选条件下尝试其他餐馆时调用。

---

### 字段对照表

**地点选项**:

| 中文名 | 英文存储值 | 前端英文显示 |
|-------|-----------|-------------|
| 后湖小区 | Houhu | Houhu District |
| 麓山南路 | Lushan | Lushan South Rd |
| 学校食堂 | Canteen | School Canteen |
| 天马小区 | Tianma | Tianma District |

**风味选项**:

| 中文名 | 英文存储值 | 前端英文显示 |
|-------|-----------|-------------|
| 中餐 | Chinese | Chinese |
| 西餐 | Western | Western |
| 日料 | Japanese | Japanese |
| 韩餐 | Korean | Korean |
| 快餐 | FastFood | Fast Food |
| 其他 | Others | Others |

**辣度选项**:

| 中文名 | 英文存储值 | 前端英文显示 |
|-------|-----------|-------------|
| 不辣 | None | None |
| 微辣 | Mild | Mild |
| 辣 | Spicy | Spicy |

---

### 数据库初始化

美食推荐模块的数据库会在服务启动时自动初始化。如需手动初始化或重置数据，可以运行：

```bash
python init_restaurant_db.py
```

该脚本会：
1. 创建 `restaurant` 数据表
2. 初始化包含26家测试餐馆的种子数据

---

### 前端集成建议

1. **页面加载时**: 调用 `/api/restaurant/filters` 获取所有筛选选项
2. **用户选择筛选条件**: 在本地保存用户的选择
3. **点击"确认推荐"**: 调用 `/api/restaurant/recommend` 带上筛选参数
4. **点击"刷新推荐"**: 调用 `/api/restaurant/refresh` 带上相同的筛选参数

---

### 扩展说明

美食推荐模块位于 `recommendation/` 目录下，采用模块化设计，便于扩展。后续可在此目录下添加：
- `changsha.py` - 长沙生活信息推荐
- `dundee.py` - 邓迪留学信息推荐

所有推荐类功能都统一在 `recommendation` 模块下管理，保持代码结构清晰。

---

## 长沙城市信息模块

长沙城市信息模块提供天气查询和景点推荐功能。

### 获取天气信息

**接口**: `GET /api/city/weather`

**说明**: 获取指定月份的长沙天气信息，默认返回当前月份。

**请求参数** (可选):
- `month`: 月份 (1-12)，不传则返回当前月份

**请求示例**:

```bash
# 获取当前月份天气
GET /api/city/weather

# 获取4月天气
GET /api/city/weather?month=4
```

**返回示例**:

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

**支持的月份**:
- 3月: "Rainy season, watch out riding e-scooters!"
- 4月: "Rainy but warming up, enjoy spring flowers!"
- 5月: "Sunny and warm, perfect for outdoor activities!"

---

### 获取景点信息

**接口**: `GET /api/city/sights`

**说明**: 获取长沙景点信息列表。

**请求参数** (可选):
- `limit`: 返回景点数量，默认3条，范围1-100

**请求示例**:

```bash
# 获取默认3条景点
GET /api/city/sights

# 获取2条景点
GET /api/city/sights?limit=2
```

**返回示例**:

```json
[
  {
    "title": "Hunan Botanical Garden",
    "description": "Enjoy flowers and beautiful garden scenery",
    "icon_url": "static/icons/flower.gif",
    "image_url": "static/images/hunan_garden.png",
    "address": "Kaifu District, Changsha, Hunan",
    "copyright": "https://baike.baidu.com/item/..."
  },
  {
    "title": "Yuelu Mountain",
    "description": "Hiking, lake view, historical culture",
    "icon_url": "static/icons/mountain.gif",
    "image_url": "static/images/yuelu_mountain.png",
    "address": "Yuelu District, Changsha, Hunan",
    "copyright": "https://ibaotu.com/sucai/..."
  },
  {
    "title": "Orange Isle",
    "description": "Walking, sightseeing, night fireworks show",
    "icon_url": "static/icons/island.gif",
    "image_url": "static/images/juzizhou.png",
    "address": "Xiangjiang River, Changsha, Hunan",
    "copyright": "https://haowallpaper.com/..."
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

---

### 数据库表结构

#### 天气表 (city_weather)
```sql
CREATE TABLE city_weather (
    id INT PRIMARY KEY AUTO_INCREMENT,
    month INT NOT NULL,               -- 月份 3,4,5
    description VARCHAR(255) NOT NULL,-- 英文天气描述
    icon VARCHAR(100) NOT NULL        -- gif 或 icon 文件名
);
```

#### 景点表 (city_sights)
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

---

### 静态资源准备

需要在 `static/` 目录下准备以下文件：

#### 天气图标 (static/icons/)
- `rain.gif` - 雨天图标
- `sunny.gif` - 晴天图标

#### 景点资源
- `flower.gif` - 植物园图标
- `static/images/hunan_garden.png` - 湖南省植物园图片

- `mountain.gif` - 山岳图标
- `static/images/yuelu_mountain.png` - 岳麓山图片

- `island.gif` - 岛屿图标
- `static/images/juzizhou.png` - 橘子洲图片

---

### 数据库初始化

城市信息模块的数据库会在服务启动时自动初始化。如需手动初始化：

```bash
python init_city_db.py
```

---

### 前端集成建议

1. **天气显示**:
   - 页面加载时调用 `/api/city/weather` 获取当前月份天气
   - 根据月份调用 `/api/city/weather?month=X` 获取对应月份天气
   - 使用返回的 `icon_url` 显示天气动画图标

2. **景点展示**:
   - 调用 `/api/city/sights?limit=3` 获取景点列表
   - 展示景点图片和描述
   - 点击景点可查看详细信息

3. **版权信息**:
   - 使用景点图片时，显示 `copyright` 字段的版权链接

---

### 测试

运行API测试：

```bash
python test_city_api.py
```

---

### 扩展说明

城市信息模块位于 `recommendation/` 目录下，后续可扩展：
- 添加更多月份的天气数据
- 添加更多景点信息
- 支持景点分类和筛选
- 添加景点评分和评论功能

与美食推荐模块 (`restaurant.py`) 同级，统一在 `recommendation` 模块下管理。
