# 本地长音轨切分与核验

[English](MEDIA_SEGMENTS.md) | 简体中文

这是高级私有资料处理流程，公开演示和 JSON 资源包不需要它。下述 MLX 命令面向兼容的 Apple Silicon/macOS 与 uv 环境，不是跨平台运行依赖；之后原音/说明补充见[资料 QA](DATA_QA.zh-CN.md)。


生成时间：2026-08-31T23:22:38+0800

原始 data 文件保持不变。切分只使用本机声学检测、源资料原文和本机 MLX Whisper；不向云端推理服务发送音频。首次下载开源模型后可离线重新处理。

## 文件与接口

- `scripts/segment_media.py`：可重复执行的扫描、转写、对齐、导出与校验工具。
- `generated/media-segments.json`：每段包含 sourceMaterialId、原音轨 SHA-256、startSeconds/endSeconds、questionIds、groupId、kind、url、confidence、verified 和证据。
- `generated/assets/media/<examId>/`：供本地播放器使用的分段音频。
- `generated/assets/media/_analysis/`：保留原时间映射、能量检测与 ASR 缓存，均为本地私有中间文件。

## 已完成的源轨

| 套题 | 源文件 | 原时长 | 已关联组 | 自动核验组 | 未匹配组 |
| --- | --- | ---: | ---: | ---: | ---: |
| pack-2 | Pack-2_Listening.MP3 | 1425.1s | 20 | 20 | 0 |
| pack-2 | Pack-2_Speaking.MP3 | 494.7s | 11 | 11 | 0 |
| pack-3 | Pack-3_Listening.MP3 | 1724.1s | 27 | 27 | 0 |
| pack-3 | Pack-3_Speaking.MP3 | 499.5s | 11 | 11 | 0 |
| pack-4 | Pack-4_Listening.MP3 | 1787.2s | 27 | 27 | 0 |
| pack-4 | Pack-4_Speaking.MP3 | 513.5s | 11 | 11 | 0 |
| pack-5 | Pack-5_Listening.MP3 | 1751.1s | 24 | 24 | 0 |
| pack-5 | Pack-5_Speaking.MP3 | 502.0s | 11 | 11 | 0 |
| pack-6 | Pack-6_Speaking.MP3 | 459.2s | 11 | 11 | 0 |
| pack-6 | Pack-6_listening.MP3 | 1729.4s | 24 | 24 | 0 |
| student-1 | 托福样题01-口语-01-Listen and Repeat.mp3 | 59.4s | 7 | 7 | 0 |
| student-1 | 托福样题01-口语-02-Interview.mp3 | 114.6s | 3 | 3 | 1 |
| student-1 | 托福样题01-听力-Module 01-01-Listen and Choose a Response.mp3 | 59.7s | 8 | 8 | 0 |
| student-1 | 托福样题01-听力-Module 01-02-Conversation 01.mp3 | 35.3s | 1 | 1 | 0 |
| student-1 | 托福样题01-听力-Module 01-02-Conversation 02.mp3 | 32.1s | 1 | 1 | 0 |
| student-1 | 托福样题01-听力-Module 01-03-Announcement.mp3 | 34.0s | 1 | 1 | 0 |
| student-1 | 托福样题01-听力-Module 01-04-Academic Talk.mp3 | 102.9s | 1 | 1 | 0 |
| student-1 | 托福样题01-听力-Module 02-01-Listen and Choose a Response.mp3 | 57.9s | 8 | 8 | 0 |
| student-1 | 托福样题01-听力-Module 02-02-Conversation 01.mp3 | 30.8s | 1 | 1 | 0 |
| student-1 | 托福样题01-听力-Module 02-03-Announcement.mp3 | 28.5s | 1 | 1 | 0 |
| student-1 | 托福样题01-听力-Module 02-04-Academic Talk.mp3 | 91.1s | 1 | 1 | 0 |
| student-2 | 托福样题02-口语-01-Listen and Repeat.mp3 | 53.3s | 7 | 7 | 0 |
| student-2 | 托福样题02-口语-02-Interview.mp3 | 114.0s | 4 | 4 | 0 |
| student-2 | 托福样题02-听力-Module 01-01-Listen and Choose a Response.mp3 | 58.4s | 8 | 8 | 0 |
| student-2 | 托福样题02-听力-Module 01-02-Conversation 01.mp3 | 24.2s | 1 | 1 | 0 |
| student-2 | 托福样题02-听力-Module 01-02-Conversation 02.mp3 | 26.2s | 1 | 1 | 0 |
| student-2 | 托福样题02-听力-Module 01-03-Announcement.mp3 | 23.9s | 1 | 1 | 0 |
| student-2 | 托福样题02-听力-Module 01-04-Academic Talk.mp3 | 72.4s | 1 | 1 | 0 |
| student-2 | 托福样题02-听力-Module 02-01-Listen and Choose a Response.mp3 | 56.7s | 8 | 8 | 0 |
| student-2 | 托福样题02-听力-Module 02-02-Conversation 01.mp3 | 21.1s | 1 | 1 | 0 |
| student-2 | 托福样题02-听力-Module 02-03-Announcement.mp3 | 18.9s | 1 | 1 | 0 |
| student-2 | 托福样题02-听力-Module 02-04-Academic Talk.mp3 | 81.5s | 1 | 1 | 0 |
| paid-1 | 口语1.m4a | 11.3s | 1 | 1 | 0 |
| paid-1 | 口语10.m4a | 24.6s | 1 | 1 | 0 |
| paid-1 | 口语11.m4a | 18.8s | 1 | 1 | 0 |
| paid-1 | 口语2.m4a | 15.4s | 1 | 1 | 0 |
| paid-1 | 口语3.m4a | 12.2s | 1 | 1 | 0 |
| paid-1 | 口语4.m4a | 10.7s | 1 | 1 | 0 |
| paid-1 | 口语5.m4a | 6.9s | 1 | 1 | 0 |
| paid-1 | 口语6.m4a | 5.8s | 1 | 1 | 0 |
| paid-1 | 口语7.m4a | 10.0s | 1 | 0 | 0 |
| paid-1 | 口语8.m4a | 30.8s | 1 | 1 | 0 |
| paid-1 | 口语9.m4a | 22.8s | 1 | 1 | 0 |
| paid-1 | 口语开始.m4a | 10.0s | 1 | 1 | 0 |
| paid-1 | 听力-M1-1.m4a | 3.4s | 1 | 1 | 0 |
| paid-1 | 听力-M1-11-12.m4a | 31.0s | 1 | 1 | 0 |
| paid-1 | 听力-M1-11-12标题.m4a | 3.1s | 1 | 1 | 0 |
| paid-1 | 听力-M1-13-14.m4a | 13.0s | 0 | 0 | 1 |
| paid-1 | 听力-M1-13-14标题.m4a | 6.2s | 1 | 1 | 0 |
| paid-1 | 听力-M1-15-16.m4a | 21.9s | 1 | 1 | 0 |
| paid-1 | 听力-M1-17-20(1).m4a | 82.5s | 0 | 0 | 0 |
| paid-1 | 听力-M1-17-20.m4a | 82.5s | 1 | 1 | 0 |
| paid-1 | 听力-M1-17-20题目.m4a | 6.5s | 1 | 1 | 0 |
| paid-1 | 听力-M1-2.m4a | 3.8s | 1 | 1 | 0 |
| paid-1 | 听力-M1-3.m4a | 4.0s | 1 | 1 | 0 |
| paid-1 | 听力-M1-4.m4a | 3.8s | 1 | 1 | 0 |
| paid-1 | 听力-M1-5.m4a | 3.3s | 1 | 1 | 0 |
| paid-1 | 听力-M1-6.m4a | 4.2s | 1 | 1 | 0 |
| paid-1 | 听力-M1-7.m4a | 5.2s | 1 | 1 | 0 |
| paid-1 | 听力-M1-8.m4a | 4.0s | 1 | 1 | 0 |
| paid-1 | 听力-M1-9-10.m4a | 30.7s | 1 | 1 | 0 |
| paid-1 | 听力-M1-9-10标题.m4a | 6.9s | 1 | 1 | 0 |
| paid-1 | 听力-M2-1.m4a | 5.0s | 1 | 1 | 0 |
| paid-1 | 听力-M2-10-11.m4a | 27.9s | 1 | 1 | 0 |
| paid-1 | 听力-M2-10-11标题.m4a | 7.1s | 1 | 1 | 0 |
| paid-1 | 听力-M2-12-13.m4a | 30.7s | 1 | 1 | 0 |
| paid-1 | 听力-M2-12-13标题.m4a | 4.6s | 1 | 1 | 0 |
| paid-1 | 听力-M2-14-15.m4a | 19.0s | 1 | 1 | 0 |
| paid-1 | 听力-M2-14-15标题.m4a | 4.3s | 1 | 1 | 0 |
| paid-1 | 听力-M2-2.m4a | 4.2s | 1 | 1 | 0 |
| paid-1 | 听力-M2-3.m4a | 6.2s | 1 | 1 | 0 |
| paid-1 | 听力-M2-4.m4a | 2.9s | 1 | 1 | 0 |
| paid-1 | 听力-M2-5.m4a | 3.3s | 1 | 1 | 0 |
| paid-1 | 听力-M2-6.m4a | 4.8s | 1 | 1 | 0 |
| paid-1 | 听力-M2-7.m4a | 4.5s | 1 | 1 | 0 |
| paid-1 | 听力-M2-8-9.m4a | 23.0s | 1 | 1 | 0 |
| paid-1 | 听力-M2-8-9标题.m4a | 3.6s | 1 | 1 | 0 |
| paid-1 | 听力M2-1.m4a | 2.2s | 1 | 1 | 0 |
| paid-1 | 听力M2-12-15.m4a | 97.4s | 1 | 1 | 0 |
| paid-1 | 听力M2-2.m4a | 3.8s | 1 | 1 | 0 |
| paid-1 | 听力M2-3.m4a | 3.6s | 1 | 1 | 0 |
| paid-1 | 听力M2-4-5.m4a | 27.7s | 1 | 1 | 0 |
| paid-1 | 听力M2-4-5标题.m4a | 4.7s | 1 | 1 | 0 |
| paid-1 | 听力M2-6-7.m4a | 19.0s | 1 | 1 | 0 |
| paid-1 | 听力M2-6-7标题.m4a | 5.5s | 1 | 1 | 0 |
| paid-1 | 听力M2-8-11.m4a | 92.8s | 1 | 1 | 0 |
| paid-2 | 口语面试题目1.mp3 | 17.0s | 1 | 1 | 0 |
| paid-2 | 口语面试题目2.mp3 | 15.2s | 1 | 1 | 0 |
| paid-2 | 口语面试题目3.mp3 | 22.2s | 1 | 1 | 0 |
| paid-2 | 口语面试题目4.mp3 | 17.2s | 1 | 1 | 0 |
| paid-2 | 口语面试题目说明音频.mp3 | 9.5s | 1 | 1 | 0 |
| paid-2 | 跟读1.mp3 | 2.0s | 1 | 1 | 0 |
| paid-2 | 跟读2.mp3 | 2.1s | 1 | 1 | 0 |
| paid-2 | 跟读3.mp3 | 3.0s | 1 | 1 | 0 |
| paid-2 | 跟读4.mp3 | 4.7s | 1 | 1 | 0 |
| paid-2 | 跟读5.mp3 | 3.4s | 1 | 1 | 0 |
| paid-2 | 跟读6.mp3 | 4.7s | 1 | 1 | 0 |
| paid-2 | 跟读7.mp3 | 4.2s | 1 | 1 | 0 |
| paid-2 | 跟读说明.mp3 | 8.8s | 1 | 1 | 0 |
| paid-2 | C1.mp3 | 28.9s | 1 | 1 | 0 |
| paid-2 | C2.mp3 | 26.9s | 1 | 1 | 0 |
| paid-2 | Listen to an announcement题目介绍音频.mp3 | 3.2s | 1 | 1 | 0 |
| paid-2 | listen to a conversation 题目介绍音频.mp3 | 2.2s | 1 | 1 | 0 |
| paid-2 | 听力部分说明音频.mp3 | 18.4s | 1 | 1 | 0 |
| paid-2 | 学术讲座（包含题目说明音频）.mp3 | 99.6s | 1 | 1 | 0 |
| paid-2 | 对答-Q1.mp3 | 4.3s | 1 | 1 | 0 |
| paid-2 | 对答-Q2.mp3 | 4.0s | 1 | 1 | 0 |
| paid-2 | 对答-Q3.mp3 | 2.7s | 1 | 1 | 0 |
| paid-2 | 对答-Q4.mp3 | 1.6s | 1 | 1 | 0 |
| paid-2 | 对答-Q5.mp3 | 1.9s | 1 | 1 | 0 |
| paid-2 | 对答-Q6.mp3 | 2.0s | 1 | 1 | 0 |
| paid-2 | 对答-Q7.mp3 | 1.7s | 1 | 1 | 0 |
| paid-2 | 对答-Q8.mp3 | 2.3s | 1 | 1 | 0 |
| paid-2 | 通知类1.mp3 | 12.9s | 1 | 1 | 0 |
| paid-2 | 通知类2（包含题目说明）.mp3 | 20.2s | 1 | 1 | 0 |
| paid-2 | C1.mp3 | 25.7s | 1 | 1 | 0 |
| paid-2 | C2.mp3 | 21.7s | 1 | 1 | 0 |
| paid-2 | 学术讲座1.mp3 | 75.7s | 1 | 1 | 0 |
| paid-2 | 学术讲座2.mp3 | 126.0s | 1 | 1 | 0 |
| paid-2 | 对答-Q1.mp3 | 2.4s | 1 | 1 | 0 |
| paid-2 | 对答-Q2.mp3 | 2.5s | 1 | 1 | 0 |
| paid-2 | 对答-Q3.mp3 | 2.3s | 1 | 1 | 0 |
| pack-1 | Pack-1_Listening.MP3 | 1108.6s | 20 | 20 | 0 |
| pack-1 | Pack-1_Speaking.MP3 | 513.4s | 11 | 11 | 0 |

## 核验方法与限制

1. 用 16 kHz 单声道 PCM 测量能量边界。阈值为 -38 dB；超过 1.45 秒的安静区间分开处理。该测量只证明带声与安静，不把每个安静区间直接宣称为官方答题时间。
2. 仅为 ASR 压缩长静音，并保存压缩时刻到原时刻的映射。播放器使用从原时间区间导出的片段，绝不播放这个压缩转写轨。
3. 已给原文与本地 ASR 的词序对齐后，再将边界吸附到可测量的安静区间。文本相似度至少 0.94、边界可靠且片段内部无 4 秒以上长静音时，标为自动核验通过。
4. Pack 采访原页没有逐字转写时，必须先匹配前面全部 7 个复述题，再找到恰好 4 段、均伴随 30 秒以上作答等待的采访提示，按已核对的四题顺序关联。此类证据另标 ordered-acoustic-structure-cross-check，不冒充人工听校。
5. verified 表示通过上述可追溯的自动核验；humanReviewed 单独标识人工听校，默认 false。低匹配或边界不确定的段落为 needs-review，不能进入严格播放。
6. sources[].excludedWaits 列出被排除的安静区间（包括末尾静音）。这些区间不作为题目音频播放，也不能再当作准备时间；作答窗口由版本化考试规则单独计时。
7. 说明候选段独立保存为 directions；没有充分证据的说明不会自动混入题干。源轨没有独立朗读问题时，不凭空生成问题音频。
8. cue 段是原轨中的录音提示音，按短时窄带频谱及其位于复述题后的顺序核对；sourceDelayAfterPromptSeconds 仅记录原录音中的间隔，不自动等同于正式准备时间。提示音与正文是独立资产，播放器不应额外再播放第二遍提示音。

## 运行

```sh
# 使用项目专属虚拟环境；不要修补系统 Homebrew FFmpeg。
uv venv --python 3.12 .venv-media
uv pip install --python .venv-media/bin/python mlx-whisper imageio-ffmpeg rapidfuzz
HF_HUB_DISABLE_XET=1 .venv-media/bin/python scripts/segment_media.py all
.venv-media/bin/python scripts/segment_media.py validate
```

工具优先使用 imageio_ffmpeg 自带二进制。macOS 安装尚未完成时可用系统自带 CoreAudio 解码，输出标准 WAV，不调用损坏的 Homebrew FFmpeg。Numba/LLVM 缺失时使用同一 DTW 函数的纯 Python 实现，计算更慢但不改变算法。

## 接入规则

只将 verified=true 且 kind 为 stimulus/prompt 的段落映射至题目。questionIds 共享同一个 groupId 时只播放一次，然后按题号分别答题。保留源轨、时间区间与核验状态以供校验页面追踪；不得把 needs-review 直接改为已核验以开放模考。

## 来源差异

- `student-1-s-interview-1-prompt`：原区间 12.22–28.16 秒，`verified=false`。纸面询问目前居住城市规模；音频询问最近到访另一城市的经历。保留不同版本，不宣称匹配。2026-09-05 官方 ZIP 复查仍有此差异。
- `pack-1-speaking-listen_repeat-6-prompt`：原区间 153.38–156.96 秒，`verified=true`。原音开头有纸面转写漏掉的引导词；保留完整单一原声并披露漏词，不截去词头。
- `mat-237f97573298`：供应 M1-13–14 音频重复 M1-15–16 的远足通知。仅在明确披露且来源核验的情况下使用匹配的 canonical 拍卖原音，原差异留档。

公开文档不重印完整私有题目/转写，详细证据保留本地。见[独立官方复核](ets-2026-verification.zh-CN.md)和[资料说明](MATERIALS.zh-CN.md)。
