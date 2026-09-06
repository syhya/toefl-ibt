import { useRef, useState, type ReactNode } from "react";
import { useI18n } from "./i18n";
import { Button } from "./components";
import Icon from "./Icons";
import type { VocabularyDraft } from "./Vocabulary";
import "./vocabulary-capture.css";

/** Offer a local vocabulary entry for selected review text, never editable answers. */
export default function VocabularyCapture({
  children,
  onAdd,
  sourceLabel,
  sourceSessionId,
}: {
  children: ReactNode;
  onAdd?: (draft: VocabularyDraft) => void;
  sourceLabel: string;
  sourceSessionId?: string;
}) {
  const { t } = useI18n();
  const root = useRef<HTMLDivElement>(null);
  const [selection, setSelection] = useState<VocabularyDraft | null>(null);
  function capture() {
    if (!onAdd) return;
    const selected = window.getSelection();
    if (!selected || selected.isCollapsed || selected.rangeCount !== 1) {
      setSelection(null);
      return;
    }
    const range = selected.getRangeAt(0);
    if (!root.current?.contains(range.commonAncestorContainer)) {
      setSelection(null);
      return;
    }
    const element =
      range.startContainer.nodeType === Node.ELEMENT_NODE
        ? (range.startContainer as Element)
        : range.startContainer.parentElement;
    if (element?.closest("input, textarea, button, [contenteditable=true]")) {
      setSelection(null);
      return;
    }
    const word = selected
      .toString()
      .trim()
      .replace(/^[\s.,:;!?()[\]{}“”"]+|[\s.,:;!?()[\]{}“”"]+$/g, "");
    if (!word || word.length > 120 || !/[a-z]/i.test(word) || /\n/.test(word)) {
      setSelection(null);
      return;
    }
    const article = element?.closest<HTMLElement>("[data-question-id]");
    const paragraph = element?.closest("p, li, td, .passage, .prompt");
    const text = (paragraph?.textContent || word).replace(/\s+/g, " ").trim();
    // Use the selected occurrence, including when a passage repeats the word.
    const before = range.cloneRange();
    if (paragraph) {
      before.selectNodeContents(paragraph);
      before.setEnd(range.startContainer, range.startOffset);
    }
    const position = paragraph
      ? before.toString().replace(/\s+/g, " ").trimStart().length
      : 0;
    const start = Math.max(0, position - 160);
    const context = text.slice(start, Math.min(text.length, start + 450));
    setSelection({
      word,
      context,
      sourceLabel: (article?.dataset.vocabularySource || sourceLabel).slice(
        0,
        240,
      ),
      sourceQuestionId: article?.dataset.questionId,
      sourceSessionId,
    });
  }
  return (
    <div
      ref={root}
      className="vocabulary-capture"
      onMouseUp={capture}
      onKeyUp={capture}
    >
      {children}
      {selection && onAdd && (
        <aside
          className="vocabulary-selection"
          aria-label={t("Save selected vocabulary", "收藏选中的生词")}
        >
          <span title={selection.word}>{selection.word}</span>
          <Button
            kind="primary small"
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => {
              onAdd(selection);
              setSelection(null);
            }}
          >
            <Icon name="bookmark" />
            {t("Add to vocabulary", "加入单词本")}
          </Button>
          <button
            type="button"
            className="vocabulary-selection-close"
            aria-label={t("Dismiss selection", "关闭生词收藏")}
            onClick={() => setSelection(null)}
          >
            <Icon name="close" />
          </button>
        </aside>
      )}
    </div>
  );
}
