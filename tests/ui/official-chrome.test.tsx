import React from "react";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import OfficialChrome, {
  OfficialDirections,
  TimingNotice,
} from "../../src/OfficialChrome";
import { setLocale } from "../../src/i18n";
import Exam from "../../src/Exam";
import type { Session } from "../../src/types";

it("identifies unverified sample timing and the full budget retained by a subset", () => {
  setLocale("en");
  const session = makeSession({ phase: "directions" });
  session.stage = {
    ...session.stage!,
    timingBasis: "local",
    partialModule: true,
  };
  const { rerender } = render(<OfficialDirections session={session} />);
  expect(screen.getByLabelText("Timing for this stage").textContent).toContain(
    "exact limit unverified",
  );
  expect(
    screen.getByText("11:30 shared across this task/module."),
  ).toBeTruthy();
  expect(screen.getByText(/Selected questions retain the full/)).toBeTruthy();
  act(() => setLocale("zh-CN"));
  expect(screen.getByLabelText("本阶段计时说明").textContent).toContain(
    "精确时限尚未核实",
  );
  expect(screen.getByText(/本任务／模块共用 11:30/)).toBeTruthy();
  act(() => setLocale("en"));
  session.stage.timingBasis = undefined;
  rerender(<OfficialDirections session={session} />);
  expect(screen.queryByLabelText("Timing for this stage")).toBeNull();
});

it("shows item response windows without using the irrelevant module seconds", () => {
  setLocale("en");
  const st = {
    ...makeSession().stage!,
    section: "speaking" as const,
    timer: "item" as const,
    timingBasis: "official" as const,
    responseWindows: [45, 45, 45],
  };
  render(<TimingNotice stage={st} />);
  expect(screen.getByText("ETS-specified limit")).toBeTruthy();
  expect(
    screen.getByText(/Response windows: 00:45 \/ 00:45 \/ 00:45/),
  ).toBeTruthy();
  expect(screen.queryByText(/11:30/)).toBeNull();
});

it("does not display a fake shared countdown on untimed reading directions", () => {
  const session = makeSession({
    phase: "directions",
    remainingSeconds: null,
    deadline: null,
  });
  session.stage = {
    ...session.stage!,
    timer: "untimed",
    timingBasis: "untimed",
  };
  render(chrome(session));
  expect(screen.queryByText("00:11:30")).toBeNull();
});

vi.mock("../../src/recording", () => ({
  saveChunk: vi.fn(),
  saveFinalization: vi.fn(),
  supportedMime: () => "audio/webm",
  trackRecorder: vi.fn(),
  stopRecorders: vi.fn(),
  flushRecordings: vi.fn(),
}));

const makeSession = (changes: Partial<Session> = {}): Session => ({
  id: "official-interface-test",
  examId: "pack-1",
  title: "Isolated UI fixture",
  mode: "strict",
  scope: "reading",
  routeMode: "fixed",
  route: "upper",
  status: "active",
  phase: "response",
  stageIndex: 0,
  questionIndex: 0,
  revision: 1,
  serverNow: Date.now(),
  deadline: Date.now() + 10000,
  remainingSeconds: 10,
  stage: {
    id: "reading-module-1",
    section: "reading",
    title: "Reading Module 1",
    timer: "shared",
    seconds: 690,
    questionCount: 11,
    itemCount: 20,
    canBack: true,
  },
  question: {
    id: "reading-1",
    type: "choice",
    number: 1,
    prompt: "An isolated test prompt.",
  },
  questionMap: [
    { index: 0, questionId: "reading-1", answered: false, flagged: false },
  ],
  allowedActions: ["answer", "next", "jump", "flag", "finish", "interrupt"],
  integrity: { interrupted: false },
  ...changes,
});

const handlers = () => ({
  onHelp: vi.fn(),
  onReview: vi.fn(),
  onBack: vi.fn(),
  onNext: vi.fn(),
  onBegin: vi.fn(),
  onPause: vi.fn(),
});
const chrome = (
  session: Session,
  events = handlers(),
  flags: { seconds?: number | null; disabled?: boolean; busy?: boolean } = {},
) => (
  <OfficialChrome
    session={session}
    seconds={session.remainingSeconds}
    disabled={false}
    busy={false}
    {...events}
    {...flags}
  />
);

beforeEach(() => {
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute("open");
  };
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-09-05T07:00:00Z"));
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
  for (const name of ["localStorage", "sessionStorage"]) {
    const values = new Map<string, string>();
    vi.stubGlobal(name, {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => values.set(key, value),
      removeItem: (key: string) => values.delete(key),
    });
  }
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("official question positions", () => {
  it("renumbers filtered source items by the server's selected-unit positions without changing full-scope labels", () => {
    const initial = makeSession({
      filtered: true,
      question: { id: "source-24", type: "choice", number: 24 },
      stage: {
        ...makeSession().stage!,
        questionCount: 1,
        itemCount: 1,
        currentQuestionUnitStart: 1,
      },
    });
    const { rerender } = render(chrome(initial));
    expect(screen.getByText("Question 1 of 1")).toBeTruthy();
    const blanks = [{ id: "a" }, { id: "b" }, { id: "c" }];
    const grouped = {
      ...initial,
      stage: { ...initial.stage!, questionCount: 2, itemCount: 4 },
      question: {
        id: "source-cloze",
        type: "cloze",
        number: 11,
        numberEnd: 13,
        blanks,
      },
    };
    rerender(chrome(grouped));
    expect(screen.getByText("Questions 1–3 of 4")).toBeTruthy();
    rerender(
      chrome({
        ...grouped,
        questionIndex: 1,
        question: initial.question,
        stage: { ...grouped.stage, currentQuestionUnitStart: 4 },
      }),
    );
    expect(screen.getByText("Question 4 of 4")).toBeTruthy();
    rerender(
      chrome({
        ...grouped,
        filtered: false,
        question: { ...grouped.question, number: 1, numberEnd: 10 },
        stage: { ...grouped.stage, itemCount: 33 },
      }),
    );
    expect(screen.getByText("Questions 1–10 of 33")).toBeTruthy();
  });

  it("does not claim two long writing tasks for a filtered single-task practice", () => {
    const initial = makeSession({
      filtered: true,
      mode: "practice",
      scope: "writing",
      question: {
        id: "only-discussion",
        type: "academic_discussion",
        number: 12,
      },
      stage: {
        ...makeSession().stage!,
        section: "writing",
        questionCount: 1,
        itemCount: 1,
        currentQuestionUnitStart: 1,
        canBack: false,
      },
    });
    render(chrome(initial));
    expect(screen.getByText("Question 1 of 1")).toBeTruthy();
  });

  it("uses original cloze question ranges and item totals rather than the number of screens", () => {
    const initial = makeSession({
      question: { id: "cloze-screen", type: "cloze", number: 1, numberEnd: 10 },
    });
    const { rerender } = render(chrome(initial));
    expect(screen.getByText("Questions 1–10 of 20")).toBeTruthy();
    expect(screen.queryByText(/of 11$/)).toBeNull();
    rerender(
      chrome({
        ...initial,
        questionIndex: 1,
        question: { id: "choice-screen", type: "choice", number: 11 },
      }),
    );
    expect(screen.getByText("Question 11 of 20")).toBeTruthy();
  });

  it.each([
    ["email", "Question 1 of 2"],
    ["academic_discussion", "Question 2 of 2"],
  ] as const)(
    "numbers %s within the two long writing tasks",
    (type, position) => {
      const initial = makeSession();
      render(
        chrome({
          ...initial,
          scope: "writing",
          question: { id: type, type, number: type === "email" ? 11 : 12 },
          stage: {
            ...initial.stage!,
            section: "writing",
            questionCount: 1,
            itemCount: 1,
            canBack: false,
          },
        }),
      );
      expect(screen.getByText(position)).toBeTruthy();
      expect(screen.queryByRole("button", { name: "Review" })).toBeNull();
      expect(screen.queryByRole("button", { name: "Back" })).toBeNull();
    },
  );

  it("renders directions with a null question without exposing a made-up question number", () => {
    const initial = Object.assign(
      makeSession({
        phase: "directions",
        deadline: null,
        remainingSeconds: null,
        allowedActions: ["begin", "interrupt", "finish"],
      }),
      { question: null },
    );
    const events = handlers();
    render(
      <>
        {chrome(initial, events, { disabled: true })}
        <OfficialDirections session={initial} />
      </>,
    );
    expect(screen.getByRole("heading", { name: "Module 1" })).toBeTruthy();
    expect(screen.queryByText(/Questions? \d+.*of/)).toBeNull();
    expect(screen.queryByRole("button", { name: "Review" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Back" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Next" })).toBeNull();
    expect(screen.getByRole("timer").textContent).toBe("00:11:30");
    fireEvent.click(screen.getByRole("button", { name: "Begin Reading" }));
    expect(events.onBegin).toHaveBeenCalledOnce();
  });
});

describe("authoritative navigation permissions", () => {
  it("dispatches only the permitted top-bar actions without adding a strict pause", () => {
    const events = handlers();
    render(
      chrome(makeSession({ allowedActions: ["next", "back", "jump"] }), events),
    );
    for (const name of ["Back", "Review", "Next"])
      fireEvent.click(screen.getByRole("button", { name }));
    expect(events.onBack).toHaveBeenCalledOnce();
    expect(events.onReview).toHaveBeenCalledOnce();
    expect(events.onNext).toHaveBeenCalledOnce();
    expect(events.onPause).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Pause" })).toBeNull();
  });

  it.each([{ disabled: true }, { busy: true }])(
    "does not navigate while response controls are unavailable: %o",
    (flags) => {
      const events = handlers();
      render(
        chrome(
          makeSession({ allowedActions: ["next", "back", "jump"] }),
          events,
          flags,
        ),
      );
      for (const name of ["Back", "Review", "Next"]) {
        const button = screen.getByRole("button", {
          name,
        }) as HTMLButtonElement;
        expect(button.disabled).toBe(true);
        fireEvent.click(button);
      }
      expect(events.onBack).not.toHaveBeenCalled();
      expect(events.onReview).not.toHaveBeenCalled();
      expect(events.onNext).not.toHaveBeenCalled();
    },
  );

  it("does not infer Review or Next permission from stage.canBack", () => {
    const events = handlers();
    render(chrome(makeSession({ allowedActions: ["answer"] }), events));
    for (const name of ["Review", "Next"]) {
      const button = screen.getByRole("button", { name }) as HTMLButtonElement;
      expect(button.disabled).toBe(true);
      fireEvent.click(button);
    }
    expect(events.onReview).not.toHaveBeenCalled();
    expect(events.onNext).not.toHaveBeenCalled();
  });

  it("requires explicit Begin and guided Pause/Resume permissions", () => {
    const events = handlers();
    const initial = makeSession({
      mode: "practice",
      phase: "directions",
      question: undefined,
      allowedActions: [],
    });
    const { rerender } = render(chrome(initial, events));
    expect(
      (
        screen.getByRole("button", {
          name: "Begin Reading",
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(true);
    expect(
      (screen.getByRole("button", { name: "Pause" }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Begin Reading" }));
    fireEvent.click(screen.getByRole("button", { name: "Pause" }));
    expect(events.onBegin).not.toHaveBeenCalled();
    expect(events.onPause).not.toHaveBeenCalled();
    rerender(
      chrome(
        { ...initial, phase: "paused", allowedActions: ["resume"] },
        events,
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: "Resume" }));
    expect(events.onPause).toHaveBeenCalledOnce();
    expect(
      (screen.getByRole("button", { name: "Next" }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
  });

  it("does not crash or leave actionable controls after the stage has been cleared", () => {
    const initial = makeSession({
      status: "completed",
      phase: "complete",
      stage: undefined,
      question: undefined,
      allowedActions: [],
    });
    const { container } = render(
      <>
        {chrome(initial)}
        <OfficialDirections session={initial} />
      </>,
    );
    expect(container.textContent).toBe("");
    expect(screen.queryByRole("button")).toBeNull();
  });
});

describe("Exam integration with the display-only timer", () => {
  const view = (session: Session, send = vi.fn()) => (
    <Exam
      session={session}
      stream={null}
      send={send}
      onLeave={vi.fn()}
      onFinish={vi.fn()}
      onNotice={vi.fn()}
      offline={false}
      acquireMic={vi.fn()}
      onFeedback={vi.fn()}
    />
  );

  it.each(["audio", "response"])(
    "shows the interviewer instead of the transcript during %s",
    (phase) => {
      const initial = makeSession();
      const s = makeSession({
        phase,
        scope: "speaking",
        sourceEdition: "student-1-interview-audio",
        deadline: phase === "audio" ? null : Date.now() + 45000,
        remainingSeconds: phase === "audio" ? null : 45,
        stage: {
          ...initial.stage!,
          section: "speaking",
          timer: "item",
          title: "Take an Interview",
          canBack: false,
        },
        question: {
          id: "audio-edition-interview",
          type: "interview",
          prompt: "PRIVATE QUESTION WORDING",
          transcript: "PRIVATE TRANSCRIPT",
          ...(phase === "audio"
            ? {
                audio: {
                  url: "/test/original-interview.wav",
                  durationSeconds: 16,
                  mediaType: "audio",
                },
              }
            : {}),
        },
      });
      render(view(s));
      expect(screen.getByText("Interviewer")).toBeTruthy();
      expect(screen.queryByText("PRIVATE QUESTION WORDING")).toBeNull();
      expect(screen.queryByText("PRIVATE TRANSCRIPT")).toBeNull();
      if (phase === "response")
        expect(screen.getByRole("timer").textContent).toBe("00:00:45");
    },
  );

  it("shows an old text-study speaking prompt only once with an edition notice", () => {
    const initial = makeSession();
    const s = makeSession({
      examId: "student-1",
      mode: "practice",
      scope: "speaking",
      phase: "response",
      deadline: null,
      remainingSeconds: null,
      stage: {
        ...initial.stage!,
        section: "speaking",
        timer: "untimed",
        title: "Take an Interview",
        canBack: false,
      },
      question: {
        id: "student-1-s-interview-1",
        type: "interview",
        prompt: "Original paper interview prompt",
        presentationSchema: "structured-v1",
        structuredContentStatus: "source-verified",
        stemBlocks: [
          { type: "instruction", text: "Original paper interview prompt" },
        ],
      },
    });
    render(view(s));
    expect(screen.getAllByText("Original paper interview prompt")).toHaveLength(
      1,
    );
    expect(screen.getByText(/This paper-version session retains/)).toBeTruthy();
  });

  it("retains expired writing as read-only until Continue and cannot dismiss expiry with Escape", async () => {
    const base = makeSession();
    const send = vi.fn();
    const session = makeSession({
      scope: "writing",
      phase: "expired",
      remainingSeconds: 0,
      deadline: Date.now() - 1000,
      question: {
        id: "expired-email",
        type: "email",
        prompt: "Original writing task",
      },
      answer: "Saved response before the cutoff.",
      stage: {
        ...base.stage!,
        section: "writing",
        canBack: false,
        questionCount: 1,
      },
      allowedActions: ["continue", "finish", "interrupt"],
    });
    const before = JSON.stringify(session);
    const { container, rerender } = render(
      view(
        {
          ...session,
          phase: "response",
          deadline: Date.now() + 1000,
          remainingSeconds: 1,
          allowedActions: ["answer", "next"],
        },
        send,
      ),
    );
    fireEvent.change(container.querySelector("textarea")!, {
      target: { value: "A late edit not accepted by the server." },
    });
    rerender(view(session, send));
    expect(
      screen.getByRole("heading", { name: "Writing Time Expired" }),
    ).toBeTruthy();
    const editor = container.querySelector("textarea")!;
    expect(editor.value).toBe("Saved response before the cutoff.");
    expect(editor.disabled).toBe(true);
    expect(screen.queryByRole("timer")).toBeNull();
    expect(
      (
        screen.getByRole("button", {
          name: "Next",
          exact: true,
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(true);
    fireEvent.keyDown(window, { key: "Escape" });
    fireEvent(
      screen.getByRole("dialog"),
      new Event("cancel", { cancelable: true }),
    );
    expect(
      screen.getByRole("heading", { name: "Writing Time Expired" }),
    ).toBeTruthy();
    await act(async () =>
      fireEvent.click(
        screen.getByRole("button", { name: "Continue", exact: true }),
      ),
    );
    expect(send).toHaveBeenCalledWith({
      action: "continue",
      questionId: "expired-email",
      index: undefined,
    });
    expect(JSON.stringify(session)).toBe(before);
  });

  it("keeps source short-response choices disabled during audio and blocks blank manual Next", () => {
    const base = makeSession();
    const session = makeSession({
      scope: "listening",
      phase: "audio",
      deadline: null,
      remainingSeconds: null,
      stage: {
        ...base.stage!,
        section: "listening",
        timer: "item",
        canBack: false,
      },
      question: {
        id: "short-response",
        type: "choice",
        taskType: "listen_response",
        number: 1,
        choices: [{ id: "A", text: "Isolated option" }],
      },
      allowedActions: ["audio-started", "audio-ended"],
    });
    const send = vi.fn();
    const { rerender } = render(view(session, send));
    expect(screen.getByText("Question 1 of 20")).toBeTruthy();
    expect((screen.getByRole("radio") as HTMLInputElement).disabled).toBe(true);
    expect(screen.queryByRole("button", { name: "Next" })).toBeNull();
    rerender(
      view(
        {
          ...session,
          phase: "response",
          remainingSeconds: 20,
          allowedActions: ["answer", "next"],
        },
        send,
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByRole("heading", { name: "Must Answer" })).toBeTruthy();
    expect(send).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Return to Question" }));
    expect((screen.getByRole("radio") as HTMLInputElement).disabled).toBe(
      false,
    );
  });

  it("removes the conversation playback heading when answering without hiding the original question", () => {
    const base = makeSession();
    const { container } = render(
      view(
        makeSession({
          scope: "listening",
          stage: {
            ...base.stage!,
            section: "listening",
            timer: "item",
            canBack: false,
          },
          question: {
            id: "conversation",
            type: "choice",
            taskType: "conversation",
            prompt: "Original question",
          },
        }),
      ),
    );
    expect(
      container.querySelector(".exam-question-heading")?.hasAttribute("hidden"),
    ).toBe(true);
    expect(screen.getByText("Original question")).toBeTruthy();
  });

  it("hides only the clock text while the original response deadline continues to expire", () => {
    const initial = makeSession();
    const original = JSON.stringify(initial);
    const send = vi.fn();
    const { unmount } = render(view(initial, send));
    fireEvent.click(screen.getByRole("button", { name: "Hide Time" }));
    expect(screen.getByRole("timer").textContent).toBe("");
    act(() => vi.advanceTimersByTime(3000));
    fireEvent.click(screen.getByRole("button", { name: "Show Time" }));
    expect(screen.getByRole("timer").textContent).toBe("00:00:07");
    fireEvent.click(screen.getByRole("button", { name: "Hide Time" }));
    act(() => vi.advanceTimersByTime(7000));
    fireEvent.click(screen.getByRole("button", { name: "Show Time" }));
    expect(screen.getByRole("timer").textContent).toBe("00:00:00");
    expect(
      (screen.getByRole("button", { name: "Next" }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
    expect(
      (screen.getByRole("button", { name: "Review" }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
    expect(send).not.toHaveBeenCalled();
    expect(JSON.stringify(initial)).toBe(original);
    unmount();
    expect(vi.getTimerCount()).toBe(0);
  });

  it("keeps writing, undo history and the same running clock through the source confirmation page", () => {
    const base = makeSession();
    const send = vi.fn();
    const { container } = render(
      view(
        makeSession({
          scope: "writing",
          remainingSeconds: 420,
          deadline: Date.now() + 420000,
          question: {
            id: "email",
            type: "email",
            prompt: "Isolated writing prompt",
          },
          stage: {
            ...base.stage!,
            section: "writing",
            canBack: false,
            questionCount: 1,
          },
        }),
        send,
      ),
    );
    const editor = screen.getByRole("textbox") as HTMLTextAreaElement;
    fireEvent.change(editor, { target: { value: "Preserved local draft" } });
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(
      screen.getByRole("heading", { name: "Time Remaining" }),
    ).toBeTruthy();
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(container.contains(editor)).toBe(true);
    act(() => vi.advanceTimersByTime(3000));
    expect(screen.getByRole("timer").textContent).toBe("00:06:57");
    fireEvent.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByRole("textbox")).toBe(editor);
    expect(editor.value).toBe("Preserved local draft");
    fireEvent.click(screen.getByRole("button", { name: "Undo" }));
    expect(editor.value).toBe("");
    expect(send.mock.calls.some(([event]) => event.action === "next")).toBe(
      false,
    );
  });

  it("mounts and cleans up a directions screen whose server question is null", () => {
    const initial = Object.assign(
      makeSession({
        phase: "directions",
        deadline: null,
        remainingSeconds: null,
        allowedActions: ["begin", "interrupt", "finish"],
      }),
      { question: null },
    );
    const { unmount } = render(view(initial));
    expect(screen.getByRole("heading", { name: "Module 1" })).toBeTruthy();
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.queryByText("An isolated test prompt.")).toBeNull();
    unmount();
    expect(vi.getTimerCount()).toBe(0);
  });
});

describe("source listening and speaking chrome", () => {
  const listening = (phase: Session["phase"]): Session => {
    const session = makeSession();
    return {
      ...session,
      scope: "listening",
      phase,
      stage: {
        ...session.stage!,
        id: "listening-module-1",
        title: "Listening Module 1",
        section: "listening",
        timer: "item",
        canBack: false,
      },
      question: { id: "listening-first", type: "choice", number: 1 },
      remainingSeconds: phase === "response" ? 20 : null,
      allowedActions:
        phase === "response"
          ? ["answer", "next"]
          : ["audio-started", "audio-ended"],
    };
  };

  const speaking = (phase: Session["phase"]): Session => {
    const session = makeSession();
    return {
      ...session,
      scope: "speaking",
      phase,
      stage: {
        ...session.stage!,
        id: "speaking-interview",
        title: "Speaking · Interview",
        section: "speaking",
        timer: "item",
        canBack: false,
        itemCount: 4,
        questionCount: 4,
        sectionItemCount: 11,
        sectionQuestionOffset: 7,
      },
      question: { id: "interview-1", type: "interview", number: 1 },
      remainingSeconds: phase === "response" ? 45 : null,
      allowedActions:
        phase === "response" ? ["answer"] : ["audio-started", "audio-ended"],
    };
  };

  it("shows language controls and Volume without test navigation while the prompt plays", () => {
    render(chrome(listening("audio")));
    expect(
      screen.getAllByRole("button").map((button) => button.textContent?.trim()),
    ).toEqual(["EN", "中文", "Volume"]);
    expect(screen.getByText("Listening")).toBeTruthy();
    expect(screen.queryByText(/Questions? \d+.*of/)).toBeNull();
    expect(screen.queryByRole("timer")).toBeNull();
    expect(screen.queryByRole("button", { name: /Time/ })).toBeNull();
  });

  it("restores permitted Next and the per-question clock only after listening audio", () => {
    const callbacks = handlers();
    render(chrome(listening("response"), callbacks));
    expect(
      screen.getAllByRole("button").map((button) => button.textContent?.trim()),
    ).toEqual(["EN", "中文", "Volume", "Help", "Next", "Hide Time"]);
    expect(screen.getByText("Question 1 of 20")).toBeTruthy();
    expect(screen.getByRole("timer").textContent).toBe("00:00:20");
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(callbacks.onNext).toHaveBeenCalledOnce();
    expect(screen.queryByRole("button", { name: "Back" })).toBeNull();
  });

  it.each(["audio", "response"] as const)(
    "keeps Speaking %s free of Next/Help/header timers and numbers all eleven questions",
    (phase) => {
      const firstInterview = speaking(phase);
      const { rerender } = render(chrome(firstInterview));
      expect(
        screen
          .getAllByRole("button")
          .map((button) => button.textContent?.trim()),
      ).toEqual(["EN", "中文", "Volume"]);
      expect(screen.getByText("Question 8 of 11")).toBeTruthy();
      expect(screen.queryByRole("timer")).toBeNull();
      rerender(
        chrome({
          ...firstInterview,
          questionIndex: 3,
          question: { id: "interview-4", type: "interview", number: 4 },
        }),
      );
      expect(screen.getByText("Question 11 of 11")).toBeTruthy();
    },
  );

  it("changes existing audio/video volume and remembers it without changing time or session actions", () => {
    sessionStorage.setItem("toefl-exam-volume", "not-a-number");
    const initial = speaking("audio");
    const original = JSON.stringify(initial);
    const callbacks = handlers();
    render(
      <>
        <audio data-testid="audio" />
        <video data-testid="video" />
        {chrome(initial, callbacks)}
      </>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Volume" }));
    const volume = screen.getByRole("slider", {
      name: "Exam volume",
    }) as HTMLInputElement;
    expect(volume.value).toBe("0.8");
    fireEvent.change(volume, { target: { value: "0.35" } });
    expect((screen.getByTestId("audio") as HTMLAudioElement).volume).toBe(0.35);
    expect((screen.getByTestId("video") as HTMLVideoElement).volume).toBe(0.35);
    expect(sessionStorage.getItem("toefl-exam-volume")).toBe("0.35");
    expect(JSON.stringify(initial)).toBe(original);
    for (const callback of Object.values(callbacks))
      expect(callback).not.toHaveBeenCalled();
  });

  it.each(["listening", "speaking"] as const)(
    "keeps %s directions startable without disclosing a question",
    (section) => {
      const initial =
        section === "listening"
          ? listening("directions")
          : speaking("directions");
      initial.question = undefined;
      initial.allowedActions = ["begin", "finish", "interrupt"];
      render(
        <>
          {chrome(initial)}
          <OfficialDirections session={initial} />
        </>,
      );
      expect(
        screen.getByRole("button", {
          name: `Begin ${section === "listening" ? "Listening" : "Speaking"}`,
        }),
      ).toBeTruthy();
      expect(screen.getByRole("button", { name: "Help" })).toBeTruthy();
      expect(screen.queryByText(/Questions? \d+.*of/)).toBeNull();
      expect(screen.queryByText(/write the email/i)).toBeNull();
      expect(screen.queryByRole("timer")).toBeNull();
    },
  );

  it("preserves supplied listening directions and uses only source navigation text when none is available", () => {
    const initial = listening("directions");
    const { rerender } = render(<OfficialDirections session={initial} />);
    expect(
      screen.getByText("You WILL NOT be able to return to previous questions."),
    ).toBeTruthy();
    expect(
      screen.getByText(
        /clock will show you how much time you have to complete each question/,
      ),
    ).toBeTruthy();
    initial.stage = {
      ...initial.stage!,
      instructions: "The verified source directions for this exact module.",
    };
    rerender(<OfficialDirections session={initial} />);
    expect(screen.getByText(initial.stage.instructions!)).toBeTruthy();
    expect(screen.queryByText(/clock will show/)).toBeNull();
  });

  it("uses the two original Speaking task instructions and retains source context when provided", () => {
    const initial = speaking("directions");
    const { rerender } = render(<OfficialDirections session={initial} />);
    expect(
      screen.getByRole("heading", { name: "Take an Interview" }),
    ).toBeTruthy();
    expect(
      screen.getByText(/An interviewer will ask you questions/),
    ).toBeTruthy();
    expect(
      screen.getByText("No time for preparation will be provided."),
    ).toBeTruthy();
    initial.stage = {
      ...initial.stage!,
      id: "speaking-listen_repeat",
      title: "Speaking · Listen Repeat",
    };
    rerender(<OfficialDirections session={initial} />);
    expect(
      screen.getByRole("heading", { name: "Listen and Repeat" }),
    ).toBeTruthy();
    expect(
      screen.getByText(/You will listen as someone speaks to you/),
    ).toBeTruthy();
    initial.stage.instructions =
      "Listen and Repeat\n\nThe source-specific hotel context remains visible.";
    rerender(<OfficialDirections session={initial} />);
    expect(screen.getAllByText("Listen and Repeat")).toHaveLength(1);
    expect(
      screen.getByText("The source-specific hotel context remains visible."),
    ).toBeTruthy();
  });
});
