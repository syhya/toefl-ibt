import { useI18n, localizeDynamic } from "./i18n";
import { useEffect, useState } from "react";
import { api, sectionLabel, ORDER, taskName } from "./api";
import { Button, Empty, Heading, Notice } from "./components";
import Icon, { sectionIcon } from "./Icons";
import type { SectionId } from "./types";

export type QuestionItem = {
  questionId: string;
  examId: string;
  examTitle: string;
  section: SectionId;
  module: string;
  moduleId?: string;
  title: string;
  taskType: string;
  number?: number;
  sourcePage?: number;
  auditStatus?: string;
  hasAudio: boolean;
  status: "not_started" | "in_progress" | "completed";
  contentId: string;
  duplicateCount: number;
};
type Listing = {
  items: QuestionItem[];
  total: number;
  page: number;
  pageSize: number;
  taskCounts?: Record<string, number>;
};
const TASKS: Record<SectionId, string[]> = {
  reading: ["cloze", "daily_life", "academic_passage"],
  listening: [
    "listen_response",
    "conversation",
    "announcement",
    "academic_talk",
  ],
  writing: ["build_sentence", "email", "academic_discussion"],
  speaking: ["listen_repeat", "interview"],
};
export default function QuestionLibrary({
  practice,
}: {
  practice: (item: QuestionItem) => void;
}) {
  const { t, locale } = useI18n();
  const [section, setSection] = useState<SectionId>("reading"),
    [task, setTask] = useState("all"),
    [query, setQuery] = useState(""),
    [dedupe, setDedupe] = useState(false),
    [page, setPage] = useState(1),
    [data, setData] = useState<Listing | null>(null),
    [loading, setLoading] = useState(true),
    [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    const timer = setTimeout(() => {
      const params = new URLSearchParams({
        section,
        page: String(page),
        pageSize: "18",
        deduplicate: String(dedupe),
      });
      if (task !== "all") params.set("taskType", task);
      if (query) params.set("q", query);
      api<Listing>(`/api/questions?${params}`, { signal: controller.signal })
        .then(setData)
        .catch((error) => {
          if (!controller.signal.aborted) setError(error.message);
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, 150);
    // Abort superseded searches so a slower response cannot replace the current filter results.
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [section, task, query, dedupe, page]);
  const pages = Math.max(1, Math.ceil((data?.total || 0) / 18));
  return (
    <>
      <Heading
        title={t("One task type at a time.", "一次专注，一种题型。")}
        subtitle={t(
          "Find individual exercises by section, task type, and keyword. Every item retains its source test and audit information.",
          "把整套资料拆成清晰的练习入口。按部分、题型和关键词定位，每道题保留原卷与审核信息。",
        )}
      />
      <div
        className="subject-tabs"
        role="tablist"
        aria-label={t("Practice section", "练习部分")}
      >
        {ORDER.map((id) => (
          <button
            key={id}
            role="tab"
            aria-selected={section === id}
            className={section === id ? "active" : ""}
            onClick={() => {
              setSection(id);
              setTask("all");
              setPage(1);
            }}
          >
            <Icon name={sectionIcon(id)} />
            {sectionLabel(id, locale)}
            <small>{t("Practice", "专项练习")}</small>
          </button>
        ))}
      </div>
      <div className="drill-filter-panel">
        <div className="filter-row">
          <span>{t("Task type", "题型")}</span>
          <button
            className={`filter-pill ${task === "all" ? "active" : ""}`}
            onClick={() => {
              setTask("all");
              setPage(1);
            }}
          >
            {t("All", "全部")}
          </button>
          {TASKS[section].map((id) => (
            <button
              key={id}
              className={`filter-pill ${task === id ? "active" : ""}`}
              onClick={() => {
                setTask(id);
                setPage(1);
              }}
            >
              {taskName(id, locale)}
            </button>
          ))}
        </div>
        <div className="filter-row">
          <span>{t("Search", "搜索")}</span>
          <div className="search">
            <Icon name="search" />
            <input
              aria-label={t("Search practice questions", "搜索专项题目")}
              placeholder={t(
                "Search tests, questions, or topics\u2026",
                "搜索套题、题目或主题…",
              )}
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setPage(1);
              }}
            />
          </div>
          <label className="dedupe-check">
            <input
              type="checkbox"
              checked={dedupe}
              onChange={(e) => {
                setDedupe(e.target.checked);
                setPage(1);
              }}
            />
            {t("Combine duplicate content", "合并重复内容")}
          </label>
        </div>
      </div>
      <div className="section-heading">
        <h2>
          {sectionLabel(section, locale)}{" "}
          <span>
            {t("{count} practice entries", "{count} 个练习入口", {
              count: (data?.total || 0).toLocaleString(locale),
            })}
          </span>
        </h2>
        <div className="status-legend">
          <span>
            <i />
            {t("Not started", "未开始")}
          </span>
          <span>
            <i />
            {t("In progress", "练习中")}
          </span>
          <span>
            <i />
            {t("Completed", "已完成")}
          </span>
        </div>
      </div>
      {error ? (
        <div className="panel">
          <p className="error-message">{localizeDynamic(error, locale)}</p>
          <p>
            {t(
              "The question library and answer access are locked during a strict mock test. Continue or end the current mock test first.",
              "严格模考进行中会锁定专项题库与答案入口。请先继续或结束当前模考。",
            )}
          </p>
        </div>
      ) : (
        <div className={`drill-grid ${loading ? "loading-grid" : ""}`}>
          {data?.items.map((item) => (
            <article className="drill-card" key={item.questionId}>
              <div className="drill-top">
                <span>{taskName(item.taskType, locale)}</span>
                <span className={`practice-state ${item.status}`}>
                  {{
                    not_started: t("Not started", "未开始"),
                    in_progress: t("In progress", "练习中"),
                    completed: t("Completed", "已完成"),
                  }[item.status] || t("Not started", "未开始")}
                </span>
              </div>
              <h3>{localizeDynamic(item.title, locale)}</h3>
              <p>
                {localizeDynamic(item.examTitle, locale)} ·{" "}
                {localizeDynamic(item.module, locale)}
                {item.sourcePage ? ` · p.${item.sourcePage}` : ""}
              </p>
              <div className="drill-tags">
                {item.hasAudio && (
                  <span className="pill teal">
                    <Icon name="headphones" />
                    {t("Audio included", "已配音频")}
                  </span>
                )}
                {item.duplicateCount > 1 && (
                  <span className="pill gray">
                    {t("Same item in {count} sources", "{count} 个来源含同题", {
                      count: item.duplicateCount,
                    })}
                  </span>
                )}
                <span className="pill gray">
                  {localizeDynamic(item.auditStatus, locale) ||
                    t("Source available", "来源可查")}
                </span>
              </div>
              <Button
                kind="outline"
                disabled={loading}
                onClick={() => practice(item)}
              >
                {t("Start practice", "开始专项练习")}
                <Icon name="arrow" />
              </Button>
            </article>
          ))}
        </div>
      )}
      {!loading && !error && !data?.items.length && (
        <Empty>
          {t(
            "No matching questions. Try another task type or keyword.",
            "没有匹配的题目。试试其他题型或关键词。",
          )}
        </Empty>
      )}
      <div className="pagination">
        <Button
          kind="outline small"
          disabled={page <= 1 || loading}
          onClick={() => setPage((p) => p - 1)}
        >
          <Icon name="back" />
          {t("Previous page", "上一页")}
        </Button>
        <span>
          {page} / {pages}
        </span>
        <Button
          kind="outline small"
          disabled={page >= pages || loading}
          onClick={() => setPage((p) => p + 1)}
        >
          {t("Next page", "下一页")}
          <Icon name="arrow" />
        </Button>
      </div>
      <Notice>
        {t(
          "Targeted practice allows pausing, audio replay, and instant checks. It does not count as a full strict mock test. Deduplication combines practice entries without changing source-test sequences; answer conflicts and missing media retain audit labels.",
          "专项练习可以暂停、重听与即时核对。它不会被当作一次完整严格模考。去重只合并练习入口，不改变原套题编排；答案冲突与缺失媒体始终保留审核标记。",
        )}
      </Notice>
    </>
  );
}
