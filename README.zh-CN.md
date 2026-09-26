# TOEFL Local Lab

[English](README.md) | 简体中文

**Powered by GPT-6 Astra。** 本项目目前在开发过程中使用 GPT-6 Astra，用于测试当前模型在完整应用开发、测试、调试和文档维护中的能力边界。日常练习在本地运行，无需调用模型 API。

支持中英文导航的本地 TOEFL 风格练习网站，提供结构化题目、写作编辑器、已支持校核资料的倒计时、麦克风录音与历史复盘。采用 **React + TypeScript + Vite、FastAPI、SQLite**。安装依赖和导入资源后，日常练习可离线运行，不需要账号或云端 AI。

**默认样题为 TOEFL iBT® Practice Test 1，题目来源：[TOEFL iBT® Practice Test 1](https://www.in.ets.org/content/dam/ets-india/pdfs/toefl/toefl-ibt-full-length-practice-test-1.pdf)。** 原题来自 ETS 网站上的这份 PDF，文档中统一使用英文资料名称 **TOEFL iBT® Practice Test 1 — Question Paper**。轻量包包含四科结构化原题、音频切片、已提取解析和必要图片，不附原始 PDF 或整轨音频；音频和解析来自单独提供的本地资料，不是上述 PDF 链接提供的下载，见[来源声明](examples/ets-practice-test-1/NOTICE.md)。2026-09-14（Asia/Shanghai）已核对本地题目 PDF 与 ETS 下载文件逐字节一致，SHA-256 记录在来源声明中。不包含作者其余私有题库与个人录音。

这是独立练习工具，不是 ETS 产品。严格模式执行选定本地规则，部分时间明确标为近似设置；不复刻 ETS 专有自适应，也不把正确率换成官方 1–6 或 120 分。依据见[规则说明](docs/OFFICIAL_RULES.md)。

**Practice Test 1 计时：**邮件 7 分钟、讨论 10 分钟、音频匹配的访谈题每题 45 秒已获得 ETS 明确确认。阅读 11:30／09:00、听力每题 20／30 秒、组句 6 分钟和复述的精确逐题序列仍是本地预设，不能认定为本套纸面样题的官方精确时限。开始页会标明依据，详见 [2026-09-26 逐项核查](docs/OFFICIAL_RULES.md#practice-test-1-timing-audit-2026-09-26)。修复仅影响新练习；访谈第 1 题继续不限时研读，第 2–4 题恢复各 45 秒。

## 快速开始

需要 **Node.js 22.12+**、**Python 3.10+** 和当前 Chrome/Edge。首次安装依赖需网络。macOS/Linux 在项目根目录运行：

```sh
./scripts/install.sh
npm run demo
npm start
```

打开 **[http://127.0.0.1:4173](http://127.0.0.1:4173)**，保持终端运行，**Control+C** 停止。不要直接打开 `index.html`。

内置 **TOEFL iBT® Practice Test 1** 含 **97 个小题、79 个题面**：阅读 40 小题/22 题面、听力 34/34、写作 12/12、口语 11/11。保留原模块、修正后的结构化文字、配套原音、讨论头像、参考答案和复盘出处。空首页点击 **Try Practice Test 1 / 体验官方样题第1套** 或运行 `npm run demo`；已有 `student-1` 时直接复用，不替换个人记录。**阅读、听力、写作可使用符合条件的严格练习；口语及整套暂以辅助练习使用，因为访谈第 1 题存在尚未解决的纸面与音频版本差异。** 不替换原题或合成音频来绕过告警。默认界面英文，顶部 **EN / 中文** 切换操作界面及根目录 README；详细指南统一使用英文，原题与音频保持来源语言。

安装脚本创建 `.venv/`、安装锁定前端依赖和 Python 依赖、构建 `dist/`，不会执行 OCR、下载私有资料或修改全局 Homebrew/FFmpeg。macOS 后续可双击 [`scripts/start.command`](scripts/start.command)。

### 手动安装

POSIX 终端：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt -r requirements-import.txt
npm ci
npm run build
npm run demo
npm start
```

Windows PowerShell：

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend/requirements.txt -r requirements-import.txt
npm ci
npm run build
.venv\Scripts\python.exe scripts/install_example.py
npm start
```

`.sh`/`.command` 启动器及调用 `.venv/bin/python` 的 npm 便利命令使用 POSIX 路径；Windows 用 `.venv\Scripts\python.exe` 运行对应 Python 脚本，或使用 WSL。CI 配置面向 Linux，本地验证使用 macOS，不代表所有 Windows/设备组合均已验证。

换端口可用 `npm start -- --port 4174`，仅监听 `127.0.0.1`。问题见[故障排查](docs/TROUBLESHOOTING.md)。

## 新环境需要哪些文件

应用代码需附带 Git 中的 [`examples/ets-practice-test-1/`](examples/ets-practice-test-1/README.md)：**56 个经过哈希校验的文件，约 17.8 MB**，另有清单和说明。保留全部结构化题目、33 个 WAV 音频切片、16 张复盘图片和 3 张头像。两个原始 PDF 与 11 个整轨 MP3 为可选资料，已排除于 Git，新用户安装不需要它们。

轻量安装器校验已准备的题目、全部必需媒体和绑定哈希的来源记录；原始文件身份仍保留，但不会声称已在新环境重新校验未附带的原文件。未安装原文件时不提供其打开链接，已有解析、答案、图片与音频切片仍可使用。新用户无需私有 `data/`、`generated/`、`storage/`，也不必额外下载资料。已有完整／私有安装继续保留原来源检查与文件，不能直接删除其原文件。个人数据不要上传 Git，请保留[来源声明](examples/ets-practice-test-1/NOTICE.md)。

## 加入资源

进入 **Help & setup / 使用与导入指南** 导入纯文字 JSON；含音频、图片、视频或原 PDF 的文件夹用：

```sh
npm run import:pack -- "/absolute/path/to/my-practice/pack.json"
```

刷新后选导入标题。自定义包用于不限时辅助练习；同 ID 内容更新时加 `--replace`，已有会话保留冻结内容与版本化资产，新建练习看新版。

[TOEFL iBT® Practice Test 1 参考包说明](examples/ets-practice-test-1/README.md)介绍完整内容和来源。它由专用的校核套题安装器处理，不要通过自定义 JSON 入口上传其内部 `exam.json`。[资源导入](docs/IMPORTING.md)另行介绍自定义资源包、题型、媒体、更新和备份。创作自己的题目可从指南中的[最小 JSON 示例](docs/IMPORTING.md#minimal-complete-pack)开始；简短自编题仅用于测试夹具，不向用户安装。

独立的 `scripts/import_materials.py` 处理完整原私有 PDF 集合和配套 `scripts/verified_*.json`，完整集合的这些输入不公开分发；内置 TOEFL iBT® Practice Test 1 已准备完成，无需运行该导入器。它不是任意 PDF 转换器；只放入 PDF 不会得到已核验题目。新用户无需该集合或 OCR，使用资源包即可开始。

## 练习与复盘

- 选择整份可用套题，或用 **R / L / W / S** 单科直达；专项题库按原套题、模块 / Part 和连续类别小节组织，每个入口启动完整题组。
- 辅助练习支持暂停；专项练习须在开始前勾选，才开放重播与即时答案。完整流程保持关闭，结束后仍可正常复盘；严格模式仅对符合条件的校核范围开放，执行服务器截止时间和导航限制。自定义包、Essentials 等补充资源保持不限时。
- 计时阅读缺字题在编辑时保留每个字母的下划线，使用放大的等宽字体；填满后失焦恢复正文大小。选择题保留原文；组句支持词块/固定片段，邮件和讨论使用分栏与字数统计。
- 口语在本地分段保存、提示未完成上传并支持回放/下载；正式使用前在本地地址测试真实麦克风。
- 历史保留接受的答案、客观结果、作文、录音与量表自评；错题集保留错误和后续掌握情况。

当前样题的纸面版本与已观察的在线 Sampler 有差异：本地阅读第一模块为 20 小题，在线页显示 17 小题，缺字段落另有一处措辞差异。输入交互对齐不会改写 PDF 版本或删题，见[有日期的界面对照记录](docs/EXAM_UI_REFERENCE.md#live-reading-interaction-checked-on-2026-09-26)。

刷新和后台不重置倒计时。新完成会话冻结客观成绩，题库/规则升级不静默重写历史。模式、题型、恢复、评分边界和备份见[使用指南](docs/USER_GUIDE.md)。

## 本地数据与隐私

| 路径 | 内容 |
| --- | --- |
| `data/` | 个人原资料和已复制资源包版本 |
| `generated/` | 规范化题目、资源包注册表、OCR、派生媒体 |
| `storage/practice.sqlite3` | 会话、接受的答卷、计时、事件、分数 |
| `storage/segments/` | 原麦克风录音分段 |
| `storage/playback/` | 可重建回放容器 |

浏览器 IndexedDB 还可能保存待上传录音，清站点数据前等待完成。备份时停服务，复制**完整 `storage/`、`data/`、`generated/`**，使用私有校核时也保留其清单；不要只拷贝运行中主数据库而遗漏 WAL。JSON 导出含答卷和录音引用，音频需另下载或备份目录。

项目无云同步、多用户鉴权，请保持本地使用。个人学习资料、生成的本地题库、录音和私有校核清单应排除于 Git。明确附带的 `examples/ets-practice-test-1/` 参考套题另有[来源声明](examples/ets-practice-test-1/NOTICE.md)；MIT 仅适用于项目代码，不改变第三方试题的原有权利，见[安全政策](SECURITY.md)及[资料说明](docs/MATERIALS.md)。

## 开发

```sh
npm test
npm run build
```

检查类型、UI、API、安全和导入/来源。缺私有集合时相关检查跳过，是公开检出的正常状态，不等于私有题库验收通过。分项及可选隔离浏览器工具见[测试说明](docs/TESTING.md)。

分别在两个终端启动后端和前端开发：

```sh
.venv/bin/python -m backend --port 4173
npm run dev
```

Vite 通常在 5173，将 `/api` 代理到 4173。生产源码改动后重新构建并重启。架构、约束和英文注释规范见[架构](docs/ARCHITECTURE.md)与[贡献指南](CONTRIBUTING.md)。

## 文档与项目规范

仅根目录 README 保留中英文版本，其余项目文档统一使用英文。应用的中英文界面不受影响。

| 主题 | Documentation (English) |
| --- | --- |
| 全部文档 | [Documentation index](docs/README.md) |
| 入门/练习 | [User guide](docs/USER_GUIDE.md) |
| 资源导入 | [Import guide](docs/IMPORTING.md) |
| 故障恢复 | [Troubleshooting](docs/TROUBLESHOOTING.md) |
| 开发设计 | [Architecture](docs/ARCHITECTURE.md) |
| 贡献 | [Contributing](CONTRIBUTING.md) |
| 安全 | [Security policy](SECURITY.md) |
| 社区 | [Code of conduct](CODE_OF_CONDUCT.md) |
| 更新 | [Changelog](CHANGELOG.md) |

[历史验收](docs/ACCEPTANCE.md)和[资料审计](docs/DATA_QA.md)描述特定日期的私有资料/构建，不代表公开检出附带这些内容，也不是所有当前 ETS 状态的认证。

项目代码使用 [MIT](LICENSE)，Open Sans 使用自己的 [SIL Open Font License](public/fonts/OFL-OpenSans.txt)，第三方学习资料保留原权利。
