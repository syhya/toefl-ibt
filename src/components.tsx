import { tr, useI18n, LanguageSwitch, localizeDynamic } from "./i18n";
import { useEffect, useRef, useState, type ReactNode } from "react";
import Icon, { sectionIcon } from "./Icons";
import { ORDER, LABELS, date, size, sectionLabel, taskName } from "./api";
import type { Exam, Material, SessionSummary, SectionId } from "./types";
export function Button({
  children,
  onClick,
  kind = "primary",
  disabled = false,
  type = "button",
  ...rest
}: {
  children: ReactNode;
  onClick?: () => void;
  kind?: string;
  disabled?: boolean;
  type?: "button" | "submit";
} & Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "onClick">) {
  return (
    <button
      type={type}
      className={`btn ${kind}`}
      onClick={onClick}
      disabled={disabled}
      {...rest}
    >
      {children}
    </button>
  );
}
export function Empty({
  children,
  icon = "folder",
}: {
  children: ReactNode;
  icon?: string;
}) {
  return (
    <div className="empty">
      <Icon name={icon} />
      {children}
    </div>
  );
}
export function Notice({ children }: { children: ReactNode }) {
  return (
    <div className="notice">
      <Icon name="info" />
      <div>{children}</div>
    </div>
  );
}
export function Heading({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      {action}
    </div>
  );
}
export function Modal({
  children,
  actions,
  onClose,
  className,
}: {
  children: ReactNode;
  actions: ReactNode;
  onClose: () => void;
  className?: string;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    ref.current?.showModal();
  }, []);
  return (
    <dialog
      ref={ref}
      className={className}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
    >
      <div className="dialog-content">{children}</div>
      <div className="dialog-actions">{actions}</div>
    </dialog>
  );
}
export function Layout({
  page,
  go,
  materialCount,
  children,
}: {
  page: string;
  go: (p: string) => void;
  materialCount: number;
  children: ReactNode;
}) {
  useI18n();
  const pages = [
      ["home", "grid", tr("Practice", "模考练习")],
      ["drills", "book", tr("Task library", "专项题库")],
      ["mistakes", "flag", tr("Mistakes", "错题集")],
      ["vocabulary", "bookmark", tr("Vocabulary", "单词本")],
      ["library", "folder", tr("Resources", "全部资料")],
      ["history", "chart", tr("History", "练习记录")],
    ],
    more = [
      ["validation", "check", tr("Validation", "资料校验")],
      ["rules", "book", tr("Test rules", "考试规则")],
      ["settings", "settings", tr("Settings", "练习设置")],
      ["help", "info", tr("Help & setup", "使用与导入指南")],
    ];
  return (
    <div className="app-layout">
      <header className="site-header">
        <div className="brand">
          <div className="brand-icon">T</div>
          <div className="brand-name">
            TOEFL Practice
            <small>
              {tr("Personal practice · Saved locally", "个人练习 · 本地保存")}
            </small>
          </div>
        </div>
        <nav className="site-nav" aria-label={tr("Main navigation", "主导航")}>
          {pages.map(([id, icon, label]) => (
            <button
              key={id}
              className={`nav-item ${page === id ? "active" : ""}`}
              onClick={() => go(id)}
            >
              <Icon name={icon} />
              {label}
            </button>
          ))}
          <details className="nav-more">
            <summary
              className={more.some(([id]) => id === page) ? "active" : ""}
            >
              <Icon name="settings" /> {tr("More", "更多")}{" "}
            </summary>
            <div className="nav-more-menu">
              {more.map(([id, icon, label]) => (
                <button
                  key={id}
                  onClick={(event) => {
                    go(id);
                    event.currentTarget
                      .closest("details")
                      ?.removeAttribute("open");
                  }}
                >
                  <Icon name={icon} />
                  {label}
                </button>
              ))}
              <span>
                {materialCount}{" "}
                {tr("resources · Local only", "份资料 · 仅存本机")}
              </span>
            </div>
          </details>
        </nav>
        <LanguageSwitch />
        <div className="local-status">
          <i className="dot" /> {tr("Local service", "本地运行")}{" "}
        </div>
      </header>
      <div className="workspace">
        <main className="main">
          {children}
          <footer className="bottom-note">
            <span>{tr("Personal local practice", "个人本地练习工具")}</span>
            <span>
              {tr(
                "Independent project · No official score conversion",
                "非 ETS 官方产品 · 不换算官方成绩",
              )}
            </span>
          </footer>
        </main>
      </div>
    </div>
  );
}
export function Home({
  exams,
  materials,
  sessions,
  choose,
  resume,
  go,
}: {
  exams: Exam[];
  materials: Material[];
  sessions: SessionSummary[];
  choose: (e: Exam, scope?: SectionId) => void;
  resume: (s: SessionSummary) => void;
  go: (p: string) => void;
}) {
  useI18n();
  const [filter, setFilter] = useState(
    exams.some((e) => e.strictEligible) ? "ready" : "all",
  );
  const strict = exams.filter(
      (e) => e.strictEligible && e.structuredReady !== false,
    ),
    active = sessions.find((s) => s.status === "active"),
    staleActive =
      active?.sourceVersionMatches === false &&
      !active.canRecoverAudio &&
      !active.audioRecoveryApplied,
    visible = exams.filter(
      (e) =>
        filter === "all" ||
        (filter === "ready"
          ? e.strictEligible && e.structuredReady !== false
          : filter === "official"
            ? ["experience", "student", "teacher"].includes(e.family || "")
            : filter === "supplemental"
              ? ["paid", "essentials", "user"].includes(e.family || "")
              : e.family === filter),
    );
  return (
    <>
      <Heading
        title={tr("Start practicing", "开始练习")}
        subtitle={tr(
          "Choose a resource and practice the 2026 test flow.",
          "选择一套原始资料，按 2026 流程完成练习。",
        )}
        action={
          <button className="quiet-link" onClick={() => go("rules")}>
            {" "}
            {tr("Test rules", "考试规则")}{" "}
          </button>
        }
      />
      <section className="start-panel">
        <div>
          <span className="start-kicker">TOEFL iBT · 2026</span>
          <h2>
            {staleActive
              ? tr("Updated question presentation", "题面已更新")
              : active
                ? tr("Continue your practice", "继续上次练习")
                : tr("Ready when you are", "准备好就开始")}
          </h2>
          <p>
            {staleActive
              ? tr(
                  "Your earlier session is in History. Start a new session to use the updated questions.",
                  "旧练习已保留在记录中；请开始一份新版练习。",
                )
              : active
                ? `${localizeDynamic(active.title)} · ${active.scope === "all" ? tr("Full test", "完整流程") : sectionLabel(active.scope)}`
                : "Reading → Listening → Writing → Speaking"}
          </p>
        </div>
        {staleActive ? (
          <div className="start-actions">
            <Button
              onClick={() => choose(strict[0] || exams[0])}
              disabled={!exams.length}
            >
              {" "}
              {tr("Start new practice", "开始新练习")} <Icon name="arrow" />
            </Button>
            <Button kind="outline" onClick={() => go("history")}>
              {" "}
              {tr("Earlier sessions", "旧记录")}{" "}
            </Button>
          </div>
        ) : active ? (
          <Button onClick={() => resume(active)}>
            {" "}
            {tr("Continue practice", "继续练习")} <Icon name="arrow" />
          </Button>
        ) : (
          <Button
            onClick={() => choose(strict[0] || exams[0])}
            disabled={!exams.length}
          >
            {" "}
            {tr("Choose and start", "选择并开始")} <Icon name="arrow" />
          </Button>
        )}
      </section>
      {!staleActive && active?.mode === "strict" && (
        <div className="home-alert">
          <Icon name="clock" />{" "}
          {tr(
            "The strict-practice timer keeps running when you leave this page.",
            "严格模考离开页面后仍会继续计时。",
          )}{" "}
        </div>
      )}
      <div className="section-heading">
        <h2>{tr("Choose a test", "选择套题")}</h2>
        <p>
          {tr(
            "{count} {testNoun} · {files} local {resourceNoun}",
            "{count} 套 · 共 {files} 份本地资料",
            {
              count: visible.length,
              files: materials.length,
              testNoun: visible.length === 1 ? "test" : "tests",
              resourceNoun: materials.length === 1 ? "resource" : "resources",
            },
          )}
        </p>
      </div>
      <div
        className="simple-filters"
        aria-label={tr("Test categories", "套题分类")}
      >
        {[
          ["ready", tr("Full strict tests", "可完整模考")],
          ["official", tr("Official samples", "官方样题")],
          ["pack", tr("Practice sets", "练习套题")],
          ["supplemental", tr("Supplemental", "补充资料")],
          ["all", tr("All", "全部")],
        ].map(([id, label]) => (
          <button
            key={id}
            className={filter === id ? "active" : ""}
            onClick={() => setFilter(id)}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="exam-list">
        {visible.map((e, i) => (
          <ExamCard
            key={e.id}
            exam={e}
            index={i}
            choose={(scope) => choose(e, scope)}
          />
        ))}
      </div>
      {!visible.length && (
        <Empty>
          {tr("No tests in this category.", "该分类没有可用套题。")}
        </Empty>
      )}
    </>
  );
}
function ExamCard({
  exam,
  index,
  choose,
}: {
  exam: Exam;
  index: number;
  choose: (scope?: SectionId) => void;
}) {
  useI18n();
  const fam: Record<string, string> = {
    experience: tr("Official Experience Day", "官方体验日"),
    pack: tr("Practice sets", "练习套题"),
    student: tr("Student samples", "学生版样题"),
    teacher: tr("Teacher resources", "教师版资料"),
    paid: tr("Supplemental sets", "补充套题"),
    essentials: tr("Essentials · Separate test", "Essentials · 非 iBT"),
  };
  const family = fam[exam.family] || tr("Local resources", "本地资料"),
    number = String(exam.id.match(/\d+/)?.[0] || index + 1).padStart(2, "0"),
    ready = exam.structuredReady !== false,
    canOpen = ready || !!exam.resourcesOnly;
  return (
    <article className="exam-card">
      <div className="exam-index">{number}</div>
      <div className="exam-summary">
        <div className="card-topline">
          <span>{family}</span>
          <span
            className={`availability ${ready && exam.strictEligible ? "ready" : "guided"}`}
          >
            {!ready
              ? tr("Presentation not ready", "题面整理中")
              : exam.strictEligible
                ? tr("Strict timing", "严格计时")
                : tr("Guided only", "辅助练习")}
          </span>
        </div>
        <h3>{localizeDynamic(exam.title)}</h3>
        <p>
          {exam.questionCount || 0} {tr("items ·", "小题 ·")}{" "}
          {exam.adaptiveEligible
            ? tr("Includes lower and upper branches", "含高低分支")
            : tr("Original question order", "保留原套题顺序")}
        </p>
      </div>
      <div className="exam-actions">
        <div
          className="section-actions"
          aria-label={tr("{title} section practice", "{title} 分科练习", {
            title: localizeDynamic(exam.title),
          })}
        >
          {ORDER.map((id) => (
            <button
              key={id}
              aria-label={tr("Practice {section}", "练习 {section}", {
                section: sectionLabel(id),
              })}
              onClick={() => choose(id)}
              disabled={
                !canOpen ||
                !exam.sections?.some(
                  (section) =>
                    section.id === id && (section.questionCount || 0) > 0,
                )
              }
            >
              {LABELS[id][0]}
            </button>
          ))}
        </div>
        <button
          className="start-exam"
          onClick={() => choose()}
          disabled={!canOpen}
        >
          {exam.resourcesOnly
            ? tr("View", "查看")
            : ready
              ? tr("Full test", "整套")
              : tr("Needs verification", "待核对")}
          <Icon name="arrow" />
        </button>
      </div>
    </article>
  );
}
function ExamMatrix({
  exams,
  sessions,
  choose,
}: {
  exams: Exam[];
  sessions: SessionSummary[];
  choose: (exam: Exam, scope?: SectionId) => void;
}) {
  useI18n();
  return (
    <div className="exam-matrix table-wrap">
      <table>
        <thead>
          <tr>
            <th>{tr("Test / source", "套题 / 来源")}</th>
            {ORDER.map((id) => (
              <th key={id}>
                <Icon name={sectionIcon(id)} />
                {sectionLabel(id)}
              </th>
            ))}
            <th>{tr("Full test", "完整流程")}</th>
          </tr>
        </thead>
        <tbody>
          {exams.map((exam) => (
            <tr key={exam.id}>
              <td>
                <strong>{localizeDynamic(exam.title)}</strong>
                <small>
                  {exam.family === "essentials"
                    ? tr("Supplement · Separate from iBT", "补充资料 · 非iBT")
                    : exam.adaptiveEligible
                      ? tr("Lower and upper branches available", "高低分支齐全")
                      : tr("Original test structure", "保留原套题编排")}
                </small>
              </td>
              {ORDER.map((id) => {
                const attempts = sessions.filter(
                    (s) =>
                      s.examId === exam.id &&
                      (s.scope === id || s.scope === "all"),
                  ),
                  complete = attempts.some(
                    (s) =>
                      s.status === "completed" &&
                      s.isFullScope === true &&
                      s.sourceVersionMatches !== false,
                  ),
                  active = attempts.some((s) => s.status === "active"),
                  state = complete
                    ? "completed"
                    : active
                      ? "in_progress"
                      : "not_started",
                  available = exam.sections?.some(
                    (s) => s.id === id && (s.questionCount || 0) > 0,
                  ),
                  verified =
                    exam.strictEligible || exam.scopedEligibility?.[id];
                return (
                  <td key={id}>
                    <button
                      className={`matrix-cell ${state}`}
                      onClick={() => choose(exam, id)}
                      disabled={!available}
                    >
                      <Icon
                        name={complete ? "check" : active ? "clock" : "play"}
                      />
                      <span>
                        {complete
                          ? tr("Completed", "已完成")
                          : active
                            ? tr("In progress", "练习中")
                            : attempts.length
                              ? tr("Previously practiced", "做过专项")
                              : tr("Not started", "未开始")}
                        <small>
                          {available
                            ? verified
                              ? tr("Timed practice", "计时练习")
                              : tr("Guided only", "辅助练习")
                            : tr("Reference only", "资料参考")}
                        </small>
                      </span>
                    </button>
                  </td>
                );
              })}
              <td>
                <Button
                  kind={exam.strictEligible ? "primary small" : "outline small"}
                  onClick={() => choose(exam)}
                >
                  {exam.strictEligible
                    ? tr("Start test", "开始模考")
                    : tr("View options", "查看选项")}
                  <Icon name="arrow" />
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
export function Library({ materials }: { materials: Material[] }) {
  useI18n();
  const [query, setQuery] = useState(""),
    [kind, setKind] = useState("all");
  const files = materials.filter(
    (m) =>
      (kind === "all" || m.kind === kind) &&
      `${m.name} ${m.category}`.toLowerCase().includes(query.toLowerCase()),
  );
  return (
    <>
      <Heading
        title={tr("Your resource library", "你的资料，都在这里。")}
        subtitle={tr(
          "Browse original questions, audio, transcripts, and rubrics. Resource access is locked during strict practice.",
          "原始资料完整保留。查阅试题、音频、原文与评分标准。严格模考进行中，资料访问暂时锁定。",
        )}
      />
      <div className="toolbar">
        <div className="search">
          <Icon name="search" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={tr(
              "Search files, tests, or folders…",
              "搜索文件名、套题或目录…",
            )}
            aria-label={tr("Search resources", "搜索资料")}
          />
        </div>
        <select
          className="select"
          value={kind}
          onChange={(e) => setKind(e.target.value)}
          aria-label={tr("Resource type", "资料类型")}
        >
          <option value="all">{tr("All file types", "全部文件类型")}</option>
          {[...new Set(materials.map((m) => m.kind))].sort().map((k) => (
            <option key={k} value={k}>
              {k.toUpperCase()}
            </option>
          ))}
        </select>
        <span className="muted" style={{ fontSize: 11 }}>
          {files.length} {tr("resources", "份资料")}{" "}
        </span>
      </div>
      <div className="material-list">
        {files.map((m) => (
          <article className="material-row" key={m.id}>
            <div className="file-icon">
              <Icon
                name={
                  m.kind === "audio"
                    ? "headphones"
                    : m.kind === "video"
                      ? "play"
                      : "file"
                }
              />
            </div>
            <div className="file-info">
              <h3>{m.name}</h3>
              <p>{m.category}</p>
            </div>
            {m.supplemental && (
              <span className="pill amber">
                {tr("Supplemental", "补充资料")}
              </span>
            )}
            <span className="file-meta">{size(m.bytes)}</span>
            <a
              href={m.url}
              target="_blank"
              rel="noopener"
              className="btn small outline"
            >
              {" "}
              {tr("Open", "打开")} <Icon name="external" />
            </a>
          </article>
        ))}
      </div>
      {!files.length && (
        <Empty>{tr("No matching resources.", "没有找到匹配的资料。")}</Empty>
      )}
    </>
  );
}
export function History({
  sessions,
  open,
}: {
  sessions: SessionSummary[];
  open: (s: SessionSummary) => void;
}) {
  const { locale } = useI18n();
  return (
    <>
      <Heading
        title={tr("Your practice history", "把练习，变成看得见的积累。")}
        subtitle={tr(
          "Continue a session or review answers, essays, and recordings. Your history stays on this computer.",
          "继续未完成的练习，或回顾错题、写作与口语录音。所有记录只保存在本机。",
        )}
      />
      {sessions.length ? (
        sessions.map((s) => (
          <article className="attempt-row" key={s.id}>
            <div className="attempt-icon">
              <Icon name={s.status === "completed" ? "check" : "clock"} />
            </div>
            <div className="info">
              <h3>{localizeDynamic(s.title)}</h3>
              {s.practiceGroup && (
                <p>
                  {localizeDynamic(s.practiceGroup.module)} ·{" "}
                  {taskName(s.practiceGroup.taskType, locale)} ·{" "}
                  {tr("{count} items", "{count} 道小题", {
                    count: s.practiceGroup.itemCount,
                  })}
                  {s.practiceGroup.numberStart != null &&
                    ` · ${s.practiceGroup.numberStart}${s.practiceGroup.numberEnd != null && s.practiceGroup.numberEnd !== s.practiceGroup.numberStart ? `–${s.practiceGroup.numberEnd}` : ""}`}
                </p>
              )}
              <p>
                {date(s.startedAt)} ·{" "}
                {s.mode === "strict"
                  ? tr("Strict timing", "严格计时")
                  : tr("Guided practice", "专项练习")}{" "}
                · {s.scope === "all" ? tr("Full test", "完整流程") : s.scope}{" "}
                {s.integrity?.interrupted || s.interrupted
                  ? tr("· Interrupted", "· 含中断")
                  : ""}
              </p>
            </div>
            <span
              className={`pill ${s.status === "completed" ? "teal" : "amber"}`}
            >
              {s.status === "active"
                ? tr("Active", "进行中")
                : s.status === "completed"
                  ? tr("Completed", "已完成")
                  : tr("Ended early", "提前结束")}
            </span>
            <Button kind="outline small" onClick={() => open(s)}>
              {s.status === "active"
                ? s.canRecoverAudio
                  ? tr("Restore listening audio", "恢复听力音频")
                  : tr("Continue practice", "继续练习")
                : tr("Review session", "查看复盘")}
              <Icon name="arrow" />
            </Button>
          </article>
        ))
      ) : (
        <Empty icon="chart">
          {" "}
          {tr("No practice sessions yet.", "还没有练习记录。")} <br />{" "}
          {tr(
            "Complete your first practice to see it here.",
            "完成第一场练习，让进步留下痕迹。",
          )}{" "}
        </Empty>
      )}
    </>
  );
}
