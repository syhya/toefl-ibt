import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import AnswerComparison from "../../src/AnswerComparison";
import { setLocale } from "../../src/i18n";
import type { Answer, Blank, Question } from "../../src/types";

beforeEach(() => setLocale("zh-CN"));
afterEach(() => {
  cleanup();
  setLocale("en");
});

type ReviewBlank = Blank & {
  acceptedAnswers?: string[];
  auditStatus?: string;
  answerConflict?: unknown;
};
function cloze(
  blanks: ReviewBlank[],
  correct: number,
  total = blanks.length,
): Question {
  return {
    id: "review-cloze",
    type: "cloze",
    number: 1,
    blanks,
    grade: { correct, total },
  };
}
const complete: ReviewBlank = {
  id: "b6",
  number: 6,
  prefix: "complet",
  missingLetters: "ely",
  answer: "ely",
  fullWord: "completely",
  acceptedAnswers: ["ely", "completely"],
};
function blankRow(id: string): HTMLElement {
  const row = document.querySelector(`[data-blank-id="${id}"]`);
  expect(row).toBeTruthy();
  return row as HTMLElement;
}
function choiceRow(id: string): HTMLElement {
  return document.querySelector(`[data-choice-id="${id}"]`) as HTMLElement;
}
function coloredRows(): Element[] {
  return [
    ...document.querySelectorAll(
      ".answer-comparison-row.is-correct, .answer-comparison-row.is-incorrect, .answer-comparison-choice.is-correct, .answer-comparison-choice.is-incorrect",
    ),
  ];
}

describe("per-blank answer comparison", () => {
  it("makes the screenshot's b6 tly/ely mistake explicit among nine correct blanks and saves the correct full word", () => {
    const blanks: ReviewBlank[] = Array.from({ length: 10 }, (_, index) =>
      index === 5
        ? complete
        : {
            id: `b${index + 1}`,
            number: index + 1,
            prefix: "wo",
            answer: "rd",
            fullWord: "word",
            missingLetters: "rd",
          },
    );
    const answer: Answer = Object.fromEntries(
      blanks.map((blank) => [blank.id, blank.id === "b6" ? "tly" : "rd"]),
    );
    const onAddWord = vi.fn();
    const question = {
      ...cloze(blanks, 9),
      passageTemplate: "The task was complet{{b6}} finished.",
    };
    render(
      <AnswerComparison
        question={question}
        answer={answer}
        onAddWord={onAddWord}
      />,
    );
    const table = screen.getByRole("table", { name: "逐空答案对照" });
    expect(
      within(table)
        .getAllByRole("columnheader")
        .map((element) => element.textContent),
    ).toEqual(["题号", "我的输入", "参考答案", "结果"]);
    expect(within(table).getAllByRole("row")).toHaveLength(11);
    const sixth = blankRow("b6");
    expect(sixth.classList.contains("is-incorrect")).toBe(true);
    expect(within(sixth).getAllByText("tly")).toHaveLength(2);
    expect(within(sixth).getByText("错误")).toBeTruthy();
    expect(
      sixth.querySelectorAll(".answer-comparison-word")[0].textContent,
    ).toBe("complettly");
    expect(
      sixth.querySelectorAll(".answer-comparison-word")[1].textContent,
    ).toBe("completely");
    expect(
      document.querySelectorAll(".answer-comparison-row.is-correct"),
    ).toHaveLength(9);
    expect(
      document.querySelectorAll(".answer-comparison-row.is-incorrect"),
    ).toHaveLength(1);
    expect(screen.getAllByRole("button")).toHaveLength(10);
    fireEvent.click(
      within(sixth).getByRole("button", {
        name: "添加 completely 到单词本 · 第 6 题",
      }),
    );
    expect(onAddWord).toHaveBeenCalledExactlyOnceWith({
      word: "completely",
      context: "The task was completely finished.",
      sourceQuestionId: "review-cloze",
      sourceLabel: "第 6 题",
    });
  });

  it.each(["ely", "completely", "  ＣＯＭＰＬＥＴＥＬＹ\u0085"])(
    "accepts missing letters or the complete word using server normalization: %s",
    (value) => {
      render(
        <AnswerComparison
          question={cloze([complete], 1)}
          answer={{ b6: value }}
        />,
      );
      expect(blankRow("b6").classList.contains("is-correct")).toBe(true);
      expect(screen.queryByText("错误")).toBeNull();
    },
  );

  it("accepts alternate missing-letter variants and displays their complete words", () => {
    const variant = {
      id: "b1",
      prefix: "orga",
      missingLetters: "nise",
      answer: "nise",
      fullWord: "organise",
      acceptedAnswers: ["nize", "organize", "organise"],
    };
    render(
      <AnswerComparison
        question={cloze([variant], 1)}
        answer={{ b1: "nize" }}
      />,
    );
    expect(blankRow("b1").classList.contains("is-correct")).toBe(true);
    expect(screen.getByText("也接受：")).toBeTruthy();
    expect(blankRow("b1").textContent).toContain("organize");
    expect(screen.queryByText("错误")).toBeNull();
  });

  it("shows prefix + missing letters + suffix without adding a new grading rule", () => {
    const blank = {
      id: "b1",
      prefix: "walk",
      suffix: "ing",
      answer: "walkthing",
      fullWord: "walkthing",
    };
    render(
      <AnswerComparison question={cloze([blank], 0)} answer={{ b1: "th" }} />,
    );
    expect(blankRow("b1").classList.contains("is-incorrect")).toBe(true);
    expect(
      blankRow("b1").querySelector(".answer-comparison-word")?.textContent,
    ).toBe("walkthing");
    // Matching the displayed complete word is insufficient: engine.grade only
    // accepts the missing substring when missingLetters/acceptedAnswers says so.
  });

  it("keeps skipped blanks neutral and distinct from wrong entries", () => {
    render(
      <AnswerComparison
        question={cloze([complete, { ...complete, id: "b7", number: 7 }], 0)}
        answer={{ b7: "tly" }}
      />,
    );
    expect(blankRow("b6").classList.contains("is-unanswered")).toBe(true);
    expect(within(blankRow("b6")).getAllByText("未作答")).toHaveLength(2);
    expect(blankRow("b7").classList.contains("is-incorrect")).toBe(true);
  });

  it("leaves a whole unanswered question neutral", () => {
    render(<AnswerComparison question={cloze([complete], 0)} />);
    expect(blankRow("b6").classList.contains("is-unanswered")).toBe(true);
    expect(coloredRows()).toHaveLength(0);
  });

  it("never invents correctness for an ungraded question", () => {
    render(
      <AnswerComparison
        question={{ ...cloze([complete], 0), grade: null }}
        answer={{ b6: "tly" }}
      />,
    );
    expect(blankRow("b6").classList.contains("is-unscored")).toBe(true);
    expect(screen.getByText("未评分")).toBeTruthy();
    expect(coloredRows()).toHaveLength(0);
  });

  it("excludes conflicting blanks from the scored denominator and disables their vocabulary action", () => {
    const conflict = {
      ...complete,
      id: "conflict",
      answerConflict: { status: "needs-review" },
    };
    render(
      <AnswerComparison
        question={cloze([complete, conflict], 1, 1)}
        answer={{ b6: "ely", conflict: "tly" }}
        onAddWord={vi.fn()}
      />,
    );
    expect(blankRow("b6").classList.contains("is-correct")).toBe(true);
    expect(blankRow("conflict").classList.contains("is-conflict")).toBe(true);
    expect(within(blankRow("conflict")).getByText("答案待核验")).toBeTruthy();
    expect(
      (within(blankRow("conflict")).getByRole("button") as HTMLButtonElement)
        .disabled,
    ).toBe(true);
  });

  it("keeps a question-wide answer conflict neutral even with a grade present", () => {
    render(
      <AnswerComparison
        question={{ ...cloze([complete], 0), auditStatus: "answer-conflict" }}
        answer={{ b6: "tly" }}
      />,
    );
    expect(blankRow("b6").classList.contains("is-conflict")).toBe(true);
    expect(coloredRows()).toHaveLength(0);
  });

  it("does not override a saved server score when local detail disagrees", () => {
    render(
      <AnswerComparison
        question={cloze([complete], 1)}
        answer={{ b6: "tly" }}
      />,
    );
    expect(blankRow("b6").classList.contains("is-uncertain")).toBe(true);
    expect(screen.getByText(/当前答案无法可靠还原/)).toBeTruthy();
    expect(coloredRows()).toHaveLength(0);
  });

  it("does not mistake an unsupported blank value's JavaScript coercion for a server match", () => {
    render(
      <AnswerComparison
        question={cloze([complete], 0)}
        answer={{ b6: ["tly"] }}
      />,
    );
    expect(blankRow("b6").classList.contains("is-uncertain")).toBe(true);
    expect(coloredRows()).toHaveLength(0);
  });

  it("uses the blanks array order and falls back to the question's starting number", () => {
    const blanks = ["b10", "b2"].map((id) => ({
      ...complete,
      number: undefined,
      id,
    }));
    render(
      <AnswerComparison
        question={{ ...cloze(blanks, 2), number: 11 }}
        answer={{ b10: "ely", b2: "ely" }}
      />,
    );
    expect(
      screen.getAllByRole("rowheader").map((item) => item.textContent),
    ).toEqual(["11b10", "12b2"]);
  });
});

const choice: Question = {
  id: "choice",
  type: "choice",
  answer: "B",
  grade: { correct: 0, total: 1 },
  choices: [
    { id: "A", text: "One option" },
    { id: "B", text: "Reference option" },
    { id: "C", text: "Third option" },
  ],
};
describe("choice and sentence comparison", () => {
  it("highlights a wrong selected option and the correct reference with explicit text", () => {
    render(<AnswerComparison question={choice} answer="A" />);
    expect(choiceRow("A").classList.contains("is-incorrect")).toBe(true);
    expect(within(choiceRow("A")).getByText("你的选择")).toBeTruthy();
    expect(within(choiceRow("A")).getByText("错误")).toBeTruthy();
    expect(choiceRow("B").classList.contains("is-correct")).toBe(true);
    expect(within(choiceRow("B")).getByText("参考正确选项")).toBeTruthy();
    expect(choiceRow("C").classList.contains("is-neutral")).toBe(true);
  });

  it("does not color ungraded or unanswered choices", () => {
    const view = render(
      <AnswerComparison question={{ ...choice, grade: null }} answer="A" />,
    );
    expect(screen.getByText("未评分")).toBeTruthy();
    expect(coloredRows()).toHaveLength(0);
    view.rerender(<AnswerComparison question={choice} />);
    expect(coloredRows()).toHaveLength(0);
    expect(screen.getAllByText("未作答")).toHaveLength(2);
  });

  it("treats answer arrays as alternative accepted answers, as the server does", () => {
    render(
      <AnswerComparison
        question={{
          ...choice,
          answer: ["A", "C"],
          grade: { correct: 1, total: 1 },
        }}
        answer="C"
      />,
    );
    expect(screen.getByText("正确")).toBeTruthy();
    expect(choiceRow("C").classList.contains("is-correct")).toBe(true);
    expect(screen.queryByText("错误")).toBeNull();
  });

  it("compares a submitted multi-option response to the joined reference without assuming set scoring", () => {
    render(
      <AnswerComparison
        question={{ ...choice, answer: "A C" }}
        answer={["A", "B"]}
      />,
    );
    expect(choiceRow("B").classList.contains("is-incorrect")).toBe(true);
    expect(choiceRow("A").classList.contains("is-correct")).toBe(true);
    expect(choiceRow("C").classList.contains("is-correct")).toBe(true);
    expect(screen.getByText("A. One option / C. Third option")).toBeTruthy();
  });

  it("keeps uncertain choice detail neutral when it contradicts the server grade", () => {
    render(
      <AnswerComparison
        question={{ ...choice, grade: { correct: 1, total: 1 } }}
        answer="A"
      />,
    );
    expect(screen.getByText("细分结果待核验")).toBeTruthy();
    expect(coloredRows()).toHaveLength(0);
  });

  const sentence: Question = {
    id: "sentence",
    type: "build_sentence",
    answer: "We use the words.",
    tokens: ["words", "the"],
    slots: [{ fixed: "We use" }, { id: "one" }, { id: "two" }, { fixed: "." }],
    grade: { correct: 0, total: 1 },
  };
  it("reconstructs word-bank answers and marks the whole incorrect sentence", () => {
    render(
      <AnswerComparison
        question={sentence}
        answer={{ tokenOrder: ["0", "1"] }}
      />,
    );
    const response = document.querySelector(".answer-comparison-response");
    expect(response?.textContent).toContain("We use words the.");
    expect(response?.classList.contains("is-incorrect")).toBe(true);
    expect(screen.getByText("We use the words.")).toBeTruthy();
  });

  it("accepts a sentence variant without treating terminal punctuation as an error", () => {
    render(
      <AnswerComparison
        question={{
          ...sentence,
          acceptedAnswers: ["We use words the!"],
          grade: { correct: 1, total: 1 },
        }}
        answer={{ tokenOrder: ["0", "1"] }}
      />,
    );
    expect(screen.getByText("正确")).toBeTruthy();
    expect(screen.queryByText("错误")).toBeNull();
  });

  it("renders partial sentence gaps and leaves a fully empty token order unanswered", () => {
    const view = render(
      <AnswerComparison
        question={sentence}
        answer={{ tokenOrder: ["1", ""] }}
      />,
    );
    expect(screen.getByText("We use the ____.")).toBeTruthy();
    expect(screen.getByText("错误")).toBeTruthy();
    view.rerender(
      <AnswerComparison
        question={sentence}
        answer={{ tokenOrder: ["", ""] }}
      />,
    );
    expect(screen.queryByText("错误")).toBeNull();
    expect(screen.getAllByText("未作答")).toHaveLength(2);
  });

  it("shows subjective writing neutrally and leaves recordings to the parent", () => {
    render(
      <AnswerComparison
        question={{ id: "writing", type: "email", grade: null }}
        answer="My draft email."
      />,
    );
    expect(screen.getByText("未评分")).toBeTruthy();
    expect(screen.getByText("My draft email.")).toBeTruthy();
    expect(screen.getByText(/本题不自动评分/)).toBeTruthy();
    expect(document.querySelector("audio")).toBeNull();
  });

  it("localizes product labels while retaining the original answer text", () => {
    setLocale("en");
    render(
      <AnswerComparison
        question={cloze([complete], 0)}
        answer={{ b6: "tly" }}
        onAddWord={vi.fn()}
      />,
    );
    expect(
      screen.getByRole("table", { name: "Compare each blank" }),
    ).toBeTruthy();
    expect(screen.getByText("Incorrect")).toBeTruthy();
    expect(
      screen.getByRole("button", {
        name: "Add completely to word book · question 6",
      }),
    ).toBeTruthy();
    expect(screen.getAllByText("tly")).toHaveLength(2);
  });
});
