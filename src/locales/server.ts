import type { Locale } from "../i18n";

/** Product-authored server messages only. Unknown content remains verbatim.
 * Keys and answer data are never translated in storage or requests. Matching
 * complete messages (or anchored templates) avoids rewriting source passages.
 */
const messages: [string, string][] = [
  [
    "Lightweight example: prepared questions and assets are verified; original PDFs and full audio tracks are optional and not included.",
    "轻量示例已校验题目和运行资源；原始 PDF 与整轨音频为可选资料，默认不附带。",
  ],
  [
    "Practice groups require practice mode and a fixed source route.",
    "题组需使用专项练习模式，并保留原卷固定路线。",
  ],
  [
    "Choose a practice group or individual question filters, not both.",
    "题组不能同时使用其他题目筛选，请重新选择练习范围。",
  ],
  [
    "This practice group is no longer available for this source exam. Refresh the practice library.",
    "本套资料中的题组已不可用，请刷新专项题库后重新选择。",
  ],
  [
    "The selected practice group belongs to a different section.",
    "所选题组与练习科目不一致，请重新选择。",
  ],
  [
    "This practice group changed after it was listed. Refresh the practice library before starting.",
    "此题组内容已更新，请刷新专项题库后重新选择并开始。",
  ],
  [
    "A group content expectation requires a practice group.",
    "题组版本信息缺少对应题组，请重新选择。",
  ],
  [
    "The selected practice group could not be frozen in its complete source order. Refresh the practice library.",
    "无法按原卷顺序完整载入本题组，请刷新专项题库后重试。",
  ],
  [
    "Pausing audio requires practice aids enabled before starting.",
    "音频播放期间暂停需要在练习开始前开启辅助；未开启时可在答题阶段暂停。",
  ],
  ["allowPracticeAids must be a boolean.", "练习辅助设置必须为勾选或未勾选。"],
  [
    "Replay and immediate feedback can only be enabled for specialized practice, not full exams or strict practice.",
    "重播和即时答案只能在专项练习开始前开启，完整流程和严格模考不能使用。",
  ],
  [
    "Replay, immediate feedback and review resources were not enabled for this practice session.",
    "本次练习未在开始前开启辅助，无法重播或即时查看答案与解析；结束后可正常复盘。",
  ],
  [
    "This older session has no saved audio verification. Recover verified audio to continue without changing your saved answers or progress.",
    "这份旧版练习缺少音频校验信息。可修复音频后继续，已答内容和当前进度会保留。",
  ],
  [
    "This session cannot safely recover legacy audio. Keep its saved answers and start a new practice with verified sources.",
    "这份旧练习的题目或资料已变化，无法直接恢复音频。已答内容会保留，请使用校验通过的资料开始新练习。",
  ],
  [
    "Audio recovery expects an empty JSON object.",
    "音频恢复请求格式不正确，请刷新后重试。",
  ],
  ["Unsupported vocabulary fields.", "单词本请求包含不支持的字段。"],
  ["Choose a valid vocabulary status.", "请选择有效的词条学习状态。"],
  [
    "Provide at least one vocabulary field to update.",
    "请填写至少一项要修改的词条内容。",
  ],
  ["Vocabulary entry not found.", "未找到此词条。"],
  ["That word is already in your vocabulary.", "该词已在单词本中。"],
  ["word must contain 1–120 characters.", "词语或短语需要 1–120 个字符。"],
  ["Invalid sourceQuestionId.", "来源题目编号无效。"],
  ["Invalid sourceSessionId.", "来源练习编号无效。"],
  ["Invalid id.", "词条编号无效。"],
  [
    "page must be an integer from 1 to 1000000.",
    "页码需要是 1 到 1000000 之间的整数。",
  ],
  [
    "pageSize must be an integer from 1 to 100.",
    "每页条数需要是 1 到 100 之间的整数。",
  ],
  ["word must be text.", "词语或短语需要是文本。"],
  ["word must be at most 120 characters.", "词语或短语不能超过 120 个字符。"],
  [
    "word contains unsupported control characters.",
    "词语或短语包含不支持的控制字符。",
  ],
  ["meaning must be text.", "释义需要是文本。"],
  ["meaning must be at most 2000 characters.", "释义不能超过 2000 个字符。"],
  [
    "meaning contains unsupported control characters.",
    "释义包含不支持的控制字符。",
  ],
  ["context must be text.", "上下文需要是文本。"],
  ["context must be at most 4000 characters.", "上下文不能超过 4000 个字符。"],
  [
    "context contains unsupported control characters.",
    "上下文包含不支持的控制字符。",
  ],
  ["sourceLabel must be text.", "来源需要是文本。"],
  ["sourceLabel must be at most 240 characters.", "来源不能超过 240 个字符。"],
  [
    "sourceLabel contains unsupported control characters.",
    "来源包含不支持的控制字符。",
  ],
  ["q must be text.", "搜索词需要是文本。"],
  ["q must be at most 200 characters.", "搜索词不能超过 200 个字符。"],
  [
    "q contains unsupported control characters.",
    "搜索词包含不支持的控制字符。",
  ],
  [
    "User-authored resource pack · Untimed guided practice.",
    "自编资源包 · 不限时专项练习。",
  ],
  ["user-authored", "自编资料"],
  [
    "A module has no valid verified or configured duration.",
    "此模块缺少已核实或有效配置的时长。",
  ],
  [
    "A question has no valid verified or configured response duration.",
    "此题缺少已核实或有效配置的作答时长。",
  ],
  [
    "Adaptive routing requires complete branch questions.",
    "模拟自适应需要完整的分支题目。",
  ],
  [
    "Adaptive routing requires verified answers for every routing question.",
    "模拟自适应的每道分流题都需要已核实答案。",
  ],
  [
    "Answers are accepted only during the response window.",
    "只能在作答时段内提交答案。",
  ],
  ["Choose one of the current question options.", "请选择当前题目的一个选项。"],
  ["Choose strict or practice mode.", "请选择严格模考或专项练习模式。"],
  [
    "Continue is only available after the writing response time has ended.",
    "写作时间结束后才能点击继续。",
  ],
  [
    "Each individual word-bank token can be used only once.",
    "词库中的每个独立词块只能使用一次。",
  ],
  [
    "Filtering would make the adaptive branches incomplete.",
    "该筛选会导致自适应分支不完整。",
  ],
  ["Invalid answer format.", "答案格式无效。"],
  ["Invalid scope or route.", "练习范围或路径无效。"],
  ["Invalid sentence token index.", "造句词块编号无效。"],
  ["Navigation is unavailable in this phase.", "当前阶段不能切换题目。"],
  ["No current audio segment.", "当前没有音频片段。"],
  [
    "No interactive questions are available for this selection.",
    "当前选择没有可用的交互题目。",
  ],
  ["No prompt is currently playing.", "当前没有正在播放的题目音频。"],
  ["Pause is only available in practice mode.", "只有专项练习模式支持暂停。"],
  [
    "Provide one token position per sentence gap.",
    "请为每个造句空格提供一个词块位置。",
  ],
  [
    "Question-type and error-review filters are only available in practice mode.",
    "题型和错题筛选仅用于专项练习模式。",
  ],
  [
    "Repeat timing requires seven positive durations.",
    "复述计时需要七个大于零的时长。",
  ],
  ["Replay is only available in practice mode.", "只有专项练习模式支持重播。"],
  [
    "Selected review questions must belong to this exam.",
    "所选复习题目必须属于这套试卷。",
  ],
  [
    "Source-page placeholders cannot enter strict practice.",
    "原始页面占位题不能用于严格模考。",
  ],
  [
    "Speaking responses submit automatically when the recording window ends.",
    "口语录音时间结束后会自动提交。",
  ],
  [
    "Strict practice does not allow skipping a prompt.",
    "严格模考不允许跳过题目音频。",
  ],
  [
    "Strict practice requires verified audio for every listening/speaking question.",
    "严格模考的每道听力和口语题都需要已核实音频。",
  ],
  [
    "Strict practice requires verified durations for all media segments.",
    "严格模考的所有媒体片段都需要已核实的时长。",
  ],
  [
    "Strict repeat response windows must remain within the verified 8–12 second range.",
    "严格模考的复述作答时间必须保持在已核实的 8–12 秒范围内。",
  ],
  [
    "Supplementary materials use practice mode only; they are not TOEFL iBT 2026 mock exams.",
    "补充资料仅用于专项练习，不作为 TOEFL iBT 2026 模考。",
  ],
  [
    "The current media segment has not finished its playback window.",
    "当前媒体片段尚未播放完毕。",
  ],
  ["The current stage has already begun.", "当前阶段已经开始。"],
  [
    "The displayed question is no longer current. Your expired answer was not submitted.",
    "页面上的题目已不是当前题目，超时答案未提交。",
  ],
  [
    "The writing response time has ended. Select Continue to leave this question.",
    "写作时间已结束，请点击继续离开本题。",
  ],
  [
    "These materials have not passed strict-practice validation.",
    "这些资料尚未通过严格模考校验。",
  ],
  [
    "This ended event belongs to a different media segment.",
    "此播放结束事件属于其他媒体片段。",
  ],
  [
    "This exam has no complete matched lower/upper branches. Choose a fixed route.",
    "这套试卷没有完整匹配的高低分支，请选择固定路径。",
  ],
  [
    "This playing event belongs to a different media segment.",
    "此播放事件属于其他媒体片段。",
  ],
  ["This question cannot be flagged now.", "当前不能标记本题。"],
  ["This session has ended.", "本次练习已结束。"],
  [
    "This source contains unavailable prompts; strict practice cannot silently omit them.",
    "此资料存在不可用的题目，严格模考不能自动略过这些题目。",
  ],
  ["Timing settings must be an object.", "计时设置必须为对象格式。"],
  [
    "Timing values must be between 1 and 7200 seconds.",
    "计时时长必须在 1–7200 秒之间。",
  ],
  ["Unknown cloze blank.", "未知的填词空格。"],
  ["Unknown session action.", "未知的练习操作。"],
  [
    "Use the manual reference-audio player for untimed practice.",
    "不限时练习请使用手动参考音频播放器。",
  ],
  [
    "You can only navigate inside the current module.",
    "只能在当前模块内切换题目。",
  ],
  [
    "You cannot return to an earlier question in this task.",
    "此任务不能返回之前的题目。",
  ],
  [
    "You must answer this question before selecting Next.",
    "请先作答，再点击下一题。",
  ],
  ["A JSON object is required.", "需要提供 JSON 对象。"],
  ["A recording chunk is unavailable.", "某个录音片段不可用。"],
  [
    "A required prompt file is missing. Strict practice cannot begin.",
    "缺少必要的题目文件，严格模考无法开始。",
  ],
  [
    "A strict session is active. New sessions are locked until it ends.",
    "严格模考进行中，结束后才能开始新的练习。",
  ],
  [
    "A strict session is already active. New sessions are locked until it ends.",
    "已有严格模考进行中，结束后才能开始新的练习。",
  ],
  [
    "A take must use one question and one audio format.",
    "同一次录音必须对应一道题并使用同一种音频格式。",
  ],
  [
    "Another strict session is active. Other sessions and their media are locked until it ends.",
    "另一场严格模考进行中，其他练习及其媒体暂时锁定。",
  ],
  ["Asset not found.", "未找到素材。"],
  [
    "Choose a valid mistake section and review status.",
    "请选择有效的错题部分和复习状态。",
  ],
  ["Exam not found.", "未找到试卷。"],
  [
    "Final metadata does not match the already saved recording chunks.",
    "最终录音信息与已保存片段不一致。",
  ],
  [
    "Finish the active strict session before importing resources.",
    "请先结束当前严格模考，再导入资源。",
  ],
  [
    "Immediate feedback is only available for visited practice questions.",
    "即时核对仅适用于专项练习中已访问的题目。",
  ],
  ["Invalid JSON.", "JSON 格式无效。"],
  ["Invalid audio MIME type.", "音频 MIME 类型无效。"],
  ["Invalid identifier.", "标识符无效。"],
  ["Invalid question section.", "题目所属部分无效。"],
  ["Invalid recording segment index.", "录音片段编号无效。"],
  ["Library asset not found.", "未找到资料库素材。"],
  [
    "No question asset is authorized in this phase.",
    "当前阶段不能访问题目素材。",
  ],
  [
    "Only a visited writing or speaking response can receive a rubric self-rating.",
    "只有已访问的写作或口语回答可以进行量表自评。",
  ],
  [
    "Only an already visited speaking question can finalize a recording.",
    "只有已访问的口语题可以完成录音保存。",
  ],
  [
    "Original source files are locked while strict practice is active.",
    "严格模考期间原始资料文件已锁定。",
  ],
  ["Recording not found.", "未找到录音。"],
  [
    "Recording playback is locked during strict practice.",
    "严格模考期间不能回放录音。",
  ],
  ["Recording storage is not accessible.", "无法访问录音存储目录。"],
  [
    "Recording uploads are limited to speaking questions already visited in this session.",
    "只能为本次练习中已访问的口语题上传录音。",
  ],
  ["Resource not found.", "未找到资源。"],
  [
    "Review assets are locked until this session ends.",
    "练习结束后才能访问复盘素材。",
  ],
  ["Review is available only after the session ends.", "练习结束后才能复盘。"],
  [
    "Review, feedback and reference resources are locked while strict practice is active.",
    "严格模考进行中，复盘、即时核对与参考资料暂时锁定。",
  ],
  ["Session not found.", "未找到练习记录。"],
  [
    "Some recording chunks have not arrived yet. Retry pending uploads before playback.",
    "部分录音片段尚未保存，请重试待上传片段后再播放。",
  ],
  [
    "Source files or verification versions changed/missing. Stop the service and reimport before starting strict practice.",
    "来源文件或核验版本发生变化或缺失，请停止服务并重新导入后再开始严格模考。",
  ],
  [
    "Strict-session self-rating is available after completion.",
    "严格模考完成后才能自评。",
  ],
  [
    "The TOEFL iBT Practice Test 1 example is missing. Restore examples/ets-practice-test-1.",
    "缺少 TOEFL iBT Practice Test 1 示例，请恢复 examples/ets-practice-test-1。",
  ],
  [
    "Existing TOEFL iBT Practice Test 1 has missing or changed sources. Reimport or restore it before installing the example.",
    "现有 TOEFL iBT Practice Test 1 的来源缺失或已更改，请先重新导入或恢复原资料，再安装示例。",
  ],
  [
    "An unregistered TOEFL iBT Practice Test 1 file already exists. Restore its catalog before installing the example.",
    "已存在未登记的 TOEFL iBT Practice Test 1 文件，请先恢复其题库目录，再安装示例。",
  ],
  [
    "The local catalog is invalid. Restore it before installing the example.",
    "本地题库目录无效，请先恢复目录，再安装示例。",
  ],
  [
    "Bundled example contains an unsafe file path.",
    "内置示例包含不安全的文件路径。",
  ],
  [
    "Bundled example paths cannot contain symbolic links.",
    "内置示例路径不能包含符号链接。",
  ],
  [
    "Bundled example path is outside the project folder.",
    "内置示例路径超出项目目录。",
  ],
  [
    "Bundled example JSON is missing or invalid.",
    "内置示例的 JSON 缺失或无效，请恢复完整的 examples/ets-practice-test-1 目录。",
  ],
  [
    "Bundled example JSON must contain an object.",
    "内置示例的 JSON 必须包含对象。",
  ],
  [
    "Bundled example catalog is missing materials or exams.",
    "内置示例目录缺少来源资料或试卷。",
  ],
  [
    "Bundled example catalog must contain only TOEFL iBT Practice Test 1.",
    "内置示例目录只能包含 TOEFL iBT Practice Test 1。",
  ],
  [
    "Bundled example material metadata is invalid.",
    "内置示例的资料元数据无效。",
  ],
  [
    "Bundled example conflicts with an existing source material.",
    "内置示例与现有来源资料冲突，未覆盖原资料。",
  ],
  [
    "Bundled example requires schemaVersion 1 and examId student-1.",
    "内置示例要求 schemaVersion 为 1，examId 为 student-1。",
  ],
  ["Bundled example file manifest is empty.", "内置示例文件清单为空。"],
  ["Bundled example file metadata is invalid.", "内置示例的文件元数据无效。"],
  [
    "Bundled example lists a source file more than once.",
    "内置示例清单重复登记了来源文件。",
  ],
  [
    "Bundled example may install only its exam and local resource files.",
    "内置示例只能安装自身试卷和本地资源文件。",
  ],
  [
    "Bundled example lists a destination more than once.",
    "内置示例清单重复登记了安装路径。",
  ],
  [
    "Bundled example manifest must verify exam.json and catalog.json.",
    "内置示例清单必须校验 exam.json 和 catalog.json。",
  ],
  [
    "Bundled example exam or catalog destination is invalid.",
    "内置示例的试卷或目录安装位置无效。",
  ],
  [
    "Bundled example must preserve the native timed TOEFL iBT Practice Test 1 exam.",
    "内置示例必须保留 TOEFL iBT Practice Test 1 的原生计时试卷。",
  ],
  [
    "Bundled example practice must retain every source question.",
    "内置示例练习必须保留全部原题。",
  ],
  [
    "Bundled example must preserve its verified reading, listening, and writing scopes.",
    "内置示例必须保留通过核验的阅读、听力和写作练习范围。",
  ],
  [
    "Bundled example must include all four ordered sections.",
    "内置示例必须包含按原顺序排列的完整四科。",
  ],
  [
    "Bundled example contains missing or unverified question content.",
    "内置示例包含缺失或未核验的题目内容。",
  ],
  [
    "Bundled example changed during validation.",
    "内置示例在核验期间发生更改，请重试。",
  ],
  [
    "Bundled example destination parent is not a directory.",
    "内置示例安装位置的上级路径不是目录。",
  ],
  ["The project folder does not exist.", "项目目录不存在。"],
  [
    "A local resource changed during example installation.",
    "本地资源在示例安装期间发生更改，未继续覆盖。",
  ],
  [
    "An installed example file failed verification.",
    "已安装的示例文件未通过核验。",
  ],
  [
    "The local catalog changed during example installation. Try again.",
    "本地题库目录在示例安装期间发生更改，请重试。",
  ],
  [
    "Installed example failed source integrity.",
    "已安装示例未通过来源完整性核验。",
  ],
  [
    "The frontend is not built. Run npm run build, or use the Vite development server.",
    "前端尚未构建，请运行 npm run build 或使用 Vite 开发服务器。",
  ],
  [
    "The original-material library is locked while strict practice is active.",
    "严格模考进行中，原始资料库暂时锁定。",
  ],
  ["The recording segment is empty.", "录音片段为空。"],
  [
    "The structured-content verification manifest does not match this generated exam. Reimport the source materials.",
    "结构化内容核验清单与生成的试卷不匹配，请重新导入来源资料。",
  ],
  ["The upload is too large.", "上传文件过大。"],
  [
    "This asset does not belong to the currently allowed question.",
    "此素材不属于当前可访问的题目。",
  ],
  [
    "This recording segment filename already contains different data.",
    "此录音片段文件名已对应其他数据。",
  ],
  [
    "This recording segment identity already contains different data.",
    "此录音片段编号已对应其他数据。",
  ],
  [
    "This segment is outside the finalized take definition.",
    "此片段不属于已完成保存的录音范围。",
  ],
  [
    "This take was already finalized with different metadata.",
    "此录音已按不同的最终信息完成保存。",
  ],
  [
    "Use a positive page, pageSize 1–100 and a short search query.",
    "页码须为正数，每页 1–100 条，搜索内容须简短。",
  ],
  ["Use a supported audio Content-Type.", "请使用受支持的音频 Content-Type。"],
  ["Use a supported audio MIME type.", "请使用受支持的音频 MIME 类型。"],
  [
    "Use a valid expected segment count and a short recording end reason.",
    "请提供有效的预期片段数和简短的录音结束原因。",
  ],
  [
    "Use an integer rubric rating from 0 to 5 and short notes.",
    "自评分须为 0–5 的整数，笔记须简短。",
  ],
  ["Use application/json.", "请使用 application/json 格式。"],
  [
    "This media/source asset no longer matches the session snapshot. The original answers and deadline are preserved; restore the source or start a reimported practice.",
    "此媒体或来源素材已不匹配练习快照。原答案和截止时间已保留，请恢复来源或重新导入后开始新的练习。",
  ],
  [
    "Source files or verification inputs changed/missing. Stop the service and reimport before strict practice.",
    "来源文件或核验输入已变化或缺失，请停止服务并重新导入后再进行严格模考。",
  ],
  [
    "A different pack with this id already exists. Use the CLI --replace option to update it.",
    "此编号已有不同的资源包，请使用命令行 --replace 选项更新。",
  ],
  ["A referenced image cannot be decoded.", "无法解码引用的图片。"],
  [
    "A resource file is missing, unsupported, or outside the pack folder.",
    "资源文件缺失、格式不受支持或位于资源包目录之外。",
  ],
  [
    "Audio duration could not be verified. Use a supported audio file.",
    "无法核实音频时长，请使用受支持的音频文件。",
  ],
  [
    "Audio must reference an audio or video file.",
    "音频必须引用音频或视频文件。",
  ],
  ["Audio requires a local file.", "音频需要本地文件。"],
  [
    "Choice answer must match a unique choice id.",
    "选择题答案必须对应一个唯一的选项编号。",
  ],
  [
    "Choice questions require 2–8 choices with id and text.",
    "选择题需要 2–8 个带编号和文字的选项。",
  ],
  [
    "Cloze answer length must match its missing-letter count.",
    "填词答案长度必须与缺失字母数一致。",
  ],
  [
    "Cloze placeholders must match each blank exactly once.",
    "每个填词空格必须恰好对应一个占位符。",
  ],
  [
    "Cloze questions require blanks and a passageTemplate.",
    "填词题需要 blanks 和 passageTemplate 字段。",
  ],
  [
    "Each image needs a local file and descriptive alt text.",
    "每张图片都需要本地文件和描述性的替代文字。",
  ],
  [
    "Each resource file must be smaller than 100 MB.",
    "每个资源文件必须小于 100 MB。",
  ],
  [
    "Each resource-pack section requires 1–200 questions.",
    "资源包的每个部分需要 1–200 道题。",
  ],
  [
    "Every cloze blank requires an id and length from 1 to 30.",
    "每个填词空格需要编号和 1–30 的长度。",
  ],
  ["Every question requires a nonempty prompt.", "每道题都需要非空的题干。"],
  [
    "Listening and speaking questions require an original audio or video file.",
    "听力和口语题需要原始音频或视频文件。",
  ],
  [
    "Pack id must use 1–48 lowercase letters, numbers, hyphens, or underscores.",
    "资源包编号须由 1–48 个小写字母、数字、连字符或下划线组成。",
  ],
  [
    "Question ids must be unique and question types must match their section.",
    "题目编号必须唯一，题型必须与所属部分匹配。",
  ],
  ["Question source must be a PDF.", "题目来源必须为 PDF。"],
  [
    "Question source requires a local PDF file and a positive page.",
    "题目来源需要本地 PDF 文件和正整数页码。",
  ],
  ["Question text fields must be strings.", "题目的文本字段必须为字符串。"],
  [
    "Resource files must use relative paths inside the pack folder.",
    "资源文件必须使用资源包目录内的相对路径。",
  ],
  [
    "Resource pack must contain valid finite JSON values.",
    "资源包必须使用有效且有限的 JSON 值。",
  ],
  ["Resource pack requires 1–4 sections.", "资源包需要 1–4 个部分。"],
  [
    "Resource pack requires a title of 1–200 characters.",
    "资源包标题需要 1–200 个字符。",
  ],
  ["Resource pack requires schemaVersion: 1.", "资源包需要 schemaVersion: 1。"],
  [
    "Resource question contains unknown fields. Check the import guide.",
    "资源题目包含未知字段，请查看导入指南。",
  ],
  [
    "Resource-pack JSON must be smaller than 2 MB.",
    "资源包 JSON 必须小于 2 MB。",
  ],
  [
    "Resource-pack destination cannot be a symbolic link.",
    "资源包目标目录不能是符号链接。",
  ],
  [
    "Resource-pack destination is outside the local data folder.",
    "资源包目标位置位于本地 data 目录之外。",
  ],
  [
    "Resource-pack files must total less than 200 MB.",
    "资源包文件总大小必须小于 200 MB。",
  ],
  [
    "Sections must have unique reading, listening, writing, or speaking ids.",
    "部分编号必须唯一，且为 reading、listening、writing 或 speaking。",
  ],
  [
    "Sentence questions require nonempty tokens and slots.",
    "造句题需要非空的 tokens 和 slots。",
  ],
  [
    "This pack id conflicts with an existing test.",
    "此资源包编号与现有试卷冲突。",
  ],
  [
    "This pack references media. Import it with npm run import:pack and its folder.",
    "此资源包引用了媒体文件，请通过 npm run import:pack 导入资源包及其目录。",
  ],
  [
    "Cloze answers must contain only the missing English letters.",
    "填词答案只能包含缺失的英文字母。",
  ],
  ["Cloze blank contains unsupported fields.", "填词空格包含不受支持的字段。"],
  [
    "Cloze blank numbers must be positive integers.",
    "填词空格题号必须为正整数。",
  ],
  ["Cloze prefixes and suffixes must be text.", "填词的前缀和后缀必须为文字。"],
  ["Documentation not found.", "未找到文档。"],
  [
    "Image imports require Pillow. Install requirements-import.txt first.",
    "导入图片需要 Pillow，请先安装 requirements-import.txt 中的依赖。",
  ],
  [
    "Invalid structured question field types. Check the import guide.",
    "结构化题目字段类型无效，请查看导入指南。",
  ],
  ["Question assets must be a list.", "题目素材必须为列表。"],
  [
    "Question interaction must be select_sentence when provided.",
    "如提供 interaction 字段，其值必须为 select_sentence。",
  ],
  [
    "Question source must be a local PDF reference object.",
    "题目来源必须为本地 PDF 引用对象。",
  ],
  [
    "Question taskType must be a lowercase identifier.",
    "题目 taskType 必须为小写标识符。",
  ],
  [
    "Resource-pack destination is outside the project folder.",
    "资源包目标位置位于项目目录之外。",
  ],
  [
    "Sentence answers must be text or a list of accepted text answers.",
    "造句答案必须为文字或可接受文字答案的列表。",
  ],
  [
    "Sentence gaps require unique ids; fixed slots require nonempty fixed text.",
    "造句空格需要唯一编号，固定位置需要非空的固定文字。",
  ],
  [
    "Sentence metadata must contain lists of words.",
    "造句元数据必须包含词语列表。",
  ],
  [
    "Sentence questions need at least one gap and enough individual word tokens.",
    "造句题至少需要一个空格和足够的独立词块。",
  ],
  [
    "Sentence slots must be objects containing an id or a fixed word.",
    "造句位置必须为包含编号或固定词语的对象。",
  ],
  [
    "Writing word counts must be integers from 1 to 10000.",
    "写作字数必须为 1–10000 的整数。",
  ],
];

messages.push(
  ...([
    [
      "Essentials is a separate supplemental test, not a 2026 iBT mock. It does not use iBT question counts, routing, timing, or scores.",
      "Essentials 是独立的补充材料，不是 2026 iBT 模考；不使用 iBT 题量、分流、计时或分数。",
    ],
    [
      "The original full audio was cross-checked automatically using local speech recognition, source text, and acoustic boundaries. Playback clips omit the original answer-wait periods; they are not ETS-certified clips.",
      "原始整轨已通过本地ASR、原文与声学边界自动交叉校验，播放切片不包含原录音作答等待；并非ETS认证切片。",
    ],
    [
      "Two Speaking items lack verifiable original audio prompts. Their sources are retained and the items are excluded from interactive counts; no replacement questions are generated.",
      "原资料缺少2道口语题的可核验原声提示，已保留出处并列入排除项，不计入交互题数，也不生成替代问题。",
    ],
    [
      "In Listening Module 1, the first question of the second conversation is unnumbered, leaving later printed numbers one behind. Local numbers 11–18 follow answer-key order while preserving original numbering.",
      "原题 Listening Module 1 第二段会话首题未编号，后续印刷题号落后一位；本地11–18按答案表顺序对齐，保留原始编号。",
    ],
    [
      "Listening Module 2 numbering jumps from 11 to 13. Local numbers 12–16 correspond to printed numbers 13–17, with answers aligned by question order.",
      "原题 Listening Module 2 的题号在11后跳到13；本地顺序号12–16对应原纸版13–17，答案按题目顺序对齐。",
    ],
    [
      "Reading Module 2 multiple-choice questions are printed as 1–10. Local numbers 11–20 follow the answer key while retaining original numbers.",
      "原题 Reading Module 2 的选择题印为1–10；本地顺序号11–20按答案表对齐，并保留原题号。",
    ],
    [
      "Fixed paper-based practice route. ETS adaptive algorithms and official scoring cannot be reproduced locally.",
      "固定纸版练习路径；ETS 自适应算法与正式评分不可本地复制。",
    ],
    [
      "Verified Listening and Speaking prompts have item or group audio. Full study tracks remain available for manual reference. All tasks are untimed supplemental practice; read-aloud tasks use the original printed text.",
      "已核验的听力题与口语原声提示提供分题或题组音频；完整学习音轨另作手动参考。所有任务采用不限时补充练习，朗读题直接使用原纸面文字。",
    ],
    [
      "Scanned questions have been checked against the source pages and structured. Original crops appear only as review evidence.",
      "扫描题面已按原页核对并结构化；原裁图仅在复盘中作为来源证据。",
    ],
    [
      "The first five response transcripts in the supplied Listening PDFs for sets 2/3 were swapped. Each was cross-checked against its test options, original audio, and the other transcript. Audio tracks and test books remain in place; questions are unchanged.",
      "提供的2/3号听力原文PDF前5个对答文本互换。已由各自题本选项、各自原音与另一原文文本交叉核验；不交换音轨或题本、不改写问题。",
    ],
    [
      "Teacher materials include current publicly available ETS companion audio, matched by official set, module, and item number with file hashes checked. Automated speech comparison assists review; it does not replace source questions or claim word-for-word manual listening verification.",
      "教师版已补充 ETS 当前公开配套原声：按官方套号、模块和题号关联并核验文件摘要；自动语音比对仅供复盘校核，不替换原题或宣称逐字人工听校。",
    ],
    [
      "Three items use verified original audio for the same questions from another supplied edition. Matching evidence and audio differences are retained in review; no synthesized audio is used.",
      "本套3道题采用所给资料另一版本中已核验的同题原声；对应关系和源音差异保留在复盘中，不使用合成音频。",
    ],
    [
      "Two objective scoring units have no unique answer supported by the sources and are excluded from automatic scoring. Answer conflicts and eligibility for question/audio timing are verified separately.",
      "本套有2个客观题计分单元无法从原资料确定唯一答案，已排除自动判分；答案争议与题面、音频的计时资格分别核验。",
    ],
    [
      "This material shares questions with the corresponding Pack. Its original sequence is preserved and matching items share a content identity.",
      "本资料与对应 Pack 存在重复题，保留原套编排并共享题库内容身份。",
    ],
    [
      "Some source reference answers conflict. Verified corrections and evidence are shown only in review and resource validation.",
      "本资料参考答案存在冲突，已核对的修正及依据仅在复盘和资料校验中显示。",
    ],
    [
      "Practice screenshots and reference keys are user-supplied materials; item counts may differ from the public basic edition.",
      "练习截图和参考答案为用户提供资料，题量与公开基本版可能不同。",
    ],
    [
      "Missing-letter items follow the letters and blank lengths in the source image. Enter only the missing letters; the original image remains available for review. Blanks without a unique supported answer are excluded from scoring.",
      "缺字题已按原图给定字母和空格长度结构化；只输入缺失字母，原图可复核。无法确定唯一答案的空不计入核分。",
    ],
    [
      "Some original audio differs in wording from the supplied printed transcript. The complete original audio is preserved, and differences are explained in review.",
      "部分原声与所给纸版转写存在措辞差异，保留完整原声；两种来源的差异在复盘中说明。",
    ],
    [
      "All Listening and Speaking audio is verified except Interview question 1, whose printed and audio versions differ. That item is available only for untimed source study; full strict and strict Speaking practice are unavailable. Reading, Listening, and Writing strict eligibility follows the current source-integrity check.",
      "除采访第1题纸面与原音版本不符外，其余听说原音已完成核验；该题仅供不限时原文学习，完整严格模考与口语严格专项不可用。阅读、听力和写作的严格计时资格以当前资料完整性检查为准。",
    ],
    [
      "Questions have been checked page by page against the original PDFs and structured. Whole-question images are for review only; necessary photos and scenes use high-resolution PDF crops.",
      "题面已按原PDF逐页核对并结构化；原整题图仅供复盘核对，题意所需照片和场景使用原PDF高清裁图。",
    ],
  ] as [string, string][]),
);

const explanationMessages: [string, string][] = [
  ["Insufficient explanation evidence", "解析依据不足"],
  ["Local assistance · Missing-letter reconstruction", "本地辅助 · 补字还原"],
  [
    "Local assistance · Word bank and reference order",
    "本地辅助 · 词块与参考语序",
  ],
  ["Local assistance · Reference-key check", "本地辅助 · 参考键核对"],
  ["Local assistance · Imported passage location", "本地辅助 · 已导入原文定位"],
  ["Source explanation (not official ETS)", "资料附带解析（非 ETS 官方）"],
  ["Original source explanation", "原资料解析"],
  ["Source explanation", "资料附带解析"],
  [
    "No verified missing-letter answer can be safely reconstructed. Check the source question and conflict records; no correctness conclusion is generated.",
    "没有可安全还原的已核验填词答案；请查看原题及冲突记录，不据此生成正确结论。",
  ],
  [
    "The following mechanically compares the given letters with source reference answers. It is not a vocabulary or grammar explanation from the source. Use the question context to check word form, tense, and collocations.",
    "以下是已给字母与资料参考答案的机械核对，不是原资料提供的词义或语法解析。请结合原题上下文检查词性、时态及搭配。",
  ],
  [
    "This item has no verifiable reference sentence. A standard answer is not inferred or invented.",
    "此题没有可核验的参考句，不推断或另造标准答案。",
  ],
  [
    "The bounded search could not reconstruct the reference sentence from the given tokens. Check the original key and verification evidence; do not infer word order from this result.",
    "未能在有界搜索内用给定词块一致还原参考句；请查看原键与题面校核证据，不凭此推断词序。",
  ],
  [
    "Word-order observation: the reference begins with a question word followed by an auxiliary. Check the positions of the question phrase, auxiliary, and subject.",
    "词序观察：参考句以疑问词开头，随后出现助动词；注意疑问词短语、助动词与主语的位置。",
  ],
  [
    "Word-order observation: an auxiliary or modal precedes the pronoun subject, consistent with a common yes/no question pattern.",
    "词序观察：参考句把助动词或情态动词放在代词主语之前，符合这类一般疑问句的常见结构。",
  ],
  [
    "This compares fixed words, individual token indices, and existing reference sentences only. Identically spelled tokens remain separate items. A final period/question-mark difference alone is not marked wrong. This is not official ETS grammar analysis.",
    "只对照原题固定词、独立词块索引与已有参考句；相同拼写的不同词块仍是独立项目。句末句号/问号差异不单独判错。这里不是 ETS 官方语法解析。",
  ],
  [
    "The reference key does not match a current option. Verify the source before drawing a conclusion about an option.",
    "参考键没有对应到当前选项，不生成选项成立的解释；请先核验来源。",
  ],
  [
    "Matching keywords do not prove the full reasoning. This tool does not infer why other options are wrong.",
    "原文关键词相同不等于完整逻辑证明；本工具不推断其他选项为何错误。",
  ],
  [
    "Matching keywords do not prove the full reasoning. This tool does not infer why other options are wrong. Check transcripts against the original audio; recognition output is not an official explanation.",
    "原文关键词相同不等于完整逻辑证明；本工具不推断其他选项为何错误。 转写内容须与原音核对，不能把识别结果当作官方解析。",
  ],
  [
    "The original key and question still have an unresolved conflict. No automatic correctness judgment or explanation is generated.",
    "此题的原键与题面尚有未解决冲突，暂不自动判定正确答案，也不生成正确性结论。",
  ],
  [
    "The original key differs from the verified answer. The source explanation may correspond to the older key; also check the conflict and verification evidence.",
    "原键与当前校核答案不同；原资料解析可能对应旧键，请同时查看答案冲突与校核证据。",
  ],
  [
    "Some blanks still have conflicting answers. The source explanation is for comparison only and is not used to score those blanks.",
    "部分空的答案仍有冲突；原资料解释仅供对照，不据此给冲突空判分。",
  ],
  [
    "This source explanation differs from the question or verified answer. The explanation does not change the scoring key.",
    "这段附带解析与原题或校核答案存在差异；评分不因附带解析而改写答案。",
  ],
  [
    "There is no automatically verifiable standard answer, or this item requires rubric-based human assessment. The question, essay/recording, and sources are kept for review; no uncalibrated automatic conclusion is generated.",
    "没有可自动核验的标准答案，或本题需要人工量表评分。保留原题、作文/录音及来源供复盘，不生成未经校准的自动结论。",
  ],
  [
    "A reference key exists, but local rules cannot reliably explain the reasoning for this item. Check the source materials; do not invent an explanation.",
    "已有参考键，但本地规则尚不能可靠说明本题理由。请对照原资料，不据此编造解释。",
  ],
];

const moduleLabels: Record<string, string> = {
  "Academic Discussion": "学术讨论",
  "Build a Sentence": "组句",
  "Listen and Repeat": "听后复述",
  "Take an Interview": "模拟访谈",
  "Write an Email": "邮件写作",
  "Essentials Listening · untimed study": "Essentials 听力 · 不限时学习",
  "Essentials Reading · untimed": "Essentials 阅读 · 不限时",
  "Essentials · Academic Discussion": "Essentials · 学术讨论",
  "Essentials · Build a Sentence": "Essentials · 组句",
  "Essentials · Describe a Photo": "Essentials · 描述图片",
  "Essentials · Listen and Repeat": "Essentials · 听后复述",
  "Essentials · Read Aloud": "Essentials · 朗读",
  "Essentials · Virtual Interview": "Essentials · 虚拟访谈",
  "Essentials · Write an Email": "Essentials · 邮件写作",
  "Speaking · Interview": "口语 · 访谈",
  "Speaking · Listen Repeat": "口语 · 听后复述",
  "Writing · Build": "写作 · 组句",
  "Writing · Discussion": "写作 · 讨论",
  "Writing · Email": "写作 · 邮件",
};

const exact = new Map<string, [string, string]>();
for (const pair of [...messages, ...explanationMessages]) {
  exact.set(pair[0], pair);
  exact.set(pair[1], pair);
}

/** Canonical keys are retained in data; their labels are localized only in reports. */
const reportFields: Record<string, [string, string]> = {
  answerKeyVerification: ["Answer-key verification", "答案键核验"],
  audioMappingVerification: ["Audio mapping verification", "音频对应核验"],
  expectedItems: ["Expected items", "预期题目数"],
  objectiveAnswers: ["Objective answers", "客观题答案"],
  scope: ["Scope", "范围"],
  verifiedAudioItems: ["Verified audio items", "已核实音频题目数"],
  schemaVersion: ["Schema version", "数据格式版本"],
  summary: ["Summary", "汇总"],
  coverage: ["Coverage", "覆盖情况"],
  exams: ["Test archives", "套题档案"],
  id: ["ID", "编号"],
  title: ["Title", "标题"],
  validation: ["Validation", "校验"],
  warnings: ["Warnings", "提示"],
  fileCount: ["File count", "文件数"],
  status: ["Status", "状态"],
  type: ["Type", "类型"],
  at: ["Time", "时间"],
  time: ["Time", "时间"],
  timestamp: ["Timestamp", "时间戳"],
  data: ["Details", "详情"],
  questionId: ["Question ID", "题目编号"],
  stageId: ["Stage ID", "阶段编号"],
  stageIndex: ["Stage index", "阶段序号"],
  questionIndex: ["Question index", "题目序号"],
  phase: ["Phase", "阶段"],
  section: ["Section", "部分"],
  reason: ["Reason", "原因"],
  mode: ["Mode", "模式"],
  kind: ["Kind", "类别"],
  error: ["Error", "错误"],
  errors: ["Errors", "错误"],
  details: ["Details", "详情"],
  checked: ["Checked", "已检查"],
  passed: ["Passed", "已通过"],
  missing: ["Missing", "缺失"],
  total: ["Total", "总数"],
  correct: ["Correct", "正确数"],
  expected: ["Expected", "预期值"],
  actual: ["Actual", "实际值"],
  source: ["Source", "来源"],
  page: ["Page", "页码"],
  materialId: ["Material ID", "资料编号"],
  label: ["Label", "标签"],
  origin: ["Origin", "来源类型"],
  official: ["Official", "官方资料"],
  sourceReferenceAnswer: ["Original reference key", "原始参考键"],
  resolutionEvidence: ["Verification evidence", "校核依据"],
  answerConflict: ["Answer conflict", "答案冲突"],
  explanationConflict: ["Explanation conflict", "解析冲突"],
  answer: ["Answer", "答案"],
  answers: ["Answers", "答案"],
  original: ["Original", "原始值"],
  resolved: ["Resolved", "已校核"],
  sourceAnswer: ["Source answer", "来源答案"],
  verifiedAnswer: ["Verified answer", "已核实答案"],
  note: ["Note", "说明"],
  notes: ["Notes", "说明"],
  missingAudio: ["Missing audio", "缺失音频"],
  missingAnswers: ["Missing answers", "缺失答案"],
  duplicateIds: ["Duplicate IDs", "重复编号"],
  answerConflicts: ["Answer conflicts", "答案冲突"],
  durationSeconds: ["Duration (seconds)", "时长（秒）"],
  remainingSeconds: ["Remaining seconds", "剩余秒数"],
  elapsedSeconds: ["Elapsed seconds", "已用秒数"],
  mediaIndex: ["Media index", "媒体序号"],
  requestId: ["Request ID", "请求编号"],
  revision: ["Revision", "修订版本"],
  interruptReason: ["Interruption reason", "中断原因"],
  takeId: ["Recording take ID", "录音编号"],
  segmentId: ["Recording chunk ID", "录音片段编号"],
  audioIssues: ["Audio issues", "音频问题"],
  issues: ["Issues", "问题"],
  strictEligible: ["Strict-mode ready", "可用于严格模考"],
  scopedEligibility: ["Section eligibility", "单项可用性"],
  adaptiveEligible: ["Adaptive-route ready", "可用于自适应路径"],
  reading: ["Reading", "阅读"],
  listening: ["Listening", "听力"],
  writing: ["Writing", "写作"],
  speaking: ["Speaking", "口语"],
};

const states: Record<string, [string, string]> = {
  "adaptive-route": ["Adaptive route selected", "已选择自适应路径"],
  "finished-early": ["Ended early", "提前结束"],
  interrupted: ["Interrupted", "已中断"],
  "missing-audio": ["Missing audio", "音频缺失"],
  "practice-replay": ["Practice audio replay", "练习音频重播"],
  "recording-error": ["Recording error", "录音错误"],
  "recording-finalized": ["Recording saved", "录音已保存"],
  resumed: ["Resumed", "已恢复"],
  "stage-end": ["Stage ended", "阶段结束"],
  "stage-start": ["Stage started", "阶段开始"],
  timeout: ["Time expired", "时间已到"],
  verified: ["Verified", "已核实"],
  "source-verified": ["Source verified", "来源已核实"],
  "needs-review": ["Needs review", "待审核"],
  "answer-conflict": ["Answer conflict", "答案冲突"],
  "verified-source": ["Verified source", "来源已核实"],
  "manual-review": ["Manual review", "人工复盘"],
  "not-started": ["Not started", "未开始"],
  not_started: ["Not started", "未开始"],
  in_progress: ["In progress", "进行中"],
  completed: ["Completed", "已完成"],
  active: ["Active", "进行中"],
  abandoned: ["Ended early", "提前结束"],
  complete: ["Complete", "完整"],
  incomplete: ["Incomplete", "不完整"],
  pending: ["Pending", "待处理"],
  passed: ["Passed", "已通过"],
  failed: ["Failed", "未通过"],
  unavailable: ["Unavailable", "不可用"],
  source_changed: ["Source changed", "来源已变化"],
  source_missing: ["Source missing", "来源缺失"],
  "source-hash-mismatch": ["Source hash mismatch", "来源哈希不一致"],
  "answer-expired": ["Answer time expired", "作答超时"],
  "source-changed": ["Source changed", "来源已变化"],
  "media-start": ["Media started", "媒体开始播放"],
  "media-ended": ["Media ended", "媒体播放结束"],
  "recording-ended": ["Recording ended", "录音结束"],
  "recording-started": ["Recording started", "录音开始"],
  "visibility-change": ["Page visibility changed", "页面可见性变化"],
  directions: ["Directions", "说明"],
  response: ["Response", "作答"],
  audio: ["Audio", "音频"],
  recording: ["Recording", "录音"],
  paused: ["Paused", "已暂停"],
  strict: ["Strict mock test", "严格模考"],
  practice: ["Practice", "专项练习"],
  lower: ["Lower branch", "较低分支"],
  upper: ["Upper branch", "较高分支"],
  fixed: ["Fixed route", "固定路径"],
  adaptive: ["Simulated adaptive route", "模拟自适应路径"],
};

// Template captures contain original answer fragments and are inserted verbatim.
// Only the surrounding explanatory prose is translated.
const explanationTemplates: [RegExp, (...captures: string[]) => string][] = [
  [
    /^第 (\d+) 空的来源答案仍有冲突，不给出正确结论，也不计入自动评分。$/,
    (n) =>
      `Blank ${n} has conflicting source answers. No correctness conclusion is given, and it is excluded from automatic scoring.`,
  ],
  [
    /^第 (\d+) 空缺少可一致还原的已核验答案。$/,
    (n) =>
      `Blank ${n} has no verified answer that can be consistently reconstructed.`,
  ],
  [
    /^第 (\d+) 空记录的长度与参考片段不一致，请对照源题核验。$/,
    (n) =>
      `The recorded length for blank ${n} differs from the reference fragment. Check the source question.`,
  ],
  [
    /^第 (\d+) 空：(已给「(.*?)」|无前缀) \+ 补入「(.*?)」(?: \+ 已给后缀「(.*?)」)? → (.*?)（缺失片段 (\d+) 个字符）。$/,
    (n, _given, prefix, missing, suffix, full, count) =>
      `Blank ${n}: ${prefix ? `given “${prefix}”` : "no prefix"} + enter “${missing}”${suffix ? ` + given suffix “${suffix}”` : ""} → ${full} (${count} missing characters).`,
  ],
  [
    /^原题上下文片段（未改写）：([\s\S]*)$/,
    (text) => `Original question context (verbatim): ${text}`,
  ],
  [/^资料参考句：([\s\S]*)$/, (text) => `Source reference sentence: ${text}`],
  [
    /^另一个有来源支持的参考变体：([\s\S]*)$/,
    (text) => `Another source-supported variant: ${text}`,
  ],
  [
    /^原题固定词块：([\s\S]*)$/,
    (text) => `Fixed words in the original question: ${text}`,
  ],
  [
    /^一种与参考句一致的空格词序：([\s\S]*)$/,
    (text) =>
      `One gap order matching the reference: ${text.replace(/〔词块 (\d+)〕/g, "[token $1]")}`,
  ],
  [
    /^本排列未使用的词块：([\s\S]*)$/,
    (text) =>
      `Tokens unused in this arrangement: ${text.replace(/〔词块 (\d+)〕/g, "[token $1]")}`,
  ],
  [
    /^资料参考键为 (.*?)。原资料未提供可用解析，且本地关键词方法没有定位到可靠依据；请结合完整原文或原音自行核对，不据此补写理由。$/,
    (key) =>
      `The source reference key is ${key}. No usable source explanation is available, and the local keyword method found no reliable evidence. Review the complete source text or audio; do not invent a reason from this result.`,
  ],
  [
    /^资料参考键为 (.*?)。下面逐字摘取本题已导入原文\/转写中与该选项关键词相符的片段，作为复盘定位线索；不把机械匹配当作官方原因说明。$/,
    (key) =>
      `The source reference key is ${key}. The excerpts below are copied verbatim from the imported passage/transcript and share keywords with this option. They help locate review evidence; mechanical matches are not official reasoning.`,
  ],
  [/^校核说明：([\s\S]*)$/, (text) => `Verification note: ${text}`],
];

export function localizeServerMessage(
  text: string,
  locale: Locale,
): string | undefined {
  const moduleName = Object.hasOwn(moduleLabels, text)
    ? text
    : Object.keys(moduleLabels).find((key) => moduleLabels[key] === text);
  if (moduleName)
    return locale === "zh-CN" ? moduleLabels[moduleName] : moduleName;
  // Catalog titles are generated labels. Original filenames and topic titles do not match these patterns.
  const collections: [RegExp, (n: string) => string][] = [
    [/^体验日官方练习 (\d+)$/, (n) => `Official Experience Day ${n}`],
    [/^官方学生版样题 (\d+)$/, (n) => `Official Student Sample ${n}`],
    [/^官方教师版样题 (\d+)$/, (n) => `Official Teacher Sample ${n}`],
    [
      /^补充套题 (\d+) · lower \/ upper 双分支$/,
      (n) => `Supplemental Set ${n} · Lower / Upper branches`,
    ],
    [
      /^补充套题 (\d+) · upper 路径$/,
      (n) => `Supplemental Set ${n} · Upper route`,
    ],
    [
      /^TOEFL Essentials 补充练习 (\d+)$/,
      (n) => `TOEFL Essentials Supplemental Practice ${n}`,
    ],
  ];
  for (const [pattern, format] of collections) {
    const match = text.match(pattern);
    if (match) return locale === "en" ? format(match[1]) : text;
  }
  const numberedModule = text.match(
    /^(Reading|Listening) · (?:M|Module )(1|2)(?: · (Upper|Lower))?(?: · (\d+))?$/,
  );
  if (numberedModule) {
    const [, section, number, branch, question] = numberedModule;
    return locale === "en"
      ? text
      : `${section === "Reading" ? "阅读" : "听力"} · 模块 ${number}${branch ? ` · ${branch === "Upper" ? "较高分支" : "较低分支"}` : ""}${question ? ` · ${question}` : ""}`;
  }
  const taskItem = text.match(/^(.+) · (\d+)$/);
  if (taskItem && Object.hasOwn(moduleLabels, taskItem[1]))
    return `${locale === "zh-CN" ? moduleLabels[taskItem[1]] : taskItem[1]} · ${taskItem[2]}`;
  const pair = exact.get(text) || reportFields[text] || states[text];
  if (pair) return pair[locale === "zh-CN" ? 1 : 0];
  if (text.startsWith("Error: ")) {
    const translated = localizeServerMessage(text.slice(7), locale);
    if (translated)
      return locale === "zh-CN"
        ? `错误：${translated}`
        : `Error: ${translated}`;
  }
  if (locale === "en") {
    const suffix = " · 存在校核差异";
    if (text.endsWith(suffix)) {
      const translated = localizeServerMessage(
        text.slice(0, -suffix.length),
        locale,
      );
      if (translated)
        return `${translated} · Verification differences recorded`;
    }
    for (const [pattern, format] of explanationTemplates) {
      const match = text.match(pattern);
      if (match) return format(...match.slice(1));
    }
  }
  if (locale === "zh-CN") {
    const exampleErrors: [RegExp, string][] = [
      [
        /^Bundled example file is missing or changed: ([\s\S]*)$/,
        "内置示例文件缺失或已更改：",
      ],
      [
        /^Bundled example would overwrite an existing file: ([\s\S]*)$/,
        "内置示例与现有文件冲突，未覆盖：",
      ],
      [
        /^Bundled example failed source integrity: ([\s\S]*)$/,
        "内置示例未通过来源完整性核验：",
      ],
      [
        /^Bundled example could not be installed: ([\s\S]*)$/,
        "无法安装内置示例：",
      ],
    ];
    for (const [pattern, prefix] of exampleErrors) {
      const match = text.match(pattern);
      if (match) return `${prefix}${match[1]}`;
    }
    const timing = text.match(/^Unknown timing setting: (.+)$/);
    if (timing) return `未知的计时设置：${timing[1]}`;
    const presentation = text.match(
      /^A structured question presentation is not source-verified or valid: ([\s\S]*)$/,
    );
    if (presentation)
      return `结构化题面未通过来源核验或格式无效：${presentation[1]}`;
  }
  return undefined;
}
