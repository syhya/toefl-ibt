# 如何导入自己的资源

[English](IMPORTING.md) | 简体中文

项目支持两条路径。**新用户建议使用可移植 JSON 资源包。** 历史 PDF/OCR 导入器只针对原私有资料集合，需要匹配的目录和私有校核清单；把任意 PDF 放入 `data/` 不会自动变成交互试卷。

## 先体验内置演示

安装后运行：

```sh
npm run demo
npm start
```

也可在空题库首页点击 **Try the demo / 体验演示题**。[`examples/demo/pack.json`](../examples/demo/pack.json) 包含四屏原创演示：阅读选择、缺字填空、邮件与讨论。演示较短、纯文字、不限时，不是官方试题。可以和私有资料共存；重复安装相同内容不会重复添加。

## 网页导入纯文字 JSON

进入 **Help & setup / 使用与导入指南**，选择 UTF-8 `.json` 资源包并导入。网页入口只支持纯文字；若引用任何本地图片、音视频或 PDF，请用下方命令行，便于读取同目录资产。活动严格练习结束后再通过网页导入。

套题标题按你提供的字符串显示。界面切换语言不翻译自定义题目或标题；需要时可在标题字符串中同时写两种语言。

## 导入含媒体的文件夹

在仓库外或被 Git 忽略的本地位置准备：

```text
my-practice/
  pack.json
  audio/prompt.mp3
  images/map.png
  source.pdf
```

在项目根目录运行：

```sh
npm run import:pack -- "/absolute/path/to/my-practice/pack.json"
```

导入器先验证 JSON 与文件，再复制到按版本保存的本地目录并注册套题。刷新网站，在补充资料/全部资料中选择标题。导入后日常使用不再需要原文件夹保持挂载；既有源资料与 `storage/` 答案不会被覆盖。

同一 ID 的内容更新使用：

```sh
npm run import:pack -- "/absolute/path/to/my-practice/pack.json" --replace
```

已有 ID 但内容不同且未指定 `--replace` 时会拒绝；相同内容保持不变。替换产生独立来源/媒体路径的新版本，旧会话保留冻结题面；新建练习才使用新版。历史记录仍引用的版本文件应继续保留。

## 最小完整示例

保存为 `pack.json`。以下是原创示例，不是 TOEFL 原题：

```json
{
  "schemaVersion": 1,
  "id": "my-first-pack",
  "title": "My first reading practice",
  "sections": [
    {
      "id": "reading",
      "questions": [
        {
          "id": "opening-hours",
          "type": "choice",
          "taskType": "daily_life",
          "passage": "The community center opens at 10 a.m. on Sundays.",
          "prompt": "When does the center open on Sunday?",
          "choices": [
            {"id": "A", "text": "At 9 a.m."},
            {"id": "B", "text": "At 10 a.m."}
          ],
          "answer": "B"
        }
      ]
    }
  ]
}
```

`title` 必须是字符串，不能写成翻译对象。JSON 使用双引号，不允许注释或末尾逗号。简单 `passage` 会自动转换为结构化展示块。

## 格式合同

实际校验见 [`backend/packs.py`](../backend/packs.py)，可运行示例见 [`examples/demo/pack.json`](../examples/demo/pack.json)。不要把生成后的 exam JSON 当输入，它包含会被拒绝的内部字段。

| 字段 | 要求 |
| --- | --- |
| `schemaVersion` | 数字 `1` |
| `id` | 1–48 个小写字母、数字、连字符或下划线；以字母/数字开头，版本间保持稳定 |
| `title` | 非空字符串，最多 200 字符 |
| `sections` | 1–4 个不重复部分，各含 `id` 和 1–200 道 `questions` |
| 部分 `id` | `reading`、`listening`、`writing`、`speaking` |
| 题目 `id` | 同样的标识格式，全包唯一 |
| 题目 `type` | 必须与所属部分匹配，见下表 |
| 题目 `prompt` | 非空字符串 |
| `taskType` | 可选分类，例如 `daily_life`、`academic_passage` |
| `source` | 可选 `{ "file": "source.pdf", "page": 1 }`，物理页码从 1 开始 |

| 部分 | 允许的题型 |
| --- | --- |
| 阅读 | `choice`、`cloze` |
| 听力 | `choice` |
| 写作 | `build_sentence`、`email`、`academic_discussion`、`picture_writing` |
| 口语 | `listen_repeat`、`interview`、`read_aloud` |

当前每道听力和口语题（包括 `read_aloud`）都要求本地音频/视频。资源包统一为补充、不限时辅助练习；有媒体也不会取得完整严格或官方来源资格。

版本 1 允许的题目字段：`id`、`type`、`taskType`、`prompt`、`passage`、`passageTemplate`、`context`、`choices`、`answer`、`blanks`、`tokens`、`slots`、`extraTokens`、`fixedTokens`、`recommendedWords`、`wordLimit`、`interaction`、`stemBlocks`、`assets`、`audio`、`source`、`transcript`。未知字段会拒绝；不要添加 `strictEligible`、`expectedTokenOrder`、截止时间、生成 URL 或任意 CSS。

### 选择、填词与组句

选择题需要 2–8 个 `id` 唯一、`text` 非空的选项。可选 `answer` 必须等于某个选项 ID；无可靠键时省略，不猜答案。

填词 `passageTemplate` 中每个 `{{blank-id}}` 恰好出现一次，原给字母留在模板里。每空需要唯一 `id` 和 1–30 的整数 `length`，`prefix`、`suffix`、`number` 及可选缺失字母 `answer` 描述输入。答案长度要等于缺字数，例如：

```json
{
  "id": "garden",
  "type": "cloze",
  "prompt": "Enter only the missing letters.",
  "passageTemplate": "Volunteers wa{{b1}} the plants.",
  "blanks": [{"id": "b1", "number": 1, "prefix": "wa", "length": 3, "answer": "ter"}]
}
```

组句需要非空字符串 `tokens` 与 `slots`。可填槽为 `{ "id": "s1" }`，已给文字为 `{ "fixed": "." }`。保留重复词、干扰词、固定词和标点；`answer` 可提供复盘/核分参考句。答案不要写进 `prompt` 或 `stemBlocks`。

### 音视频、图片与原 PDF

```json
{
  "audio": {"file": "audio/prompt.mp3"},
  "assets": [{"file": "images/map.png", "alt": "Map showing the entrance and reading room"}],
  "source": {"file": "source.pdf", "page": 1}
}
```

这些是可选题目字段，但听力/口语需要媒体。音频时长由文件实测，不以手填估值为准。图片必须能解码且有具体 `alt`。未自定义 `stemBlocks` 时图在原文后；自定义时需用 `essential_visual` 块或对话头像索引引用。

文件路径相对于 `pack.json`，拒绝绝对路径、`..`、隐藏路径片段、反斜杠及目录外路径。支持扩展名 `.pdf`、`.txt`、`.json`、`.png`、`.jpg`、`.jpeg`、`.webp`、`.mp3`、`.wav`、`.ogg`、`.m4a`、`.mp4`、`.webm`，仍需通过音频/图片校验，改扩展名不是格式转换。JSON 小于 2 MiB，单文件小于 100 MiB，总引用文件小于 200 MiB。

PDF 是来源参考，不会自动 OCR 成题。摘要让字节可追踪，不证明官方作者、答案正确或版权许可；导入和再分发内容由你负责。

### 高级排版

`stemBlocks` 支持段落、说明、标题、消息、对话、列表、表格、高亮句、表单图和必要视觉。演示讨论有教授和两名学生。要使用自己的授权头像，将图片放入 `assets`，在对应 `dialogue` 发言中添加从 0 开始的 `avatarAssetIndex`，保持姓名和发言原顺序。校验见 [`backend/presentation.py`](../backend/presentation.py)；不支持 HTML/脚本，大多数资源包只需普通 JSON。

## 安装文件和备份

```text
data/user-packs/<id>/<revision>/   已复制的清单和资源
generated/pack-catalogs/<id>.json  资源包注册信息
generated/exams/user-<id>.json    当前规范化套题
storage/                         既有答案与录音
```

运行时合并自定义注册表与私有基础题库。完整备份 `data/`、`generated/` 和 `storage/` 才能保留资源及历史。导入不向远程上传；存储一致性和待上传录音见[使用指南](USER_GUIDE.zh-CN.md)。

## 原私有 PDF/OCR 资料

高级导入器只支持原已知目录，要求合法获取的原文件及匹配的私有 `scripts/verified_*.json`，这些不随公开代码分发。新用户请用可移植资源包。

```sh
.venv/bin/python -m pip install -r requirements-import.txt
tesseract --list-langs
.venv/bin/python scripts/import_materials.py --jobs 4
```

OCR 需要外部 Tesseract 和 `eng` 语言包。`--ocr-all` 扩大扫描页提取范围，但提取不等于来源校核。保持原目录/文件名，重导入前先备份；日常启动复用生成结果，不需要每次 OCR。

流程检查原文件 SHA、页码、内容身份、校核选项/缺字、结构块和媒体/视觉来源。缺清单或不匹配时关闭相关严格范围，不编造内容。必要时用 `.venv/bin/python scripts/extract_exam_ui.py` 重建界面资产；用 `.venv/bin/python scripts/attach_teacher_audio.py` 离线核对已安装教师原音。方法和日期范围见[资料说明](MATERIALS.zh-CN.md)、[资料验收](DATA_QA.zh-CN.md)和[媒体切分](MEDIA_SEGMENTS.zh-CN.md)。
