import React from "react";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Exam from "../../src/Exam";
import type { Session } from "../../src/types";

const recording = vi.hoisted(() => ({
  saveChunk: vi.fn(),
  saveFinalization: vi.fn(),
  supportedMime: () => "audio/webm",
  trackRecorder: vi.fn(),
  stopRecorders: vi.fn(),
  flushRecordings: vi.fn(),
}));
vi.mock("../../src/recording", () => recording);

class Recorder {
  state = "inactive";
  mimeType = "audio/webm";
  onstop?: () => void;
  start() {
    this.state = "recording";
  }
  stop() {
    this.state = "inactive";
    this.onstop?.();
  }
}
const stream = { active: true } as MediaStream;
const makeSession = (): Session => ({
  id: "timing-regression",
  examId: "timing-fixture",
  title: "Timing test",
  mode: "strict",
  scope: "speaking",
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
  question: { id: "repeat-window", type: "listen_repeat" },
  stage: {
    id: "repeat",
    section: "speaking",
    title: "Listen and Repeat",
    timer: "item",
    seconds: 8,
    questionCount: 7,
    canBack: false,
  },
  integrity: { interrupted: false },
  allowedActions: [],
});
const view = (session: Session) => (
  <Exam
    session={session}
    stream={stream}
    send={vi.fn()}
    onLeave={vi.fn()}
    onFinish={vi.fn()}
    onNotice={vi.fn()}
    offline={false}
    acquireMic={vi.fn()}
    onFeedback={vi.fn()}
  />
);

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-09-05T07:00:00Z"));
  vi.stubGlobal("MediaRecorder", Recorder);
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
  vi.stubGlobal("localStorage", {
    getItem: vi.fn(() => null),
    setItem: vi.fn(),
    removeItem: vi.fn(),
  });
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("speaking response deadline", () => {
  it("keeps the same original video frame during recording and clears it for the next question", () => {
    vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();
    vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => {});
    const drawImage = vi.fn();
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({
      drawImage,
    } as unknown as CanvasRenderingContext2D);
    vi.spyOn(HTMLCanvasElement.prototype, "toDataURL").mockReturnValue(
      "data:image/png;base64,c291cmNlZnJhbWU=",
    );
    const initial = makeSession();
    const question = {
      id: "source-video",
      type: "interview",
      assets: [],
      audio: { url: "/api/source-video.mp4", mediaType: "video" },
    };
    const audioSession: Session = {
      ...initial,
      phase: "audio",
      deadline: null,
      remainingSeconds: null,
      question,
    };
    const ui = render(view(audioSession));
    const video = screen.getByLabelText("Question audio");
    Object.defineProperties(video, {
      videoWidth: { value: 640 },
      videoHeight: { value: 480 },
    });
    fireEvent.ended(video);
    expect(drawImage).toHaveBeenCalledWith(video, 0, 0);
    ui.rerender(
      view({
        ...initial,
        question: { id: question.id, type: "interview", assets: [] },
      }),
    );
    expect(
      screen
        .getByAltText("Last frame of the original interviewer video")
        .getAttribute("src"),
    ).toBe("data:image/png;base64,c291cmNlZnJhbWU=");
    ui.rerender(
      view({
        ...audioSession,
        question: { id: "next-source-video", type: "interview", assets: [] },
      }),
    );
    expect(
      screen.queryByAltText("Last frame of the original interviewer video"),
    ).toBeNull();
  });
  it("preserves a natural stop when a server refresh moves the display clock back", () => {
    const initial = makeSession();
    const ui = render(view(initial));
    act(() => vi.advanceTimersByTime(2000));
    ui.rerender(view({ ...initial, revision: 2, serverNow: Date.now() - 12 }));
    act(() => vi.advanceTimersByTime(6000));
    expect(recording.saveFinalization).toHaveBeenCalledExactlyOnceWith(
      expect.objectContaining({
        questionId: "repeat-window",
        endedReason: "time-limit",
      }),
      expect.any(Function),
    );
  });

  it("still records leaving before the deadline as an early stop", () => {
    const ui = render(view(makeSession()));
    act(() => vi.advanceTimersByTime(2000));
    ui.unmount();
    expect(recording.saveFinalization).toHaveBeenCalledExactlyOnceWith(
      expect.objectContaining({ endedReason: "stopped-early" }),
      expect.any(Function),
    );
  });

  it("accepts authoritative server expiry when the server advances first", () => {
    const initial = makeSession();
    const ui = render(view(initial));
    act(() => vi.advanceTimersByTime(7990));
    ui.rerender(
      view({
        ...initial,
        phase: "audio",
        revision: 2,
        serverNow: initial.deadline!,
        deadline: null,
        remainingSeconds: null,
        questionIndex: 1,
        question: { id: "next-repeat-window", type: "listen_repeat" },
      }),
    );
    expect(recording.saveFinalization).toHaveBeenCalledExactlyOnceWith(
      expect.objectContaining({
        questionId: "repeat-window",
        endedReason: "time-limit",
      }),
      expect.any(Function),
    );
  });
});
