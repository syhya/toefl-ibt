import { useI18n } from "./i18n";
import type { Answer, Blank, Question } from "./types";
import "./answer-comparison.css";

type WordDraft = {
  word: string;
  meaning?: string;
  context?: string;
  sourceLabel?: string;
  sourceQuestionId?: string;
};
type Props = {
  question: Question;
  answer?: Answer;
  onAddWord?: (draft: WordDraft) => void;
};
type ReviewBlank = Blank & {
  acceptedAnswers?: string[];
  auditStatus?: string;
  answerConflict?: unknown;
};
type Status =
  | "correct"
  | "incorrect"
  | "unanswered"
  | "unscored"
  | "conflict"
  | "uncertain";
const subjectiveTypes = new Set([
  "email",
  "academic_discussion",
  "listen_repeat",
  "interview",
  "read_aloud",
  "picture_writing",
]);

// Match engine.normalize, including Python's whitespace set (which differs
// from JavaScript \s). These comparisons only explain a matching server grade;
// they never replace or create the authoritative question.grade.
const pythonWhitespace =
  /[\t\n\v\f\r\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+/g;
function normalize(value: string | undefined | null): string {
  return (value ?? "")
    .normalize("NFKC")
    .replace(pythonWhitespace, " ")
    .replace(/^ | $/g, "")
    .toLowerCase()
    .replace(/’/g, "'")
    .replace(/[“”]/g, '"');
}
function hasAnswer(value: unknown): boolean {
  if (Array.isArray(value)) return value.some(hasAnswer);
  if (value && typeof value === "object")
    return Object.values(value).some(hasAnswer);
  return (
    value != null &&
    String(value).replace(pythonWhitespace, " ").replace(/^ | $/g, "") !== ""
  );
}
function hasConflict(value: {
  auditStatus?: string;
  answerConflict?: unknown;
}): boolean {
  return (
    value.auditStatus === "answer-conflict" ||
    (!!value.answerConflict &&
      typeof value.answerConflict === "object" &&
      "status" in value.answerConflict &&
      value.answerConflict.status === "needs-review")
  );
}
function validGrade(question: Question): boolean {
  const grade = question.grade;
  return (
    !!grade &&
    Number.isInteger(grade.correct) &&
    Number.isInteger(grade.total) &&
    grade.total > 0 &&
    grade.correct >= 0 &&
    grade.correct <= grade.total
  );
}
function isSubjective(question: Question): boolean {
  return (
    subjectiveTypes.has(question.type) ||
    (question as Question & { subjective?: boolean }).subjective === true
  );
}
function neutralStatus(question: Question): Status | undefined {
  if (hasConflict(question)) return "conflict";
  if (isSubjective(question) || !validGrade(question)) return "unscored";
}
function showValue(value: unknown): string {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.join(" ");
  if (value && typeof value === "object") {
    return Object.entries(value)
      .map(([key, item]) => `${key}: ${showValue(item)}`)
      .join("\n");
  }
  return value == null ? "" : String(value);
}
function unique(values: string[]): string[] {
  const seen = new Set<string>();
  return values.filter((value) => {
    const key = normalize(value);
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function StatusLabel({ status }: { status: Status }) {
  const { t } = useI18n();
  const label = {
    correct: t("Correct", "正确"),
    incorrect: t("Incorrect", "错误"),
    unanswered: t("Not answered", "未作答"),
    unscored: t("Not scored", "未评分"),
    conflict: t("Answer needs review", "答案待核验"),
    uncertain: t("Detail unavailable", "细分结果待核验"),
  }[status];
  return (
    <span className={`answer-comparison-status is-${status}`}>
      <span aria-hidden="true">
        {status === "correct"
          ? "✓"
          : status === "incorrect"
            ? "✕"
            : status === "conflict"
              ? "!"
              : "—"}
      </span>
      {label}
    </span>
  );
}

function blankMatch(blank: ReviewBlank, value: unknown): boolean | undefined {
  if (typeof value !== "string" && value != null) return undefined;
  const actual = normalize(value);
  const expected = normalize(
    blank.fullWord !== undefined ? blank.fullWord : blank.answer,
  );
  const prefix = normalize(blank.prefix);
  const missing = normalize(blank.missingLetters);
  const accepted = (blank.acceptedAnswers ?? []).map(normalize);
  return (
    !!actual &&
    (actual === expected ||
      accepted.includes(actual) ||
      (!!prefix && prefix + actual === expected) ||
      (!!missing && actual === missing))
  );
}

// Keep the stored input visible separately. Prefix/suffix reconstruction is
// presentation only: engine.grade does not append a suffix when scoring.
function completeWord(blank: ReviewBlank, value: string): string {
  const prefix = blank.prefix ?? "";
  const suffix = blank.suffix ?? "";
  const actual = normalize(value);
  if (actual === normalize(blank.fullWord) && actual) return value;
  if (actual === normalize(blank.missingLetters) && actual)
    return prefix + value + suffix;
  if (
    prefix &&
    actual.startsWith(normalize(prefix)) &&
    (!suffix || actual.endsWith(normalize(suffix)))
  )
    return value;
  return prefix + value + suffix;
}
function referenceWord(blank: ReviewBlank): string {
  if (blank.fullWord) return blank.fullWord;
  if (blank.missingLetters)
    return `${blank.prefix ?? ""}${blank.missingLetters}${blank.suffix ?? ""}`;
  return blank.answer ? completeWord(blank, blank.answer) : "";
}
function Word({ blank, word }: { blank: ReviewBlank; word: string }) {
  const prefix = blank.prefix ?? "";
  const suffix = blank.suffix ?? "";
  const start =
    prefix && normalize(word).startsWith(normalize(prefix)) ? prefix.length : 0;
  const end =
    suffix && normalize(word).endsWith(normalize(suffix))
      ? word.length - suffix.length
      : word.length;
  return (
    <span className="answer-comparison-word" lang="en">
      <span className="answer-comparison-given">{word.slice(0, start)}</span>
      <strong>{word.slice(start, Math.max(start, end))}</strong>
      <span className="answer-comparison-given">
        {word.slice(Math.max(start, end))}
      </span>
    </span>
  );
}

function blankContext(question: Question): string | undefined {
  const source =
    question.passageTemplate || question.passage || question.context;
  if (!source) return question.prompt;
  return source.replace(/\{\{([^{}]+)\}\}/g, (placeholder, id: string) => {
    const blank = question.blanks?.find((item) => item.id === id);
    if (!blank || hasConflict(blank as ReviewBlank)) return placeholder;
    if (blank.missingLetters) return blank.missingLetters;
    const word = referenceWord(blank);
    const prefix = blank.prefix ?? "";
    const suffix = blank.suffix ?? "";
    return word.startsWith(prefix) && word.endsWith(suffix)
      ? word.slice(prefix.length, suffix ? -suffix.length : undefined)
      : blank.answer || placeholder;
  });
}

function ClozeComparison({ question, answer, onAddWord }: Props) {
  const { t } = useI18n();
  const blanks: ReviewBlank[] = question.blanks ?? [];
  const values =
    answer && typeof answer === "object" && !Array.isArray(answer)
      ? answer
      : {};
  const neutral = neutralStatus(question);
  const scored = blanks.filter(
    (blank) =>
      (blank.answer != null || blank.fullWord != null) && !hasConflict(blank),
  );
  const matches = scored.map((blank) => blankMatch(blank, values[blank.id]));
  const consistent =
    !neutral &&
    matches.every((value) => value !== undefined) &&
    question.grade!.total === scored.length &&
    question.grade!.correct === matches.filter(Boolean).length;
  const columns = [
    t("Question", "题号"),
    t("Your input", "我的输入"),
    t("Reference answer", "参考答案"),
    t("Result", "结果"),
  ];
  const incorrect = consistent
    ? blanks.filter(
        (blank) =>
          scored.includes(blank) &&
          hasAnswer(values[blank.id]) &&
          !blankMatch(blank, values[blank.id]),
      )
    : [];
  return (
    <div className="answer-comparison">
      {incorrect.length > 0 && (
        <nav
          className="answer-comparison-jumps"
          aria-label={t("Incorrect blanks", "错误空定位")}
        >
          <span>{t("Incorrect blanks:", "错误空：")}</span>
          {incorrect.map((blank) => {
            const number =
              blank.number ?? (question.number ?? 1) + blanks.indexOf(blank);
            return (
              <a key={blank.id} href={`#answer-${question.id}-${blank.id}`}>
                {t("Question {number}", "第 {number} 题", { number })}
              </a>
            );
          })}
        </nav>
      )}
      <table className="answer-comparison-table" role="table">
        <caption>{t("Compare each blank", "逐空答案对照")}</caption>
        <thead role="rowgroup">
          <tr role="row">
            {columns.map((label) => (
              <th scope="col" role="columnheader" key={label}>
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody role="rowgroup">
          {blanks.map((blank, index) => {
            const raw = showValue(values[blank.id]);
            const attempted = hasAnswer(values[blank.id]);
            const scorable = scored.includes(blank);
            const status: Status = hasConflict(blank)
              ? "conflict"
              : neutral ||
                (!scorable
                  ? "unscored"
                  : !consistent
                    ? "uncertain"
                    : !attempted
                      ? "unanswered"
                      : blankMatch(blank, values[blank.id])
                        ? "correct"
                        : "incorrect");
            const word = referenceWord(blank);
            const variants = unique(
              (blank.acceptedAnswers ?? []).map((value) =>
                completeWord(blank, value),
              ),
            ).filter((value) => normalize(value) !== normalize(word));
            const number =
              blank.number ??
              (question.number != null ? question.number + index : index + 1);
            const canAdd =
              !!word && !hasConflict(blank) && !hasConflict(question);
            return (
              <tr
                key={blank.id}
                role="row"
                className={`answer-comparison-row is-${status}`}
                data-blank-id={blank.id}
                id={`answer-${question.id}-${blank.id}`}
              >
                <th scope="row" role="rowheader" data-label={columns[0]}>
                  <span>{number}</span>
                  <small>{blank.id}</small>
                </th>
                <td role="cell" data-label={columns[1]}>
                  {attempted ? (
                    <>
                      <span className="answer-comparison-input" lang="en">
                        {raw}
                      </span>
                      <Word blank={blank} word={completeWord(blank, raw)} />
                    </>
                  ) : (
                    <span>{t("Not answered", "未作答")}</span>
                  )}
                </td>
                <td role="cell" data-label={columns[2]}>
                  {word ? (
                    <Word blank={blank} word={word} />
                  ) : (
                    <span>{t("Reference unavailable", "暂无参考答案")}</span>
                  )}
                  {variants.length > 0 && (
                    <span className="answer-comparison-variants">
                      {t("Also accepted: ", "也接受：")}
                      <span lang="en">{variants.join(" / ")}</span>
                    </span>
                  )}
                  {onAddWord && (
                    <button
                      type="button"
                      className="answer-comparison-add"
                      disabled={!canAdd}
                      aria-label={t(
                        "Add {word} to word book · question {number}",
                        "添加 {word} 到单词本 · 第 {number} 题",
                        { word: word || blank.id, number },
                      )}
                      onClick={() =>
                        onAddWord({
                          word,
                          context: blankContext(question),
                          sourceQuestionId: question.id,
                          sourceLabel: t(
                            "Question {number}",
                            "第 {number} 题",
                            { number },
                          ),
                        })
                      }
                    >
                      <span aria-hidden="true">＋</span>
                      {t("Add word", "加入单词本")}
                    </button>
                  )}
                </td>
                <td role="cell" data-label={columns[3]}>
                  <StatusLabel status={status} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {!neutral && !consistent && (
        <p className="answer-comparison-note">
          {t(
            "The saved server score cannot be reliably broken down from these answers. Per-blank correctness is not shown.",
            "当前答案无法可靠还原服务端保存的逐空得分，因此暂不标记各空对错。",
          )}
        </p>
      )}
      {neutral === "conflict" && (
        <p className="answer-comparison-note">
          {t(
            "The reference answer has an unresolved conflict. The text below is for review only.",
            "参考答案存在未解决的冲突，所列答案仅供核验。",
          )}
        </p>
      )}
    </div>
  );
}

function acceptedAnswers(question: Question): string[] {
  // The engine treats an answer array as alternative complete answers, not as
  // a set of selected options. A submitted array is instead joined with spaces.
  const answers = Array.isArray(question.answer)
    ? question.answer
    : typeof question.answer === "string"
      ? [question.answer]
      : [];
  return unique([...answers, ...(question.acceptedAnswers ?? [])]);
}
function sentenceAnswer(
  question: Question,
  value: Answer | undefined,
): { text: string; complete: boolean } {
  if (!value || typeof value !== "object" || Array.isArray(value))
    return { text: showValue(value), complete: true };
  const order = value.tokenOrder;
  if (!Array.isArray(order)) return { text: showValue(value), complete: false };
  const slots = question.slots ?? [];
  const standardSlots = slots.every(
    (slot) => !!slot && typeof slot === "object",
  );
  const gaps = slots.filter(
    (slot) => slot && typeof slot === "object" && !("fixed" in slot),
  );
  let complete =
    standardSlots &&
    order.length > 0 &&
    !order.includes("") &&
    (!gaps.length || order.length === gaps.length);
  const token = (index: string | undefined): string => {
    if (
      index == null ||
      !/^\d+$/.test(index) ||
      question.tokens?.[Number(index)] == null
    ) {
      complete = false;
      return "____";
    }
    return question.tokens[Number(index)];
  };
  let next = 0;
  const text = (
    slots.length
      ? slots.map((slot) => {
          if (typeof slot === "string") return slot;
          if (slot && "fixed" in slot) return slot.fixed ?? "";
          return token(order[next++]);
        })
      : order.map(token)
  )
    .join(" ")
    .replace(/\s+([?.!,;:])/g, "$1");
  return { text, complete };
}
function normalizedResponse(question: Question, text: string): string {
  const result = normalize(text);
  return question.type === "build_sentence"
    ? result
        .replace(/\s+([?.!,;:])/g, "$1")
        .replace(/[.!?]+$/, "")
        .replace(/ +$/, "")
    : result;
}

function ResponseComparison({ question, answer }: Props) {
  const { t } = useI18n();
  const neutral = neutralStatus(question);
  const references = acceptedAnswers(question);
  const response =
    question.type === "build_sentence"
      ? sentenceAnswer(question, answer)
      : { text: showValue(answer), complete: true };
  const matched =
    response.complete &&
    references.some(
      (reference) =>
        normalizedResponse(question, response.text) ===
        normalizedResponse(question, reference),
    );
  const consistent =
    !neutral &&
    references.length > 0 &&
    question.grade!.total === 1 &&
    question.grade!.correct === Number(matched);
  const status: Status =
    neutral ||
    (!consistent
      ? "uncertain"
      : !hasAnswer(answer)
        ? "unanswered"
        : matched
          ? "correct"
          : "incorrect");
  const choices = question.choices ?? [];
  const optionIds = (value: string): string[] | undefined => {
    const exact = choices.find(
      (choice) => normalize(choice.id) === normalize(value),
    );
    if (exact) return [exact.id];
    const ids = normalize(value).split(" ");
    const resolved = ids.map(
      (id) => choices.find((choice) => normalize(choice.id) === id)?.id,
    );
    return resolved.length && resolved.every((id) => id !== undefined)
      ? (resolved as string[])
      : undefined;
  };
  const referenceOptions = references.map(optionIds);
  const selectedIds = optionIds(response.text) ?? [];
  const canCompareOptions =
    consistent &&
    hasAnswer(answer) &&
    referenceOptions.every((ids) => ids !== undefined);
  const correctIds = new Set(referenceOptions.flatMap((ids) => ids ?? []));
  const describe = (value: string) => {
    const ids = optionIds(value);
    return choices.length && ids
      ? ids
          .map((id) => {
            const choice = choices.find((item) => item.id === id)!;
            return choice.text === id ? choice.text : `${id}. ${choice.text}`;
          })
          .join(" / ")
      : value;
  };
  const fallback = question.answer ?? question.sourceReferenceAnswer;
  return (
    <div className="answer-comparison">
      <div className="answer-comparison-summary">
        <StatusLabel status={status} />
      </div>
      {choices.length > 0 && (
        <ul
          className="answer-comparison-choices"
          aria-label={t("Answer choices", "答案选项")}
        >
          {choices.map((choice) => {
            const selected = selectedIds.includes(choice.id);
            const reference = canCompareOptions && correctIds.has(choice.id);
            // Alternate multi-option references can overlap. Membership alone does
            // not prove an individual option wrong; only mark excluded selections.
            const wrong =
              canCompareOptions &&
              status === "incorrect" &&
              selected &&
              !reference;
            const style = wrong
              ? "incorrect"
              : reference
                ? "correct"
                : "neutral";
            return (
              <li
                key={choice.id}
                className={`answer-comparison-choice is-${style}`}
                data-choice-id={choice.id}
              >
                <span className="answer-comparison-choice-id" lang="en">
                  {choice.id}
                </span>
                <span className="answer-comparison-choice-text" lang="en">
                  {choice.text}
                </span>
                <span className="answer-comparison-choice-labels">
                  {selected && <span>{t("Your selection", "你的选择")}</span>}
                  {wrong && <StatusLabel status="incorrect" />}
                  {reference && (
                    <span className="answer-comparison-status is-correct">
                      <span aria-hidden="true">✓</span>
                      {t("Accepted option", "参考正确选项")}
                    </span>
                  )}
                </span>
              </li>
            );
          })}
        </ul>
      )}
      <div className="answer-comparison-pair">
        <div className={`answer-comparison-response is-${status}`}>
          <strong className="answer-comparison-heading">
            {t("Your response", "你的回答")}
          </strong>
          <p lang={hasAnswer(answer) ? "en" : undefined}>
            {hasAnswer(answer)
              ? describe(response.text)
              : t("Not answered", "未作答")}
          </p>
        </div>
        <div className="answer-comparison-reference">
          <strong className="answer-comparison-heading">
            {t("Source reference / Review guidance", "资料参考 / 复盘提示")}
          </strong>
          {references.length > 0 ? (
            <ul>
              {references.map((reference) => (
                <li key={reference} lang="en">
                  {describe(reference)}
                </li>
              ))}
            </ul>
          ) : hasAnswer(fallback) ? (
            <p lang="en">{showValue(fallback)}</p>
          ) : (
            <p>
              {isSubjective(question)
                ? t(
                    "This response is not automatically scored. Use the relevant rubric to review delivery, language, and content.",
                    "本题不自动评分。请参照适用量表核对表达、语言和内容。",
                  )
                : t(
                    "Reference answer unavailable; check the source material.",
                    "暂无可靠参考答案，请核对原始资料。",
                  )}
            </p>
          )}
        </div>
      </div>
      {status === "uncertain" && (
        <p className="answer-comparison-note">
          {t(
            "The saved server score cannot be reliably explained by this reference. Detailed correctness is not shown.",
            "当前参考答案无法可靠解释服务端保存的得分，因此暂不标记细节对错。",
          )}
        </p>
      )}
      {status === "conflict" && (
        <p className="answer-comparison-note">
          {t(
            "The reference answer has an unresolved conflict and is shown for review only.",
            "参考答案存在未解决的冲突，所列答案仅供核验。",
          )}
        </p>
      )}
    </div>
  );
}

export default function AnswerComparison(props: Props) {
  return (props.question.type === "cloze" ||
    props.question.type === "complete_words") &&
    props.question.blanks?.length ? (
    <ClozeComparison {...props} />
  ) : (
    <ResponseComparison {...props} />
  );
}
