import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import VocabularyCapture from "../../src/VocabularyCapture";
import { setLocale } from "../../src/i18n";

beforeEach(() => setLocale("en"));
afterEach(() => {
  window.getSelection()?.removeAllRanges();
  cleanup();
});

function selectText(element: HTMLElement, word: string, last = false) {
  const text = element.firstChild!;
  const start = last
    ? text.textContent!.lastIndexOf(word)
    : text.textContent!.indexOf(word);
  const range = document.createRange();
  range.setStart(text, start);
  range.setEnd(text, start + word.length);
  const selection = window.getSelection()!;
  selection.removeAllRanges();
  selection.addRange(range);
  fireEvent.mouseUp(element);
}

it("captures the selected word with sentence, question, and session provenance", () => {
  const onAdd = vi.fn();
  render(
    <VocabularyCapture
      onAdd={onAdd}
      sourceLabel="Practice"
      sourceSessionId="session-1"
    >
      <article
        data-question-id="question-6"
        data-vocabulary-source="Practice · Reading · 6"
      >
        <p>Consider the word “accurately” in this sentence.</p>
      </article>
    </VocabularyCapture>,
  );
  selectText(screen.getByText(/Consider the word/), "“accurately”");
  fireEvent.click(screen.getByRole("button", { name: "Add to vocabulary" }));
  expect(onAdd).toHaveBeenCalledWith({
    word: "accurately",
    context: "Consider the word “accurately” in this sentence.",
    sourceLabel: "Practice · Reading · 6",
    sourceQuestionId: "question-6",
    sourceSessionId: "session-1",
  });
  expect(screen.queryByRole("complementary")).toBeNull();
});

it("keeps context around the selected occurrence when the word repeats", () => {
  const onAdd = vi.fn();
  const paragraph = `The first word is accurate. ${"Earlier sentence. ".repeat(40)}The later measurement is accurate and reliable.`;
  render(
    <VocabularyCapture onAdd={onAdd} sourceLabel="Practice">
      <p>{paragraph}</p>
    </VocabularyCapture>,
  );
  selectText(screen.getByText(paragraph), "accurate", true);
  fireEvent.click(screen.getByRole("button", { name: "Add to vocabulary" }));
  expect(onAdd.mock.calls[0][0].context).toContain(
    "The later measurement is accurate and reliable.",
  );
  expect(onAdd.mock.calls[0][0].context).not.toContain("The first word");
});

it("ignores editable text and clears a dismissed selection", () => {
  const onAdd = vi.fn();
  render(
    <VocabularyCapture onAdd={onAdd} sourceLabel="Practice">
      <p>Read carefully.</p>
      <div contentEditable suppressContentEditableWarning>
        unsubmitted
      </div>
    </VocabularyCapture>,
  );
  selectText(screen.getByText("Read carefully."), "carefully");
  expect(screen.getByRole("complementary")).toBeTruthy();
  selectText(screen.getByText("unsubmitted"), "unsubmitted");
  expect(screen.queryByRole("complementary")).toBeNull();
  selectText(screen.getByText("Read carefully."), "carefully");
  fireEvent.click(screen.getByRole("button", { name: "Dismiss selection" }));
  expect(screen.queryByRole("complementary")).toBeNull();
  expect(onAdd).not.toHaveBeenCalled();
});

it("does not offer numbers, excessive selections, or capture without an add handler", () => {
  const { rerender } = render(
    <VocabularyCapture onAdd={vi.fn()} sourceLabel="Practice">
      <p>{`123 ${"a".repeat(121)}`}</p>
    </VocabularyCapture>,
  );
  const paragraph = screen.getByText(/^123/);
  selectText(paragraph, "123");
  expect(screen.queryByRole("complementary")).toBeNull();
  selectText(paragraph, "a".repeat(121));
  expect(screen.queryByRole("complementary")).toBeNull();
  rerender(
    <VocabularyCapture sourceLabel="Practice">
      <p>carefully</p>
    </VocabularyCapture>,
  );
  selectText(screen.getByText("carefully"), "carefully");
  expect(screen.queryByRole("complementary")).toBeNull();
});
