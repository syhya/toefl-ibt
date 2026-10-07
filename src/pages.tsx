import { useEffect, useState } from "react";
import {
  api,
  DEFAULT_TIMING,
  ORDER,
  time,
  date,
  taskName,
  sectionLabel,
} from "./api";
import { useI18n, tr, localizeDynamic } from "./i18n";
import type {
  Answer,
  Material,
  Question,
  Review,
  Rating,
  Timing,
} from "./types";
import { Button, Heading, Notice, Modal, Empty } from "./components";
import Icon from "./Icons";
import { StemAssets } from "./Questions";
import AnswerComparison from "./AnswerComparison";
import VocabularyCapture from "./VocabularyCapture";
import type { VocabularyDraft } from "./Vocabulary";
import "./review-enhancements.css";
import rules from "../shared/rules.json";

export function Rules() {
  const { t, locale } = useI18n();
  return (
    <>
      <Heading
        title={t("Know the rules before you begin.", "了解规则，再走进练习。")}
        subtitle={t(
          "Based on public ETS sources, with official rules, source observations, and local practice settings clearly distinguished.",
          "以 ETS 公开资料为依据；明确区分官方规则、原始题库截图与本地模拟设定。",
        )}
      />
      <div className="panel">
        <h2>{t("2026 edition · Section order", "2026 新版 · 正式部分顺序")}</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>{t("Order / section", "顺序 / 部分")}</th>
                <th>{t("Task types", "题型")}</th>
                <th>{t("Official baseline", "官方基准参考")}</th>
                <th>{t("Practice behavior", "软件执行方式")}</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>01 {sectionLabel("reading", locale)}</td>
                <td>
                  {taskName("cloze", locale)}
                  <br />
                  {taskName("daily_life", locale)}
                  <br />
                  {taskName("academic_passage", locale)}
                </td>
                <td>
                  {t("50 items · about 30 minutes*", "50 题 · 约 30 分钟*")}
                </td>
                <td>
                  {t(
                    "Two separate 15-minute practice clocks; navigation within the module is allowed.",
                    "两个模块分别按 15 分钟练习预设计时；同模块可返回",
                  )}
                  <br />
                  {t(
                    "Submitted modules cannot be revisited.",
                    "提交后不能返回上一模块",
                  )}
                </td>
              </tr>
              <tr>
                <td>02 {sectionLabel("listening", locale)}</td>
                <td>
                  {taskName("listen_response", locale)}
                  <br />
                  {taskName("conversation", locale)} /{" "}
                  {taskName("announcement", locale)} /{" "}
                  {taskName("academic_talk", locale)}
                </td>
                <td>
                  {t("47 items · about 29 minutes*", "47 题 · 约 29 分钟*")}
                </td>
                <td>
                  {t(
                    "Each question is timed after its audio finishes.",
                    "音频播放结束后逐题倒计时",
                  )}
                  <br />
                  {t(
                    "Strict mode disables back navigation and replay.",
                    "模考不可返回或重播",
                  )}
                </td>
              </tr>
              <tr>
                <td>03 {sectionLabel("writing", locale)}</td>
                <td>
                  {taskName("build_sentence", locale)} × 10
                  <br />
                  {taskName("email", locale)} × 1<br />
                  {taskName("academic_discussion", locale)} × 1
                </td>
                <td>
                  {t("12 items · about 23 minutes*", "12 题 · 约 23 分钟*")}
                </td>
                <td>
                  {t(
                    "Sentence building shares a timer; email: 7 minutes.",
                    "造句单独共享计时；邮件 7 分钟",
                  )}
                  <br />
                  {t("Academic discussion: 10 minutes.", "学术讨论 10 分钟")}
                </td>
              </tr>
              <tr>
                <td>04 {sectionLabel("speaking", locale)}</td>
                <td>
                  {taskName("listen_repeat", locale)} × 7<br />
                  {taskName("interview", locale)} × 4
                </td>
                <td>
                  {t("11 items · about 8 minutes*", "11 题 · 约 8 分钟*")}
                </td>
                <td>
                  {t(
                    "Recording starts after listening, with no preparation time.",
                    "无准备时间，听后自动录音",
                  )}
                  <br />
                  {t(
                    "Repeat: 8–12 seconds; interview: 45 seconds per question.",
                    "复述 8–12 秒；采访每题 45 秒",
                  )}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p style={{ margin: "17px 0 0" }}>
          {t(
            "* Baseline times exclude directions and other transitions. Official Reading and Listening are adaptive, so item counts and duration can vary; allow about 2 hours. This app preserves each source test's sequence rather than combining unrelated questions to match headline counts.",
            "* 官方基准不含说明等流程。正式阅读、听力自适应，题数与时长可能变化，请预留约 2 小时。软件保留原套题编排，不为凑官方总览数量而随意拼题。",
          )}
        </p>
      </div>
      <div className="panel">
        <h2>
          {t(
            "Rules, approximations, and differences",
            "规则、近似参数与差异清单",
          )}
        </h2>
        <div className="rule-grid">
          {[
            [
              t("VERIFIED RULES", "已核实规则"),
              t("Verified workflow constraints", "已核实的流程约束"),
              t(
                "The new section order; navigation within Reading modules; timed Listening questions without back navigation; 7-minute email; 10-minute discussion; no Speaking preparation time; and 45 seconds per interview response. Strict mode cannot pause and submits automatically at the deadline.",
                "新版部分顺序、阅读模块内导航、听力逐题计时且不能回退、邮件7分钟、讨论10分钟、口语无准备和采访每题45秒。严格模考无暂停，到时自动提交。",
              ),
            ],
            [
              t("OBSERVED TIMING", "资料计时"),
              t("Timing observed in source materials", "原始资料中的计时"),
              t(
                "Pack 1 screenshots show Reading at 11:30/09:00, Listening at 20/30 seconds, and Repeat at 8/8/10/10/10/12/12 seconds. These are source observations, not a complete verification of the current ETS production client. The 6-minute sentence-building default is explicitly approximate.",
                "Pack-1截图可见阅读11:30/09:00、听力20/30秒、复述8/8/10/10/10/12/12秒。这是资料观察值，不是ETS当前生产客户端的完整校验。造句默认6分钟明确标为近似。",
              ),
            ],
            [
              t("LOCAL ADAPTATION", "本地分流"),
              t("Fixed paths and simulated adaptation", "固定路径与模拟自适应"),
              t(
                "Simulated adaptation is available only for complete, matched high/low branches. Reading and Listening route independently at 70% accuracy on verified first-module items. This is a transparent local practice rule, not the ETS algorithm.",
                "仅完整匹配高低分支的题库支持模拟自适应。阅读、听力各自以首模块已核验题正确率70%分流。该阈值是公开的本地练习规则，不能等同ETS算法。",
              ),
            ],
            [
              t("REVIEW AND REFLECTION", "核对与自评"),
              t("Objective checks and self-assessment", "客观核对与自评"),
              t(
                "Correct counts and accuracy are calculated only for objective items with reliable keys. Use the official rubrics to self-assess Speaking and essays. The app does not use AI scoring or produce uncalibrated 1–6 or 120-point scores.",
                "仅对有可靠答案的客观题给出正确数和正确率。口语和作文依官方量表自评，不调用AI评分，不换算未经校准的1–6或120分。",
              ),
            ],
          ].map(([tag, title, text]) => (
            <div className="rule" key={tag}>
              <div className="eyebrow">{tag}</div>
              <h3>{title}</h3>
              <p>{text}</p>
            </div>
          ))}
        </div>
        <Notice>
          {t(
            "Directions wait for you to continue and do not use answer time. Answering or recording begins after the cue tone. Teacher exercises without source audio and Essentials materials are not included in full 2026 iBT mock tests. Refreshing, switching away, and media or recording failures are logged; a recovered session is still recorded as interrupted.",
            "说明页默认手动继续且不扣答题时间。提示音结束后才启动作答／录音。缺原音的教师专项和 Essentials 不混入完整新版 iBT 模考。页面刷新、后台切换、录音或媒体故障会留下异常记录，恢复不等于无中断完成。",
          )}
        </Notice>
      </div>
      <div className="panel">
        <h2>{t("Sources and verification date", "依据与核对日期")}</h2>
        <p>
          {Object.entries(rules.sources)
            .filter(([key]) => key !== "pack1")
            .map(([key, url]) => (
              <span key={key}>
                <a href={url} target="_blank" rel="noopener">
                  ETS · {key} ↗
                </a>
                <br />
              </span>
            ))}
        </p>
        <p>
          {t(
            "Rules verified: {date}. See docs/OFFICIAL_RULES.md for evidence, screenshot pages, and differences. This is an independent learning tool, not the ETS test client.",
            "规则核对：{date}。完整证据、截图页码和差异见 docs/OFFICIAL_RULES.md。界面为独立学习工具，不是 ETS 官方客户端。",
            { date: rules.verifiedAt },
          )}
        </p>
      </div>
    </>
  );
}

export function Settings({
  timing,
  onSave,
}: {
  timing: Timing;
  onSave: (t: Timing) => void;
}) {
  const { t } = useI18n();
  const fields: [keyof Timing, string, string][] = [
    [
      "readingCommon",
      t("Reading · Module 1", "阅读 · Module 1"),
      t(
        "Seconds; default 15:00, shared within Module 1",
        "秒，默认 15:00，模块 1 内共用",
      ),
    ],
    [
      "readingSecond",
      t("Reading · Module 2", "阅读 · Module 2"),
      t(
        "Seconds; default 15:00, shared within Module 2",
        "秒，默认 15:00，模块 2 内共用",
      ),
    ],
    [
      "listeningResponse",
      t("Listening · Standard question", "听力 · 普通题"),
      t("Seconds; source screenshot: 20 seconds", "秒，资料截图参考20秒"),
    ],
    [
      "listeningAcademic",
      t("Listening · Academic talk", "听力 · 学术讲座"),
      t("Seconds; source screenshot: 30 seconds", "秒，资料截图参考30秒"),
    ],
    [
      "buildSentence",
      t("Writing · Build a Sentence", "写作 · 造句"),
      t(
        "Seconds; no exact official written confirmation; default: 360",
        "秒，未获官方精确文字核证，默认360秒",
      ),
    ],
  ];
  return (
    <>
      <Heading
        title={t("Set up your practice environment.", "适合你的练习环境。")}
        subtitle={t(
          "Changes apply to new sessions. Existing sessions retain the rules and timing saved when they started.",
          "新设置只影响新开始的练习；已开始的练习会冻结当时的规则版本与计时。",
        )}
      />
      <form
        className="panel"
        key={JSON.stringify(timing)}
        onSubmit={(e) => {
          e.preventDefault();
          const data = new FormData(e.currentTarget),
            next = { ...timing };
          // Session plans freeze these values at creation; editing presets never retimes an active test.
          for (const [key] of fields) {
            const n = Number(data.get(key));
            if (!Number.isInteger(n) || n < 5 || n > 7200) return;
            (next as unknown as Record<string, unknown>)[key] = n;
          }
          onSave(next);
        }}
      >
        <h2>{t("Local timing presets", "本地计时预设")}</h2>
        <p>
          {t(
            "These settings customize new guided practice. Strict iBT practice uses the standard profile, including Email 7 minutes, Discussion 10 minutes and Interview 45 seconds. Exact limits not published by ETS remain labelled practice presets.",
            "以下设置用于新建的辅助练习。严格 iBT 模考使用固定预设，其中邮件 7 分钟、讨论 10 分钟、采访每题 45 秒。ETS 未公布的精确时限仍标为练习预设。",
          )}
        </p>
        <p>
          {t(
            "Reading default for all iBT sets: 15:00 + 15:00 = 30:00. This retains the equal practice allocation; ETS's approximate 30-minute overview does not establish exact module deadlines. Older preview clocks no longer override this profile.",
            "所有 iBT 套题的阅读默认：15:00＋15:00＝30:00，保留均分时间的练习配置。ETS 公布的约 30 分钟不代表已确认的逐模块时限；旧版资料时钟不再覆盖当前预设。",
          )}
        </p>
        <div className="settings-grid">
          {fields.map(([key, label, hint]) => (
            <label className="field" key={key}>
              {label}
              <input
                name={key}
                type="number"
                min={5}
                max={7200}
                required
                defaultValue={Number(timing[key])}
              />
              <small>{hint}</small>
            </label>
          ))}
        </div>
        <Notice>
          {t(
            "Email 07:00 · Academic discussion 10:00 · Interview 00:45. Repeat presets: 8/8/10/10/10/12/12 seconds. Official Reading and Listening overview times are not used as freely distributable section timers.",
            "邮件07:00 · 学术讨论10:00 · 采访00:45。复述预设8/8/10/10/10/12/12秒。阅读与听力的官方总览用时不作为自由分配的总倒计时。",
          )}
        </Notice>
        <div style={{ display: "flex", gap: 10, marginTop: 22 }}>
          <Button type="submit">{t("Save settings", "保存设置")}</Button>
          <Button kind="outline" onClick={() => onSave(DEFAULT_TIMING)}>
            {t("Restore defaults", "恢复预设")}
          </Button>
        </div>
      </form>
      <div className="panel">
        <h2>{t("Local storage and privacy", "本地保存与隐私")}</h2>
        <p>
          {t(
            "Use desktop Chrome or Edge at localhost or 127.0.0.1. The server listens only on your computer. Materials, the SQLite database, and recordings stay local; scoring does not depend on an AI service.",
            "使用桌面 Chrome / Edge，通过 localhost 或127.0.0.1访问。服务器仅监听本机地址。资料、SQLite数据库与录音不会上传云端，评分不依赖AI服务。",
          )}
        </p>
        <p>
          {t(
            "Recordings are saved in one-second chunks. If the local service is unavailable, browser drafts retain them for retry. Keep browser site data, and keep data, generated, and storage private. After a session, you can export your answers and download recordings.",
            "录音每秒分段保存，断网或本机服务故障时先放入浏览器本地草稿并重试。不要清除浏览器站点数据，也不要公开发布 data、generated、storage。结束练习后可以导出答卷和下载录音。",
          )}
        </p>
      </div>
    </>
  );
}

export function Validation() {
  const { t, locale } = useI18n();
  const [data, setData] = useState<Record<string, unknown> | null>(null),
    [error, setError] = useState("");
  useEffect(() => {
    api<Record<string, unknown>>("/api/validation")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);
  const coverage = (data?.coverage || {}) as Record<string, unknown>;
  return (
    <>
      <Heading
        title={t(
          "Every question should be traceable.",
          "每一道题，都应该有据可查。",
        )}
        subtitle={t(
          "Inspect import coverage, duplicates, missing media, and items needing manual review. Original files are preserved.",
          "查看导入覆盖、重复内容、缺失媒体及需人工核对的问题。原始文件始终保留。",
        )}
      />
      {error && (
        <p className="error-message">{localizeDynamic(error, locale)}</p>
      )}
      {!data && !error ? (
        <Empty>
          {t("Loading the validation report…", "正在读取校验报告…")}
        </Empty>
      ) : (
        <>
          <div className="stat-grid">
            {Object.entries(coverage)
              .slice(0, 4)
              .map(([key, value]) => (
                <div className="stat" key={key}>
                  <span className="stat-icon">
                    <Icon name="check" />
                  </span>
                  <div>
                    <div className="stat-label">
                      {{
                        fileCount: t("Material files", "资料文件"),
                        exams: t("Test archives", "套题档案"),
                        strictEligible: t("Strict-mode ready", "严格模考可用"),
                        interactive: t("Interactive library", "交互题库"),
                      }[key] || localizeDynamic(key, locale)}
                    </div>
                    <div className="stat-value">
                      {typeof value === "number"
                        ? value.toLocaleString(locale)
                        : String(value)}
                    </div>
                  </div>
                </div>
              ))}
          </div>
          <div className="panel">
            <h2>{t("Material import audit", "资料导入审核")}</h2>
            <Report value={data} />
          </div>
          <Notice>
            {t(
              "Supplemental, missing-audio, and pending-review materials are excluded from strict tests. System files such as .DS_Store are inventory entries, not question content. Machine reports and human audit notes are stored locally in generated and docs.",
              "标为补充、缺音频或待审核的材料不会静默混入严格模考。.DS_Store 等系统文件仅列入盘点，不作题库内容。完整机器报告与人工说明均保存在本机 generated 与 docs 目录。",
            )}
          </Notice>
        </>
      )}
    </>
  );
}

function Report({ value, depth = 0 }: { value: unknown; depth?: number }) {
  const { t, locale } = useI18n();
  if (value === null || value === undefined)
    return <span className="muted">—</span>;
  if (Array.isArray(value)) {
    if (!value.length)
      return <span className="pill teal">{t("None", "无")}</span>;
    return (
      <div className="report-list">
        {value.map((v, i) => (
          <div className="report-entry" key={i}>
            <Report value={v} depth={depth + 1} />
          </div>
        ))}
      </div>
    );
  }
  if (typeof value === "object")
    return (
      <div className="report-fields">
        {Object.entries(value)
          .filter(([k]) => k !== "coverage")
          .map(([k, v]) => (
            <details key={k} open={depth < 1}>
              <summary>{localizeDynamic(k, locale)}</summary>
              <Report value={v} depth={depth + 1} />
            </details>
          ))}
      </div>
    );
  return (
    <span style={{ overflowWrap: "anywhere" }}>
      {typeof value === "number"
        ? value.toLocaleString(locale)
        : typeof value === "boolean"
          ? value
            ? t("Yes", "是")
            : t("No", "否")
          : localizeDynamic(String(value), locale)}
    </span>
  );
}

// Reconstruct sentence answers from stable token IDs without changing the stored response.
function displayUserAnswer(q: Question, value: Answer | undefined): unknown {
  if (
    q.type === "build_sentence" &&
    value &&
    typeof value === "object" &&
    !Array.isArray(value) &&
    Array.isArray(value.tokenOrder)
  ) {
    let i = 0;
    return (
      q.slots
        ?.map((slot) => {
          if (typeof slot === "string") return slot;
          if (slot?.fixed) return slot.fixed;
          const id = value.tokenOrder[i++];
          return id !== "" && id !== undefined
            ? q.tokens?.[Number(id)] || "____"
            : "____";
        })
        .join(" ")
        .replace(/\s+([?.!,;:])/g, "$1") || value
    );
  }
  if (typeof value === "string" && q.choices?.length) {
    const choice = q.choices.find((item) => item.id === value);
    if (choice)
      return q.interaction === "select_sentence" || choice.text === value
        ? choice.text
        : `${value}. ${choice.text}`;
  }
  return value;
}
const answerText = (value: unknown): string =>
  value == null || value === ""
    ? tr("Not answered", "未作答")
    : typeof value === "object"
      ? Object.entries(value)
          .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(" / ") : v}`)
          .join("\n")
      : String(value);
export function ReviewPage({
  review,
  materials,
  onHistory,
  onWrongPractice,
  onNotice,
  onAddWord,
}: {
  review: Review;
  materials: Material[];
  onHistory: () => void;
  onWrongPractice: (ids: string[]) => void;
  onNotice: (s: string) => void;
  onAddWord?: (draft: VocabularyDraft) => void;
}) {
  const { t, locale } = useI18n();
  const r = review,
    s = r.session,
    [wrongOnly, setWrongOnly] = useState(false),
    [ratings, setRatings] = useState(r.ratings || {});
  useEffect(() => setRatings(r.ratings || {}), [r]);
  const sections =
      r.sections ||
      ((r.exam?.sections || []) as NonNullable<Review["sections"]>),
    questions = sections.flatMap((section) =>
      section.modules.flatMap((m) => m.questions || []),
    ),
    correct = Number(r.score?.correct || 0),
    total = Number(r.score?.total || 0);
  const wrong = questions
    .filter((q) => q.grade && q.grade.correct < q.grade.total)
    .map((q) => q.id);
  const audioIntegrity = r.recordingIntegrity || s.recordingIntegrity;
  const overview = ORDER.flatMap((id) => {
    const selected = sections
      .filter((section) => section.id === id)
      .flatMap((section) =>
        section.modules.flatMap((module) => module.questions || []),
      );
    if (!selected.length) return [];
    const objective = selected.flatMap((question) =>
      question.grade && question.grade.total > 0 ? [question.grade] : [],
    );
    const subjective = selected.filter(
      (question) =>
        ("subjective" in question && question.subjective === true) ||
        id === "speaking" ||
        (id === "writing" && question.type !== "build_sentence") ||
        [
          "email",
          "academic_discussion",
          "listen_repeat",
          "interview",
          "read_aloud",
          "picture_writing",
        ].includes(question.type),
    );
    // An unrated response is unknown, not zero; only valid saved ratings enter the average.
    const selfScores = subjective.flatMap((question) => {
      const value = ratings[question.id]?.value;
      return typeof value === "number" &&
        Number.isInteger(value) &&
        value >= 0 &&
        value <= 5
        ? [value]
        : [];
    });
    return [
      {
        section: id,
        correct: objective.reduce((sum, grade) => sum + grade.correct, 0),
        total: objective.reduce((sum, grade) => sum + grade.total, 0),
        subjective: subjective.length,
        rated: selfScores.length,
        selfScore: selfScores.reduce((sum, value) => sum + value, 0),
      },
    ];
  });
  const overviewTotal = overview.reduce(
    (sum, row) => ({
      correct: sum.correct + row.correct,
      total: sum.total + row.total,
      subjective: sum.subjective + row.subjective,
      rated: sum.rated + row.rated,
      selfScore: sum.selfScore + row.selfScore,
    }),
    { correct: 0, total: 0, subjective: 0, rated: 0, selfScore: 0 },
  );
  const overviewCells = (row: typeof overviewTotal) => (
    <>
      <td>{row.total ? `${row.correct} / ${row.total}` : "—"}</td>
      <td>
        {row.total ? `${Math.round((row.correct / row.total) * 100)}%` : "—"}
      </td>
      <td>
        {row.subjective
          ? t("Rated {rated} / {total}", "已评 {rated} / {total}", {
              rated: row.rated,
              total: row.subjective,
            })
          : "—"}
      </td>
      <td>
        {row.rated
          ? `${(row.selfScore / row.rated).toLocaleString(locale, { minimumFractionDigits: 1, maximumFractionDigits: 1 })} / 5`
          : row.subjective
            ? t("Awaiting self-assessment", "待自评")
            : "—"}
      </td>
    </>
  );
  const saveRating = async (qid: string, rating: Rating) => {
    await api(`/api/sessions/${s.id}/ratings`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ questionId: qid, ...rating }),
    });
    setRatings((old) => ({ ...old, [qid]: rating }));
    onNotice(t("Self-assessment saved locally.", "自评已保存到本机。"));
  };
  return (
    <VocabularyCapture
      onAdd={onAddWord}
      sourceLabel={s.title}
      sourceSessionId={s.id}
    >
      <div className="result-hero">
        <div>
          <div
            className="eyebrow"
            style={{ color: "#a3bf8f", marginBottom: 13 }}
          >
            {t("PRACTICE COMPLETE", "练习完成")}
          </div>
          <h1>{localizeDynamic(s.title, locale)}</h1>
          <p>
            {date(s.startedAt, locale)} ·{" "}
            {s.mode === "strict"
              ? t("Strict timing", "严格计时")
              : t("Guided practice", "辅助练习")}{" "}
            ·{" "}
            {s.status === "completed"
              ? t("Completed", "已完成")
              : t("Ended early", "提前结束")}
            {s.integrity?.interrupted
              ? t(" \u00b7 Interrupted", " · 含中断")
              : ""}
          </p>
        </div>
        <div className="result-score">
          {total ? (
            <>
              {correct}
              <span style={{ fontSize: 20, color: "#7e9f72" }}> / {total}</span>
              <small>
                {t(
                  "Objective accuracy: {percent}%",
                  "客观题正确率 {percent}%",
                  { percent: Math.round((correct / total) * 100) },
                )}
              </small>
            </>
          ) : (
            <>
              {t("Awaiting self-assessment", "待自评")}
              <small>
                {t(
                  "No automatically scored objective items in this session",
                  "本次没有可自动评分的客观题",
                )}
              </small>
            </>
          )}
        </div>
      </div>
      <div className="section-heading">
        <h2>{t("Review this session", "回顾这一次练习")}</h2>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <a
            className="btn outline small"
            href={`/api/sessions/${s.id}/export`}
            download={`toefl-${s.id}.json`}
          >
            <Icon name="download" />
            {t("Export answers", "导出答卷")}
          </a>
          <Button kind="outline small" onClick={onHistory}>
            {t("All sessions", "全部记录")}
          </Button>
        </div>
      </div>
      <Notice>
        {t(
          "These are practice results, not official scores. Objective responses use verified reference keys; check the original for semantic, OCR, or sentence-building differences. Self-assess open responses with the official rubrics; results are not converted to a 1\u20136 or 120-point scale.",
          "此结果不是官方成绩。客观题按已核验参考答案核对；语义、OCR及造句差异仍可对照原题。主观题请使用官方量表自评，不换算1–6或120分。",
        )}
        {s.integrity?.interrupted
          ? t(
              " This session was interrupted and is not a continuous strict mock test.",
              " 本次存在中断，不能视为一次连续严格模考。",
            )
          : ""}
      </Notice>
      {s.scoreSnapshotStatus === "frozen" && (
        <p className="review-score-note">
          {t(
            "Objective scores were frozen on {date} · {version}. Recording uploads and self-assessments may still be updated.",
            "客观评分已于 {date} 冻结保存 · {version}。录音补传和主观自评可继续更新。",
            {
              date: date(s.scoreSnapshotCalculatedAt || s.completedAt, locale),
              version: s.scoringEngineVersion || "—",
            },
          )}
        </p>
      )}
      {s.scoreSnapshotStatus === "legacy-recomputed" && (
        <Notice>
          {t(
            "This older session has no score snapshot from submission. Objective results have been recalculated from the preserved answers; the original answers have not been changed.",
            "这份旧记录没有交卷时的评分快照，当前客观分按保留的原答卷重新核对；原答卷未被改写。",
          )}
        </Notice>
      )}
      {audioIntegrity &&
        audioIntegrity.expectedQuestionIds.length > 0 &&
        audioIntegrity.status !== "complete" && (
          <div className="recording-integrity-warning" role="alert">
            <strong>
              {t("Recording completeness is not confirmed", "录音尚未确认完整")}
            </strong>
            <p>
              {t(
                "{missing} Speaking responses have no saved recording; {incomplete} takes are incomplete or missing a completion marker. Keep browser drafts for retry. Responses lost because of a device or permission problem need a new practice attempt.",
                "{missing} 道口语题没有已保存录音，{incomplete} 段录音缺少完成标记或部分数据。请保留浏览器草稿并等待重试；设备或权限导致的缺失需要重新练习。",
                {
                  missing: audioIntegrity.missingQuestionIds.length,
                  incomplete: audioIntegrity.incompleteTakes.length,
                },
              )}
            </p>
          </div>
        )}
      <div className="review-metrics">
        <span>
          {t("Practice duration", "练习用时")}{" "}
          <b>
            {time(
              Math.round(
                Number(r.score.durationSeconds || r.score.elapsedSeconds || 0),
              ),
            )}
          </b>
        </span>
        <span>
          {t("Screens answered", "已作答题面")}{" "}
          <b>{Number(r.score.attemptedCount || 0).toLocaleString(locale)}</b>
        </span>
        <span>
          {t("Recorded responses", "含录音题目")}{" "}
          <b>{Object.keys(r.recordings).length.toLocaleString(locale)}</b>
        </span>
        <span>
          {t("Rules version", "规则版本")}{" "}
          <b>
            {s.rulesVersion ||
              s.ruleVersion ||
              t("Frozen session settings", "本次冻结配置")}
          </b>
        </span>
      </div>
      {overview.length > 0 && (
        <section className="review-score-overview">
          <h2>{t("Score overview by section", "本次分科评分概览")}</h2>
          <p className="review-score-note">
            {t(
              "Only questions selected for this session are included. Open-response scores are local self-assessments; unrated responses do not count as zero. Objective checks and self-assessments are shown separately and are not combined or converted to ETS 1\u20136 or 120-point scores.",
              "仅统计本次所选题目。主观列为本地自评，未自评不按0分处理；客观核对与自评单独列示，不合成或换算 ETS 1–6 或120分。",
            )}
          </p>
          <div className="review-score-table-wrap">
            <table
              className="review-score-table"
              aria-label={t("Score overview by section", "本次分科评分概览")}
            >
              <thead>
                <tr>
                  <th scope="col">{t("Section", "部分")}</th>
                  <th scope="col">
                    {t("Objective correct / total", "客观题正确 / 总数")}
                  </th>
                  <th scope="col">{t("Objective accuracy", "客观正确率")}</th>
                  <th scope="col">
                    {t("Open-response rating progress", "主观题自评进度")}
                  </th>
                  <th scope="col">
                    {t("Average self-rating (0\u20135)", "平均自评分（0–5）")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {overview.map((row) => (
                  <tr key={row.section}>
                    <th scope="row">{sectionLabel(row.section, locale)}</th>
                    {overviewCells(row)}
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <th scope="row">{t("Session total", "本次合计")}</th>
                  {overviewCells(overviewTotal)}
                </tr>
              </tfoot>
            </table>
          </div>
        </section>
      )}
      <div className="toolbar" style={{ marginTop: 22 }}>
        <Button
          kind={wrongOnly ? "primary small" : "outline small"}
          onClick={() => setWrongOnly(!wrongOnly)}
        >
          {wrongOnly
            ? t("Show all answers", "查看全部答案")
            : t("Only incorrect questions", "只看错题")}
        </Button>
        {onAddWord && (
          <Button
            kind="outline small"
            onClick={() =>
              onAddWord({
                word: "",
                sourceLabel: s.title.slice(0, 240),
                sourceSessionId: s.id,
              })
            }
          >
            <Icon name="bookmark" />
            {t("Add a word", "添加生词")}
          </Button>
        )}
        <Button
          kind="outline small"
          disabled={!wrong.length}
          onClick={() => onWrongPractice(wrong)}
        >
          {t("Retry unmatched objective items", "重练未匹配客观题")}
          <Icon name="arrow" />
        </Button>
        <span className="muted" style={{ fontSize: 10 }}>
          {t(
            "Filtered using reference-answer checks; unscored and conflicting-answer items are excluded.",
            "按服务端参考答案核对筛选，不包含未评分或答案冲突的题目。",
          )}
        </span>
      </div>
      {onAddWord && (
        <p className="review-vocabulary-hint">
          {t(
            "Select a word in the passage or answers to save it to your vocabulary book.",
            "在原文或答案中选中单词，即可加入单词本。",
          )}
        </p>
      )}
      {wrong.length > 0 && (
        <nav
          className="review-question-nav"
          aria-label={t("Jump to incorrect questions", "错题定位")}
        >
          <span className="muted">{t("Needs correction:", "待订正：")}</span>
          {sections.flatMap((section) =>
            section.modules
              .flatMap((module) => module.questions || [])
              .filter((q) => wrong.includes(q.id))
              .map((q) => (
                <a key={q.id} href={`#review-${q.id}`}>
                  {sectionLabel(section.id, locale)} {q.number ?? ""}
                  {q.numberEnd ? `–${q.numberEnd}` : ""}
                </a>
              )),
          )}
        </nav>
      )}
      {sections.map((section) => (
        <section key={section.id}>
          <div className="section-heading" style={{ marginTop: 28 }}>
            <h2>{sectionLabel(section.id, locale)}</h2>
          </div>
          {section.modules
            .flatMap((m) => m.questions || [])
            .filter((q) => !wrongOnly || wrong.includes(q.id))
            .map((q) => (
              <article
                className={`review-item ${wrong.includes(q.id) ? "review-item-incorrect" : ""}`}
                key={q.id}
                id={`review-${q.id}`}
                data-question-id={q.id}
                data-vocabulary-source={`${s.title} · ${sectionLabel(section.id, locale)} · ${q.number ?? ""}`}
              >
                <div className="review-top">
                  <h3>
                    {q.number}
                    {q.numberEnd ? `–${q.numberEnd}` : ""}.{" "}
                    {taskName(q.type, locale)}
                  </h3>
                  <span
                    className={`pill ${wrong.includes(q.id) ? "review-incorrect-badge" : "gray"}`}
                  >
                    {wrong.includes(q.id) && (
                      <>
                        <Icon name="close" />
                        {t("Needs correction", "需要订正")} ·{" "}
                      </>
                    )}
                    {q.grade
                      ? `${q.grade.correct} / ${q.grade.total}`
                      : localizeDynamic(q.auditStatus, locale) ||
                        t("Manual review", "人工复盘")}
                  </span>
                </div>
                {q.textCorrection && (
                  <p className="muted" style={{ fontSize: 12 }}>
                    {t(
                      "Text corrected against the original page. Your saved answer and score are unchanged.",
                      "题目文字已按原页校正，你的作答与原成绩保持不变。",
                    )}
                  </p>
                )}
                <div className="prompt" style={{ fontSize: 13 }}>
                  {q.prompt}
                </div>
                {q.sourceVariant?.paperPrompt && (
                  <details className="source-edition-note">
                    <summary>
                      {t(
                        "Audio edition · Compare with the paper question",
                        "音频版本 · 查看与纸面题目的差异",
                      )}
                    </summary>
                    <p>
                      {q.sourceVariant.id === "student-1-interview-audio"
                        ? t(
                            "This practice used the original audio prompt. The paper PDF asks a different question; its attached sample response is not used for this audio version.",
                            "本次练习使用原始音频提问。纸面 PDF 的问题不同，纸面资料附带的示范回答不用于此音频版本。",
                          )
                        : t(
                            "This practice uses the supplied original recording. Its wording or question order differs from the paper PDF. The paper text is retained below for comparison.",
                            "本次练习使用资料中的原始录音，其措辞或题目顺序与纸面 PDF 存在差异。下方保留纸面原文供对照。",
                          )}
                    </p>
                    <p lang="en">{q.sourceVariant.paperPrompt}</p>
                    {q.sourceVariant.id === "student-1-interview-audio" && (
                      <a
                        href="https://www.ets.org/pdfs/toefl/toefl-ibt-test-overview.pdf#page=19"
                        target="_blank"
                        rel="noreferrer"
                      >
                        {t(
                          "ETS Test Overview · audio-version wording",
                          "ETS Test Overview · 音频版题目原文",
                        )}
                      </a>
                    )}
                  </details>
                )}
                {q.choices && (
                  <p
                    className="muted"
                    style={{ fontSize: 12, lineHeight: 1.9 }}
                  >
                    {q.choices.map((c) => (
                      <span key={c.id}>
                        {c.id}. {c.text}
                        <br />
                      </span>
                    ))}
                  </p>
                )}
                {r.recordings[q.id]?.map((take) => (
                  <div key={take.takeId} style={{ marginTop: 15 }}>
                    <small className="muted">
                      {t(
                        "Recording · {count} saved chunks",
                        "录音片段 · {count} 个保存分段",
                        {
                          count: Array.isArray(take.segments)
                            ? take.segments.length
                            : take.segments,
                        },
                      )}{" "}
                      {take.completeSequence === false
                        ? t(
                            "\u00b7 Some chunks are not synchronized; retry saving",
                            "· 存在未同步片段，请重试保存",
                          )
                        : ""}
                    </small>
                    <audio
                      controls
                      src={take.url}
                      aria-label={t(
                        "Speaking recording for this question",
                        "本题口语录音",
                      )}
                    />
                    <a className="btn small" href={take.url} download>
                      {t("Download recording", "下载录音")}
                      <Icon name="download" />
                    </a>
                  </div>
                ))}
                {q.grade ||
                [
                  "cloze",
                  "complete_words",
                  "choice",
                  "build_sentence",
                  "short_answer",
                ].includes(q.type) ? (
                  <AnswerComparison
                    question={q}
                    answer={r.answers[q.id]}
                    onAddWord={
                      onAddWord
                        ? (draft) =>
                            onAddWord({
                              ...draft,
                              sourceSessionId: s.id,
                              sourceQuestionId: q.id,
                              sourceLabel:
                                `${s.title} · ${sectionLabel(section.id, locale)} · ${draft.sourceLabel || q.number || ""}`.slice(
                                  0,
                                  240,
                                ),
                            })
                        : undefined
                    }
                  />
                ) : (
                  <div className="review-answer">
                    <div>
                      <strong>{t("Your response", "你的回答")}</strong>
                      {answerText(
                        displayUserAnswer(q, r.answers[q.id]) ||
                          (r.recordings[q.id]?.length
                            ? t(
                                "Recorded; play it above",
                                "已录音，点击上方回放",
                              )
                            : undefined),
                      )}
                    </div>
                    <div>
                      <strong>
                        {t(
                          "Source reference / Review guidance",
                          "资料参考 / 复盘提示",
                        )}
                      </strong>
                      {q.answer != null
                        ? answerText(displayUserAnswer(q, q.answer))
                        : [
                              "email",
                              "academic_discussion",
                              "listen_repeat",
                              "interview",
                              "read_aloud",
                              "picture_writing",
                            ].includes(q.type)
                          ? t(
                              "This response is not automatically scored. Use the relevant rubric to review delivery, language, and content.",
                              "本题不自动评分。请参照适用量表核对表达、语言和内容。",
                            )
                          : t(
                              "The source answer is missing or has an unresolved conflict. This item is excluded from automatic scoring; check the original question and passage.",
                              "原资料答案缺失或存在未解决的冲突，本题未计入自动评分。请对照原题与原文核验。",
                            )}
                    </div>
                  </div>
                )}
                <Explanation question={q} />
                <details>
                  <summary>
                    {q.mediaSequence?.length
                      ? t(
                          "Show original audio, text and question images",
                          "展开原音、原文与原题图",
                        )
                      : t(
                          "Show original text and question images",
                          "展开原文与原题图",
                        )}
                  </summary>
                  {q.mediaSequence?.map((media, index) => (
                    <div
                      key={media.assetId || media.url}
                      className="review-source-media"
                    >
                      <strong>
                        {t(
                          "Original question audio {number}",
                          "原题音频 {number}",
                          { number: index + 1 },
                        )}
                      </strong>
                      {media.mediaType === "video" ? (
                        <video
                          controls
                          preload="metadata"
                          src={media.url}
                          aria-label={t(
                            "Original question video {number}",
                            "原题视频 {number}",
                            { number: index + 1 },
                          )}
                        />
                      ) : (
                        <audio
                          controls
                          preload="metadata"
                          src={media.url}
                          aria-label={t(
                            "Original question audio {number}",
                            "原题音频 {number}",
                            { number: index + 1 },
                          )}
                        />
                      )}
                    </div>
                  ))}
                  <div className="passage" style={{ marginTop: 15 }}>
                    {q.transcript ||
                      q.passage ||
                      q.passageTemplate?.replace(
                        /\{\{([^{}]+)\}\}/g,
                        (_, id: string) =>
                          `___ (${q.blanks?.find((blank) => blank.id === id)?.number ?? id})`,
                      )}
                  </div>
                  <StemAssets
                    question={{
                      ...q,
                      assets: q.sourceEvidenceAssets?.length
                        ? q.sourceEvidenceAssets
                        : q.assets,
                    }}
                  />
                  {q.source?.url && (
                    <p>
                      <a href={q.source.url} target="_blank" rel="noopener">
                        {t(
                          "Question source · Page {page} ↗",
                          "原题来源 · 第 {page} 页 ↗",
                          { page: q.source.page || "—" },
                        )}
                      </a>
                    </p>
                  )}
                  {q.stimulusSource?.url && (
                    <p>
                      <a
                        href={q.stimulusSource.url}
                        target="_blank"
                        rel="noopener"
                      >
                        {t(
                          "Stimulus source · Page {page} ↗",
                          "刺激材料来源 · 第 {page} 页 ↗",
                          { page: q.stimulusSource.page || "—" },
                        )}
                      </a>
                    </p>
                  )}
                </details>
                {[
                  "email",
                  "academic_discussion",
                  "listen_repeat",
                  "interview",
                  "read_aloud",
                  "picture_writing",
                ].includes(q.type) && (
                  <RatingForm
                    supplemental={s.examId.startsWith("essentials-")}
                    key={`${q.id}:${ratings[q.id]?.value}`}
                    rating={ratings[q.id]}
                    save={(value) => saveRating(q.id, value)}
                    rubrics={materials.filter((m) =>
                      m.name
                        .toLowerCase()
                        .includes(
                          q.type === "email" || q.type === "academic_discussion"
                            ? "writing-rubrics"
                            : "speaking-rubrics",
                        ),
                    )}
                  />
                )}
              </article>
            ))}
        </section>
      ))}
      <div className="panel">
        <h2>{t("Workflow and incident log", "流程与异常记录")}</h2>
        <details>
          <summary>
            {t("View {count} events", "查看 {count} 条事件", {
              count: r.events?.length || 0,
            })}
          </summary>
          <Report value={r.events} />
        </details>
      </div>
    </VocabularyCapture>
  );
}
function RatingForm({
  rating,
  save,
  rubrics,
  supplemental = false,
}: {
  rating?: Rating;
  save: (r: Rating) => Promise<void>;
  rubrics: Material[];
  supplemental?: boolean;
}) {
  const { t, locale } = useI18n();
  const [error, setError] = useState("");
  return (
    <form
      className="self-rating"
      onSubmit={async (e) => {
        e.preventDefault();
        const data = new FormData(e.currentTarget);
        try {
          await save({
            value: Number(data.get("value")),
            notes: String(data.get("notes") || ""),
          });
        } catch (e) {
          setError(String(e));
        }
      }}
    >
      <div className="section-heading">
        <h3 style={{ fontSize: 13, margin: 0 }}>
          {supplemental
            ? t(
                "Study self-assessment \u00b7 Unofficial score",
                "学习自评 · 非官方分数",
              )
            : t(
                "Official rubric \u00b7 Local self-assessment",
                "官方量表 · 本地自评",
              )}
        </h3>
        {!supplemental &&
          rubrics.map((r) =>
            r.url ? (
              <a
                key={r.id}
                className="btn small"
                href={r.url}
                target="_blank"
                rel="noopener"
              >
                {t("Open rubric", "打开 Rubric")}
                <Icon name="external" />
              </a>
            ) : null,
          )}
      </div>
      <div style={{ display: "flex", gap: 12 }}>
        <label className="field">
          {t("Self-assessment score (0\u20135)", "自评分（0–5）")}
          <select
            name="value"
            defaultValue={rating?.value ?? ""}
            required
            aria-label={t("Self-assessment score", "自评分")}
          >
            <option value="" disabled>
              {t("Choose a score", "选择分数")}
            </option>
            {[0, 1, 2, 3, 4, 5].map((n) => (
              <option key={n}>{n}</option>
            ))}
          </select>
        </label>
        <label className="field" style={{ flex: 1 }}>
          {t("Review notes", "复盘笔记")}
          <input
            name="notes"
            defaultValue={rating?.notes || ""}
            placeholder={t(
              "Content, language, delivery, and next steps\u2026",
              "内容、语言、表达和下次改进…",
            )}
          />
        </label>
        <Button kind="outline" type="submit" style={{ alignSelf: "end" }}>
          {t("Save self-assessment", "保存自评")}
        </Button>
      </div>
      {error && (
        <p className="error-message">{localizeDynamic(error, locale)}</p>
      )}
    </form>
  );
}
export function Feedback({
  data,
  onClose,
}: {
  data: { question: Question; answer?: Answer; grade?: unknown };
  onClose: () => void;
}) {
  const { t } = useI18n();
  const grade = data.grade as { correct: number; total: number } | null;
  return (
    <Modal
      onClose={onClose}
      actions={
        <Button onClick={onClose}>{t("Continue practice", "继续练习")}</Button>
      }
    >
      <h2>
        {t("Instant check \u00b7 Assisted practice", "即时核对 · 辅助练习")}
      </h2>
      {grade && (
        <span
          className={`pill ${grade.correct === grade.total ? "teal" : "amber"}`}
        >
          {t("Correct: {correct} / {total}", "正确 {correct} / {total}", {
            correct: grade.correct,
            total: grade.total,
          })}
        </span>
      )}
      <AnswerComparison
        question={{ ...data.question, grade }}
        answer={data.answer}
      />
      <Explanation question={data.question} />
      {data.question.transcript && (
        <div className="passage" style={{ fontSize: 14, marginTop: 20 }}>
          {data.question.transcript}
        </div>
      )}
      <p>
        {t(
          "This window does not pause the timer. Use Pause on the practice page if you need a break.",
          "这个窗口不会自动暂停计时，需要暂停时先使用练习页面的 Pause。",
        )}
      </p>
    </Modal>
  );
}

// Select authored rationale translations without altering the saved question or source quotations.
function Explanation({ question: q }: { question: Question }) {
  const { t, locale } = useI18n();
  const original: Exclude<Question["explanation"], string> =
    typeof q.explanation === "string"
      ? {
          origin: "source",
          label: t("Source explanation", "资料附带解析"),
          text: q.explanation,
        }
      : q.explanation;
  const explanation = original && {
    ...original,
    ...original.translations?.[locale],
  };
  const language = explanation?.language;
  const explanationText = (text: string) =>
    language || explanation?.origin === "source"
      ? text
      : localizeDynamic(text, locale);
  return (
    <section className="explanation-panel">
      <div className="explanation-heading">
        <Icon name="book" />
        <h4>{t("Answers and explanations", "答案与解析")}</h4>
        <span
          className={`pill ${explanation?.origin === "source" ? "teal" : "gray"}`}
        >
          {(language
            ? explanation?.label
            : localizeDynamic(explanation?.label, locale)) ||
            t("Source evidence", "原资料依据")}
        </span>
      </div>
      {explanation ? (
        <>
          {q.explanationConflict !== undefined &&
          explanation.origin === "source" ? (
            <>
              <p className="explanation-warning">
                {t(
                  "This source explanation conflicts with the question or verified reference key. Do not use it as the sole basis for your answer; the original is retained below for comparison.",
                  "这份附带解析与原题或已核对的参考键存在冲突，不能作为唯一解题依据。原文保留在下方供对照。",
                )}
              </p>
              <details>
                <summary>
                  {t(
                    "View the conflicting source explanation",
                    "查看有冲突的资料附带解析原文",
                  )}
                </summary>
                <p lang={language}>{explanationText(explanation.text)}</p>
              </details>
            </>
          ) : (
            <p lang={language}>{explanationText(explanation.text)}</p>
          )}
          {explanation.reviewed && explanation.evidence?.length ? (
            <ul className="explanation-reasons" lang={language}>
              {explanation.evidence?.map((item, index) => (
                <li key={index}>{item}</li>
              ))}
            </ul>
          ) : (
            explanation.evidence?.map((evidence, index) => (
              <blockquote key={index}>
                {explanation.origin === "source"
                  ? evidence
                  : localizeDynamic(evidence, locale)}
              </blockquote>
            ))
          )}
          {explanation.warnings?.map((warning, index) => (
            <p className="explanation-warning" key={index} lang={language}>
              {explanationText(warning)}
            </p>
          ))}
          {explanation.source?.page && (
            <small className="muted">
              {explanation.reviewed ? (
                t("Question source · Page {page}", "原题来源 · 第 {page} 页", {
                  page: explanation.source.page,
                })
              ) : explanation.source.url ? (
                <a
                  href={`${explanation.source.url}${explanation.source.url.includes("#") ? "" : `#page=${explanation.source.page}`}`}
                  target="_blank"
                  rel="noopener"
                >
                  {t(
                    "Explanation source · Page {page} ↗",
                    "资料解析来源 · 第 {page} 页 ↗",
                    { page: explanation.source.page },
                  )}
                </a>
              ) : (
                <>
                  {t(
                    "Explanation source · Page {page}",
                    "资料解析来源 · 第 {page} 页",
                    { page: explanation.source.page },
                  )}
                </>
              )}
            </small>
          )}
        </>
      ) : (
        <p>
          {t(
            "The source does not include an explanation for this item. The original passage and question images remain available below for verification. Inferences are not presented as official explanations.",
            "这份原资料没有附带该题解析。下方保留原文与原题图供核验；软件不将推测写成官方解析。",
          )}
        </p>
      )}
      {q.sourceReferenceAnswer !== undefined && (
        <details>
          <summary>
            {t(
              "View the original key and verification notes",
              "查看原参考键与题面校核记录",
            )}
          </summary>
          <p>
            {t("Original answer key: ", "原参考键：")}
            {answerText(q.sourceReferenceAnswer)}
          </p>
          {q.resolutionEvidence !== undefined && !explanation?.reviewed && (
            <Report value={q.resolutionEvidence} />
          )}
        </details>
      )}
      {!!q.acceptedAnswers?.length && (
        <details>
          <summary>
            {t(
              "View accepted variants from the source",
              "查看资料中已有的可接受写法",
            )}
          </summary>
          {q.acceptedAnswers.map((answer, index) => (
            <p key={index}>{answer}</p>
          ))}
          {q.sourceAnswerVariants !== undefined && (
            <Report value={q.sourceAnswerVariants} />
          )}
        </details>
      )}
      {q.answerConflict !== undefined &&
        (!explanation?.reviewed || explanation.origin === "unavailable") && (
          <details>
            <summary>
              {t(
                "Source differences recorded for this question",
                "此题有来源差异记录",
              )}
            </summary>
            <Report value={q.answerConflict} />
          </details>
        )}
      {q.explanationConflict !== undefined && !explanation?.reviewed && (
        <details open>
          <summary>
            {t(
              "Conflicting source explanation; use with care",
              "资料附带解析存在冲突，请谨慎使用",
            )}
          </summary>
          <Report value={q.explanationConflict} />
        </details>
      )}
    </section>
  );
}
