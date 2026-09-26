import { useI18n } from "./i18n";
import { examText as tx } from "./locales/exam";
import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type ButtonHTMLAttributes,
  type ReactNode,
} from "react";
import type { Answer, Question, StemBlock } from "./types";
import { taskName, wordCount } from "./api";
import Icon from "./Icons";
import { createPortal } from "react-dom";
import { Button } from "./components";

export function StemAssets({ question }: { question: Question }) {
  useI18n();
  return (
    <>
      {question.assets?.map((a) => (
        <img
          key={a.assetId || a.url}
          className="stem-image"
          src={a.url}
          alt={a.alt || tx("Original question from your materials")}
        />
      ))}
    </>
  );
}
export function StructuredStem({
  question,
  value,
  onChange,
  disabled = false,
  discussionPart,
  displayPart,
}: {
  question: Question;
  value?: Answer;
  onChange?: (value: Answer) => void;
  disabled?: boolean;
  discussionPart?: "professor" | "students";
  displayPart?: "email-prompt" | "email-response";
}) {
  const { locale } = useI18n();
  // Matching and highlighting operate only on canonical source text. Translations
  // are confined to controls so selecting a sentence never changes its answer ID.
  const usedAssets = new Set<number>(),
    quoted = question.prompt?.match(/["“]([^"”]+)["”]/)?.[1],
    sourceText = (text: string) => {
      if (!quoted) return text;
      const at = text.toLocaleLowerCase().indexOf(quoted.toLocaleLowerCase());
      return at < 0 ? (
        text
      ) : (
        <>
          {text.slice(0, at)}
          <mark className="source-target">
            {text.slice(at, at + quoted.length)}
          </mark>
          {text.slice(at + quoted.length)}
        </>
      );
    },
    selectableText = (text: string) => {
      if (question.interaction !== "select_sentence" || !onChange)
        return sourceText(text);
      const matches = (question.choices || [])
        .map((choice, index) => ({
          choice,
          index,
          at: text.indexOf(choice.text),
        }))
        .filter((item) => item.at >= 0)
        .sort((a, b) => a.at - b.at);
      if (!matches.length) return sourceText(text);
      const result: ReactNode[] = [];
      let cursor = 0;
      for (const item of matches) {
        if (item.at < cursor) continue;
        if (item.at > cursor) result.push(text.slice(cursor, item.at));
        result.push(
          <button
            key={item.choice.id}
            className={`selectable-sentence ${value === item.choice.id ? "selected" : ""}`}
            lang={locale}
            disabled={disabled}
            aria-pressed={value === item.choice.id}
            aria-label={tx("Select sentence {number}: {text}", {
              number: item.index + 1,
              text: item.choice.text,
            })}
            onClick={() => onChange(item.choice.id)}
          >
            <span lang="en">{item.choice.text}</span>
          </button>,
        );
        cursor = item.at + item.choice.text.length;
      }
      if (cursor < text.length) result.push(text.slice(cursor));
      return <>{result}</>;
    };
  for (const item of question.stemBlocks || [])
    if (item.type === "dialogue")
      for (const turn of item.turns)
        if (typeof turn.avatarAssetIndex === "number")
          usedAssets.add(turn.avatarAssetIndex);
  const block = (item: StemBlock, index: number) => {
    const responseFields =
      item.type === "table" && item.caption === "Your Response";
    if (displayPart === "email-response" && !responseFields) return null;
    if (displayPart === "email-prompt" && responseFields) return null;
    if (displayPart === "email-response" && item.type === "table")
      return (
        <section className="email-response-fields" key={index}>
          <p className="email-response-title">{item.caption}:</p>
          {item.rows.map((row, rowIndex) => (
            <div className="email-response-row" key={rowIndex}>
              {row.map((text, columnIndex) => (
                <span
                  className={
                    columnIndex === 0
                      ? "email-response-label"
                      : "email-response-value"
                  }
                  key={columnIndex}
                >
                  {text}
                  {columnIndex === 0 && !text.trim().endsWith(":") ? ":" : ""}
                  {columnIndex < row.length - 1 ? " " : ""}
                </span>
              ))}
            </div>
          ))}
        </section>
      );
    if (discussionPart === "students" && item.type !== "dialogue") return null;
    if (discussionPart && item.type === "title") return null;
    if (
      item.type === "title" &&
      item.text.trim().toLocaleLowerCase() ===
        taskName(question.type).toLocaleLowerCase()
    )
      return null;
    if (item.type === "title")
      return (
        <h3 key={index} className="structured-title">
          {sourceText(item.text)}
        </h3>
      );
    if (item.type === "instruction")
      return (
        <p key={index} className="structured-instruction">
          {sourceText(item.text)}
        </p>
      );
    if (item.type === "paragraph") {
      const prior = question.stemBlocks?.[index - 1],
        insertionCandidate =
          question.interaction === "select_sentence" &&
          prior?.type === "instruction" &&
          /following sentence/i.test(prior.text) &&
          !(question.choices || []).some((choice) =>
            item.text.includes(choice.text),
          );
      return (
        <p
          key={index}
          className={`structured-paragraph ${insertionCandidate ? "sentence-to-insert" : ""}`}
        >
          {selectableText(item.text)}
        </p>
      );
    }
    if (item.type === "highlighted_sentence")
      return (
        <p key={index} className="highlighted-source-sentence">
          <span lang={locale}>{tx("Highlighted sentence")}</span>
          <mark>{item.text}</mark>
        </p>
      );
    // The verified question block duplicates q.prompt. Exam renders the prompt
    // beside its response controls so material and question never get mixed.
    if (item.type === "question") return null;
    if (item.type === "message")
      return (
        <section key={index} className="structured-message">
          <dl>
            {item.sender && (
              <>
                <dt>From</dt>
                <dd>{item.sender}</dd>
              </>
            )}
            {item.recipient && (
              <>
                <dt>To</dt>
                <dd>{item.recipient}</dd>
              </>
            )}
            {item.date && (
              <>
                <dt>Date</dt>
                <dd>{item.date}</dd>
              </>
            )}
            {item.subject && (
              <>
                <dt>Subject</dt>
                <dd>{item.subject}</dd>
              </>
            )}
          </dl>
          <div className="structured-message-body">
            {item.paragraphs.map((text, i) => (
              <p key={i}>{text}</p>
            ))}
          </div>
        </section>
      );
    if (item.type === "dialogue") {
      if (question.type !== "academic_discussion")
        return (
          <div key={index} className="structured-dialogue">
            {item.turns.map((turn, i) => (
              <p key={i}>
                <b>{turn.speaker}</b>
                <span>{turn.text}</span>
              </p>
            ))}
          </div>
        );
      const turns = item.turns
        .map((turn, turnIndex) => ({ turn, turnIndex }))
        .filter(({ turnIndex }) =>
          discussionPart === "professor"
            ? turnIndex === 0
            : discussionPart === "students"
              ? turnIndex > 0
              : true,
        );
      return (
        <div
          key={index}
          className={`structured-dialogue academic-thread ${discussionPart ? `discussion-${discussionPart}` : ""}`}
        >
          {turns.map(({ turn, turnIndex }) => {
            const asset =
                typeof turn.avatarAssetIndex === "number"
                  ? question.assets?.[turn.avatarAssetIndex]
                  : undefined,
              initials = turn.speaker
                .split(/\s+/)
                .map((part) => part[0])
                .join("")
                .slice(0, 2)
                .toLocaleUpperCase();
            return (
              <article
                className={`discussion-turn ${turnIndex === 0 ? "professor" : "student"}`}
                key={`${turnIndex}:${turn.speaker}`}
              >
                <figure>
                  {asset ? (
                    <img className="discussion-avatar" src={asset.url} alt="" />
                  ) : (
                    <span className="discussion-avatar fallback" aria-hidden>
                      {initials}
                    </span>
                  )}
                  <figcaption>{turn.speaker}</figcaption>
                </figure>
                <p>{turn.text}</p>
              </article>
            );
          })}
        </div>
      );
    }
    if (item.type === "list") {
      const marker = item.marker || (item.ordered ? "decimal" : "bullet"),
        List = marker === "bullet" ? "ul" : "ol";
      return (
        <List
          key={index}
          className={`structured-list ${marker === "lower-alpha" ? "lower-alpha" : ""}`}
        >
          {item.items.map((text, i) => (
            <li key={i}>{text}</li>
          ))}
        </List>
      );
    }
    if (item.type === "form_diagram") {
      const position = (number: number) => (
        <span
          className={`form-position ${item.highlightedPosition === number ? "active" : ""}`}
          aria-label={tx(
            item.highlightedPosition === number
              ? "Position {number}, highlighted"
              : "Position {number}",
            { number },
          )}
        >
          {number}
        </span>
      );
      return (
        <div
          key={index}
          className="form-diagram"
          lang={locale}
          role="img"
          aria-label={tx("Form layout with position {number} highlighted", {
            number: item.highlightedPosition,
          })}
        >
          <div className="form-title">
            {position(1)}
            <strong lang="en">Form</strong>
          </div>
          {[2, 3, 4].map((number) => (
            <div className="form-line" key={number}>
              {position(number)}
              <i />
            </div>
          ))}
          <div className="form-columns">
            <div>
              {position(5)}
              <i />
            </div>
            <div>
              {position(6)}
              <i />
            </div>
          </div>
          {[7, 8].map((number) => (
            <div className="form-line" key={number}>
              {position(number)}
              <i />
            </div>
          ))}
        </div>
      );
    }
    if (item.type === "table")
      return (
        <div key={index} className="structured-table-wrap">
          <table
            className={`structured-table ${item.caption === "Your Response" ? "email-fields" : ""}`}
          >
            {item.caption && <caption>{item.caption}</caption>}
            <thead>
              <tr>
                {item.headers.map((text, i) => (
                  <th scope="col" key={i}>
                    {text}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {item.rows.map((row, i) => (
                <tr key={i}>
                  {row.map((text, j) =>
                    item.rowHeaders && j === 0 ? (
                      <th scope="row" key={j}>
                        {text}
                      </th>
                    ) : (
                      <td key={j}>{text}</td>
                    ),
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    if (!("assetIndex" in item)) return null;
    const asset = question.assets?.[item.assetIndex];
    usedAssets.add(item.assetIndex);
    return asset ? (
      <img
        key={index}
        className="essential-visual"
        src={asset.url}
        alt={item.alt || asset.alt || tx("Question visual")}
      />
    ) : null;
  };
  return (
    <div
      lang="en"
      className={`structured-stem${displayPart ? ` ${displayPart}` : ""}`}
    >
      {question.stemBlocks?.map(block)}
      {displayPart !== "email-response" &&
        question.assets?.map((asset, index) =>
          usedAssets.has(index) ? null : (
            <img
              key={asset.assetId || asset.url}
              className="essential-visual"
              src={asset.url}
              alt={asset.alt || tx("Question visual")}
            />
          ),
        )}
    </div>
  );
}
export function AnswerInput({
  question: q,
  value,
  onChange,
  disabled,
  strict,
  examStyle = false,
}: {
  question: Question;
  value: Answer | undefined;
  onChange: (v: Answer) => void;
  disabled: boolean;
  strict: boolean;
  examStyle?: boolean;
}) {
  useI18n();
  if (q.interaction === "select_sentence" && q.choices?.length)
    return (
      <div
        className="selectable-paragraph"
        role="group"
        aria-label={tx("Select a sentence")}
      >
        {q.choices.map((choice, index) => (
          <button
            key={choice.id}
            className={`selectable-sentence ${value === choice.id ? "selected" : ""}`}
            disabled={disabled}
            aria-pressed={value === choice.id}
            aria-label={tx("Select sentence {number}: {text}", {
              number: index + 1,
              text: choice.text,
            })}
            onClick={() => onChange(choice.id)}
          >
            <span lang="en">{choice.text}</span>{" "}
          </button>
        ))}
      </div>
    );
  if (q.type === "choice" && q.choices?.length)
    return (
      <div
        className="answers"
        role="radiogroup"
        aria-label={tx("Answer choices")}
      >
        {q.choices.map((c) => (
          <label className="answer-choice" key={c.id}>
            <input
              type="radio"
              name={`answer-${q.id}`}
              value={c.id}
              checked={value === c.id}
              disabled={disabled}
              onChange={() => onChange(c.id)}
            />
            <span
              className="choice-letter"
              aria-hidden={c.id.length > 1 ? true : undefined}
            >
              {c.id.length === 1 ? c.id : ""}
            </span>
            <span className="answer-text" lang="en">
              {c.text}
            </span>
          </label>
        ))}
      </div>
    );
  if (q.type === "cloze" && q.passageTemplate)
    return (
      <ClozePassage
        q={q}
        value={value}
        onChange={onChange}
        disabled={disabled}
        examStyle={examStyle}
      />
    );
  if (q.type === "cloze") {
    const values =
      value && typeof value === "object" && !Array.isArray(value) ? value : {};
    return (
      <>
        <div className="cloze-grid">
          {q.blanks?.map((b, i) => (
            <label className="blank-field" key={b.id}>
              <span>{b.number || i + 1}.</span>
              {b.prefix && <span>{b.prefix}</span>}
              <input
                value={
                  typeof values[b.id] === "string" ? String(values[b.id]) : ""
                }
                onChange={(e) =>
                  onChange({ ...values, [b.id]: e.target.value })
                }
                disabled={disabled}
                maxLength={b.length || undefined}
                spellCheck={false}
                autoCapitalize="off"
                autoComplete="off"
                aria-label={tx("Missing letters for word {number}", {
                  number: b.number || i + 1,
                })}
              />
              {b.suffix && <span>{b.suffix}</span>}
            </label>
          ))}
        </div>
        <p className="muted" style={{ fontSize: 10, margin: "17px 0 0" }}>
          {tx(
            "Enter only the missing letters after the given prefix. Use the original question to check the order.",
          )}
        </p>
      </>
    );
  }
  if (q.type === "build_sentence" && q.slots?.length)
    return (
      <SentenceBuilder
        q={q}
        value={
          value &&
          typeof value === "object" &&
          !Array.isArray(value) &&
          Array.isArray(value.tokenOrder)
            ? value.tokenOrder
            : []
        }
        onChange={(order) => onChange({ tokenOrder: order })}
        disabled={disabled}
      />
    );
  if (
    q.type === "listen_repeat" ||
    q.type === "interview" ||
    q.type === "read_aloud"
  )
    return null;
  return (
    <WritingEditor
      key={q.id}
      q={q}
      value={typeof value === "string" ? value : ""}
      onChange={onChange}
      disabled={disabled}
      strict={strict}
      examStyle={examStyle}
    />
  );
}
function ClozePassage({
  q,
  value,
  onChange,
  disabled,
  examStyle,
}: {
  q: Question;
  value: Answer | undefined;
  onChange: (v: Answer) => void;
  disabled: boolean;
  examStyle: boolean;
}) {
  useI18n();
  const values =
      value && typeof value === "object" && !Array.isArray(value) ? value : {},
    blankList = q.blanks || [],
    blanks = new Map(blankList.map((b) => [b.id, b])),
    [activeBlankId, setActiveBlankId] = useState(blankList[0]?.id || ""),
    activeBlank = blanks.get(activeBlankId) || blankList[0],
    activeValue = activeBlank ? String(values[activeBlank.id] || "") : "",
    activeLength = activeBlank?.length || 3,
    activeNumber = activeBlank
      ? activeBlank.number || blankList.indexOf(activeBlank) + 1
      : 0,
    completed = blankList.filter((blank) => {
      const expected = blank.length || 3;
      return String(values[blank.id] || "").length === expected;
    }).length,
    guideId = `cloze-entry-guide-${q.id}`,
    templateParts = q.passageTemplate!.split(/(\{\{[^{}]+\}\})/g),
    placeholderId = (part?: string) => part?.match(/^\{\{([^{}]+)\}\}$/)?.[1];
  return (
    <>
      <div className="cloze-entry-guide" id={guideId}>
        <span>{tx("{count} missing words", { count: blankList.length })}</span>
        <span>{tx("One blue slot = one letter")}</span>
        {activeBlank && (
          <span className="cloze-active-count" aria-live="polite">
            {tx("Blank {number} · {entered} / {required} letters", {
              number: activeNumber,
              entered: Math.min(activeValue.length, activeLength),
              required: activeLength,
            })}
          </span>
        )}
      </div>
      <div className="cloze-passage" lang="en">
        {templateParts.map((part, i) => {
          const id = placeholderId(part),
            blank = id ? blanks.get(id) : null;
          if (!id || !blank) {
            let visibleText = part;
            const priorBlank = blanks.get(
                placeholderId(templateParts[i - 1]) || "",
              ),
              nextBlank = blanks.get(placeholderId(templateParts[i + 1]) || "");
            if (priorBlank?.suffix && visibleText.startsWith(priorBlank.suffix))
              visibleText = visibleText.slice(priorBlank.suffix.length);
            if (nextBlank?.prefix && visibleText.endsWith(nextBlank.prefix))
              visibleText = visibleText.slice(0, -nextBlank.prefix.length);
            return visibleText ? <span key={i}>{visibleText}</span> : null;
          }
          const requiredLength = blank.length || 3,
            blankNumber = blank.number || blankList.indexOf(blank) + 1,
            currentValue = String(values[id] || ""),
            previousText = templateParts[i - 1] || "",
            nextText = templateParts[i + 1] || "",
            prefix =
              blank.prefix && previousText.endsWith(blank.prefix)
                ? blank.prefix
                : "",
            suffix =
              blank.suffix && nextText.startsWith(blank.suffix)
                ? blank.suffix
                : "";
          return (
            <span className="cloze-word" key={i}>
              {prefix && <span className="cloze-word-part">{prefix}</span>}
              <span
                className={`cloze-blank-wrap${examStyle && currentValue.length === requiredLength ? " is-complete" : ""}`}
                style={{ "--blank-slots": requiredLength } as CSSProperties}
              >
                <input
                  className="inline-blank"
                  lang="en"
                  style={{ "--blank-slots": requiredLength } as CSSProperties}
                  value={currentValue}
                  maxLength={requiredLength}
                  disabled={disabled}
                  onFocus={() => setActiveBlankId(id)}
                  onChange={(e) => {
                    const letters = e.target.value
                      .replace(/[^a-z]/gi, "")
                      .slice(0, requiredLength);
                    setActiveBlankId(id);
                    onChange({
                      ...values,
                      [id]: examStyle ? letters.toLowerCase() : letters,
                    });
                  }}
                  spellCheck={false}
                  autoComplete="off"
                  autoCapitalize="off"
                  autoCorrect="off"
                  aria-label={tx(
                    "Missing letters for word {number}, {length} letters required",
                    { number: blankNumber, length: requiredLength },
                  )}
                  aria-describedby={guideId}
                  placeholder={"_".repeat(requiredLength)}
                />
                {examStyle && currentValue.length === requiredLength && (
                  <span className="cloze-completed-text" aria-hidden="true">
                    {currentValue}
                  </span>
                )}
              </span>
              {suffix && <span className="cloze-word-part">{suffix}</span>}
            </span>
          );
        })}
      </div>
      <div className="editor-meta">
        <span>{tx("Use Tab to move between blanks.")}</span>
        <span>
          {tx("{completed} / {total} completed", {
            completed,
            total: blanks.size,
          })}
        </span>
      </div>
    </>
  );
}
function SentenceBuilder({
  q,
  value,
  onChange,
  disabled,
}: {
  q: Question;
  value: string[];
  onChange: (v: string[]) => void;
  disabled: boolean;
}) {
  useI18n();
  const tokens = q.tokens || [],
    slots = q.slots || [],
    gaps = slots.filter((s) => !fixed(s)).length,
    [selected, setSelected] = useState(0),
    [interactionStatus, setInteractionStatus] = useState<{
      text: string;
      values?: Record<string, string | number>;
    } | null>(null),
    [ghost, setGhost] = useState<{ text: string; x: number; y: number } | null>(
      null,
    ),
    pointerDrag = useRef<{
      token: number;
      x: number;
      y: number;
      moved: boolean;
    } | null>(null),
    nativeDragToken = useRef<number | null>(null),
    suppressClick = useRef(false);
  const fill = (token: number, gap = selected) => {
    if (disabled) return;
    const next = Array.from({ length: gaps }, (_, i) => value[i] || "").map(
      (v) => (v === String(token) ? "" : v),
    );
    next[gap] = String(token);
    onChange(next);
    setInteractionStatus({
      text: "Placed {word} in gap {number}.",
      values: { word: tokens[token], number: gap + 1 },
    });
    setSelected(
      Math.min(
        gaps - 1,
        next.findIndex((v, i) => i > gap && !v) === -1
          ? gap + 1
          : next.findIndex((v, i) => i > gap && !v),
      ),
    );
  };
  const finishDrag = () => {
    nativeDragToken.current = null;
    pointerDrag.current = null;
    suppressClick.current = false;
    setGhost(null);
  };
  // Native drag and pointer drag share indices; captions never become answer data.
  // Pointer capture allows touch users to leave a token before dropping it.
  const dragHandlers = (
    i: number,
  ): ButtonHTMLAttributes<HTMLButtonElement> => ({
    onDragStart: (e) => {
      suppressClick.current = true;
      nativeDragToken.current = i;
      setInteractionStatus({
        text: "Dragging {word}.",
        values: { word: tokens[i] },
      });
      e.dataTransfer.setData(
        "application/x-toefl-word",
        JSON.stringify({ questionId: q.id, index: i }),
      );
    },
    onDragEnd: finishDrag,
    onPointerDown: (event) => {
      if (disabled || event.button !== 0) return;
      setInteractionStatus({
        text: "Picked up {word}.",
        values: { word: tokens[i] },
      });
      suppressClick.current = false;
      pointerDrag.current = {
        token: i,
        x: event.clientX,
        y: event.clientY,
        moved: false,
      };
      event.currentTarget.setPointerCapture?.(event.pointerId);
    },
    onPointerMove: (event) => {
      const drag = pointerDrag.current;
      if (!drag) return;
      if (Math.hypot(event.clientX - drag.x, event.clientY - drag.y) > 5)
        drag.moved = true;
      if (drag.moved)
        setInteractionStatus({
          text: "Dragging {word}.",
          values: { word: tokens[drag.token] },
        });
      if (drag.moved)
        setGhost({
          text: tokens[drag.token],
          x: event.clientX,
          y: event.clientY,
        });
    },
    onPointerUp: (event) => {
      const drag = pointerDrag.current;
      pointerDrag.current = null;
      setGhost(null);
      if (!drag?.moved) return;
      suppressClick.current = true;
      const target = document
        .elementFromPoint(event.clientX, event.clientY)
        ?.closest<HTMLElement>("[data-sentence-gap]");
      if (target?.dataset.questionId === q.id) {
        const gap = Number(target.dataset.sentenceGap);
        if (Number.isInteger(gap) && gap >= 0 && gap < gaps)
          fill(drag.token, gap);
      } else
        setInteractionStatus({
          text: "Word was not placed. Drop it inside a gap.",
        });
    },
    onPointerCancel: () => {
      pointerDrag.current = null;
      setGhost(null);
    },
  });
  let gapIndex = 0;
  return (
    <>
      <p className="muted" style={{ fontSize: 11, lineHeight: 1.8 }}>
        {tx(
          "Drag word blocks into the gaps or between filled gaps. You can also select a gap and click a word.",
        )}
      </p>
      <div
        className="sentence-slots"
        role="group"
        aria-label={tx("Sentence word slots")}
      >
        {q.sentencePrefix && (
          <span className="fixed-token" lang="en">
            {q.sentencePrefix}
          </span>
        )}
        {slots.map((slot, i) => {
          const text = fixed(slot);
          if (text)
            return (
              <span className="fixed-token" lang="en" key={i}>
                {text}
              </span>
            );
          const gap = gapIndex++,
            v = value[gap],
            filled = v !== "" && v !== undefined;
          return (
            <button
              key={i}
              type="button"
              className={`sentence-slot ${selected === gap ? "selected" : ""} ${filled ? "filled" : ""}`}
              disabled={disabled}
              draggable={!disabled && filled}
              {...(filled ? dragHandlers(Number(v)) : {})}
              onDragEnd={finishDrag}
              data-sentence-gap={gap}
              data-question-id={q.id}
              aria-label={
                filled
                  ? tx("Gap {number}: {word}. Click to remove.", {
                      number: gap + 1,
                      word: tokens[Number(v)],
                    })
                  : tx("Gap {number}: empty", { number: gap + 1 })
              }
              onClick={() => {
                if (suppressClick.current) {
                  suppressClick.current = false;
                  return;
                }
                setSelected(gap);
                if (filled) {
                  const next = [...value];
                  next[gap] = "";
                  onChange(next);
                }
              }}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                const fallbackToken =
                  nativeDragToken.current ?? pointerDrag.current?.token;
                nativeDragToken.current = null;
                pointerDrag.current = null;
                setGhost(null);
                const raw = e.dataTransfer.getData("application/x-toefl-word");
                if (!raw) {
                  const token = fallbackToken;
                  if (token !== undefined && token !== null) fill(token, gap);
                  return;
                }
                let data;
                try {
                  data = JSON.parse(raw);
                } catch {
                  return;
                }
                if (data.questionId !== q.id) return;
                const token = Number(data.index);
                if (
                  Number.isInteger(token) &&
                  token >= 0 &&
                  token < tokens.length
                )
                  fill(token, gap);
              }}
            >
              {filled ? (
                <span lang="en">{tokens[Number(v)]}</span>
              ) : (
                ` ${gap + 1} `
              )}
            </button>
          );
        })}
        {q.terminalPunctuation && (
          <span className="fixed-token" lang="en">
            {q.terminalPunctuation}
          </span>
        )}
      </div>
      <div className="word-bank" aria-label={tx("Available word blocks")}>
        {tokens.map((token, i) => {
          const used = value.includes(String(i));
          return (
            <button
              key={i}
              className={`word-token ${used ? "used" : ""}`}
              lang="en"
              disabled={disabled || used}
              draggable={!disabled && !used}
              {...dragHandlers(i)}
              onClick={() => {
                nativeDragToken.current = null;
                if (suppressClick.current) {
                  suppressClick.current = false;
                  return;
                }
                fill(i);
              }}
              aria-label={tx("Use word block {number}: {word}", {
                number: i + 1,
                word: token,
              })}
            >
              {token}
            </button>
          );
        })}
      </div>
      {ghost &&
        createPortal(
          <span
            className="word-drag-ghost"
            lang="en"
            style={{ left: ghost.x + 12, top: ghost.y + 12 }}
            aria-hidden="true"
          >
            {ghost.text}
          </span>,
          document.body,
        )}
      <div className="editor-meta">
        <span className="sr-only" role="status">
          {interactionStatus &&
            tx(interactionStatus.text, interactionStatus.values)}
        </span>
        <span aria-live="polite">
          {tx("{completed} / {total} gaps filled · selected gap {selected}", {
            completed: value.filter((v) => v !== "").length,
            total: gaps,
            selected: selected + 1,
          })}
        </span>
        <button
          disabled={disabled}
          onClick={() => {
            onChange(Array(gaps).fill(""));
            setSelected(0);
          }}
        >
          {tx("Clear sentence")}
        </button>
      </div>
    </>
  );
}
const fixed = (slot: NonNullable<Question["slots"]>[number]) =>
  typeof slot === "string" ? slot : slot?.fixed || slot?.text || "";
function WritingEditor({
  q,
  value,
  onChange,
  disabled,
  strict,
  examStyle,
}: {
  q: Question;
  value: string;
  onChange: (v: string) => void;
  disabled: boolean;
  strict: boolean;
  examStyle: boolean;
}) {
  useI18n();
  const history = useRef([value]),
    index = useRef(0),
    editor = useRef<HTMLTextAreaElement>(null),
    clipboard = useRef(""),
    [showWordCount, setShowWordCount] = useState(true),
    [revision, setRevision] = useState(0);
  // A recovered local draft can arrive before the first edit. It becomes the
  // undo baseline, while subsequent user edits keep their own history.
  if (
    history.current.length === 1 &&
    index.current === 0 &&
    history.current[0] !== value
  )
    history.current[0] = value;
  const change = (text: string) => {
    if (disabled || text === value) return;
    history.current = history.current.slice(0, index.current + 1);
    history.current.push(text);
    if (history.current.length > 300) history.current.shift();
    index.current = history.current.length - 1;
    setRevision((r) => r + 1);
    onChange(text);
  };
  const undo = (delta: number) => {
    const next = index.current + delta;
    if (disabled || next < 0 || next >= history.current.length) return;
    index.current = next;
    onChange(history.current[next]);
    setRevision((r) => r + 1);
    editor.current?.focus();
  };
  const selectedText = () => {
    const field = editor.current;
    return field ? value.slice(field.selectionStart, field.selectionEnd) : "";
  };
  const rememberSelection = () => {
    if (disabled) return;
    const text = selectedText();
    if (text) {
      clipboard.current = text;
      setRevision((r) => r + 1);
    }
  };
  const replaceSelection = (text: string) => {
    const field = editor.current;
    if (disabled || !field) return;
    const start = field.selectionStart,
      end = field.selectionEnd;
    change(value.slice(0, start) + text + value.slice(end));
    requestAnimationFrame(() => {
      if (editor.current !== field) return;
      field.focus();
      field.setSelectionRange(start + text.length, start + text.length);
    });
  };
  const cut = () => {
    if (disabled || !selectedText()) return;
    rememberSelection();
    replaceSelection("");
  };
  const paste = () => {
    if (!disabled && clipboard.current) replaceSelection(clipboard.current);
  };
  return (
    <>
      {q.type === "build_sentence" && q.tokens?.length && (
        <>
          <div className="word-bank">
            {q.tokens.map((t, i) => (
              <button
                key={i}
                disabled={disabled}
                className="word-token"
                lang="en"
                onClick={() => change(`${value.trim()} ${t}`.trim())}
              >
                {t}
              </button>
            ))}
          </div>
          <p className="muted" style={{ fontSize: 10, marginTop: 10 }}>
            {tx(
              "This source has not yet been verified for fixed-slot interaction. Type the complete sentence, including its fixed words.",
            )}
          </p>
        </>
      )}
      <div className="editor-toolbar">
        {examStyle && (
          <>
            <Button
              kind="small"
              className="editor-cut"
              disabled={disabled}
              onMouseDown={(event) => event.preventDefault()}
              onClick={cut}
              aria-label={tx("Cut")}
            >
              {tx("Cut")}
            </Button>
            <Button
              kind="small"
              className="editor-paste"
              disabled={disabled || !clipboard.current}
              onMouseDown={(event) => event.preventDefault()}
              onClick={paste}
              aria-label={tx("Paste")}
            >
              {tx("Paste")}
            </Button>
          </>
        )}
        <Button
          kind="small"
          className="editor-undo"
          disabled={disabled || index.current === 0}
          onClick={() => undo(-1)}
          aria-label={tx("Undo")}
        >
          {!examStyle && <Icon name="undo" />}
          {tx("Undo")}
        </Button>
        <Button
          kind="small"
          className="editor-redo"
          disabled={disabled || index.current === history.current.length - 1}
          onClick={() => undo(1)}
          aria-label={tx("Redo")}
        >
          {!examStyle && <Icon name="redo" />}
          {tx("Redo")}
        </Button>
        {examStyle ? (
          <span className="editor-word-count-control">
            <button
              type="button"
              className="word-count-toggle"
              onClick={() => setShowWordCount((shown) => !shown)}
              aria-expanded={showWordCount}
              aria-controls={`word-count-${q.id}`}
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z" />
                <circle cx="12" cy="12" r="3" />
                {showWordCount && <path d="m4 20 16-16" />}
              </svg>
              {showWordCount ? tx("Hide Word Count") : tx("Show Word Count")}
            </button>
            <span
              className="editor-word-count"
              id={`word-count-${q.id}`}
              hidden={!showWordCount}
            >
              {wordCount(value)}
            </span>
          </span>
        ) : (
          <span>
            {strict
              ? tx("Spelling assistance off · Clipboard disabled")
              : tx("Spelling assistance off")}
          </span>
        )}
      </div>
      <textarea
        lang="en"
        ref={editor}
        value={value}
        onChange={(e) => change(e.target.value)}
        disabled={disabled}
        className={`writing-editor ${q.type === "build_sentence" ? "sentence" : ""}`}
        spellCheck={false}
        autoCorrect="off"
        autoCapitalize="off"
        autoComplete="off"
        aria-label={
          q.type === "build_sentence"
            ? tx("Complete sentence")
            : tx("Your written response")
        }
        placeholder={
          examStyle
            ? undefined
            : q.type === "build_sentence"
              ? tx("Type the complete sentence, including the fixed words.")
              : tx("Write your response here…")
        }
        onPaste={(e) => {
          if (strict) {
            e.preventDefault();
            if (examStyle) paste();
          }
        }}
        onCopy={(e) => {
          if (strict) e.preventDefault();
          if (examStyle) rememberSelection();
        }}
        onCut={(e) => {
          if (strict) {
            e.preventDefault();
            if (examStyle) cut();
          } else if (examStyle) rememberSelection();
        }}
        onKeyDown={(e) => {
          if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "z") {
            e.preventDefault();
            undo(e.shiftKey ? 1 : -1);
          } else if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "y") {
            e.preventDefault();
            undo(1);
          }
        }}
      />
      {!examStyle && (
        <div className="editor-meta">
          <span>
            {q.type === "academic_discussion"
              ? tx("An effective response contains at least 100 words.")
              : tx("Your response is saved locally.")}
          </span>
          <span>
            {tx("Word count:")}
            <b>{wordCount(value)}</b>
          </span>
        </div>
      )}
    </>
  );
}
