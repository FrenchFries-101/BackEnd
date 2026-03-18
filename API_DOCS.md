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
