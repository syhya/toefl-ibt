import React from "react";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { setLocale } from "../../src/i18n";
import { DEFAULT_TIMING } from "../../src/api";
import { Rules, Settings, ReviewPage } from "../../src/pages";
import QuestionLibrary, { type PracticeGroup } from "../../src/QuestionLibrary";
import Mistakes, { type Mistake } from "../../src/Mistakes";
import type { Review } from "../../src/types";

beforeEach(() => {
  setLocale("en");
});
afterEach(() => {
  cleanup();
  setLocale("en");
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

it("switches the complete rules page while retaining official numeric limits", () => {
  const { container } = render(<Rules />);
  expect(
    screen.getByRole("heading", { name: "Know the rules before you begin." }),
  ).toBeTruthy();
  expect(container.textContent).not.toMatch(/[\u3400-\u9fff]/);
  expect(
    screen.getByText(/Repeat: 8–12 seconds; interview: 45 seconds/),
  ).toBeTruthy();
  act(() => setLocale("zh-CN"));
  expect(
    screen.getByRole("heading", { name: "了解规则，再走进练习。" }),
  ).toBeTruthy();
  expect(screen.getByText(/复述 8–12 秒；采访每题 45 秒/)).toBeTruthy();
});

it("preserves unsaved timing values when switching language and submits canonical timing keys", () => {
  vi.stubGlobal("FormData", window.FormData);
  const save = vi.fn();
  render(<Settings timing={DEFAULT_TIMING} onSave={save} />);
  fireEvent.change(
    screen.getByRole("spinbutton", { name: /Reading · Module 1/ }),
    { target: { value: "700" } },
  );
  act(() => setLocale("zh-CN"));
  expect(
    (
      screen.getByRole("spinbutton", {
        name: /阅读 · Module 1/,
      }) as HTMLInputElement
    ).value,
  ).toBe("700");
  fireEvent.click(screen.getByRole("button", { name: "保存设置" }));
  expect(save).toHaveBeenCalledExactlyOnceWith({
    ...DEFAULT_TIMING,
    readingCommon: 700,
  });
});

function reviewFixture(): Review {
  return {
    session: {
      id: "bilingual-review",
      examId: "original-source",
      title: "Original source test",
      mode: "practice",
      scope: "writing",
      routeMode: "fixed",
      route: "upper",
      status: "completed",
      phase: "complete",
      stageIndex: 1,
      questionIndex: 0,
      revision: 1,
      serverNow: 1000,
      startedAt: 1000,
      deadline: null,
      remainingSeconds: null,
      allowedActions: [],
    },
    sections: [
      {
        id: "writing",
        modules: [
          {
            id: "w",
            title: "Original writing module",
            questions: [
              {
                id: "original-email",
                type: "email",
                number: 11,
                prompt: "Write an email to your professor.",
                explanation: {
                  origin: "source",
                  label: "原资料解析",
                  text: "原作者的中文解析 — preserve this source text.",
                },
              },
            ],
          },
        ],
      },
    ],
    answers: {
      "original-email": "Dear Professor, this is my original answer.",
    },
    ratings: {},
    recordings: {},
    score: { correct: 0, total: 0 },
    events: [],
  };
}

it("keeps source text, answers, and unfinished self-assessments intact across review language changes", () => {
  render(
    <ReviewPage
      review={reviewFixture()}
      materials={[]}
      onHistory={vi.fn()}
      onWrongPractice={vi.fn()}
      onNotice={vi.fn()}
    />,
  );
  fireEvent.change(
    screen.getByRole("combobox", { name: "Self-assessment score" }),
    { target: { value: "4" } },
  );
  fireEvent.change(screen.getByRole("textbox", { name: "Review notes" }), {
    target: { value: "Keep this unsaved note." },
  });
  expect(
    screen.getByRole("table", { name: "Score overview by section" }),
  ).toBeTruthy();
  act(() => setLocale("zh-CN"));
  expect(screen.getByRole("table", { name: "本次分科评分概览" })).toBeTruthy();
  expect(
    (screen.getByRole("combobox", { name: "自评分" }) as HTMLSelectElement)
      .value,
  ).toBe("4");
  expect(
    (screen.getByRole("textbox", { name: "复盘笔记" }) as HTMLInputElement)
      .value,
  ).toBe("Keep this unsaved note.");
  expect(screen.getByText("Write an email to your professor.")).toBeTruthy();
  expect(
    screen.getByText("Dear Professor, this is my original answer."),
  ).toBeTruthy();
  expect(
    screen.getByText("原作者的中文解析 — preserve this source text."),
  ).toBeTruthy();
  act(() => setLocale("en"));
  expect(
    screen.getByText("原作者的中文解析 — preserve this source text."),
  ).toBeTruthy();
});

it("localizes group-library controls without refetching or changing full source membership", async () => {
  vi.useFakeTimers();
  const source: PracticeGroup = {
    groupId: "original-cloze-group",
    groupContentId: "group-revision-original",
    questionIds: ["original-cloze"],
    examId: "source-test",
    examTitle: "原始资料名称",
    section: "reading",
    module: "Original module",
    moduleId: "original-module",
    route: "common",
    taskType: "cloze",
    numberStart: 1,
    numberEnd: 10,
    screenCount: 1,
    itemCount: 10,
    completedCount: 0,
    hasAudio: false,
    status: "not_started",
    audioCount: 0,
    duplicateCount: 2,
  };
  const fetch = vi.fn(
    async () =>
      new Response(
        JSON.stringify({ items: [source], total: 1, page: 1, pageSize: 18 }),
      ),
  );
  vi.stubGlobal("fetch", fetch);
  const practice = vi.fn();
  render(<QuestionLibrary practice={practice} />);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(160);
  });
  expect(
    screen.getByRole("heading", { name: "One task type at a time." }),
  ).toBeTruthy();
  const calls = fetch.mock.calls.length;
  act(() => setLocale("zh-CN"));
  expect(fetch).toHaveBeenCalledTimes(calls);
  expect(
    screen.getByRole("heading", { name: "一次专注，一种题型。" }),
  ).toBeTruthy();
  expect(screen.getByRole("heading", { name: "原始资料名称" })).toBeTruthy();
  expect(screen.getByRole("heading", { name: "Original module" })).toBeTruthy();
  expect(screen.getByText("10 道小题")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: /^开始本组：/ }));
  expect(practice).toHaveBeenCalledExactlyOnceWith(source);
});

it("switches mistake statuses and actions without losing the original review target", async () => {
  vi.useFakeTimers();
  const source: Mistake = {
    mistakeId: "mistake-source",
    questionId: "source-question",
    examId: "source-test",
    examTitle: "Original test name",
    section: "reading",
    taskType: "choice",
    number: 1,
    title: "Original item title",
    wrongAttempts: 2,
    attempts: 3,
    lastAttemptAt: 1000,
    lastSessionId: "latest-session",
    lastWrongSessionId: "wrong-session",
    lastGrade: { correct: 1, total: 1 },
    status: "needs_review",
    available: true,
  };
  const fetch = vi.fn(
    async () =>
      new Response(
        JSON.stringify({
          items: [source],
          total: 1,
          page: 1,
          pageSize: 24,
          summary: { total: 1, needsReview: 1, mastered: 0, attempts: 3 },
        }),
      ),
  );
  vi.stubGlobal("fetch", fetch);
  const review = vi.fn();
  render(<Mistakes practice={vi.fn()} review={review} />);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(160);
  });
  expect(
    screen.getByRole("heading", { name: "Mistakes", exact: true }),
  ).toBeTruthy();
  act(() => setLocale("zh-CN"));
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(
    screen.getByRole("heading", { name: "错题集", exact: true }),
  ).toBeTruthy();
  expect(screen.getByText(/错误 2 次 \/ 作答 3 次 · 最近 1\/1/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "查看错题复盘" }));
  expect(review).toHaveBeenCalledExactlyOnceWith("wrong-session");
});
