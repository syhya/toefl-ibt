import { useI18n, localizeDynamic } from "./i18n";
import { useEffect, useState } from "react";
import { api, date, sectionLabel, ORDER, taskName } from "./api";
import { Button, Empty, Heading, Notice } from "./components";
import type { SectionId } from "./types";

export type Mistake = {
  mistakeId: string;
  questionId: string;
  examId: string;
  examTitle: string;
  section: SectionId;
  taskType: string;
  number?: number;
  title: string;
  sourcePage?: number;
  wrongAttempts: number;
  attempts: number;
  lastAttemptAt: number | string;
  lastSessionId: string;
  lastWrongSessionId?: string;
  lastGrade: { correct: number; total: number };
  status: "needs_review" | "mastered";
  available: boolean;
  unavailableReason?: string | null;
};
type Listing = {
  items: Mistake[];
  total: number;
  page: number;
  pageSize: number;
  summary: {
    total: number;
    needsReview: number;
    mastered: number;
    attempts: number;
  };
};

export default function Mistakes({
  practice,
  review,
}: {
  practice: (item: Mistake) => void;
  review: (sessionId: string) => void;
}) {
  const { t, locale } = useI18n();
  const [section, setSection] = useState("all"),
    [status, setStatus] = useState("needs_review"),
    [query, setQuery] = useState(""),
    [page, setPage] = useState(1),
    [data, setData] = useState<Listing | null>(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    const timer = setTimeout(() => {
      const params = new URLSearchParams({
        section,
        status,
        q: query,
        page: String(page),
        pageSize: "24",
      });
      api<Listing>(`/api/mistakes?${params}`, { signal: controller.signal })
        .then(setData)
        .catch((error) => {
          if (!controller.signal.aborted) {
            setError(error.message);
            setData(null);
          }
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
  }, [section, status, query, page]);
  return (
    <>
      <Heading
        title={t("Mistakes", "错题集")}
        subtitle={t(
          "Review mistakes collected from your local sessions. A correct retry marks an item as mastered while preserving earlier attempts.",
          "从本机历次作答自动汇总，按原题复习。再次答对会标为已掌握，原记录继续保留。",
        )}
      />
      <div className="mistake-summary">
        <div>
          <strong>
            {data?.summary.needsReview.toLocaleString(locale) ?? "—"}
          </strong>
          <span>{t("Needs review", "待复习")}</span>
        </div>
        <div>
          <strong>
            {data?.summary.mastered.toLocaleString(locale) ?? "—"}
          </strong>
          <span>{t("Mastered", "已掌握")}</span>
        </div>
        <div>
          <strong>
            {data?.summary.attempts.toLocaleString(locale) ?? "—"}
          </strong>
          <span>{t("Related attempts", "相关作答次数")}</span>
        </div>
      </div>
      <div className="drill-filter-panel">
        <div
          className="filter-row"
          aria-label={t("Mistake section", "错题部分")}
        >
          {["all", ...ORDER].map((id) => (
            <button
              key={id}
              className={`filter-pill ${section === id ? "active" : ""}`}
              onClick={() => {
                setSection(id);
                setPage(1);
              }}
            >
              {id === "all"
                ? t("All sections", "全部部分")
                : sectionLabel(id as SectionId, locale)}
            </button>
          ))}
        </div>
        <div className="filter-row">
          {[
            ["needs_review", t("Needs review", "待复习")],
            ["mastered", t("Mastered", "已掌握")],
            ["all", t("All records", "全部记录")],
          ].map(([id, label]) => (
            <button
              key={id}
              className={`filter-pill ${status === id ? "active" : ""}`}
              onClick={() => {
                setStatus(id);
                setPage(1);
              }}
            >
              {label}
            </button>
          ))}
          <input
            className="mistake-search"
            aria-label={t("Search mistakes", "搜索错题")}
            placeholder={t(
              "Search source tests, task types, or question numbers\u2026",
              "搜索原卷、题型或题号…",
            )}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setPage(1);
            }}
          />
        </div>
      </div>
      {error ? (
        <Notice>{localizeDynamic(error, locale)}</Notice>
      ) : loading ? (
        <p role="status">
          {t("Loading local mistake records\u2026", "正在读取本地错题记录…")}
        </p>
      ) : !data?.items.length ? (
        <Empty icon="check">
          {status === "mastered"
            ? t(
                "Items you answer correctly on a later attempt appear here.",
                "再次答对的错题会保存在这里。",
              )
            : t(
                "No matching mistakes. After you finish a session, objective questions you attempted but answered incorrectly are added automatically.",
                "当前没有符合条件的错题。完成练习后，已作答且未答对的客观题会自动收录。",
              )}
        </Empty>
      ) : (
        <div className="mistake-list">
          {data.items.map((item) => (
            <article className="mistake-card" key={item.mistakeId}>
              <div className="mistake-description">
                <span
                  className={`pill ${item.status === "mastered" ? "green" : "amber"}`}
                >
                  {item.status === "mastered"
                    ? t("Mastered", "已掌握")
                    : t("Needs review", "待复习")}
                </span>
                <h2>
                  {localizeDynamic(item.examTitle, locale)} ·{" "}
                  {sectionLabel(item.section, locale)}
                  {item.number
                    ? t(" · Question {number}", " · 第 {number} 题", {
                        number: item.number,
                      })
                    : ""}
                </h2>
                <p>
                  {taskName(item.taskType, locale)} ·{" "}
                  {t(
                    "{wrong} incorrect / {attempts} attempts · Latest {correct}/{total}",
                    "错误 {wrong} 次 / 作答 {attempts} 次 · 最近 {correct}/{total}",
                    {
                      wrong: item.wrongAttempts,
                      attempts: item.attempts,
                      correct: item.lastGrade.correct,
                      total: item.lastGrade.total,
                    },
                  )}
                </p>
                <small>
                  {date(item.lastAttemptAt, locale)}
                  {item.sourcePage
                    ? t(
                        " · Original PDF page {page}",
                        " · 原 PDF 第 {page} 页",
                        { page: item.sourcePage },
                      )
                    : ""}
                </small>
                {!item.available && (
                  <p className="mistake-unavailable">
                    {t(
                      "The question version has changed or its source needs verification; previous answers and reviews are still available.",
                      "原题版本已变更或来源待核验；旧作答与复盘仍保留。",
                    )}
                  </p>
                )}
              </div>
              <div className="mistake-actions">
                <Button
                  kind="outline small"
                  onClick={() =>
                    review(item.lastWrongSessionId || item.lastSessionId)
                  }
                >
                  {t("Review this mistake", "查看错题复盘")}
                </Button>
                <Button
                  kind="small"
                  disabled={!item.available}
                  onClick={() => practice(item)}
                >
                  {t("Retry the original question", "重新练习原题")}
                </Button>
              </div>
            </article>
          ))}
        </div>
      )}
      {!!data?.total && (
        <div className="mistake-pagination">
          <Button
            kind="outline small"
            disabled={page === 1 || loading}
            onClick={() => setPage(page - 1)}
          >
            {t("Previous page", "上一页")}
          </Button>
          <span>
            {t(
              "Page {page} / {pages} · {count} items",
              "第 {page} / {pages} 页 · {count} 道",
              {
                page,
                pages: Math.ceil(data.total / data.pageSize),
                count: data.total.toLocaleString(locale),
              },
            )}
          </span>
          <Button
            kind="outline small"
            disabled={page * data.pageSize >= data.total || loading}
            onClick={() => setPage(page + 1)}
          >
            {t("Next page", "下一页")}
          </Button>
        </div>
      )}
      <p className="mistake-note">
        {t(
          "Only attempted questions with verifiable results are included. Unanswered items and questions without reliable keys are not treated as mistakes. Essays, Speaking responses, and rubric self-assessments are stored in Practice history.",
          "只收录有可核验评分结果的实际作答；未答题和无可靠答案的题目不会伪判为错题。作文、口语回答与量表自评保存在“练习记录”中。",
        )}
      </p>
    </>
  );
}
