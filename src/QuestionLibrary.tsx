import { useI18n, localizeDynamic, tr, type Locale } from "./i18n";
import { useEffect, useState } from "react";
import { api, sectionLabel, ORDER, taskName } from "./api";
import { Button, Empty, Heading, Notice } from "./components";
import Icon, { sectionIcon } from "./Icons";
import type { SectionId } from "./types";
import "./practice-groups.css";

// Individual identities remain available to the independent mistake workflow.
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
export type PracticeGroup = {
  groupId: string;
  examId: string;
  examTitle: string;
  section: SectionId;
  moduleId: string;
  module: string;
  route: "common" | "upper" | "lower";
  taskType: string;
  questionIds: string[];
  numberStart?: number;
  numberEnd?: number;
  screenCount: number;
  itemCount: number;
  completedCount: number;
  status: "not_started" | "in_progress" | "completed";
  hasAudio: boolean;
  audioCount: number;
  duplicateCount: number;
  groupContentId: string;
  sourcePages?: number[];
  sourceScreenCount?: number;
  unavailableCount?: number;
};
type Listing = {
  items: PracticeGroup[];
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
export function practiceGroupTaskName(value: string, locale: Locale) {
  const task = value.replace(/^essentials_/, "");
  const additional: Record<string, [string, string]> = {
    vocabulary: ["Vocabulary", "词汇"],
    read_a_text: ["Read a Text", "阅读短文"],
    true_false_not_stated: ["True, False, or Not Stated", "判断正误与未提及"],
    listen_and_reply: ["Listen and Reply", "听后回应"],
    listen_to_a_text: ["Listen to a Text", "听短文"],
    text_completion: ["Text Completion", "补全文本"],
    listening_mcq: ["Listening Questions", "听力选择题"],
  };
  if (additional[task]) return tr(...additional[task], {}, locale);
  const label = taskName(task, locale);
  return label === task
    ? task.replace(/_/g, " ").replace(/^./, (letter) => letter.toUpperCase())
    : label;
}

// Arrange complete server groups without filtering their individual members.
function arrange(groups: PracticeGroup[]) {
  const exams = new Map<
    string,
    {
      title: string;
      modules: Map<
        string,
        {
          title: string;
          route: PracticeGroup["route"];
          groups: PracticeGroup[];
        }
      >;
    }
  >();
  for (const group of groups) {
    if (!exams.has(group.examId))
      exams.set(group.examId, { title: group.examTitle, modules: new Map() });
    const exam = exams.get(group.examId)!;
    const key = `${group.section}:${group.moduleId}:${group.route}`;
    if (!exam.modules.has(key))
      exam.modules.set(key, {
        title: group.module,
        route: group.route,
        groups: [],
      });
    exam.modules.get(key)!.groups.push(group);
  }
  return [...exams];
}

export default function QuestionLibrary({
  practice,
}: {
  practice: (group: PracticeGroup) => void;
}) {
  const { t, locale } = useI18n();
  const [section, setSection] = useState<SectionId>("reading");
  const [task, setTask] = useState("all"),
    [query, setQuery] = useState("");
  const [dedupe, setDedupe] = useState(false),
    [page, setPage] = useState(1);
  const [data, setData] = useState<Listing | null>(null),
    [loading, setLoading] = useState(true);
  const [error, setError] = useState(""),
    [revision, setRevision] = useState(0);
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
      api<Listing>(`/api/practice-groups?${params}`, {
        signal: controller.signal,
      })
        .then((listing) => {
          if (controller.signal.aborted) return;
          const last = Math.max(1, Math.ceil(listing.total / listing.pageSize));
          if (page > last) {
            setPage(last);
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
              : t("Could not load practice groups.", "读取专项题组失败。"),
          );
          setLoading(false);
        });
    }, 150);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [section, task, query, dedupe, page, revision]);
  const pages = Math.max(
    1,
    Math.ceil((data?.total || 0) / (data?.pageSize || 18)),
  );
  const arranged = arrange(data?.items || []);
  const availableTasks = [
    ...new Set([...TASKS[section], ...Object.keys(data?.taskCounts || {})]),
  ];
  const statusLabel = (status: PracticeGroup["status"]) =>
    ({
      not_started: t("Not started", "未开始"),
      in_progress: t("In progress", "练习中"),
      completed: t("Completed", "已完成"),
    })[status];
  const groupRange = (group: PracticeGroup, index: number) =>
    group.numberStart != null
      ? group.numberEnd != null && group.numberEnd !== group.numberStart
        ? t("Questions {start}–{end}", "第 {start}–{end} 题", {
            start: group.numberStart,
            end: group.numberEnd,
          })
        : t("Question {number}", "第 {number} 题", {
            number: group.numberStart,
          })
      : t("Group {number}", "第 {number} 组", { number: index + 1 });
  return (
    <div className="practice-group-library">
      <Heading
        title={t("One task type at a time.", "一次专注，一种题型。")}
        subtitle={t(
          "Practice available questions as source task groups, in their original order.",
          "按原卷模块和题型成组练习，保留可用题目的原始顺序。",
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
        <div
          className="filter-row"
          role="group"
          aria-label={t("Task type", "题型")}
        >
          <span>{t("Task type", "题型")}</span>
          {["all", ...availableTasks].map((id) => (
            <button
              key={id}
              className={`filter-pill ${task === id ? "active" : ""}`}
              aria-pressed={task === id}
              onClick={() => {
                setTask(id);
                setPage(1);
              }}
            >
              {id === "all"
                ? t("All", "全部")
                : practiceGroupTaskName(id, locale)}
            </button>
          ))}
        </div>
        <div className="filter-row">
          <span>{t("Search", "搜索")}</span>
          <div className="search">
            <Icon name="search" />
            <input
              type="search"
              maxLength={200}
              aria-label={t("Search practice groups", "搜索专项题组")}
              placeholder={t(
                "Search source tests, modules, or topics…",
                "搜索原卷、模块或主题…",
              )}
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setPage(1);
              }}
            />
          </div>
          <label className="dedupe-check">
            <input
              type="checkbox"
              checked={dedupe}
              onChange={(event) => {
                setDedupe(event.target.checked);
                setPage(1);
              }}
            />
            {t("Combine duplicate groups", "合并重复题组")}
          </label>
        </div>
      </div>
      <div className="practice-group-overview">
        <h2>
          {sectionLabel(section, locale)}{" "}
          <span>
            {t("{count} practice groups", "{count} 个专项题组", {
              count: (data?.total || 0).toLocaleString(locale),
            })}
          </span>
        </h2>
        <p>
          {t(
            "Choose a group, then review its practice settings.",
            "选择题组后，在开始前确认练习设置。",
          )}
        </p>
      </div>
      {error ? (
        <div className="panel" role="alert">
          <p className="error-message">{localizeDynamic(error, locale)}</p>
          <Button
            kind="outline small"
            onClick={() => setRevision((value) => value + 1)}
          >
            {t("Try again", "重试")}
          </Button>
        </div>
      ) : (
        <div
          className={`practice-exam-list ${loading ? "is-loading" : ""}`}
          aria-busy={loading}
        >
          {loading && (
            <p role="status">
              {t("Loading practice groups…", "正在读取专项题组…")}
            </p>
          )}
          {arranged.map(([examId, exam]) => (
            <section
              className="practice-exam-panel"
              key={examId}
              aria-labelledby={`practice-exam-${examId}`}
            >
              <header className="practice-exam-heading">
                <span>{t("SOURCE TEST", "来源试卷")}</span>
                <h3 id={`practice-exam-${examId}`}>
                  {localizeDynamic(exam.title, locale)}
                </h3>
              </header>
              <div className="practice-module-grid">
                {[...exam.modules].map(([moduleId, module]) => (
                  <section
                    className="practice-module-panel"
                    key={moduleId}
                    aria-label={localizeDynamic(module.title, locale)}
                  >
                    <header className="practice-module-heading">
                      <h4>{localizeDynamic(module.title, locale)}</h4>
                      {module.route !== "common" && (
                        <span>
                          {module.route === "lower"
                            ? t("Lower branch", "较低难度分支")
                            : t("Upper branch", "较高难度分支")}
                        </span>
                      )}
                    </header>
                    <ul className="practice-category-list">
                      {module.groups.map((group, groupIndex) => (
                        <li
                          className="practice-category-row"
                          key={group.groupId}
                          data-practice-group-id={group.groupId}
                        >
                          <div className="practice-category-main">
                            <h5>
                              {practiceGroupTaskName(group.taskType, locale)}
                            </h5>
                            <p>
                              <span>{groupRange(group, groupIndex)}</span>
                              <span>
                                {t("{count} items", "{count} 道小题", {
                                  count: group.itemCount,
                                })}
                              </span>
                              {group.screenCount !== group.itemCount && (
                                <span>
                                  {t(
                                    "{count} response screens",
                                    "{count} 个作答页",
                                    { count: group.screenCount },
                                  )}
                                </span>
                              )}
                            </p>
                            <div className="practice-group-tags">
                              {group.hasAudio && (
                                <span>
                                  <Icon name="headphones" />
                                  {t("{count} audio clips", "{count} 段音频", {
                                    count: group.audioCount,
                                  })}
                                </span>
                              )}
                              {group.duplicateCount > 1 && (
                                <span>
                                  {t(
                                    "Same group in {count} sources",
                                    "{count} 个来源含同组题",
                                    { count: group.duplicateCount },
                                  )}
                                </span>
                              )}
                            </div>
                            {!!group.unavailableCount && (
                              <p className="practice-group-availability">
                                {t(
                                  "Some source questions are unavailable. This group contains the available questions.",
                                  "部分原题暂不可练习，本组保留当前可用题目。",
                                )}
                              </p>
                            )}
                          </div>
                          <div className="practice-category-actions">
                            <span
                              className={`practice-group-state ${group.status}`}
                            >
                              {statusLabel(group.status)}
                            </span>
                            <small>
                              {t(
                                group.screenCount !== group.itemCount
                                  ? "Completed {done} / {total} response screens"
                                  : "Completed {done} / {total} questions",
                                group.screenCount !== group.itemCount
                                  ? "已完成 {done} / {total} 个作答页"
                                  : "已完成 {done} / {total} 题",
                                {
                                  done: group.completedCount,
                                  total: group.screenCount,
                                },
                              )}
                            </small>
                            <Button
                              kind="outline small"
                              disabled={loading || !group.questionIds.length}
                              onClick={() => practice(group)}
                              aria-label={t(
                                "Start group: {task} · {range} · {module} · {exam}",
                                "开始本组：{task} · {range} · {module} · {exam}",
                                {
                                  range: groupRange(group, groupIndex),
                                  task: practiceGroupTaskName(
                                    group.taskType,
                                    locale,
                                  ),
                                  module: localizeDynamic(group.module, locale),
                                  exam: localizeDynamic(
                                    group.examTitle,
                                    locale,
                                  ),
                                },
                              )}
                            >
                              {t("Start group", "开始本组")}
                              <Icon name="arrow" />
                            </Button>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </section>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
      {!loading && !error && !data?.items.length && (
        <Empty>
          {t(
            "No matching groups. Try another task type or keyword.",
            "没有匹配的题组。试试其他题型或关键词。",
          )}
        </Empty>
      )}
      <div className="pagination">
        <Button
          kind="outline small"
          disabled={page <= 1 || loading}
          onClick={() => setPage((value) => value - 1)}
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
          onClick={() => setPage((value) => value + 1)}
        >
          {t("Next page", "下一页")}
          <Icon name="arrow" />
        </Button>
      </div>
      <Notice>
        {t(
          "Each group stays within its source module and task category. Replay and instant answers are optional in setup and off by default. Combining duplicates never splits a group.",
          "每个题组保留原卷模块和题型范围。重播与即时解析需在开始前自行勾选，默认关闭；合并重复内容不会拆散题组。",
        )}
      </Notice>
    </div>
  );
}
