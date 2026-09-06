import React, { useState } from "react";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AnswerInput, StructuredStem } from "../../src/Questions";
import Exam from "../../src/Exam";
import { LanguageSwitch, setLocale } from "../../src/i18n";
import type { Answer, Question, Session } from "../../src/types";

const recording = vi.hoisted(() => ({
  saveChunk: vi.fn(),
  saveFinalization: vi.fn(),
  supportedMime: () => "audio/webm",
  trackRecorder: vi.fn(),
  stopRecorders: vi.fn(),
  flushRecordings: vi.fn(),
}));
vi.mock("../../src/recording", () => recording);

function EditableQuestion({ question }: { question: Question }) {
  const [value, setValue] = useState<Answer>();
  return (
    <>
      <LanguageSwitch />
      <AnswerInput
        question={question}
        value={value}
        onChange={setValue}
        disabled={false}
        strict={false}
        examStyle
      />
      <output data-testid="answer">{JSON.stringify(value)}</output>
    </>
  );
}
const answer = () =>
  JSON.parse(screen.getByTestId("answer").textContent || "null");
const session = (section: "reading" | "speaking" = "reading"): Session => ({
  id: "i18n-preservation",
  examId: "pack-1",
  title: "Language test",
  mode: "strict",
  scope: section,
  routeMode: "fixed",
  route: "upper",
  status: "active",
  phase: "response",
  stageIndex: 0,
  questionIndex: 0,
  revision: 1,
  serverNow: Date.now(),
  deadline: Date.now() + 8000,
  remainingSeconds: 8,
  stage: {
    id: `${section}-1`,
    section,
    title: section === "reading" ? "Reading · Module 1" : "Listen and Repeat",
    timer: section === "reading" ? "shared" : "item",
    seconds: 8,
    questionCount: 7,
    canBack: section === "reading",
  },
  question:
    section === "reading"
      ? {
          id: "source-question",
          type: "choice",
          prompt: "Which option is correct?",
          choices: [{ id: "a", text: "The office opens at nine." }],
        }
      : { id: "repeat-1", type: "listen_repeat" },
  allowedActions: ["answer", "next", "jump"],
  integrity: { interrupted: false },
});
const exam = (
  s: Session,
  stream: MediaStream | null = null,
  send = vi.fn(),
) => (
  <>
    <Exam
      session={s}
      stream={stream}
      send={send}
      onLeave={vi.fn()}
      onFinish={vi.fn()}
      onNotice={vi.fn()}
      offline={false}
      acquireMic={vi.fn()}
      onFeedback={vi.fn()}
    />
  </>
);

beforeEach(() => {
  setLocale("en");
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
});
afterEach(() => {
  cleanup();
  setLocale("en");
  vi.useRealTimers();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe("live bilingual exam UI", () => {
  it("preserves written text and undo history while translating editor controls", () => {
    render(
      <EditableQuestion
        question={{ id: "writing", type: "academic_discussion" }}
      />,
    );
    const input = screen.getByRole("textbox", {
      name: "Your written response",
    }) as HTMLTextAreaElement;
    fireEvent.change(input, { target: { value: "My first response" } });
    fireEvent.change(input, { target: { value: "My revised response" } });
    fireEvent.click(screen.getByRole("button", { name: "中文" }));
    expect(screen.getByRole("textbox", { name: "你的写作答案" })).toBe(input);
    expect(input.value).toBe("My revised response");
    expect(input.lang).toBe("en");
    expect(screen.getByRole("button", { name: "隐藏字数" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "撤销" }));
    expect(answer()).toBe("My first response");
    fireEvent.click(screen.getByRole("button", { name: "EN" }));
    fireEvent.click(screen.getByRole("button", { name: "Redo" }));
    expect(answer()).toBe("My revised response");
  });

  it("keeps cloze letters and source English while translating required-letter counts", () => {
    render(
      <EditableQuestion
        question={{
          id: "cloze",
          type: "cloze",
          passageTemplate: "Conservationists sa{{one}} endangered species.",
          blanks: [{ id: "one", prefix: "sa", length: 2 }],
        }}
      />,
    );
    const input = screen.getByRole("textbox", {
      name: "Missing letters for word 1, 2 letters required",
    }) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "v" } });
    fireEvent.click(screen.getByRole("button", { name: "中文" }));
    expect(screen.getByText("第 1 空 · 已填 1 / 需填 2 个字母")).toBeTruthy();
    expect(screen.getByText("共 1 个缺词")).toBeTruthy();
    expect(
      screen.getByRole("textbox", {
        name: "第 1 个单词缺失的字母，需填 2 个字母",
      }),
    ).toBe(input);
    fireEvent.change(input, { target: { value: "ve" } });
    expect(answer()).toEqual({ one: "ve" });
    expect(
      screen
        .getByText("Conservationists")
        .closest("[lang]")
        ?.getAttribute("lang"),
    ).toBe("en");
    expect(screen.getByText("已完成 1 / 1")).toBeTruthy();
  });

  it("continues building a sentence using the same token indices after changing language", () => {
    render(
      <EditableQuestion
        question={{
          id: "build",
          type: "build_sentence",
          tokens: ["the", "the"],
          slots: [{ fixed: "We use" }, { id: "one" }, { id: "two" }],
        }}
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Use word block 1: the" }),
    );
    fireEvent.click(screen.getByRole("button", { name: "中文" }));
    expect(screen.getByText("已将 the 放入第 1 空。")).toBeTruthy();
    fireEvent.click(
      screen.getByRole("button", { name: "使用第 2 个词块：the" }),
    );
    expect(answer()).toEqual({ tokenOrder: ["0", "1"] });
    expect(screen.getByText("We use").getAttribute("lang")).toBe("en");
  });

  it("keeps the original deadline running and source choices intact while changing exam controls", () => {
    vi.useFakeTimers();
    const send = vi.fn();
    render(exam(session(), null, send));
    expect(
      screen.getByRole("timer", { name: "Time remaining" }).textContent,
    ).toBe("00:00:08");
    act(() => vi.advanceTimersByTime(2100));
    fireEvent.click(screen.getByRole("button", { name: "中文" }));
    expect(screen.getByRole("timer", { name: "剩余时间" }).textContent).toBe(
      "00:00:06",
    );
    expect(screen.getByRole("button", { name: "下一题" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "帮助" })).toBeTruthy();
    expect(
      screen.getByText("The office opens at nine.").getAttribute("lang"),
    ).toBe("en");
    expect(send).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "隐藏时间" }));
    act(() => vi.advanceTimersByTime(1000));
    fireEvent.click(screen.getByRole("button", { name: "EN" }));
    fireEvent.click(screen.getByRole("button", { name: "Show Time" }));
    expect(
      screen.getByRole("timer", { name: "Time remaining" }).textContent,
    ).toBe("00:00:05");
  });

  it("does not restart microphone recording when a speaking response changes language", () => {
    vi.useFakeTimers();
    const start = vi.fn(),
      stop = vi.fn();
    class Recorder {
      state = "inactive";
      mimeType = "audio/webm";
      onstop?: () => void;
      start() {
        start();
        this.state = "recording";
      }
      stop() {
        stop();
        this.state = "inactive";
        this.onstop?.();
      }
    }
    vi.stubGlobal("MediaRecorder", Recorder);
    render(exam(session("speaking"), { active: true } as MediaStream));
    expect(start).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "中文" }));
    expect(screen.getByText("正在录音 · 分段保存到本机")).toBeTruthy();
    expect(start).toHaveBeenCalledTimes(1);
    expect(stop).not.toHaveBeenCalled();
    act(() => vi.advanceTimersByTime(8000));
    expect(stop).toHaveBeenCalledTimes(1);
  });

  it("does not translate source words that also occur in the interface dictionary", () => {
    setLocale("zh-CN");
    render(
      <StructuredStem
        question={{
          id: "source-language",
          type: "academic_discussion",
          stemBlocks: [
            { type: "paragraph", text: "Help" },
            {
              type: "dialogue",
              turns: [{ speaker: "Dr. Gupta", text: "Your response" }],
            },
          ],
        }}
      />,
    );
    expect(
      screen.getByText("Help").closest("[lang]")?.getAttribute("lang"),
    ).toBe("en");
    expect(screen.getByText("Your response")).toBeTruthy();
    expect(screen.getByText("Dr. Gupta")).toBeTruthy();
  });
});
