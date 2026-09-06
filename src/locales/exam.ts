import { tr } from "../i18n";

/** UI copy only. Verified passages, choices, dialogue and audio stay in English. */
export const examMessages: Record<string, string> = {
  "Essentials Listening · untimed study": "Essentials 听力 · 不限时学习",
  "Essentials Reading · untimed": "Essentials 阅读 · 不限时",
  "Essentials · Academic Discussion": "Essentials · 学术讨论",
  "Essentials · Build a Sentence": "Essentials · 组句",
  "Essentials · Describe a Photo": "Essentials · 描述图片",
  "Essentials · Listen and Repeat": "Essentials · 听后复述",
  "Essentials · Read Aloud": "Essentials · 朗读",
  "Essentials · Virtual Interview": "Essentials · 模拟访谈",
  "Essentials · Write an Email": "Essentials · 邮件写作",
  "Listening · M1": "听力 · 模块 1",
  "Listening · M2": "听力 · 模块 2",
  "Listening · M2 · Upper": "听力 · 模块 2 · 较高难度",
  "Listening · Module 1": "听力 · 模块 1",
  "Listening · Module 2": "听力 · 模块 2",
  "Listening · Module 2 · Lower": "听力 · 模块 2 · 较低难度",
  "Reading · M1": "阅读 · 模块 1",
  "Reading · M2": "阅读 · 模块 2",
  "Reading · M2 · Upper": "阅读 · 模块 2 · 较高难度",
  "Reading · Module 1": "阅读 · 模块 1",
  "Reading · Module 2": "阅读 · 模块 2",
  "Reading · Module 2 · Lower": "阅读 · 模块 2 · 较低难度",
  "Speaking · Interview": "口语 · 访谈",
  "Speaking · Listen Repeat": "口语 · 听后复述",
  "Writing · Build": "写作 · 组句",
  "Writing · Discussion": "写作 · 学术讨论",
  "Writing · Email": "写作 · 邮件",
  "Choose an answer": "选择答案",
  "Source practice": "原始资料练习",
  "Saved locally": "已保存到本机",
  "Browser draft recovered · saving…": "已恢复浏览器草稿 · 正在保存…",
  "Saving…": "正在保存…",
  "Saving newer response…": "正在保存最新答案…",
  "Saved in browser · retry needed": "已保存到浏览器 · 需要重试同步",
  "Microphone unavailable. This response is marked interrupted.":
    "麦克风不可用，本次回答已标记为中断。",
  "Recording error. The interruption has been saved.":
    "录音出错，已保存中断记录。",
  "Recording · saved in local segments": "正在录音 · 分段保存到本机",
  "Response time finished · saving final segment":
    "作答时间已结束 · 正在保存最后一段录音",
  "Could not start recording. Check your microphone.":
    "无法开始录音，请检查麦克风。",
  "Local server disconnected · timer continues": "本地服务已断开 · 倒计时继续",
  "Recording saved in local segments": "录音已分段保存到本机",
  "Read each text and answer the questions.": "阅读每篇材料并回答问题。",
  "You may use Back, Next and Review within this module. Once you submit a module, you cannot return to it.":
    "你可以在本模块内使用上一题、下一题和题目回顾。提交模块后不能返回。",
  "The clock runs continuously during the module. Your responses are submitted when time expires.":
    "模块内倒计时持续运行，时间到后自动提交答案。",
  "Listen carefully. Each recording plays once in strict mode.":
    "请仔细听。严格模考模式下，每段录音仅播放一次。",
  "The response clock starts after the recording finishes. Each question has its own time limit.":
    "录音播放结束后开始作答倒计时，每题单独计时。",
  "You cannot return to an earlier question. Use paper for notes if you need it.":
    "不能返回之前的题目。如需记笔记，请使用纸笔。",
  "Complete the sentence-building tasks, write an email, and contribute to an academic discussion.":
    "完成组句任务、撰写邮件，并参与学术讨论。",
  "The email task is 7 minutes. The academic discussion is 10 minutes. Unused time does not transfer.":
    "邮件写作限时 7 分钟，学术讨论限时 10 分钟，剩余时间不结转。",
  "Spelling assistance is off. Your responses are automatically saved on this computer.":
    "拼写辅助已关闭，答案会自动保存到这台电脑。",
  "Listen and repeat 7 sentences, then answer 4 interview questions.":
    "听并复述 7 个句子，然后回答 4 个访谈问题。",
  "There is no preparation time. Recording starts automatically after each prompt finishes.":
    "没有准备时间，每段题目播放结束后自动开始录音。",
  "Speak clearly into your microphone. Recording stops when your response time expires.":
    "请对着麦克风清晰作答，作答时间结束后自动停止录音。",
  "This is untimed supplemental source practice, not a TOEFL iBT 2026 mock exam.":
    "这是不限时的补充资料练习，不属于 TOEFL iBT 2026 模考。",
  "Work with the original material at your own pace. Reference audio may contain explanations or sample answers.":
    "按自己的节奏练习原始材料。参考音频可能包含讲解或示范答案。",
  "For speaking, use Record and Stop to save your response. There is no automatic official time limit in this mode.":
    "口语练习请使用录音和停止按钮保存回答，此模式没有自动的官方作答时限。",
  "Please answer the interviewer's questions.": "请回答访谈者的问题。",
  "Listen and repeat only once.": "听录音并复述一次。",
  "Choose the best response.": "选择最佳回应。",
  "Listen to a conversation.": "听一段对话。",
  "Listen to an announcement.": "听一则通知。",
  "Listen to an academic talk.": "听一段学术讲座。",
  "Listen carefully.": "请仔细听。",
  "Make an appropriate sentence.": "组成一个恰当的句子。",
  "UNTIMED SUPPLEMENTAL PRACTICE": "不限时补充练习",
  "STRICT LOCAL PRACTICE": "本地严格模考",
  "GUIDED PRACTICE": "自由练习",
  "UNTIMED PRACTICE": "不限时练习",
  "LISTENING · TIMER WAITS": "播放音频 · 尚未开始计时",
  DIRECTIONS: "考试说明",
  "PRACTICE PAUSED": "练习已暂停",
  "MODULE TIME LEFT": "模块剩余时间",
  "RESPONSE TIME LEFT": "作答剩余时间",
  "Time remaining": "剩余时间",
  Resume: "继续",
  Pause: "暂停",
  Help: "帮助",
  "Leave practice": "退出练习",
  "Save & Exit": "保存并退出",
  "Section progress": "考试部分进度",
  "Local server disconnected. Your response is backed up in this browser. Reconnect to continue; strict timers keep running.":
    "本地服务已断开，答案已备份在浏览器中。重新连接后可继续；严格模考的倒计时持续运行。",
  "Time Remaining": "还有剩余时间",
  "You still have time to respond. As long as there is time remaining, you can keep writing or revise your response.":
    "你还有作答时间。只要时间未结束，就可以继续写作或修改答案。",
  "Once you leave this question, you WILL NOT be able to return to it.":
    "离开本题后，将无法返回。",
  "SECTION DIRECTIONS": "本部分说明",
  "Task directions": "任务说明音频",
  Untimed: "不限时",
  "Per question": "每题单独计时",
  "RESPONSE TIMER": "作答计时",
  "QUESTION SCREENS": "题目页面",
  Strict: "严格模考",
  Guided: "自由练习",
  "LOCAL PRACTICE": "本地练习",
  "Directions are untimed. Your local timing profile is frozen for this session. This practice does not reproduce ETS’s proprietary adaptive algorithm or score scale.":
    "说明页面不限时。本次练习使用的计时设置已固定；此练习不复现 ETS 的专有自适应算法或评分标准。",
  "Connect microphone": "连接麦克风",
  "Practice paused": "练习已暂停",
  "Pause is available only in guided practice. Resume when you are ready.":
    "仅自由练习可以暂停，准备好后即可继续。",
  "Resume practice": "继续练习",
  "Original question media · untimed practice": "原题音视频 · 不限时练习",
  "Full reference track · may include examples": "完整参考音频 · 可能包含示例",
  "Supplemental reference track": "补充资料参考音频",
  "Repeat what you hear when recording begins.":
    "录音开始后，复述刚才听到的内容。",
  "Answer the interviewer when recording begins.":
    "录音开始后，回答访谈者的问题。",
  "You will answer the question after the recording.": "音频结束后开始答题。",
  "Question audio": "题目音频",
  "No verified audio is available for this question.":
    "本题没有经过核实的可用音频。",
  "Audio plays once · response clock starts afterwards":
    "音频播放一次 · 结束后开始作答计时",
  "Last frame of the original interviewer video": "原始访谈视频的最后一帧",
  "RESPONSE TIME": "作答时间",
  "Source speaker portrait": "原题说话者头像",
  "Source respondent portrait": "原题回应者头像",
  "Source transcript · no matching original audio":
    "原始文字稿 · 没有匹配的原始音频",
  "Speaking prompt": "口语题目",
  "Listening context": "听力材料",
  "Writing task": "写作任务",
  "Original question": "原题",
  "Reading material": "阅读材料",
  "Your response": "你的答案",
  "Question & response": "题目与作答",
  "Flag question": "标记本题",
  "Record your response.": "录制你的回答。",
  "Speak now.": "现在开始作答。",
  "Stop recording": "停止录音",
  "Record response": "录制回答",
  "Ready when you are.": "准备好即可开始。",
  "Reconnect microphone": "重新连接麦克风",
  "This supplemental task has no official iBT countdown. Stop recording before moving on.":
    "本补充练习没有官方 iBT 倒计时，请先停止录音再进入下一题。",
  "Recording stops automatically when time expires.":
    "时间结束后自动停止录音。",
  "Replay audio": "重播音频",
  "Check answer & explanation": "查看答案与解析",
  "THIS MODULE ONLY": "仅限本模块",
  Review: "题目回顾",
  Back: "上一题",
  "Recording · auto-submit": "正在录音 · 自动提交",
  Submit: "提交",
  Next: "下一题",
  Continue: "继续",
  "Writing Time Expired": "写作时间已结束",
  "Your time for answering this question has ended.": "本题作答时间已结束。",
  "Return to Question": "返回题目",
  Close: "关闭",
  "Keep working": "继续作答",
  "End & review": "结束并查看结果",
  "Save & leave": "保存并离开",
  "Must Answer": "请先作答",
  "You must enter an answer before you can leave this question.":
    "请先选择答案，再进入下一题。",
  "The response timer keeps running while this window is open.":
    "此窗口打开时，作答倒计时仍继续运行。",
  "Submit this task?": "提交本任务？",
  "You cannot return after submission. Unanswered items remain blank, and unused time does not transfer.":
    "提交后无法返回。未作答的题目保持空白，剩余时间不结转。",
  "Leave this practice?": "退出本次练习？",
  "Strict response timers keep running after you leave. Leaving during audio or recording marks this session as interrupted. Completed recording segments are preserved.":
    "退出后严格模考倒计时继续运行。在音频播放或录音期间退出会将本次练习标记为中断，已录制的片段会保留。",
  "Audio playback stalled. The interruption is recorded; your response timer has not started.":
    "音频播放停滞，已记录此次中断；作答倒计时尚未开始。",
  "Audio could not load. Check your local server and retry.":
    "无法加载音频，请检查本地服务后重试。",
  "Your browser requires a click before playing audio.":
    "浏览器需要你点击后才能播放音频。",
  "Play audio": "播放音频",
  Volume: "音量",
  "Playback volume": "播放音量",
  "Exam volume": "考试音量",
  Begin: "开始",
  "Show Time": "显示时间",
  "Hide Time": "隐藏时间",
  "In an actual test, the clock will show you how much time you have to complete each question.":
    "正式考试中，计时器会显示每道题的剩余作答时间。",
  "You WILL NOT be able to return to previous questions.":
    "不能返回之前的题目。",
  "An interviewer will ask you questions. Answer the questions and be sure to say as much as you can in the time allowed.":
    "访谈者会向你提问。请回答问题，并在规定时间内尽可能充分地表达。",
  "You will listen as someone speaks to you. Listen carefully and then repeat what you have heard. The clock will indicate how much time you have to speak.":
    "你将听到一段话。请仔细听，然后复述所听到的内容。计时器会显示你的作答时间。",
  "No time for preparation will be provided.": "不提供准备时间。",
  "You WILL NOT be able to return to Module 1 once you have begun Module 2.":
    "开始模块 2 后，不能返回模块 1。",
  "Move the words in the boxes to create grammatical sentences.":
    "移动方框中的词语，组成语法正确的句子。",
  "A clock will show you how much time you have to complete this task.":
    "计时器会显示完成本任务的剩余时间。",
  "A professor has posted a question about a topic and students have responded with their thoughts and ideas. Make a contribution to the discussion.":
    "教授发布了一个话题问题，学生们已发表自己的想法。请撰写回复，参与讨论。",
  "You will have 10 minutes to write.": "你有 10 分钟完成写作。",
  "You will read some information and use the information to write an email.":
    "你将阅读一些信息，并根据这些信息撰写一封邮件。",
  "You will have 7 minutes to write the email.": "你有 7 分钟完成邮件写作。",
  Reading: "阅读",
  Listening: "听力",
  Writing: "写作",
  Speaking: "口语",
  "Complete the Words": "补全单词",
  "Read in Daily Life": "日常阅读",
  "Read an Academic Passage": "学术阅读",
  "Listen and Choose a Response": "听句选回应",
  "Listen to a Conversation": "听对话",
  "Listen to an Announcement": "听通知",
  "Listen to an Academic Talk": "听学术讲座",
  "Take an Interview": "访谈",
  "Listen and Repeat": "听后复述",
  "Build a Sentence": "组句",
  "Write for an Academic Discussion": "学术讨论写作",
  "Write an Email": "邮件写作",
  "Academic Discussion": "学术讨论",
  "Read Aloud": "朗读",
  "Original question from your materials": "资料中的原题图片",
  "Question visual": "题目插图",
  "Highlighted sentence": "高亮句子",
  "Select a sentence": "选择一个句子",
  "Answer choices": "答案选项",
  "Enter only the missing letters after the given prefix. Use the original question to check the order.":
    "只输入给定词头后缺少的字母，请按原题顺序作答。",
  "One blue slot = one letter": "每个蓝色格子填写一个字母",
  "Use Tab to move between blanks.": "按 Tab 键切换填空。",
  "Word was not placed. Drop it inside a gap.":
    "词块未放入空位，请拖入空位内。",
  "Drag word blocks into the gaps or between filled gaps. You can also select a gap and click a word.":
    "将词块拖入空位，也可在已填空位间移动词块。你还可以先选中空位，再点击词块。",
  "Sentence word slots": "句子词块空位",
  "Available word blocks": "可用词块",
  "Clear sentence": "清空句子",
  "This source has not yet been verified for fixed-slot interaction. Type the complete sentence, including its fixed words.":
    "本资料尚未核实固定空位，请输入完整句子，包括已给出的词语。",
  Cut: "剪切",
  Paste: "粘贴",
  Undo: "撤销",
  Redo: "重做",
  "Hide Word Count": "隐藏字数",
  "Show Word Count": "显示字数",
  "Spelling assistance off · Clipboard disabled":
    "拼写辅助已关闭 · 外部剪贴板已禁用",
  "Spelling assistance off": "拼写辅助已关闭",
  "Complete sentence": "完整句子",
  "Your written response": "你的写作答案",
  "Type the complete sentence, including the fixed words.":
    "输入完整句子，包括已给出的词语。",
  "Write your response here…": "在这里输入你的答案…",
  "An effective response contains at least 100 words.":
    "有效回复应至少包含 100 个英文单词。",
  "Your response is saved locally.": "你的答案已保存到本机。",
  "Word count:": "字数：",
  "Browser backup storage is full. Keep the local server running.":
    "浏览器备份空间不足，请保持本地服务运行。",
  "Task directions audio could not play.": "说明音频播放出错。",
  "Select Back to keep writing or revising.": "选择“上一题”继续写作或修改。",
  "Select Continue to leave this question.": "选择“继续”离开本题。",
  "Begin {section}": "开始{section}",
  "Question {number}": "第 {number} 题",
  "Question {number} of {total}": "第 {number} 题 / 共 {total} 题",
  "Questions {start}–{end} of {total}": "第 {start}–{end} 题 / 共 {total} 题",
  "Screen {current} / {total}": "第 {current} 页 / 共 {total} 页",
  "Original prompt {number}": "原题音视频 {number}",
  "Go to screen {number}": "前往第 {number} 页",
  "{section} · Help": "{section} · 帮助",
  "Module {number}": "模块 {number}",
  "You can use Next to move to the next question.":
    "可以使用“下一题”进入下一道题。",
  "The clock will show you how much time you have to complete Module {number}.":
    "计时器会显示完成模块 {number} 的剩余时间。",
  "You can use Next and Back to move to the next question or return to previous questions within the same module.":
    "可以使用“下一题”和“上一题”，在同一模块内切换题目。",
  "Select sentence {number}: {text}": "选择第 {number} 个句子：{text}",
  "Position {number}": "位置 {number}",
  "Position {number}, highlighted": "位置 {number}，已高亮",
  "Form layout with position {number} highlighted":
    "表单布局，位置 {number} 已高亮",
  "Missing letters for word {number}": "第 {number} 个单词缺失的字母",
  "Missing letters for word {number}, {length} letters required":
    "第 {number} 个单词缺失的字母，需填 {length} 个字母",
  "{count} missing words": "共 {count} 个缺词",
  "Blank {number} · {entered} / {required} letters":
    "第 {number} 空 · 已填 {entered} / 需填 {required} 个字母",
  "{completed} / {total} completed": "已完成 {completed} / {total}",
  "Placed {word} in gap {number}.": "已将 {word} 放入第 {number} 空。",
  "Dragging {word}.": "正在拖动 {word}。",
  "Picked up {word}.": "已选取 {word}。",
  "Gap {number}: {word}. Click to remove.":
    "第 {number} 空：{word}。点击移除。",
  "Gap {number}: empty": "第 {number} 空：未填写",
  "Use word block {number}: {word}": "使用第 {number} 个词块：{word}",
  "{completed} / {total} gaps filled · selected gap {selected}":
    "已填 {completed} / {total} 空 · 当前选中第 {selected} 空",
  "Your local response is saved.": "你的答案已保存到本机。",
};

/** Resolve labels at render time; recorder and autosave states keep stable keys. */
export function examText(
  text: string,
  values?: Record<string, string | number>,
): string {
  return tr(text, examMessages[text] ?? text, values);
}
