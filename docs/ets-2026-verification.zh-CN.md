# ETS 2026 规则独立复核

[English](ets-2026-verification.md) | 简体中文

本文是 2026-09-05 的独立复核记录，双语文档更新本身不代表一次新的联网复核。


复核日期：2026-09-05。范围：2026-01-21 起的 TOEFL iBT，独立浏览 ETS 官方页面与 PDF，并对照现有 `OFFICIAL_RULES.md`、`shared/rules.json`。规则核验后，另对已有教师题的 ETS 配套音频进行来源核对；不添加或自编新题。

## 流程与倒计时

考试顺序为 Reading → Listening → Writing → Speaking。Reading、Listening 为两阶段自适应；Writing、Speaking 为线性流程。官网列出 50 / 47 / 12 / 11 题，约计基础时间 30 / 29 / 23 / 8 分钟，同时明确说明题量与用时可随自适应变化，说明页不计入时间。不能据此设置四个固定全节强制结束时钟。[ETS 当前考试结构](https://www.ets.org/toefl/test-takers/ibt/about/content.html)、[ETS Teacher FAQ，第 2–4 页](https://www.ets.org/content/dam/ets-org/pdfs/toefl/teacher-faq.pdf)

| 任务 | 本次核实结果 | 官方出处 |
| --- | --- | --- |
| Reading | 模块时钟；模块内 Next / Back；进入 Module 2 后不能回 Module 1 | [Teacher Practice Test 1，物理页 3、7](https://www.ets.org/content/dam/ets-org/pdfs/toefl/toefl-ibt-teachers-resources-practice-test-1.pdf) |
| Listening | 每题独立时钟；Next 后不可返回；原录音播放一次 | [Teacher Practice Test 1，物理页 15、20](https://www.ets.org/content/dam/ets-org/pdfs/toefl/toefl-ibt-teachers-resources-practice-test-1.pdf)、[Specifications，物理页 12](https://www.eu.ets.org/pdfs/toefl/toefl-enki-test-specifications-2026.pdf) |
| Build a Sentence | 10 题；移动给定词块；任务时钟；公开文字未核实统一 6:00 或 6:50 初始时间 | [Specifications，物理页 6](https://www.eu.ets.org/pdfs/toefl/toefl-enki-test-specifications-2026.pdf)、[Teacher Practice Test 1，物理页 27](https://www.ets.org/content/dam/ets-org/pdfs/toefl/toefl-ibt-teachers-resources-practice-test-1.pdf) |
| Write an Email | 1 题，读题及写作总计 7 分钟 | [Writing Lesson Plans，物理页 7](https://www.ets.org/content/dam/ets-org/pdfs/toefl/toefl-ibt-lesson-plan-writing.pdf) |
| Academic Discussion | 1 题，读题及写作总计 10 分钟；建议至少 100 词；提供字数统计，无拼写检查 | [Writing Lesson Plans，物理页 4、7](https://www.ets.org/content/dam/ets-org/pdfs/toefl/toefl-ibt-lesson-plan-writing.pdf) |
| Listen and Repeat | 7 句；无准备时间；复述一次；每句录音窗口最长 8–12 秒 | [Teacher Practice Test 1，物理页 33](https://www.ets.org/content/dam/ets-org/pdfs/toefl/toefl-ibt-teachers-resources-practice-test-1.pdf)、[Test Overview，物理页 17](https://www.ets.org/pdfs/toefl/toefl-ibt-test-at-a-glance.pdf) |
| Take an Interview | 4 题；无准备时间；每题 45 秒 | [Teacher Practice Test 1，物理页 34](https://www.ets.org/content/dam/ets-org/pdfs/toefl/toefl-ibt-teachers-resources-practice-test-1.pdf)、[Test Overview，物理页 18](https://www.ets.org/pdfs/toefl/toefl-ibt-test-overview.pdf) |

蓝图 Reading router 为 18–21 分钟、第二模块 9 分钟；Listening router 为 18 分钟、第二模块 lower 7 分钟 / upper 11 分钟。蓝图明确把这些列为估算，并保留发布前修订提示。它们不是每套练习卷的精确倒计时证据。[ETS Specifications，物理页 2–3](https://www.eu.ets.org/pdfs/toefl/toefl-enki-test-specifications-2026.pdf)

## 实施结论

- 现有 `shared/rules.json` 中确定的顺序、导航规则、邮件/讨论/面试时限与本次官方复核一致。
- Reading 模块初始时间、Listening 的 20/30 秒分类、Repeat 的 8/8/10/10/10/12/12 秒序列，仍须作为具体 `data` 来源截图的观察值引用，不能升级成所有正式卷统一规则。
- Build a Sentence 的 360 秒应继续明确标为本地练习设定；不能用约计写作 23 分钟减去 7 与 10 分钟倒推正式精确限时。
- 听力每题时钟和禁止回退是独立要求，不能仅实现 29 分钟的全节倒计时。
- 教学活动中的准备 30 秒、准备 15 秒等属于循序练习建议，不是新口语考试规则；不得混入模考。[ETS Speaking Lesson Plan，物理页 3](https://www.ets.org/content/dam/ets-org/pdfs/toefl/toefl-ibt-lesson-plan-speaking.pdf)
- 可以报告按原答案核对的练习正确数。正式 Reading/Listening 报分含题目难度、IRT 等值与转换；不能通过正确率线性生成“官方 1–6 分”。[ETS Teacher FAQ，物理页 4–5](https://www.ets.org/content/dam/ets-org/pdfs/toefl/teacher-faq.pdf)

## 证据边界

ETS 公开资料未提供本项目可直接复刻的生产客户端完整状态机、所有计时分配、题目校准参数和自适应路由阈值。早期访问[官方互动 Sample 1](https://www.ets.org/toefl/test-takers/ibt/prepare/sample-test-jan-2026-1.html)仅取得表单入口。随后同日已进入用户提供的ETS Sampler，观察阅读、听力、组句和两道长写作，以及邮件Time Remaining确认页；邮件06:56、讨论09:34是首次可读剩余值。完整观测在 [EXAM_UI_REFERENCE.md](EXAM_UI_REFERENCE.zh-CN.md) 中逐项记录。该Sampler不是完整生产考试的等价证据，未显示时钟的组句仍不能核证初始时限。

[官方教师资源页](https://www.ets.org/toefl/teachers-advisors-agents/ibt/teaching/preparing-students.html)目前列有各套练习的 PDF 与音频链接。已有教师题的配套原音已下载、核对并以新增文件保存；本项目题文仍取自用户原有 `data`，没有用机器转写生成或改写题目。

## 配套音频补充核验

[教师样题 1 官方音频 ZIP](https://www.ets.org/content/dam/ets-org/pdfs/toefl/teacher-practice-test-1-audio-file.zip)为 6,812,272 字节，[教师样题 2 官方音频 ZIP](https://www.ets.org/content/dam/ets-org/pdfs/toefl/teacher-practice-test-2-audio-file.zip)为 6,728,221 字节。两包均通过完整下载和 ZIP CRC 核验；每包 36 个 MP3，包含覆盖 34 道听力题的 23 段刺激、11 段口语题音频和两段口语说明。官方页面配套关系、套号、模块、文件题号与本地题文主题/顺序一致，区别于体验日三套。

文件及题目映射保存于私有 `scripts/verified_teacher_audio.json`，源 PDF、每题源页、原转写内容和每段音频均绑定 SHA-256。`scripts/attach_teacher_audio.py` 默认离线核验；显式安装只新增原 MP3，不覆盖已有文件。机器语音识别仅用于来源比较；18 段的机器词差另存供复核，不当作已确认的原文错误，也不宣称人耳逐字听校。原转写仍用于复盘；活动听力/口语题面必须隐藏刺激全文后才能开放计时。

## 学生样题 1 仍存在官方版本差异

2026-09-05 重新下载并完整检查了[学生样题 1 当前官方音频 ZIP](https://www.ets.org/content/dam/ets-org/pdfs/toefl/student-practice-test-1-audio-files.zip)，大小 22,617,951 字节，ZIP CRC 通过。包内 `Speaking/Interview/Speaking_Interview_Question1.mp4` 的问题仍围绕最近一次到访其他城市的经历；用户原有 PDF 第一题询问目前居住的城市规模。两者是实质不同的题目，当前官网原音不能解决这一题的版本不匹配。

因此学生样题 1 的这一口语题继续保持来源不匹配状态，不替换原题、不合成音频、不冒充完整严格模考。新下载包只保留在 `tmp/qa/official-audio-verification/` 核验目录，没有作为该题的有效音频导入。文件摘要与本地核对记录见该目录的 `student-1-interview-1-check.json`。
