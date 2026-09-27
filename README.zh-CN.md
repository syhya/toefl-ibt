# TOEFL Local Lab

[English](README.md) | 简体中文

**Powered by GPT-6 Astra。** 本项目目前在开发过程中使用 GPT-6 Astra，用于测试当前模型在完整应用开发、测试、调试和文档维护中的能力边界。日常练习在本地运行，无需调用模型 API。

支持中英文导航的本地 TOEFL 风格练习网站，提供结构化题目、写作编辑器、已支持校核资料的倒计时、麦克风录音与历史复盘。采用 **React + TypeScript + Vite、FastAPI、SQLite**。安装依赖和导入资源后，日常练习可离线运行，不需要账号或云端 AI。

**内置样题：**[TOEFL iBT® Practice Test 1](examples/ets-practice-test-1/README.md) 覆盖听、说、读、写四科，附带准备好的音频、图片和中英文解析，无需另行准备原始 PDF 或私有资料即可安装使用。资料归属见[来源声明](examples/ets-practice-test-1/NOTICE.md)。

这是独立练习工具，不是 ETS 产品。严格模式执行选定本地规则，部分时间明确标为近似设置；不复刻 ETS 专有自适应，也不把正确率换成官方 1–6 或 120 分。依据见[规则说明](docs/OFFICIAL_RULES.md)。

## 快速开始

需要 **Node.js 22.12+**、**Python 3.10+** 和当前 Chrome/Edge。首次安装依赖需网络。macOS/Linux 在项目根目录运行：

```sh
./scripts/install.sh
npm run demo
npm start
```

打开 **[http://127.0.0.1:4173](http://127.0.0.1:4173)**，保持终端运行，**Control+C** 停止。不要直接打开 `index.html`。

`npm run demo` 安装内置样题，并保留已有练习记录。顶部 **EN / 中文** 切换操作界面和样题解析；原题与音频保持来源语言。

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

## 加入资源

进入 **Help & setup / 使用与导入指南** 导入纯文字 JSON；含音频、图片、视频或原 PDF 的文件夹用：

```sh
npm run import:pack -- "/absolute/path/to/my-practice/pack.json"
```

刷新后选导入标题。自定义包用于不限时辅助练习；同 ID 内容更新时加 `--replace`，已有会话保留冻结内容与版本化资产，新建练习看新版。

支持的题型、媒体、更新和备份方式见[资源导入指南](docs/IMPORTING.md)。创作自己的题目可从[最小 JSON 示例](docs/IMPORTING.md#minimal-complete-pack)开始。

## 练习与复盘

- 选择整份可用套题，或用 **R / L / W / S** 单科直达；专项题库按原套题、模块 / Part 和连续类别小节组织，每个入口启动完整题组。
- 辅助练习支持暂停；专项练习须在开始前勾选，才开放重播与即时答案。完整流程保持关闭，结束后仍可正常复盘；严格模式仅对符合条件的校核范围开放，执行服务器截止时间和导航限制。自定义包、Essentials 等补充资源保持不限时。
- 计时阅读缺字题在编辑时保留每个字母的下划线，使用放大的等宽字体；填满后失焦恢复正文大小。选择题保留原文；组句支持词块/固定片段，邮件和讨论使用分栏与字数统计。
- 口语在本地分段保存、提示未完成上传并支持回放/下载；正式使用前在本地地址测试真实麦克风。
- 历史保留接受的答案、客观结果、作文、录音与量表自评；错题集保留错误和后续掌握情况。

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

项目无云同步、多用户鉴权，请保持本地使用。个人学习资料、生成的题库、录音和私有校核文件应排除于 Git。MIT 仅适用于项目代码，第三方学习资料保留原有权利。见[安全政策](SECURITY.md)及[资料说明](docs/MATERIALS.md)。

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

## 文档

[文档索引](docs/README.md)汇总了使用指南和技术参考，可按需要查阅：

- [使用指南](docs/USER_GUIDE.md)：了解练习模式、各科操作、口语录音、成绩复盘和进度备份。
- [资源导入](docs/IMPORTING.md)：创建与导入题包、添加配套媒体，以及更新已有资源。
- [故障排查](docs/TROUBLESHOOTING.md)：处理安装、启动、麦克风、音频播放和录音恢复问题。
- [架构设计](docs/ARCHITECTURE.md)：了解前端、本地 API、数据库、练习会话生命周期和评分设计。
- [测试说明](docs/TESTING.md)：运行自动化检查，并使用浏览器验证流程。
- [更新日志](CHANGELOG.md)：查看功能更新、问题修复和版本说明。

## 参与贡献

欢迎提交问题报告、功能建议、文档改进和 Pull Request。开始前请阅读[贡献指南](CONTRIBUTING.md)，了解开发环境配置、代码约定和提交前需要执行的检查。

参与讨论与协作时，请遵守[行为准则](CODE_OF_CONDUCT.md)。如需报告安全漏洞，请按照[安全政策](SECURITY.md)中的渠道和说明提交。

## 许可证

项目源代码采用 [MIT 许可证](LICENSE)。内置 Open Sans 字体采用 [SIL Open Font License](public/fonts/OFL-OpenSans.txt)。

第三方题目、音频、图片及其他学习资料仍受各自原有权利和许可证约束。来源与署名信息见[资料说明](docs/MATERIALS.md)。
