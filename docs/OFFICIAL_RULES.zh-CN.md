# TOEFL iBT 2026 规则核对与模拟边界

[English](OFFICIAL_RULES.md) | 简体中文

本文保留有日期的来源核对；双语翻译不意味着本轮重新访问并核验了全部外部链接。


初次核对：2026-08-31；再次独立复核：2026-09-05。适用考试日期：2026-01-21 起。规则以 ETS 当前页面、技术文档、官方样题为依据；`data/` 中的界面截图只作为该练习材料的计时证据。最新官方链接和音频来源核对见 [9月5日复核记录](ets-2026-verification.zh-CN.md)；本轮未将近似计时升级为官方已确认规则。

本项目是本地练习软件，不是 ETS 官方考试客户端。**“严格计时”表示软件严格执行选定练习配置，不表示已复现 ETS 所有正式考试规则、机考界面或评分系统。**

## 证据等级

- **verified**：ETS 官方文字明确说明的流程、题量或时间。
- **observed_material**：用户提供 PDF 中能直接读出的界面和时间；不能推定为当前正式考试的全部规则。
- **approximation**：本地练习需要、但未获得官方精确值的默认配置。开始练习前必须披露。
- **unsupported**：当前材料和公开资料不能复现，不能宣传已实现。

结构化对应文件：`shared/rules.json`。其中 `referenceElapsed` **只能展示时长参考，不能直接作为答题倒计时**。`verifiedRules` 中 `null` 表示尚未核实，不代表零秒。

## 已确认的考试流程

顺序是 **Reading → Listening → Writing → Speaking**。Reading、Listening 各分两阶段，第二阶段按第一阶段表现选定；Writing、Speaking 是线性固定题序。见 [ETS Technical Manual，IV-1 与 II-7](https://rr.ets.org/index.php/etsrr/article/download/28/17/34)。

当前官网的基础参考值如下。官方明确说明：说明页不计入这些时间，自适应会使题数、用时变化，完整安排约两小时。因此不能把下面四个数当作四个全节强制结束计时器。[ETS Test Content and Structure](https://www.ets.org/toefl/test-takers/ibt/about/content.html)

| 部分 | 题型 | 官网基础题数 | 官网约计时间 |
| --- | --- | ---: | ---: |
| Reading | Complete the Words；Read in Daily Life；Read an Academic Passage | 50 | 30 分钟 |
| Listening | Listen and Choose a Response；Conversation；Announcement；Academic Talk | 47 | 29 分钟 |
| Writing | Build a Sentence；Write an Email；Academic Discussion | 12 | 23 分钟 |
| Speaking | Listen and Repeat；Take an Interview | 11 | 8 分钟 |

蓝图估算 Reading router 为 18–21 分钟、第二模块 9 分钟；Listening router 为 18 分钟、第二模块 lower 7 / upper 11 分钟。这是包含路线差异的 **estimated time**，不能代替模块或单题屏幕上的实际时间；文档还带有发布前可能修订说明。[ETS Blueprint and Specifications，第 2–3 页](https://www.eu.ets.org/pdfs/toefl/toefl-enki-test-specifications-2026.pdf)

## 倒计时与导航

| 部分 | verified：官方明确规则 | 未证实或本地限制 |
| --- | --- | --- |
| Reading | 按模块显示时钟；同模块内可 Next / Back；进入模块 2 后不能返回模块 1 | 不能把所有套题统一认定为 9/10/15 分钟；应保留套题自己的时间证据 |
| Listening | 按**每题**显示时钟；Next 后不可返回；录音只播放一次 | 公开文字未确认所有题统一 20 秒；不以 29 分钟全节倒计时替代逐题计时 |
| Build a Sentence | 10 题，拖动给定词块组成句子；该任务有时钟 | 本次未从 ETS 公开文字核实总计 6:00 或 6:50；截图中的剩余时间不能证明初始时间 |
| Write an Email | 1 题，**7 分钟**，包含读题和写作 | 不能把组句剩余时间带入邮件任务 |
| Academic Discussion | 1 题，**10 分钟**；有效回答建议至少 100 词 | 100 词是写作要求提示，不应设为不足即禁止提交或自动零分 |
| Listen and Repeat | 7 句，每句只听、复述一次；**无准备时间**；每句最大录音窗口 **8–12 秒** | 官方概述未逐句列明 8/8/10/10/10/12/12；本项目按截图证据使用该序列 |
| Take an Interview | 4 题，**无准备时间**；每题 **45 秒** | 不添加旧版 15/30 秒准备时间；问题结束后进入录音 |

Reading 导航、Listening 每题时钟和禁止回退、两类口语无准备时间、邮件与讨论时限，见 [ETS Teacher Practice Test 1，第 3、15、27、29–30、33–34 页](https://www.ets.org/content/dam/ets-org/pdfs/toefl/toefl-ibt-teachers-resources-practice-test-1.pdf)。Listen and Repeat 8–12 秒及 Interview 45 秒，见 [ETS Test Overview，第 17–18 页](https://www.ets.org/content/dam/ets-org/pdfs/toefl/toefl-ibt-test-overview.pdf)。听力一次播放与组句 10 题，见 [ETS Specifications，第 6、12 页](https://www.eu.ets.org/pdfs/toefl/toefl-enki-test-specifications-2026.pdf)。

严格模式应禁重播、拖动音频进度、修改倍速、暂停答题时钟、跨模块返回。技术故障应明确标记此次考试已中断，不能悄悄变成正常严格成绩。声音能否自动播放和麦克风权限应在开始前预检。模拟软件的这种故障处理是本地设计，不等同 ETS 监考员的处理决定。

居家考试不允许考生自行休息；ETS 有监考员处理技术异常。Writing 应关闭拼写/语法辅助，禁止外部粘贴。正式系统对应用切换的封锁无法由普通网页完全实现。[ETS Home Test Day](https://www.ets.org/toefl/test-takers/ibt/test-day/at-home-test-day.html)；[ETS Technical Manual，IV-2](https://rr.ets.org/index.php/etsrr/article/download/28/17/34)

## 用户材料中直接观察到的计时

来源是 `data/2026新托福 18套题+备考资料/00. TPO1-6 全套（包含音频、听力原文和答案）/2026新托福Pack-1/2026新托福Pack-1.pdf`，下面均为 **PDF 物理页码**。已对关键页渲染核对，并对所有页顶栏 OCR。

| 页码 | 观察结果 | 可如何使用 |
| --- | --- | --- |
| 2 | Reading Module 1 的 Begin 页显示 00:11:30 | 仅作为 Pack 1 来源界面的快照值，不推广到其他试卷 |
| 18 | Reading Module 2 的 Begin 页显示 00:09:00 | 同上 |
| 27、30、37、39、42、43 等 | 短回应、对话、公告答题页显示 00:00:20 | 本地这些题型采用 20 秒默认值，有材料支持 |
| 48、49、51、66 | Academic Talk 答题页显示 00:00:30 | 本地学术讲座题采用 30 秒默认值，有材料支持 |
| 35、38、41、47 等 | 播放材料的页面不显示答题倒计时 | 模拟中将播音阶段与回答阶段分开，回答时钟在题目进入后开始 |
| 74 | Build a Sentence 说明页已剩 00:05:47 | **无法证明**任务开始时为 6:00 或 6:50 |
| 75–84 | 组句有 Review、Back 按钮 | 本地可允许同一组句任务内检查和返回 |
| 92–98 | Repeat 依次为 **8、8、10、10、10、12、12 秒** | 可作为这批练习的口语录音默认配置 |
| 101 | Interview 显示 00:00:45 | 与官方文字一致 |

该 PDF 开头仍显示 Reading 35–48、Listening 35–45 题，与现官网基础表不同，且截图采集时间和版本未知。不能因为界面有 TOEFL 标识，就声称这些截图证明了现行生产系统的全部细节。其他 Pack 的初始阅读/组句时限应逐卷核实；运行时如存在人为默认值，应显示“练习设定”。

## 评分与不能复现的能力

可按已核对答案统计客观题练习正确数、保存作文、保存与回放口语、对照量表自评。官方 Reading/Listening 分数经过题目校准和等值转换，**不是正确率线性换成 1–6 分**。组句每题 0/1；邮件、讨论及各口语回答按各自 0–5 量表评分；官方主观题评分引擎为 ETS 专有系统。[ETS Technical Manual，III-1 与 III-2](https://rr.ets.org/index.php/etsrr/article/download/28/17/34)

本地量表来源：`data/2026新托福 18套题+备考资料/06. 口语写作评分标准/` 下的 `writing-rubrics.pdf` 和 `speaking-rubrics.pdf`。它们适合结束后查看和人工自评，不代表本项目已有官方评分能力。

以下为 **unsupported**：ETS 真实自适应选卷门槛、题目校准参数、非计分题判定、正式分数转换表、ETS AI/人工评分、监考和锁机安全、与全部当前 ETS 正式客户端像素或行为一致的保证。固定路线必须显示“固定练习路线”，不能借正确率阈值伪装 ETS 自适应。

## 数据接入要求

题目、顺序、题型及必要音频与切分边界核验完整，才能开放对应范围的严格计时。答案核验决定可自动评分的范围：原题完整但参考键仍有冲突时，保留该题计时作答，将歧义评分单元排除出分母并明确告知，不猜造答案。Pack 3 的两个歧义空按此处理。

纸面教师版明确说明并非真实考试的完全复制，且 `data/` 有些资料没有音频。不得用朗读合成、猜测音频配对、合并整段录音播放或缺题占位来冒充完整严格模考。可以继续作为资料库或明确标识的非严格专项练习开放。

早期官方互动样题访问停留在表单入口。2026-09-05之后已使用用户提供的现行ETS Sampler会话，实际观察阅读、听力、组句、邮件和学术讨论；邮件与讨论的首次可读剩余时间分别为06:56和09:34，组句未见时钟。观测范围及原客户端样式见 [界面对照记录](EXAM_UI_REFERENCE.zh-CN.md)。这更新了早期访问状态，仍不证明未观察到的初始时限或完整生产流程。Sampler直接进入两道长写作与部分原PDF的独立Begin页存在差别，不能据练习Sampler自动改写正式计时规范。

### 现行客户端写作超时提示

2026-09-05实际Sampler学术讨论到时后仍保留原题面，通过Writing Time Expired弹窗的Continue离题。v5新会话在邮件/讨论到时进入不可编辑的expired状态，仍保留原截止时间；Continue不能恢复或延长原题时间。该行为作为observed_client记录，旧会话保持其冻结策略。口语仍按原录音窗口自动停录，不泛化此等待状态。
