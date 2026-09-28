import { setLocale } from "../../src/i18n";
import React from "react";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ReviewPage } from "../../src/pages";
import type { Review } from "../../src/types";
import englishExplanations from "../../shared/example1-explanations.en.json";
import chineseExplanations from "../../shared/example1-explanations.zh-CN.json";

beforeEach(() => setLocale("zh-CN"));

afterEach(() => {
  setLocale("en");
  cleanup();
  vi.unstubAllGlobals();
});

function reviewFixture(): Review {
  return {
    session: {
      id: "review-score-fixture",
      examId: "selected-source-exam",
      title: "Isolated scoring review",
      mode: "practice",
      scope: "all",
      routeMode: "fixed",
      route: "upper",
      status: "completed",
      phase: "complete",
      stageIndex: 4,
      questionIndex: 0,
      revision: 1,
      serverNow: 1000000,
      startedAt: 1000,
      deadline: null,
      remainingSeconds: null,
      allowedActions: [],
      integrity: { interrupted: false },
    },
    sections: [
      {
        id: "reading",
        modules: [
          {
            id: "r",
            title: "Reading source",
            questions: [
              {
                id: "cloze",
                type: "cloze",
                number: 1,
                numberEnd: 3,
                grade: { correct: 2, total: 3 },
              },
              {
                id: "reading-choice",
                type: "choice",
                number: 4,
                grade: { correct: 1, total: 1 },
              },
              { id: "unresolved-key", type: "choice", number: 5, grade: null },
            ],
          },
        ],
      },
      {
        id: "listening",
        modules: [
          {
            id: "l",
            title: "Listening source",
            questions: [
              {
                id: "listening-choice",
                type: "choice",
                number: 1,
                grade: { correct: 0, total: 1 },
              },
            ],
          },
        ],
      },
      {
        id: "writing",
        modules: [
          {
            id: "w",
            title: "Writing source",
            questions: [
              {
                id: "build",
                type: "build_sentence",
                number: 1,
                grade: { correct: 1, total: 1 },
              },
              { id: "email", type: "email", number: 11, grade: null },
              {
                id: "discussion",
                type: "academic_discussion",
                number: 12,
                grade: null,
              },
            ],
          },
        ],
      },
      {
        id: "speaking",
        modules: [
          {
            id: "s",
            title: "Speaking source",
            questions: [
              { id: "repeat", type: "listen_repeat", number: 1, grade: null },
              { id: "interview", type: "interview", number: 8, grade: null },
            ],
          },
        ],
      },
    ],
    answers: {},
    recordings: {},
    score: { correct: 4, total: 6 },
    ratings: {
      email: { value: 4 },
      repeat: { value: 0 },
      "outside-this-selection": { value: 5 },
    },
    events: [],
  };
}

function show(review: Review) {
  return render(
    <ReviewPage
      review={review}
      materials={[]}
      onHistory={vi.fn()}
      onWrongPractice={vi.fn()}
      onNotice={vi.fn()}
    />,
  );
}

it("discloses other recovered audio editions without linking them to the unrelated Student 1 overview", () => {
  const review = reviewFixture();
  review.sections![3].modules[0].questions![1].sourceVariant = {
    id: "experience-2-original-audio",
    paperPrompt: "The retained paper prompt differs from this recording.",
    paperPage: 40,
  };
  show(review);
  expect(screen.getByText("音频版本 · 查看与纸面题目的差异")).toBeTruthy();
  expect(
    screen.getByText("The retained paper prompt differs from this recording."),
  ).toBeTruthy();
  expect(screen.queryByRole("link", { name: /ETS Test Overview/ })).toBeNull();
});

it("keeps legacy English-only rationales readable without misattributing them to the source", () => {
  const review = reviewFixture();
  const q = review.sections![1].modules[0].questions![0];
  q.explanation = {
    origin: "local_assistance",
    label: "Reviewed explanation · Not ETS-authored",
    language: "en",
    reviewed: true,
    text: "Correct answer: A. I overslept. This indirectly explains missing the seminar.",
    evidence: ["B: The question asks about attendance, not performance."],
    warnings: ["An unrelated next-task segment was removed."],
    source: { page: 18, materialId: "question-paper" },
  };
  q.sourceReferenceAnswer = "A";
  q.resolutionEvidence = { oldNote: "旧版中文解析校核内容" };
  q.answerConflict = {
    status: "resolved-from-source",
    reason: "旧版中文键差异",
  };
  q.explanationConflict = { resolutionEvidence: "旧版中文解析冲突" };
  show(review);
  expect(screen.getByText(q.explanation.label!)).toBeTruthy();
  const body = screen.getByText(q.explanation.text);
  expect(body.getAttribute("lang")).toBe("en");
  expect(
    screen
      .getByText(q.explanation.evidence![0])
      .closest("ul")
      ?.getAttribute("lang"),
  ).toBe("en");
  expect(
    screen.getByText(q.explanation.evidence![0]).closest("blockquote"),
  ).toBeNull();
  expect(
    screen.getByText(q.explanation.warnings![0]).getAttribute("lang"),
  ).toBe("en");
  expect(screen.getByText("原题来源 · 第 18 页")).toBeTruthy();
  expect(screen.queryByText(/旧版中文解析校核内容/)).toBeNull();
  expect(screen.queryByText(/旧版中文键差异/)).toBeNull();
  expect(screen.queryByText(/旧版中文解析冲突/)).toBeNull();
  expect(screen.queryByText(/资料解析来源 · 第 18 页/)).toBeNull();
});

it("switches the full reviewed rationale, distractors and warnings with the interface language", () => {
  const review = reviewFixture();
  const q = review.sections![1].modules[0].questions![0];
  const en = englishExplanations.questions["student-1-l1-8"];
  const zh = chineseExplanations.questions["student-1-l1-8"];
  q.explanation = {
    origin: "local_assistance",
    label: "Reviewed explanation · Not ETS-authored",
    language: "en",
    reviewed: true,
    text: en.text,
    evidence: en.evidence,
    warnings: en.warnings,
    source: { page: 18, materialId: "question-paper" },
    translations: {
      "zh-CN": {
        language: "zh-CN",
        label: "校核解析 · 非 ETS 官方编写",
        text: zh.text,
        evidence: zh.evidence,
        warnings: zh.warnings,
      },
    },
  };
  q.resolutionEvidence = { oldNote: "旧版中文解析校核内容" };
  q.explanationConflict = { resolutionEvidence: "旧版中文解析冲突" };
  const saved = JSON.stringify(review);
  show(review);
  for (const language of ["zh-CN", "en", "zh-CN"] as const) {
    act(() => setLocale(language));
    const expected = language === "zh-CN" ? zh : en;
    const hidden = language === "zh-CN" ? en : zh;
    expect(
      screen.getByText(expected.text.replace(/\s+/g, " ")).getAttribute("lang"),
    ).toBe(language);
    for (const reason of expected.evidence) {
      expect(screen.getByText(reason).closest("ul")?.getAttribute("lang")).toBe(
        language,
      );
    }
    expect(screen.getByText(expected.warnings[0]).getAttribute("lang")).toBe(
      language,
    );
    expect(screen.queryByText(hidden.text.replace(/\s+/g, " "))).toBeNull();
    expect(screen.queryByText(hidden.evidence[0])).toBeNull();
    expect(screen.queryByText(hidden.warnings[0])).toBeNull();
    expect(
      screen.getByText(
        language === "zh-CN"
          ? "校核解析 · 非 ETS 官方编写"
          : "Reviewed explanation · Not ETS-authored",
      ),
    ).toBeTruthy();
    expect(screen.queryByText(/旧版中文解析/)).toBeNull();
    expect(JSON.stringify(review)).toBe(saved);
  }
});

it("shows the withheld-explanation notice in Chinese when the source binding fails", () => {
  const review = reviewFixture();
  const q = review.sections![1].modules[0].questions![0];
  q.explanation = {
    origin: "unavailable",
    reviewed: true,
    language: "en",
    label: "Explanation requires a new source check",
    text: "This saved question differs from the reviewed version.",
    translations: {
      "zh-CN": {
        language: "zh-CN",
        label: "解析需要重新核验来源",
        text: "此题与校核版本不一致，暂不展示校核解析。",
        evidence: [],
        warnings: [],
      },
    },
  };
  show(review);
  expect(screen.getByText("解析需要重新核验来源")).toBeTruthy();
  expect(
    screen
      .getByText("此题与校核版本不一致，暂不展示校核解析。")
      .getAttribute("lang"),
  ).toBe("zh-CN");
  expect(screen.queryByText(q.explanation.text)).toBeNull();
});

it("offers manual original-prompt playback in review without autoplay or optional PDFs", () => {
  const review = reviewFixture();
  review.sections![1].modules[0].questions![0].mediaSequence = [
    {
      url: "/api/sessions/review-fixture/review-assets/original-prompt",
      mediaType: "audio",
      durationSeconds: 16,
    },
  ];
  show(review);
  fireEvent.click(screen.getByText("展开原音、原文与原题图"));
  const source = screen.getByLabelText("原题音频 1") as HTMLAudioElement;
  expect(source.tagName).toBe("AUDIO");
  expect(source.controls).toBe(true);
  expect(source.autoplay).toBe(false);
  expect(source.getAttribute("src")).toBe(
    "/api/sessions/review-fixture/review-assets/original-prompt",
  );
});

function rowValues(name: string) {
  const table = screen.getByRole("table", { name: "本次分科评分概览" });
  const row = within(table)
    .getByRole("rowheader", { name, exact: true })
    .closest("tr")!;
  return within(row)
    .getAllByRole("cell")
    .map((cell) => cell.textContent);
}

it("keeps blank provenance, exposes template text, and links directly to the incorrect blank", () => {
  const review = reviewFixture();
  review.sections = [
    {
      id: "reading",
      modules: [
        {
          id: "reading",
          questions: [
            {
              id: "cloze-six",
              type: "cloze",
              number: 1,
              numberEnd: 6,
              passageTemplate: "The task was complet{{b6}} finished.",
              blanks: [
                {
                  id: "b6",
                  number: 6,
                  prefix: "complet",
                  length: 3,
                  answer: "ely",
                  fullWord: "completely",
                  missingLetters: "ely",
                },
              ],
              grade: { correct: 0, total: 1 },
            },
          ],
        },
      ],
    },
  ];
  review.answers = { "cloze-six": { b6: "tly" } };
  review.score = { correct: 0, total: 1 };
  const onAddWord = vi.fn();
  render(
    <ReviewPage
      review={review}
      materials={[]}
      onHistory={vi.fn()}
      onWrongPractice={vi.fn()}
      onNotice={vi.fn()}
      onAddWord={onAddWord}
    />,
  );
  const jump = screen.getByRole("link", { name: "第 6 题", exact: true });
  expect(jump.getAttribute("href")).toBe("#answer-cloze-six-b6");
  expect(
    document
      .getElementById("answer-cloze-six-b6")
      ?.classList.contains("is-incorrect"),
  ).toBe(true);
  expect(
    screen.getByText("The task was complet___ (6) finished."),
  ).toBeTruthy();
  fireEvent.click(
    screen.getByRole("button", { name: "添加 completely 到单词本 · 第 6 题" }),
  );
  expect(onAddWord).toHaveBeenCalledWith({
    word: "completely",
    context: "The task was completely finished.",
    sourceSessionId: review.session.id,
    sourceQuestionId: "cloze-six",
    sourceLabel: "Isolated scoring review · 阅读 · 第 6 题",
  });
});

it("summarizes selected objective units and keeps ungraded questions and subjective self-ratings distinct", () => {
  show(reviewFixture());
  expect(rowValues("阅读")).toEqual(["3 / 4", "75%", "—", "—"]);
  expect(rowValues("听力")).toEqual(["0 / 1", "0%", "—", "—"]);
  expect(rowValues("写作")).toEqual(["1 / 1", "100%", "已评 1 / 2", "4.0 / 5"]);
  expect(rowValues("口语")).toEqual(["—", "—", "已评 1 / 2", "0.0 / 5"]);
  expect(rowValues("本次合计")).toEqual([
    "4 / 6",
    "67%",
    "已评 2 / 4",
    "2.0 / 5",
  ]);
  expect(screen.getByText(/未自评不按0分处理/)).toBeTruthy();
  expect(screen.getByText(/不合成或换算 ETS 1–6 或120分/)).toBeTruthy();
});

it("limits a filtered review to its selected questions even when broader exam metadata and ratings exist", () => {
  const review = reviewFixture();
  review.exam = {
    id: "original-exam",
    title: "Whole source",
    family: "fixture",
    strictEligible: true,
    warnings: [],
    sections: review.sections,
  };
  review.session.filtered = true;
  review.sections = [
    {
      id: "writing",
      modules: [
        {
          id: "selected",
          title: "Only selected email",
          questions: [{ id: "email", type: "email", number: 11, grade: null }],
        },
      ],
    },
  ];
  show(review);
  const table = screen.getByRole("table", { name: "本次分科评分概览" });
  expect(within(table).queryByRole("rowheader", { name: "阅读" })).toBeNull();
  expect(within(table).queryByRole("rowheader", { name: "口语" })).toBeNull();
  expect(rowValues("写作")).toEqual(["—", "—", "已评 1 / 1", "4.0 / 5"]);
  expect(rowValues("本次合计")).toEqual(["—", "—", "已评 1 / 1", "4.0 / 5"]);
});

it("shows unrated or invalid ratings as pending rather than adding zero to the average", () => {
  const review = reviewFixture();
  review.ratings = { email: { value: 6 }, discussion: { value: -1 } };
  show(review);
  expect(rowValues("写作")).toEqual(["1 / 1", "100%", "已评 0 / 2", "待自评"]);
  expect(rowValues("口语")).toEqual(["—", "—", "已评 0 / 2", "待自评"]);
  expect(rowValues("本次合计")).toEqual([
    "4 / 6",
    "67%",
    "已评 0 / 4",
    "待自评",
  ]);
});

it("updates the section and whole-session self-rating averages immediately after a successful local save", async () => {
  const review = reviewFixture();
  const fetch = vi.fn(
    async () =>
      new Response(JSON.stringify({ questionId: "discussion", value: 2 }), {
        status: 200,
      }),
  );
  vi.stubGlobal("fetch", fetch);
  vi.stubGlobal("FormData", window.FormData);
  show(review);
  const article = screen
    .getByRole("heading", { name: "12. 学术讨论" })
    .closest("article")!;
  fireEvent.change(within(article).getByRole("combobox", { name: "自评分" }), {
    target: { value: "2" },
  });
  await act(async () => {
    fireEvent.submit(article.querySelector("form")!);
  });
  expect(fetch).toHaveBeenCalledOnce();
  const [url, options] = fetch.mock.calls[0] as unknown as [
    string,
    RequestInit,
  ];
  expect(url).toBe("/api/sessions/review-score-fixture/ratings");
  expect(options.method).toBe("PUT");
  expect(JSON.parse(String(options.body))).toEqual({
    questionId: "discussion",
    value: 2,
    notes: "",
  });
  expect(rowValues("写作")).toEqual(["1 / 1", "100%", "已评 2 / 2", "3.0 / 5"]);
  expect(rowValues("本次合计")).toEqual([
    "4 / 6",
    "67%",
    "已评 3 / 4",
    "2.0 / 5",
  ]);
  expect(review.ratings).not.toHaveProperty("discussion");
});

it("does not claim an unsaved self-rating when SQLite persistence fails", async () => {
  const review = reviewFixture();
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(JSON.stringify({ error: "Local rating save failed" }), {
          status: 503,
        }),
    ),
  );
  vi.stubGlobal("FormData", window.FormData);
  show(review);
  const article = screen
    .getByRole("heading", { name: "12. 学术讨论" })
    .closest("article")!;
  fireEvent.change(within(article).getByRole("combobox", { name: "自评分" }), {
    target: { value: "5" },
  });
  await act(async () => {
    fireEvent.submit(article.querySelector("form")!);
  });
  expect(screen.getByText(/Local rating save failed/)).toBeTruthy();
  expect(rowValues("写作")).toEqual(["1 / 1", "100%", "已评 1 / 2", "4.0 / 5"]);
});
