import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { api, date, post } from "./api";
import { Button, Empty, Heading } from "./components";
import Icon from "./Icons";
import { localizeDynamic, useI18n } from "./i18n";
import "./vocabulary.css";

export type VocabularyDraft = {
  word: string;
  meaning?: string;
  context?: string;
  sourceLabel?: string;
  sourceQuestionId?: string;
  sourceSessionId?: string;
};

export type VocabularyEntry = {
  id: string;
  word: string;
  meaning: string;
  context: string;
  sourceLabel: string;
  sourceQuestionId?: string;
  sourceSessionId?: string;
  status: "learning" | "mastered";
  createdAt: string | number;
  updatedAt: string | number;
};

type Listing = {
  items: VocabularyEntry[];
  total: number;
  page: number;
  pageSize: number;
  summary: { learning: number; mastered: number };
};
type NoticeHandler = (message: string) => void;

function DialogFrame({
  title,
  children,
  actions,
  onClose,
  busy = false,
}: {
  title: string;
  children: ReactNode;
  actions: ReactNode;
  onClose: () => void;
  busy?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const opener = document.activeElement;
    const dialog = ref.current;
    dialog?.showModal();
    dialog?.querySelector<HTMLElement>("[data-initial-focus]")?.focus();
    return () => {
      dialog?.close();
      if (opener instanceof HTMLElement && opener.isConnected) opener.focus();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className="vocabulary-dialog"
      aria-labelledby={titleId}
      aria-busy={busy}
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onClose();
      }}
    >
      <div className="dialog-content">
        <h2 id={titleId}>{title}</h2>
        {children}
      </div>
      <div className="dialog-actions">{actions}</div>
    </dialog>
  );
}

export function VocabularyEntryDialog({
  draft,
  entry,
  onClose,
  onSaved,
  onNotice,
}: {
  draft?: VocabularyDraft;
  entry?: VocabularyEntry;
  onClose: () => void;
  onSaved?: (entry: VocabularyEntry, created: boolean) => void;
  onNotice?: NoticeHandler;
}) {
  const { t, locale } = useI18n();
  const initial = entry || draft;
  const [word, setWord] = useState(initial?.word || "");
  const [meaning, setMeaning] = useState(initial?.meaning || "");
  const [context, setContext] = useState(initial?.context || "");
  const [sourceLabel, setSourceLabel] = useState(initial?.sourceLabel || "");
  const [status, setStatus] = useState(entry?.status || "learning");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [wordError, setWordError] = useState(false);
  const wordRef = useRef<HTMLInputElement>(null);
  const savingRef = useRef(false);
  const formId = useId();
  const errorId = useId();

  async function save() {
    if (savingRef.current) return;
    if (!word.trim()) {
      setWordError(true);
      setError(t("Enter a word or phrase.", "请输入词语或短语。"));
      wordRef.current?.focus();
      return;
    }
    setError("");
    setWordError(false);
    savingRef.current = true;
    setSaving(true);
    try {
      const fields = {
        word: word.trim(),
        meaning: meaning.trim(),
        context: context.trim(),
      };
      const result = entry
        ? await api<{ entry: VocabularyEntry }>(
            `/api/vocabulary/${encodeURIComponent(entry.id)}`,
            {
              method: "PATCH",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ ...fields, status }),
            },
          )
        : await post<{ entry: VocabularyEntry; created: boolean }>(
            "/api/vocabulary",
            {
              ...fields,
              sourceLabel: sourceLabel.trim() || undefined,
              sourceQuestionId: draft?.sourceQuestionId,
              sourceSessionId: draft?.sourceSessionId,
            },
          );
      const created = "created" in result && result.created === true;
      onNotice?.(
        entry
          ? t("Vocabulary entry updated.", "词条已更新。")
          : created
            ? t("Added to your vocabulary.", "已加入单词本。")
            : t(
                "This word is already in your vocabulary. Your existing entry was kept.",
                "该词已在单词本中，原有词条已保留。",
              ),
      );
      onSaved?.(result.entry, created);
      onClose();
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : t("Could not save this word. Try again.", "保存失败，请重试。"),
      );
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  }

  return (
    <DialogFrame
      title={entry ? t("Edit word", "编辑词条") : t("Add a word", "新增生词")}
      busy={saving}
      onClose={onClose}
      actions={
        <>
          <Button kind="outline" disabled={saving} onClick={onClose}>
            {t("Cancel", "取消")}
          </Button>
          <Button type="submit" form={formId} disabled={saving}>
            {saving
              ? t("Saving…", "正在保存…")
              : entry
                ? t("Save changes", "保存修改")
                : t("Add to vocabulary", "加入单词本")}
          </Button>
        </>
      }
    >
      <p>
        {t(
          "Keep a word with its meaning and the sentence where you found it.",
          "记下生词、释义和遇到它的原句，方便回顾。",
        )}
      </p>
      <form
        id={formId}
        className="vocabulary-form"
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        <label className="field">
          <span>{t("Word or phrase (required)", "词语或短语（必填）")}</span>
          <input
            ref={wordRef}
            data-initial-focus
            name="word"
            value={word}
            required
            maxLength={120}
            disabled={saving}
            aria-invalid={wordError}
            aria-describedby={wordError ? errorId : undefined}
            autoComplete="off"
            onChange={(event) => {
              setWord(event.target.value);
              setWordError(false);
            }}
          />
        </label>
        <label className="field">
          <span>{t("Meaning (optional)", "释义（选填）")}</span>
          <textarea
            name="meaning"
            rows={2}
            maxLength={2000}
            value={meaning}
            disabled={saving}
            onChange={(event) => setMeaning(event.target.value)}
          />
        </label>
        <label className="field">
          <span>{t("Context (optional)", "上下文（选填）")}</span>
          <textarea
            name="context"
            rows={3}
            maxLength={4000}
            value={context}
            disabled={saving}
            onChange={(event) => setContext(event.target.value)}
          />
        </label>
        <label className="field">
          <span>{t("Source (optional)", "来源（选填）")}</span>
          <input
            name="sourceLabel"
            value={sourceLabel}
            maxLength={240}
            readOnly={!!entry}
            disabled={saving}
            placeholder={t(
              "For example, Reading · Question 3",
              "例如：阅读 · 第 3 题",
            )}
            onChange={(event) => setSourceLabel(event.target.value)}
          />
          {!!entry && (
            <small>
              {t("The original source is preserved.", "保留最初收录时的来源。")}
            </small>
          )}
        </label>
        {!!entry && (
          <label className="field">
            <span>{t("Learning status", "学习状态")}</span>
            <select
              name="status"
              value={status}
              disabled={saving}
              onChange={(event) =>
                setStatus(event.target.value as VocabularyEntry["status"])
              }
            >
              <option value="learning">{t("Learning", "学习中")}</option>
              <option value="mastered">{t("Mastered", "已掌握")}</option>
            </select>
          </label>
        )}
        {error && (
          <div className="vocabulary-error" role="alert" id={errorId}>
            {localizeDynamic(error, locale)}
          </div>
        )}
      </form>
    </DialogFrame>
  );
}

export default function VocabularyPage({
  onNotice,
}: {
  onNotice?: NoticeHandler;
}) {
  const { t, locale } = useI18n();
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<"all" | VocabularyEntry["status"]>(
    "all",
  );
  const [page, setPage] = useState(1);
  const [revision, setRevision] = useState(0);
  const [data, setData] = useState<Listing | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");
  const [notice, setNotice] = useState("");
  const [editor, setEditor] = useState<VocabularyEntry | "new" | null>(null);
  const [deleting, setDeleting] = useState<VocabularyEntry | null>(null);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const mutationRef = useRef(false);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    const timer = setTimeout(() => {
      const params = new URLSearchParams({
        q: query,
        status,
        page: String(page),
        pageSize: "24",
      });
      api<Listing>(`/api/vocabulary?${params}`, { signal: controller.signal })
        .then((listing) => {
          if (controller.signal.aborted) return;
          const lastPage = Math.max(
            1,
            Math.ceil(listing.total / listing.pageSize),
          );
          if (page > lastPage) {
            setPage(lastPage);
            return;
          }
          setData(listing);
          setLoading(false);
        })
        .catch((cause) => {
          if (controller.signal.aborted) return;
          setData(null);
          setError(
            cause instanceof Error
              ? cause.message
              : t("Could not load your vocabulary.", "读取单词本失败。"),
          );
          setLoading(false);
        });
    }, 150);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query, status, page, revision]);

  function refresh() {
    setLoading(true);
    setRevision((value) => value + 1);
  }

  function reportNotice(message: string) {
    setNotice(message);
    onNotice?.(message);
  }

  async function mutate(entry: VocabularyEntry, remove: boolean) {
    if (mutationRef.current) return;
    mutationRef.current = true;
    setPendingId(entry.id);
    setActionError("");
    setNotice("");
    try {
      await api(`/api/vocabulary/${encodeURIComponent(entry.id)}`, {
        method: remove ? "DELETE" : "PATCH",
        ...(remove
          ? {}
          : {
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                status: entry.status === "learning" ? "mastered" : "learning",
              }),
            }),
      });
      setDeleting(null);
      reportNotice(
        remove
          ? t("Word removed from your vocabulary.", "已从单词本删除。")
          : t("Learning status updated.", "学习状态已更新。"),
      );
      refresh();
    } catch (cause) {
      setActionError(
        cause instanceof Error
          ? cause.message
          : t("Could not update this word. Try again.", "更新失败，请重试。"),
      );
    } finally {
      mutationRef.current = false;
      setPendingId(null);
    }
  }

  return (
    <section className="vocabulary-page">
      <Heading
        title={t("Vocabulary", "单词本")}
        subtitle={t(
          "Collect useful words from practice and revisit them in context.",
          "收集练习中的生词，结合原句反复回顾。",
        )}
        action={
          <Button onClick={() => setEditor("new")} disabled={!!pendingId}>
            <Icon name="book" /> {t("Add a word", "新增生词")}
          </Button>
        }
      />
      <div className="vocabulary-summary">
        <div>
          <strong>
            {data?.summary.learning.toLocaleString(locale) ?? "—"}
          </strong>
          <span>{t("Words learning", "学习中的词语")}</span>
        </div>
        <div>
          <strong>
            {data?.summary.mastered.toLocaleString(locale) ?? "—"}
          </strong>
          <span>{t("Words mastered", "已掌握的词语")}</span>
        </div>
      </div>
      <div className="vocabulary-toolbar">
        <div
          className="filter-row"
          role="group"
          aria-label={t("Vocabulary status", "词条状态")}
        >
          {(["all", "learning", "mastered"] as const).map((value) => (
            <button
              type="button"
              key={value}
              className={`filter-pill ${status === value ? "active" : ""}`}
              aria-pressed={status === value}
              onClick={() => {
                setStatus(value);
                setPage(1);
              }}
            >
              {value === "all"
                ? t("All words", "全部词语")
                : value === "learning"
                  ? t("Learning", "学习中")
                  : t("Mastered", "已掌握")}
            </button>
          ))}
        </div>
        <label className="vocabulary-search">
          <Icon name="search" />
          <input
            type="search"
            maxLength={200}
            aria-label={t("Search vocabulary", "搜索单词本")}
            placeholder={t(
              "Search words, meanings, or context…",
              "搜索词语、释义或上下文…",
            )}
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setPage(1);
            }}
          />
        </label>
      </div>
      {notice && (
        <p className="vocabulary-notice" role="status">
          {localizeDynamic(notice, locale)}
        </p>
      )}
      {actionError && !deleting && (
        <div className="vocabulary-error" role="alert">
          {localizeDynamic(actionError, locale)}
        </div>
      )}
      {error ? (
        <div className="vocabulary-error" role="alert">
          <span>{localizeDynamic(error, locale)}</span>
          <Button kind="outline small" onClick={refresh}>
            {t("Try again", "重试")}
          </Button>
        </div>
      ) : loading ? (
        <p role="status">{t("Loading your vocabulary…", "正在读取单词本…")}</p>
      ) : !data?.items.length ? (
        <Empty icon="book">
          {query || status !== "all"
            ? t(
                "No matching words. Try another search or filter.",
                "没有匹配的词语，请尝试其他关键词或筛选条件。",
              )
            : t(
                "Your vocabulary is empty. Add your first word here or save one while reviewing a session.",
                "单词本还是空的。点击“新增生词”，或在练习复盘时收藏词语。",
              )}
        </Empty>
      ) : (
        <div className="vocabulary-grid">
          {data.items.map((entry) => (
            <article className="vocabulary-card" key={entry.id}>
              <div className="vocabulary-card-heading">
                <h2>
                  <bdi>{entry.word}</bdi>
                </h2>
                <span
                  className={`pill ${entry.status === "mastered" ? "green" : "amber"}`}
                >
                  {entry.status === "mastered"
                    ? t("Mastered", "已掌握")
                    : t("Learning", "学习中")}
                </span>
              </div>
              <p
                className={`vocabulary-meaning ${entry.meaning ? "" : "vocabulary-unfilled"}`}
              >
                {entry.meaning ||
                  t(
                    "Add a meaning when you review this word.",
                    "复习时可以补充释义。",
                  )}
              </p>
              {entry.context && (
                <blockquote className="vocabulary-context">
                  {entry.context}
                </blockquote>
              )}
              <div className="vocabulary-source">
                <Icon name="bookmark" />
                <span>
                  {entry.sourceLabel || t("Added manually", "手动添加")}
                </span>
              </div>
              <small className="vocabulary-date">
                {t("Added {date}", "收录于 {date}", {
                  date: date(entry.createdAt, locale),
                })}
              </small>
              <div className="vocabulary-card-actions">
                <Button
                  kind="outline small"
                  disabled={!!pendingId}
                  onClick={() => void mutate(entry, false)}
                >
                  <Icon name={entry.status === "learning" ? "check" : "undo"} />
                  {pendingId === entry.id
                    ? t("Saving…", "正在保存…")
                    : entry.status === "learning"
                      ? t("Mark mastered", "标为已掌握")
                      : t("Keep learning", "继续学习")}
                </Button>
                <button
                  className="vocabulary-text-action"
                  type="button"
                  disabled={!!pendingId}
                  onClick={() => setEditor(entry)}
                >
                  {t("Edit", "编辑")}
                </button>
                <button
                  className="vocabulary-text-action vocabulary-remove"
                  type="button"
                  disabled={!!pendingId}
                  onClick={() => {
                    setActionError("");
                    setDeleting(entry);
                  }}
                >
                  {t("Delete", "删除")}
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
      {!error && !!data?.total && (
        <div className="vocabulary-pagination">
          <Button
            kind="outline small"
            disabled={page === 1 || loading}
            onClick={() => setPage((value) => value - 1)}
          >
            {t("Previous page", "上一页")}
          </Button>
          <span>
            {t(
              "Page {page} / {pages} · {count} words",
              "第 {page} / {pages} 页 · {count} 个词语",
              {
                page,
                pages: Math.max(1, Math.ceil(data.total / data.pageSize)),
                count: data.total.toLocaleString(locale),
              },
            )}
          </span>
          <Button
            kind="outline small"
            disabled={page * data.pageSize >= data.total || loading}
            onClick={() => setPage((value) => value + 1)}
          >
            {t("Next page", "下一页")}
          </Button>
        </div>
      )}
      {editor && (
        <VocabularyEntryDialog
          entry={editor === "new" ? undefined : editor}
          onClose={() => setEditor(null)}
          onNotice={reportNotice}
          onSaved={(_entry, created) => {
            setActionError("");
            if (created) {
              setPage(1);
              setStatus("all");
              setQuery("");
            }
            refresh();
          }}
        />
      )}
      {deleting && (
        <DialogFrame
          title={t("Delete this word?", "删除这个词条？")}
          busy={!!pendingId}
          onClose={() => {
            setDeleting(null);
            setActionError("");
          }}
          actions={
            <>
              <Button
                kind="outline"
                data-initial-focus
                disabled={!!pendingId}
                onClick={() => {
                  setDeleting(null);
                  setActionError("");
                }}
              >
                {t("Cancel", "取消")}
              </Button>
              <Button
                kind="vocabulary-danger"
                disabled={!!pendingId}
                onClick={() => void mutate(deleting, true)}
              >
                {pendingId
                  ? t("Deleting…", "正在删除…")
                  : t("Delete word", "删除词条")}
              </Button>
            </>
          }
        >
          <p>
            {t(
              "“{word}” and its saved meaning and context will be removed from your vocabulary.",
              "将从单词本移除“{word}”及其释义、上下文。",
              { word: deleting.word },
            )}
          </p>
          {actionError && (
            <div className="vocabulary-error" role="alert">
              {localizeDynamic(actionError, locale)}
            </div>
          )}
        </DialogFrame>
      )}
    </section>
  );
}
