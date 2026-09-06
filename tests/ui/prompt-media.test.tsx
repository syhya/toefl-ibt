import React from "react";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Exam, { PromptMedia } from "../../src/Exam";
import { setLocale } from "../../src/i18n";
import type { Session } from "../../src/types";

const SOURCE_CHANGED =
  "This media/source asset no longer matches the session snapshot. The original answers and deadline are preserved; restore the source or start a reimported practice.";
const LEGACY_AUDIO =
  "This older session has no saved audio verification. Recover verified audio to continue without changing your saved answers or progress.";
const URL = "/api/sessions/fixture/assets/audio-five";
const source = { url: URL, mediaType: "audio" };
const httpError = (status: number, error: string, code?: string) =>
  new Response(JSON.stringify({ error, code }), {
    status,
    headers: { "Content-Type": "application/json" },
  });

function player(
  overrides: Partial<React.ComponentProps<typeof PromptMedia>> = {},
) {
  return (
    <PromptMedia
      media={source}
      label="Question audio"
      onError={vi.fn()}
      onEnded={vi.fn()}
      {...overrides}
    />
  );
}
async function fail() {
  await act(async () => {
    fireEvent.error(screen.getByLabelText("Question audio"));
  });
  await waitFor(() =>
    expect(screen.queryByText("Checking audio access…")).toBeNull(),
  );
}
beforeEach(() => {
  vi.stubGlobal("sessionStorage", {
    getItem: vi.fn(() => null),
    setItem: vi.fn(),
  });
  setLocale("en");
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
  vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();
  vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => {});
  vi.spyOn(HTMLMediaElement.prototype, "load").mockImplementation(() => {});
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response("x", {
          status: 206,
          headers: { "Content-Type": "audio/ogg" },
        }),
    ),
  );
});
afterEach(() => {
  cleanup();
  setLocale("en");
  vi.useRealTimers();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("prompt media failure and recovery", () => {
  it("keeps autoplay permission failures separate from server and decoder errors", async () => {
    vi.mocked(HTMLMediaElement.prototype.play).mockRejectedValueOnce(
      new DOMException("A click is required", "NotAllowedError"),
    );
    const onError = vi.fn(),
      onStarted = vi.fn(),
      onEnded = vi.fn();
    render(player({ onError, onStarted, onEnded }));
    expect(
      await screen.findByText(
        "Your browser requires a click before playing audio.",
      ),
    ).toBeTruthy();
    expect(fetch).not.toHaveBeenCalled();
    expect(onError).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Play audio" }));
    expect(HTMLMediaElement.prototype.load).not.toHaveBeenCalled();
    fireEvent.playing(screen.getByLabelText("Question audio"));
    expect(onStarted).toHaveBeenCalledTimes(1);
    expect(onEnded).not.toHaveBeenCalled();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("shows the localized server 409 and never loops through Play or attempts to repair a changed source", async () => {
    vi.mocked(fetch).mockResolvedValue(
      httpError(409, SOURCE_CHANGED, "source-changed"),
    );
    const onError = vi.fn(),
      onEnded = vi.fn(),
      onRecoverAudio = vi.fn();
    render(player({ onError, onEnded, onRecoverAudio }));
    await fail();
    fireEvent.error(screen.getByLabelText("Question audio"));
    fireEvent.ended(screen.getByLabelText("Question audio"));
    expect(fetch).toHaveBeenCalledExactlyOnceWith(URL, {
      headers: { Range: "bytes=0-0" },
      signal: expect.any(AbortSignal),
    });
    expect(onError).toHaveBeenCalledTimes(1);
    expect(onEnded).not.toHaveBeenCalled();
    expect(screen.getByText(SOURCE_CHANGED)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Play audio" })).toBeNull();
    expect(
      screen.queryByRole("button", { name: "Repair audio and continue" }),
    ).toBeNull();
    act(() => setLocale("zh-CN"));
    expect(
      screen.getByText(
        "此媒体或来源素材已不匹配练习快照。原答案和截止时间已保留，请恢复来源或重新导入后开始新的练习。",
      ),
    ).toBeTruthy();
  });

  it("repairs legacy verification before reloading the same source and waits for real playback to progress", async () => {
    vi.mocked(fetch).mockResolvedValue(
      httpError(409, LEGACY_AUDIO, "legacy-audio-unverified"),
    );
    let finishRepair!: () => void;
    const onRecoverAudio = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          finishRepair = resolve;
        }),
    );
    const onStarted = vi.fn(),
      onEnded = vi.fn();
    const view = render(player({ onRecoverAudio, onStarted, onEnded }));
    await fail();
    expect(screen.getByText(LEGACY_AUDIO)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Play audio" })).toBeNull();
    fireEvent.click(
      screen.getByRole("button", { name: "Repair audio and continue" }),
    );
    const repairing = screen.getByRole("button", { name: "Repairing audio…" });
    expect((repairing as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(repairing);
    expect(onRecoverAudio).toHaveBeenCalledTimes(1);
    expect(HTMLMediaElement.prototype.load).not.toHaveBeenCalled();
    expect(onStarted).not.toHaveBeenCalled();
    expect(onEnded).not.toHaveBeenCalled();
    // App can withdraw repair eligibility once it applies the repaired session.
    view.rerender(player({ onStarted, onEnded }));
    await act(async () => {
      finishRepair();
    });
    const audio = screen.getByLabelText("Question audio");
    expect(audio.getAttribute("src")).toBe(URL);
    expect(HTMLMediaElement.prototype.load).toHaveBeenCalledTimes(1);
    expect(HTMLMediaElement.prototype.play).toHaveBeenCalledTimes(2);
    expect(onEnded).not.toHaveBeenCalled();
    fireEvent.playing(audio);
    fireEvent.playing(audio);
    expect(onStarted).toHaveBeenCalledTimes(1);
    fireEvent.ended(audio);
    expect(onEnded).toHaveBeenCalledTimes(1);
  });

  it("keeps a failed repair retryable without reloading or advancing", async () => {
    vi.mocked(fetch).mockResolvedValue(
      httpError(409, LEGACY_AUDIO, "legacy-audio-unverified"),
    );
    const onRecoverAudio = vi
      .fn()
      .mockRejectedValueOnce(new Error("Repair service unavailable."))
      .mockResolvedValueOnce(undefined);
    const onEnded = vi.fn();
    render(player({ onRecoverAudio, onEnded }));
    await fail();
    await act(async () => {
      fireEvent.click(
        screen.getByRole("button", { name: "Repair audio and continue" }),
      );
    });
    expect(screen.getByText("Repair service unavailable.")).toBeTruthy();
    expect(
      (
        screen.getByRole("button", {
          name: "Repair audio and continue",
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(false);
    expect(HTMLMediaElement.prototype.load).not.toHaveBeenCalled();
    expect(onEnded).not.toHaveBeenCalled();
    await act(async () => {
      fireEvent.click(
        screen.getByRole("button", { name: "Repair audio and continue" }),
      );
    });
    expect(onRecoverAudio).toHaveBeenCalledTimes(2);
    expect(HTMLMediaElement.prototype.load).toHaveBeenCalledTimes(1);
    expect(screen.queryByText("Repair service unavailable.")).toBeNull();
    expect(onEnded).not.toHaveBeenCalled();
  });

  it("retries other HTTP failures and diagnoses each attempt once while reporting only one interruption", async () => {
    vi.mocked(fetch).mockImplementation(async () =>
      httpError(503, "Audio storage unavailable."),
    );
    const onError = vi.fn();
    render(player({ onError }));
    await fail();
    expect(screen.getByText("Audio storage unavailable.")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Play audio" }));
    expect(HTMLMediaElement.prototype.load).toHaveBeenCalledTimes(1);
    await fail();
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(onError).toHaveBeenCalledTimes(1);
  });

  it("cancels a successful media response instead of consuming its body", async () => {
    const response = new Response("audio bytes", {
      status: 200,
      headers: { "Content-Type": "audio/ogg" },
    });
    const cancel = vi.spyOn(response.body!, "cancel");
    vi.mocked(fetch).mockResolvedValue(response);
    render(player());
    await fail();
    expect(cancel).toHaveBeenCalledTimes(1);
    expect(
      screen.getByText(
        "Audio could not load. Check your local server and retry.",
      ),
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: "Play audio" })).toBeTruthy();
  });

  it("retains a retry when the diagnostic network request fails", async () => {
    vi.mocked(fetch).mockRejectedValue(new TypeError("Failed to fetch"));
    render(player());
    await fail();
    expect(
      screen.getByText(
        "Audio could not load. Check your local server and retry.",
      ),
    ).toBeTruthy();
    expect(
      (screen.getByRole("button", { name: "Play audio" }) as HTMLButtonElement)
        .disabled,
    ).toBe(false);
  });

  it("bounds a stalled diagnostic request so playback retry remains available", async () => {
    vi.useFakeTimers();
    vi.mocked(fetch).mockImplementationOnce(() => new Promise(() => {}));
    render(player());
    fireEvent.error(screen.getByLabelText("Question audio"));
    const signal = vi.mocked(fetch).mock.calls[0][1]!.signal!;
    expect(
      (screen.getByRole("button", { name: "Play audio" }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    expect(signal.aborted).toBe(true);
    expect(screen.queryByText("Checking audio access…")).toBeNull();
    expect(
      (screen.getByRole("button", { name: "Play audio" }) as HTMLButtonElement)
        .disabled,
    ).toBe(false);
  });

  it("diagnoses a NotSupportedError promise rejection even without a media error event", async () => {
    vi.mocked(HTMLMediaElement.prototype.play).mockRejectedValueOnce(
      new DOMException("No decoder", "NotSupportedError"),
    );
    const onError = vi.fn();
    render(player({ onError }));
    expect(
      await screen.findByText(
        "This audio format could not play in your browser.",
      ),
    ).toBeTruthy();
    await waitFor(() =>
      expect(screen.queryByText("Checking audio access…")).toBeNull(),
    );
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(onError).toHaveBeenCalledTimes(1);
    expect(
      screen.queryByText("Your browser requires a click before playing audio."),
    ).toBeNull();
  });

  it("retains HTTP status when an error response has no JSON message", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response("Conflict", { status: 409 }),
    );
    render(player());
    await fail();
    expect(screen.getByText("Audio request failed (HTTP 409).")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Play audio" })).toBeNull();
  });

  it("aborts diagnostics and ignores late results after the media URL changes", async () => {
    let complete!: (response: Response) => void;
    vi.mocked(fetch).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          complete = resolve;
        }),
    );
    const view = render(player());
    fireEvent.error(screen.getByLabelText("Question audio"));
    const signal = vi.mocked(fetch).mock.calls[0][1]!.signal!;
    view.rerender(player({ media: { url: `${URL}-next` } }));
    expect(signal.aborted).toBe(true);
    await act(async () => {
      complete(httpError(409, SOURCE_CHANGED, "source-changed"));
    });
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.getByLabelText("Question audio").getAttribute("src")).toBe(
      `${URL}-next`,
    );
  });

  it("aborts the diagnostic request on unmount", async () => {
    let complete!: (response: Response) => void;
    vi.mocked(fetch).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          complete = resolve;
        }),
    );
    const onError = vi.fn();
    const view = render(player({ onError }));
    fireEvent.error(screen.getByLabelText("Question audio"));
    const signal = vi.mocked(fetch).mock.calls[0][1]!.signal!;
    view.unmount();
    expect(signal.aborted).toBe(true);
    await act(async () => {
      complete(httpError(409, SOURCE_CHANGED));
    });
    expect(onError).toHaveBeenCalledTimes(1);
    expect(document.querySelector("audio")).toBeNull();
  });

  it("does not reload the next question when an older repair finishes", async () => {
    vi.mocked(fetch).mockResolvedValue(
      httpError(409, LEGACY_AUDIO, "legacy-audio-unverified"),
    );
    let finishRepair!: () => void;
    const onRecoverAudio = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          finishRepair = resolve;
        }),
    );
    const view = render(player({ onRecoverAudio }));
    await fail();
    fireEvent.click(
      screen.getByRole("button", { name: "Repair audio and continue" }),
    );
    view.rerender(player({ media: { url: `${URL}-next` } }));
    await act(async () => {
      finishRepair();
    });
    expect(HTMLMediaElement.prototype.load).not.toHaveBeenCalled();
    expect(HTMLMediaElement.prototype.play).toHaveBeenCalledTimes(2);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("ignores a late play rejection from the previous media", async () => {
    let reject!: (error: Error) => void;
    vi.mocked(HTMLMediaElement.prototype.play).mockImplementationOnce(
      () =>
        new Promise((_resolve, rejectPromise) => {
          reject = rejectPromise;
        }),
    );
    const view = render(player());
    view.rerender(player({ media: { url: `${URL}-next` } }));
    await act(async () => {
      reject(new DOMException("old source", "NotSupportedError"));
    });
    expect(fetch).not.toHaveBeenCalled();
    expect(screen.queryByRole("alert")).toBeNull();
  });
});

it.each([true, false])(
  "Exam exposes audio repair only when the session permits it: %s",
  async (canRecoverAudio) => {
    vi.mocked(fetch).mockResolvedValue(
      httpError(409, LEGACY_AUDIO, "legacy-audio-unverified"),
    );
    const session: Session = {
      id: "audio-fixture",
      examId: "experience-1",
      title: "Audio regression",
      mode: "practice",
      scope: "listening",
      routeMode: "fixed",
      route: "upper",
      status: "active",
      phase: "audio",
      stageIndex: 0,
      questionIndex: 4,
      revision: 1,
      serverNow: Date.now(),
      deadline: null,
      remainingSeconds: null,
      canRecoverAudio,
      stage: {
        id: "listening",
        section: "listening",
        title: "Listening",
        timer: "item",
        seconds: 20,
        questionCount: 8,
        canBack: false,
      },
      question: {
        id: "experience-1-l1-5",
        number: 5,
        type: "choice",
        taskType: "listen_response",
        audio: source,
        choices: [{ id: "A", text: "Saved answer" }],
      },
      answer: "A",
      integrity: { interrupted: false },
      allowedActions: ["audio-started", "audio-ended", "finish"],
    };
    const send = vi.fn(),
      onRecoverAudio = vi.fn(async () => {});
    render(
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
        onRecoverAudio={onRecoverAudio}
      />,
    );
    await fail();
    const repair = screen.queryByRole("button", {
      name: "Repair audio and continue",
    });
    expect(!!repair).toBe(canRecoverAudio);
    expect(send).toHaveBeenCalledExactlyOnceWith({
      action: "interrupt",
      reason: "media-error",
      details: { questionId: "experience-1-l1-5" },
    });
    expect(session.answer).toBe("A");
    expect(session.deadline).toBeNull();
    expect(onRecoverAudio).not.toHaveBeenCalled();
  },
);
