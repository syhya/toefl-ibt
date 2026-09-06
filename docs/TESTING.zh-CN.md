# 本地验收工具

[English](TESTING.md) | 简体中文

公开 CI 在干净检出安装项目依赖并运行检查/构建；安装原创演示后还检查仅资源包题库下的资料测试跳过行为。私有资料不存在时的跳过不能当作题库验收通过。内置原创演示明确属于公开入门内容，不是向原私有套题填入测试题；界面语言和自定义资源导入由对应行为回归验证。


自动回归和构建：

```sh
npm test
npm run build
```

`npm test`依次执行类型检查、界面、后端与安全、真实资料与导入检查。2026-09-05当前完整日志 `tmp/qa/client-expiry-v5-tests.log` 记录80项界面、146项后端/安全和28项资料检查通过，共254项。此数字对应该次代码快照；新改动后应重新执行相关检查，再更新 [ACCEPTANCE.md](ACCEPTANCE.zh-CN.md)，不能沿用旧数字或旧截图宣称新版本已经通过。

需要定位问题时，按项目现有作用域分别运行：

```sh
npm run typecheck
npm run test:ui
npm run test:api
npm run test:data
```

后端与安全测试使用临时目录和独立SQLite。真实资料检查读取本项目的原文件、题库、10份校核文件和派生素材，不向题库添加测试题；没有私有资料的公开检出会跳过相关真实资料检查，不能将这种跳过记为真实题库验收通过。

## 当前回归的关键范围

- 服务端截止时间、Begin与自动模块衔接、原音单次播放、迟到请求及当前题身份、同题重复请求、后台/休眠时钟间隔和恢复。
- 来源文件及校核摘要、28项资料/导入检查、44段原说明的模块/题组绑定、说明结束后才开始回答时限，以及9道合并Read指示不丢失原正文或材料标题。
- 缺失字母、词块拖放/重排、重复词块、固定文字与原标点；编辑器字数、内部剪切/粘贴及撤销/重做。
- `scoreSnapshot`在完成/主动结束时冻结，重启或判分引擎变化不改旧客观分；旧记录标为 `legacy-recomputed`。迟到录音和量表自评与客观快照分离。
- 跨次错题集的实际已答/可核分条件、已掌握与再次答错、最后错误复盘、来源版本变化和活动严格会话隔离；分科客观成绩与主观自评数量/均值不混算。
- 原视频末帧的同题保留和换题清除。单元测试及一段原采访视频的浏览器复验通过，记录于 `tmp/qa/final-video-frame-ui.json`。

测试夹具可以使用明确标记的工程数据与测试音源，但不得写进正式 `data/`、`generated/`或用户的 `storage/`。

## 可推进时钟的浏览器夹具

```sh
npm run build
.venv/bin/python scripts/e2e_fixture.py serve --reset --port 4176
```

打开 [隔离浏览器夹具](http://127.0.0.1:4176)。它使用 `tmp/qa/e2e-sandbox` 中的独立素材快照与SQLite，不读写正式练习记录。题目选自体验日1；每条阅读路径只有两屏真实题，保留高低分支和题型代表内容，**不是完整官方试卷**。

在另一个终端推进测试时间：

```sh
.venv/bin/python scripts/e2e_fixture.py advance 700
.venv/bin/python scripts/e2e_fixture.py status
```

专用时钟保存在 `tmp/qa/e2e-clock.json`，仍随真实时间前进。正式服务没有HTTP调时接口；邮件420秒、讨论600秒和采访45秒等规则没有被缩短，只在夹具中推进专用时钟。`tmp/qa/e2e-fixture-manifest.json`保存来源、模块及测试答案夹具，不由生产API提供。

更新前端后，构建并同步界面：

```sh
npm run build
.venv/bin/python scripts/e2e_fixture.py sync-ui
```

再确认浏览器加载的是新构建。需要重建夹具时先停止4176服务，再用 `--reset` 启动；该参数只重建带工具所有权标记的临时目录。旧会话、截图和构建哈希不能混成新版本证据。

## 显式合成麦克风与真实窗口

```sh
.venv/bin/python scripts/e2e_fixture.py serve --synthetic-mic --port 4176
```

默认不开启。该选项仅向临时夹具页面注入Web Audio正弦测试音源，并显示 **E2E / SYNTHETIC MICROPHONE**。它不调用真实麦克风；停止stream tracks后关闭振荡器与AudioContext，`sync-ui`保留所选模式。正式 `src/`、`dist/`和主服务不含该注入。

要验证真实作答窗口，使用正常速度原音/视频并让服务器自然到时；整轮不得调用 `advance`、手动跳题、刷新或暂停。已完成3轮、每轮7次复述＋4次采访的此类检查，验证真实MediaRecorder、自动录停、分段、完成标记与回放链路。其中v4报告为 `tmp/qa/2026-09-05-source-ui-speaking.json`，保留了被测构建、无快进记录和当时的视觉限制。

合成链路不证明真实麦克风已授权、实际输入正确或人声质量合格。用户在ETS页面做过麦克风校准，也不能代替本地软件的真实麦克风测试。官方Sampler的版式观察没有由助手录制或上传人声；不要把本地夹具的合成音注入当成官方设备验收。

## 真实时长服务器流程

```sh
.venv/bin/python scripts/realtime_smoke.py
```

该脚本使用独立端口4175、临时SQLite及复制的题库/后端版本，按真实时间走体验日1流程，读取授权原音视频并等待模块与逐题截止时间。默认最多运行3小时，进度和摘要保存到 `tmp/qa/realtime-report.json`。

当前脚本复制派生素材，仅对不修改的原始资料使用硬链接；早期已完成的4,127.039秒运行也曾硬链接派生素材，报告中已注明这一限制。它验证的是当时版本的HTTP/服务器流程，不播放声音、不操作浏览器、不测试真实麦克风，不能证明当前v4的全部代码或后来新增末帧功能已经完成浏览器长跑。结束后清理临时数据库和素材链接，保留不含用户作答的报告。

## 真实题库、独立记录的界面预览

```sh
.venv/bin/python scripts/qa_full_catalog_preview.py --port 4177
```

打开 [真实题库预览](http://127.0.0.1:4177)。该服务使用实际 `data/`、`generated/`和 `dist/`，保留来源门禁与真实时钟，只将SQLite及录音重定向到 `tmp/qa/full-catalog-preview/storage/`。不注入测试题或合成麦克风，不向4173写验收答卷；日常仍使用 `npm start`。

原生Chrome中的原词块拖入空槽、已放入词块重排已实际通过。当前软件使用本地Open Sans与1024×768等比画布；应在有代表性的视口下检查材料内部滚动、词块、长写作编辑器及口语时钟，不能只以DOM尺寸或单张旧截图判断实际显示效果。

界面截图保存于 `output/playwright/official-*.png`。现有截图涵盖阅读、造句、邮件、讨论、听力和口语，但部分早于字体、画布、说明或原视频末帧修复，必须说明版本。`tmp/qa/final-video-frame-ui.json`已记录原视频结束→同题45秒窗口→自然停录：显示PNG与原帧一致，录音可回放；换题清除由界面回归覆盖。该局部构建早于之后的听力改动，最终整套浏览器验收单独记录。

## 官方客户端对照与设备边界

已在现行原生ETS Sampler会话观察欢迎、音量、阅读缺字/通知/学术文章、听力播放与答题，以及组句、邮件和学术讨论。公开客户端CSS确认默认控件使用Open Sans，并提供1024像素宽的直接证据；本地768像素基准高结合结构与实际4:3比例确定。当前普通正文以16px／21px行高对照，特定材料仍可使用不同字体和字号，不据此断言全部生产控件完全一致。

Sampler的计时按任务区分：已见阅读、听力和组句未显示时钟，邮件首次可读剩余06:56、学术讨论09:34。不要把剩余时间当初始值，或把局部无时钟及Sampler题量移植成正式试卷规格。邮件Next的同画布Time Remaining确认继续计时，Back返回同题编辑，Continue离题；本地确认页须同时保持编辑器与撤销状态。短答播放期可见但禁用原选项，手动Next空答提示也不能阻止服务器超时自动跳题。本轮未继续口语录制作答；其它未见状态以 [EXAM_UI_REFERENCE.md](EXAM_UI_REFERENCE.zh-CN.md) 的具体观察范围为准。

最终构建的完整原套浏览器与服务重启验收已通过；本地真实麦克风、人声质量、真实设备休眠/断网仍需独立验证。测试结果不复制ETS专有自适应、标定和主观评分；已知资料缺项与未公开规则保留原有边界，详见 [OFFICIAL_RULES.md](OFFICIAL_RULES.zh-CN.md) 和 [MATERIALS.md](MATERIALS.zh-CN.md)。

## 完整原套浏览器验收

`qa_full_catalog_preview.py` 只把 SQLite 与录音写入指定的 `tmp/qa/full-catalog-preview-<tag>/storage`，题库、来源校验、前端、计时器和 API 均使用当前真实实现；不启动测试时钟。

```sh
.venv/bin/python scripts/qa_full_catalog_preview.py --port 4185 --tag final-full-20260905
.venv/bin/python scripts/qa_full_exam_browser.py --port 4185 --browser final-full-exam
```

运行 driver 前，须在名为 `final-full-exam` 的隔离 headless 浏览器中明确注入合成麦克风与媒体事件记录，选定完整严格模式，在首个 Reading Begin 页停留。仅 QA 的答案清单位于 `tmp/qa/final-full-exam-answers.json`：客观项来自原资料已核验键，两篇写作是针对原题写出的测试答卷，明确不是官方范文；不将任何 QA 答案导入题库。

该 driver 通过原界面填字母、点击原选项、操作原词块和写作编辑器；每题保存成功后才正常 Next。它不直接调用答题写入 API、不跳过原声、不加快时钟，口语使用真实窗口自动停录。正常提前交题意味着运行时长小于把每一段时限全部用尽的模考；报告不能把自动作答耗时称为正式考试的总时长。

终态检查四科完整范围、68份非口语作答、原84个客观核分单元、按原题对应的11段完整录音、浏览器错误、来源与构建摘要。还包括第一道组句的真实拖动换位，以及邮件确认页 Back 保留正文。当前记录目录为 `tmp/qa/final-full-exam-browser/`；排版修正前已完成的一遍保留在 `tmp/qa/full-exam-discovery-20260905/`，不混作最终构建的验收证据。

2026-09-05最终结果：完整9阶段／79屏／97小题，原媒体43次正常播放、11段录音可解码回放、客观84/84与原键一致，服务重启后三类记录保持一致；15项终态检查全过。耗时1,157.197秒，属使用正常Next提前提交的自动验收。证据：`tmp/qa/final-full-exam-browser/summary.json`。

v5自然超时整卷命令在原driver后追加 `--exercise-writing-expiry academic_discussion`。该次实际运行1,793.006秒，并自然用完讨论600秒，再Continue进入口语；最终报告为 `tmp/qa/final-full-exam-browser/summary.json`。随后仅调整弹窗CSS、修正版号，JS字节相同，后端逻辑仅标签常量变化；独立外观夹具明确使用测试时钟，记录在 `tmp/qa/writing-expiry-visual/summary.json`，不冒充第二次十分钟自然等待。
