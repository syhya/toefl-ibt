import React from "react";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App, { Prepare } from "../../src/App";
import Exam, { type ReferencePlayback } from "../../src/Exam";
import { setLocale } from "../../src/i18n";
import type { Exam as ExamInfo, Session } from "../../src/types";

vi.mock("../../src/recording", () => ({
  flushRecordings: vi.fn(async () => {}),
  pendingRecordings: vi.fn(async () => 0),
  retryRecordings: vi.fn(async () => 0),
  stopRecorders: vi.fn(async () => {}),
  supportedMime: vi.fn(() => ""),
  saveChunk: vi.fn(),
  saveFinalization: vi.fn(),
  trackRecorder: vi.fn(),
}));

const LABEL = "Enable audio replay and instant answers";
const fixture: ExamInfo = {
  id: "practice-aids-fixture",
  title: "Practice aids fixture",
  family: "user",
  strictEligible: false,
  warnings: [],
  sections: [
    { id: "reading", questionCount: 1 },
    { id: "listening", questionCount: 1 },
  ],
};
function memoryStorage() {
  const values = new Map<string, string>();
  return {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, String(value)),
    removeItem: (key: string) => values.delete(key),
    clear: () => values.clear(),
  };
}
function session(changes: Partial<Session> = {}): Session {
  return {
    id: "aids-session",
    examId: fixture.id,
    title: fixture.title,
    mode: "practice",
    scope: "listening",
    routeMode: "fixed",
    route: "upper",
    status: "active",
    phase: "response",
    stageIndex: 0,
    questionIndex: 0,
    revision: 1,
    serverNow: Date.now(),
    deadline: null,
    remainingSeconds: null,
    stage: {
      id: "listening",
      section: "listening",
      title: "Listening",
      timer: "item",
      seconds: 20,
      questionCount: 2,
      canBack: false,
    },
    question: {
      id: "aids-question",
      number: 1,
      type: "choice",
      taskType: "listen_response",
      prompt: "Choose a response.",
      choices: [{ id: "A", text: "Fixture answer" }],
    },
    answer: "A",
    integrity: { interrupted: false },
    allowedActions: ["answer", "next", "replay"],
    ...changes,
  };
}
function prepare(changes: Partial<React.ComponentProps<typeof Prepare>> = {}) {
  return (
    <Prepare
      exam={fixture}
      initialScope="listening"
      materials={[]}
      stream={null}
      acquireMic={vi.fn()}
      start={vi.fn(async () => {})}
      close={vi.fn()}
      {...changes}
    />
  );
}
function exam(
  value: Session,
  changes: Partial<React.ComponentProps<typeof Exam>> = {},
) {
  return (
    <Exam
      session={value}
      stream={null}
      send={vi.fn(async () => undefined)}
      onLeave={vi.fn()}
      onFinish={vi.fn()}
      onNotice={vi.fn()}
      offline={false}
      acquireMic={vi.fn()}
      onFeedback={vi.fn()}
      {...changes}
    />
  );
}
function checkbox() {
  return screen.getByRole("checkbox", { name: LABEL }) as HTMLInputElement;
}

beforeEach(() => {
  Object.defineProperty(HTMLDialogElement.prototype, "showModal", {
    configurable: true,
    value: function (this: HTMLDialogElement) {
      this.setAttribute("open", "");
    },
  });
  vi.stubGlobal("localStorage", memoryStorage());
  vi.stubGlobal("sessionStorage", memoryStorage());
  setLocale("en");
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
  vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();
  vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => {});
});
afterEach(() => {
  cleanup();
  setLocale("en");
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("practice aid setup", () => {
  it.each([false, true])(
    "defaults off and submits the deliberate scoped choice: %s",
    async (enabled) => {
      const start = vi.fn(async () => {});
      render(prepare({ start }));
      expect(checkbox().checked).toBe(false);
      expect(checkbox().disabled).toBe(false);
      if (enabled) fireEvent.click(checkbox());
      await act(async () => {
        fireEvent.click(screen.getByRole("button", { name: "Start practice" }));
      });
      expect(start).toHaveBeenCalledWith(
        expect.objectContaining({
          mode: "practice",
          scope: "listening",
          allowPracticeAids: enabled,
        }),
      );
    },
  );

  it("disables and clears the choice for full tests and never restores opt-in when scope changes back", async () => {
    const start = vi.fn(async () => {});
    render(prepare({ start }));
    fireEvent.click(checkbox());
    fireEvent.change(screen.getByRole("combobox", { name: "Practice scope" }), {
      target: { value: "all" },
    });
    expect(checkbox().checked).toBe(false);
    expect(checkbox().disabled).toBe(true);
    expect(
      screen.getByText(
        "Off by default. Available only for specialized guided practice; full tests show answers after finishing.",
      ),
    ).toBeTruthy();
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Start practice" }));
    });
    expect(start).toHaveBeenCalledWith(
      expect.objectContaining({ scope: "all", allowPracticeAids: false }),
    );
    fireEvent.change(screen.getByRole("combobox", { name: "Practice scope" }), {
      target: { value: "listening" },
    });
    expect(checkbox().checked).toBe(false);
    expect(checkbox().disabled).toBe(false);
  });

  it("defaults strict mode off, resets on mode changes, and submits false in strict mode", async () => {
    const start = vi.fn(async () => {});
    render(prepare({ exam: { ...fixture, strictEligible: true }, start }));
    expect(checkbox().disabled).toBe(true);
    fireEvent.click(screen.getByRole("radio", { name: /Guided practice/ }));
    fireEvent.click(checkbox());
    expect(checkbox().checked).toBe(true);
    fireEvent.click(screen.getByRole("radio", { name: /Strict practice/ }));
    expect(checkbox().disabled).toBe(true);
    expect(checkbox().checked).toBe(false);
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Start practice" }));
    });
    expect(start).toHaveBeenCalledWith(
      expect.objectContaining({ mode: "strict", allowPracticeAids: false }),
    );
    fireEvent.click(screen.getByRole("radio", { name: /Guided practice/ }));
    expect(checkbox().checked).toBe(false);
  });

  it("permits filtered all-scope practice but resets when the task selection or setup changes", () => {
    const view = render(
      prepare({ initialScope: "all", wrongCount: 2, selectionLabel: "Task A" }),
    );
    expect(checkbox().disabled).toBe(false);
    fireEvent.click(checkbox());
    view.rerender(
      prepare({ initialScope: "all", wrongCount: 3, selectionLabel: "Task B" }),
    );
    expect(checkbox().checked).toBe(false);
    fireEvent.click(checkbox());
    view.unmount();
    render(
      prepare({ initialScope: "all", wrongCount: 3, selectionLabel: "Task B" }),
    );
    expect(checkbox().checked).toBe(false);
  });

  it("localizes the checkbox and disabled explanation without changing its value", () => {
    render(prepare());
    fireEvent.click(checkbox());
    act(() => setLocale("zh-CN"));
    const input = screen.getByRole("checkbox", {
      name: "允许重播音频和即时查看答案与解析",
    }) as HTMLInputElement;
    expect(input.checked).toBe(true);
    expect(
      screen.getByText(
        "默认关闭，仅专项练习可勾选；完整考试结束后统一查看答案与解析。",
      ),
    ).toBeTruthy();
  });
});

describe("effective session aid permission", () => {
  it("offers no enabled Pause during timed audio when the server withholds it", () => {
    const send = vi.fn(async () => undefined);
    const current = session({
      allowPracticeAids: false,
      phase: "audio",
      question: {
        ...session().question!,
        audio: { url: "/api/original-prompt.mp3" },
      },
      allowedActions: ["audio-started", "audio-ended", "finish"],
    });
    const view = render(exam(current, { send }));
    const pause = screen.queryByRole("button", {
      name: "Pause",
      exact: true,
    }) as HTMLButtonElement | null;
    expect(!pause || pause.disabled).toBe(true);
    if (pause) fireEvent.click(pause);
    expect(send).not.toHaveBeenCalled();
    view.rerender(
      exam(
        {
          ...current,
          phase: "response",
          allowedActions: ["answer", "next", "pause"],
        },
        { send },
      ),
    );
    expect(
      (
        screen.getByRole("button", {
          name: "Pause",
          exact: true,
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(false);
  });
  it.each([undefined, false])(
    "hides both helpers for default-off and older sessions: %s",
    (allowPracticeAids) => {
      render(exam(session({ allowPracticeAids })));
      expect(screen.queryByRole("button", { name: "Replay audio" })).toBeNull();
      expect(
        screen.queryByRole("button", { name: "Check answer & explanation" }),
      ).toBeNull();
    },
  );

  it("shows opted-in helpers but still respects the server replay action", async () => {
    const onFeedback = vi.fn(),
      send = vi.fn(async () => undefined);
    const current = session({ allowPracticeAids: true });
    const view = render(exam(current, { onFeedback, send }));
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Replay audio" }));
    });
    expect(send).toHaveBeenCalledWith({
      action: "replay",
      questionId: "aids-question",
      index: undefined,
    });
    await act(async () => {
      fireEvent.click(
        screen.getByRole("button", { name: "Check answer & explanation" }),
      );
    });
    expect(onFeedback).toHaveBeenCalledTimes(1);
    view.rerender(
      exam(
        { ...current, allowedActions: ["answer", "next"] },
        { onFeedback, send },
      ),
    );
    expect(screen.queryByRole("button", { name: "Replay audio" })).toBeNull();
    expect(
      screen.getByRole("button", { name: "Check answer & explanation" }),
    ).toBeTruthy();
  });

  it("never exposes helpers in strict mode, even if a supplied flag is true", () => {
    render(exam(session({ mode: "strict", allowPracticeAids: true })));
    expect(screen.queryByRole("button", { name: "Replay audio" })).toBeNull();
    expect(
      screen.queryByRole("button", { name: "Check answer & explanation" }),
    ).toBeNull();
  });
});

describe("untimed original media", () => {
  function untimed(allowPracticeAids?: boolean) {
    const value = session({ allowPracticeAids });
    return {
      ...value,
      stage: {
        ...value.stage!,
        timer: "untimed" as const,
        practiceAudio: [{ url: "/api/full-source.mp3" }],
      },
      question: {
        ...value.question!,
        practiceMediaSequence: [
          { url: "/api/item-source.mp3", assetId: "source-one" },
        ],
      },
    };
  }
  it("keeps both primary and sole full-source first playback without exposing native repeat or seek controls", async () => {
    const value = untimed();
    render(exam(value));
    const audio = screen.getByLabelText(
      "Original prompt 1",
    ) as HTMLAudioElement;
    const full = screen.getByLabelText(
      "Supplemental reference track",
    ) as HTMLAudioElement;
    fireEvent.loadedMetadata(audio);
    fireEvent.loadedMetadata(full);
    expect(HTMLMediaElement.prototype.play).not.toHaveBeenCalled();
    expect(audio.controls).toBe(false);
    expect(full.controls).toBe(false);
    await act(async () => {
      fireEvent.click(
        within(audio.parentElement!).getByRole("button", {
          name: "Play audio",
        }),
      );
    });
    expect(HTMLMediaElement.prototype.play).toHaveBeenCalledTimes(1);
    fireEvent.playing(audio);
    fireEvent.ended(audio);
    expect(within(audio.parentElement!).queryByRole("button")).toBeNull();
    expect(
      within(audio.parentElement!).getByText(
        "Audio already played. Replay was not enabled for this practice.",
      ),
    ).toBeTruthy();
    expect(
      within(full.parentElement!).getByRole("button", {
        name: "Play audio",
        hidden: true,
      }),
    ).toBeTruthy();
  });

  it("keeps one-pass progress when switching away and back to the same source", async () => {
    const value = untimed(false);
    const view = render(exam(value));
    const audio = screen.getByLabelText(
      "Original prompt 1",
    ) as HTMLAudioElement;
    await act(async () => {
      fireEvent.click(
        within(audio.parentElement!).getByRole("button", {
          name: "Play audio",
        }),
      );
    });
    fireEvent.playing(audio);
    audio.currentTime = 7;
    fireEvent.timeUpdate(audio);
    const other = {
      ...value,
      question: { ...value.question!, id: "other", practiceMediaSequence: [] },
    };
    view.rerender(exam(other));
    view.rerender(exam(value));
    const resumed = screen.getByLabelText(
      "Original prompt 1",
    ) as HTMLAudioElement;
    fireEvent.loadedMetadata(resumed);
    expect(resumed.currentTime).toBe(7);
    expect(
      within(resumed.parentElement!).getByRole("button", {
        name: "Resume audio",
      }),
    ).toBeTruthy();
    fireEvent.ended(resumed);
    view.rerender(exam(other));
    view.rerender(exam(value));
    expect(
      within(
        screen.getByLabelText("Original prompt 1").parentElement!,
      ).queryByRole("button"),
    ).toBeNull();
    expect(HTMLMediaElement.prototype.play).toHaveBeenCalledTimes(1);
  });

  it("enables native replay controls only for an opted-in practice", () => {
    render(exam(untimed(true)));
    expect(
      (screen.getByLabelText("Original prompt 1") as HTMLAudioElement).controls,
    ).toBe(true);
    expect(
      (
        screen.getByLabelText(
          "Supplemental reference track",
        ) as HTMLAudioElement
      ).controls,
    ).toBe(true);
    expect(screen.queryByRole("button", { name: "Play audio" })).toBeNull();
  });

  it("retains consumed audio when the exam unmounts for History and resumes, while leaving unseen media playable", async () => {
    const value = untimed(false);
    const referencePlayback = new Map<string, ReferencePlayback>();
    const view = render(exam(value, { referencePlayback }));
    const original = screen.getByLabelText(
      "Original prompt 1",
    ) as HTMLAudioElement;
    await act(async () => {
      fireEvent.click(
        within(original.parentElement!).getByRole("button", {
          name: "Play audio",
        }),
      );
    });
    fireEvent.playing(original);
    original.currentTime = 9;
    fireEvent.timeUpdate(original);
    view.unmount();
    const resumed = render(exam(value, { referencePlayback }));
    const audio = screen.getByLabelText(
      "Original prompt 1",
    ) as HTMLAudioElement;
    fireEvent.loadedMetadata(audio);
    expect(audio.currentTime).toBe(9);
    fireEvent.ended(audio);
    resumed.unmount();
    render(exam(value, { referencePlayback }));
    expect(
      within(
        screen.getByLabelText("Original prompt 1").parentElement!,
      ).queryByRole("button"),
    ).toBeNull();
    expect(
      within(
        screen.getByLabelText("Supplemental reference track").parentElement!,
      ).getByRole("button", { name: "Play audio", hidden: true }),
    ).toBeTruthy();
    expect(HTMLMediaElement.prototype.play).toHaveBeenCalledTimes(1);
  });
});

it.each([false, true])(
  "App reviews setup instead of resuming an existing matching attempt and sends the chosen boolean: %s",
  async (enabled) => {
    const old = session({ id: "old-attempt", sourceVersionMatches: true });
    const created = session({ id: "new-attempt", allowPracticeAids: enabled });
    const requests: {
      url: string;
      method: string;
      body?: Record<string, unknown>;
    }[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, options: RequestInit = {}) => {
        const url = String(input),
          method = options.method || "GET";
        const body = options.body
          ? JSON.parse(String(options.body))
          : undefined;
        requests.push({ url, method, body });
        const json = (value: unknown) =>
          new Response(JSON.stringify(value), {
            headers: { "Content-Type": "application/json" },
          });
        if (url === "/api/catalog")
          return json({ exams: [fixture], materials: [] });
        if (url === "/api/sessions" && method === "GET")
          return json({ sessions: [old] });
        if (url === `/api/exams/${fixture.id}`) return json(fixture);
        if (url === "/api/sessions" && method === "POST") return json(created);
        if (url === `/api/sessions/${created.id}`) return json(created);
        if (url.startsWith(`/api/sessions/${created.id}/feedback?`))
          return json({
            question: created.question,
            answer: "A",
            grade: { correct: 1, total: 1 },
          });
        throw new Error(`Unexpected request ${method} ${url}`);
      }),
    );
    await act(async () => {
      render(<App />);
    });
    await act(async () => {
      fireEvent.click(
        screen.getByRole("button", { name: "Practice Listening", exact: true }),
      );
    });
    expect(screen.getByRole("dialog")).toBeTruthy();
    expect(checkbox().checked).toBe(false);
    expect(
      requests.some(
        (request) =>
          request.url === `/api/sessions/${old.id}` ||
          request.url.endsWith("/events"),
      ),
    ).toBe(false);
    if (enabled) fireEvent.click(checkbox());
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Start practice" }));
    });
    await waitFor(() =>
      expect(
        requests.find(
          (request) =>
            request.url === "/api/sessions" && request.method === "POST",
        ),
      ).toBeTruthy(),
    );
    expect(
      requests.find(
        (request) =>
          request.url === "/api/sessions" && request.method === "POST",
      )?.body,
    ).toMatchObject({
      examId: fixture.id,
      mode: "practice",
      scope: "listening",
      allowPracticeAids: enabled,
    });
    expect(old.id).toBe("old-attempt");
    expect(old.answer).toBe("A");
    expect(old.allowPracticeAids).toBeUndefined();
    if (enabled) {
      await act(async () => {
        fireEvent.click(
          screen.getByRole("button", { name: "Check answer & explanation" }),
        );
      });
      expect(
        requests.filter((request) => request.url.includes("/feedback?")),
      ).toHaveLength(1);
    } else {
      expect(
        screen.queryByRole("button", { name: "Check answer & explanation" }),
      ).toBeNull();
      expect(
        requests.some((request) => request.url.includes("/feedback?")),
      ).toBe(false);
    }
  },
);
