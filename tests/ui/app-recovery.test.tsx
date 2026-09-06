import React from "react";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../../src/App";
import type { Catalog, EventInput, Session } from "../../src/types";

// These tests cover the App/HTTP recovery boundary, not MediaRecorder or its
// separately tested IndexedDB outbox. Reading has no microphone requirement.
vi.mock("../../src/recording", () => ({
  flushRecordings: vi.fn(async () => {}),
  pendingRecordings: vi.fn(async () => 0),
  retryRecordings: vi.fn(async () => 0),
  stopRecorders: vi.fn(async () => {}),
  supportedMime: vi.fn(() => ""),
  saveChunk: vi.fn(async () => {}),
  saveFinalization: vi.fn(async () => {}),
  trackRecorder: vi.fn(),
}));

const START = Date.UTC(2026, 8, 1, 0, 0, 0);
const DEADLINE = START + 60_000;
const SESSION_ID = "session-ui-recovery-fixture";
const QUESTION_ID = "ui-recovery-reading-fixture";
const LOCK_REASON =
  "Another strict session is active. Other sessions and their media are locked until it ends.";

function memoryStorage(): Storage {
  const values = new Map<string, string>();
  return {
    get length() {
      return values.size;
    },
    clear: () => values.clear(),
    getItem: (key) => values.get(key) ?? null,
    key: (index) => [...values.keys()][index] ?? null,
    removeItem: (key) => {
      values.delete(key);
    },
    setItem: (key, value) => {
      values.set(key, String(value));
    },
  };
}

function sourceSession(): Session {
  return {
    id: SESSION_ID,
    examId: "ui-only-fixture",
    title: "UI recovery fixture — never part of the source question bank",
    mode: "strict",
    scope: "reading",
    routeMode: "fixed",
    route: "upper",
    status: "active",
    phase: "response",
    stageIndex: 0,
    questionIndex: 0,
    revision: 1,
    serverNow: START,
    deadline: DEADLINE,
    remainingSeconds: 60,
    stage: {
      id: "reading-fixture",
      section: "reading",
      title: "Reading recovery fixture",
      timer: "shared",
      seconds: 60,
      questionCount: 1,
      canBack: true,
    },
    question: {
      id: QUESTION_ID,
      type: "choice",
      number: 1,
      prompt: "Engineering fixture for retaining an existing answer.",
      choices: [
        { id: "A", text: "Unselected fixture choice" },
        { id: "B", text: "Previously saved fixture choice" },
      ],
    },
    answer: "B",
    questionMap: [
      { index: 0, questionId: QUESTION_ID, answered: true, flagged: false },
    ],
    integrity: { interrupted: false, events: [] },
    allowedActions: ["answer", "next", "flag", "finish"],
    progress: {
      stageIndex: 0,
      totalStages: 1,
      questionIndex: 0,
      totalQuestions: 1,
    },
  };
}

function installServer() {
  const saved = sourceSession();
  const events: (EventInput & { requestId: string })[] = [];
  const requests: { url: string; method: string }[] = [];
  const catalog: Catalog = { exams: [], materials: [], stats: {} };
  let showHistory = false;
  let recoveryFailure = false;
  let historyFailure = false;
  let pollFailure = false;
  const snapshot = (): Session =>
    structuredClone({
      ...saved,
      serverNow: Date.now(),
      remainingSeconds: Math.max(0, Math.ceil((DEADLINE - Date.now()) / 1000)),
    });
  const json = (body: unknown, status = 200) =>
    Promise.resolve(
      new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
      }),
    );
  const fetchMock = vi.fn(
    (input: RequestInfo | URL, options: RequestInit = {}) => {
      const url = String(input),
        method = options.method || "GET";
      requests.push({ url, method });
      if (url === "/api/catalog") return json(catalog);
      if (url === "/api/sessions")
        return historyFailure
          ? json({ error: "History temporarily unavailable." }, 503)
          : json({ sessions: showHistory ? [snapshot()] : [] });
      if (url === `/api/exams/${saved.examId}`) return json(catalog.exams[0]);
      if (
        url === `/api/sessions/${SESSION_ID}/recover-audio` &&
        method === "POST"
      ) {
        if (recoveryFailure)
          return json({ error: "Audio repair temporarily failed." }, 503);
        saved.canRecoverAudio = false;
        saved.audioRecoveryApplied = true;
        saved.revision++;
        return json(snapshot());
      }
      if (url === `/api/sessions/${SESSION_ID}/events` && method === "POST") {
        const event = JSON.parse(String(options.body));
        events.push(event);
        if (event.action !== "interrupt")
          throw new Error(`Unexpected recovery action: ${event.action}`);
        saved.revision++;
        saved.integrity = {
          interrupted: true,
          events: [
            ...(saved.integrity.events || []),
            {
              type: "interrupt",
              detail: { reason: event.reason },
              at: Date.now(),
            },
          ],
        };
        return json(snapshot());
      }
      if (url === `/api/sessions/${SESSION_ID}` && method === "GET")
        return pollFailure
          ? json({ error: LOCK_REASON }, 403)
          : json(snapshot());
      throw new Error(`Unexpected fixture request: ${method} ${url}`);
    },
  );
  vi.stubGlobal("fetch", fetchMock);
  return {
    events,
    requests,
    saved,
    catalog,
    showHistory: () => {
      showHistory = true;
    },
    failRecovery: (value: boolean) => {
      recoveryFailure = value;
    },
    failHistory: () => {
      historyFailure = true;
    },
    lockPoll: () => {
      pollFailure = true;
    },
  };
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(START);
  // Avoid Node's optional file-backed Web Storage, which may shadow jsdom's
  // storage on newer runtimes. Each test owns fresh browser-like stores.
  vi.stubGlobal("localStorage", memoryStorage());
  vi.stubGlobal("sessionStorage", memoryStorage());
  sessionStorage.setItem("toefl-active-session", SESSION_ID);
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
  Object.defineProperty(HTMLDialogElement.prototype, "showModal", {
    configurable: true,
    value: function (this: HTMLDialogElement) {
      this.setAttribute("open", "");
    },
  });
});

afterEach(() => {
  cleanup();
  vi.clearAllTimers();
  vi.useRealTimers();
  localStorage.clear();
  sessionStorage.clear();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

it("offers explicit legacy audio recovery before resuming and preserves the existing response deadline", async () => {
  const server = installServer();
  Object.assign(server.saved, {
    mode: "practice",
    canRecoverAudio: true,
    sourceVersionMatches: false,
  });
  await act(async () => {
    render(<App />);
  });
  expect(
    screen.getByRole("heading", { name: "Restore listening audio" }),
  ).toBeTruthy();
  expect(server.events).toHaveLength(0);
  expect(server.requests.some((r) => r.method === "POST")).toBe(false);
  await act(async () => {
    fireEvent.click(
      screen.getByRole("button", { name: "Repair audio and continue" }),
    );
  });
  expect(
    server.requests.filter((r) => r.url.endsWith("/recover-audio")),
  ).toHaveLength(1);
  expect(server.events.map((e) => e.reason)).toEqual(["session-restored"]);
  expect(server.saved.answer).toBe("B");
  expect(server.saved.deadline).toBe(DEADLINE);
  expect(
    screen.getByRole("timer", { name: "Time remaining" }).textContent,
  ).toBe("00:01:00");
  expect(
    screen.queryByRole("heading", { name: "Restore listening audio" }),
  ).toBeNull();
});

it("keeps recovery available after a failed repair without resuming or clearing the session", async () => {
  const server = installServer();
  Object.assign(server.saved, {
    mode: "practice",
    canRecoverAudio: true,
    sourceVersionMatches: false,
  });
  server.failRecovery(true);
  await act(async () => {
    render(<App />);
  });
  await act(async () => {
    fireEvent.click(
      screen.getByRole("button", { name: "Repair audio and continue" }),
    );
  });
  expect(screen.getByRole("alert").textContent).toBe(
    "Audio repair temporarily failed.",
  );
  expect(server.events).toHaveLength(0);
  expect(server.saved.answer).toBe("B");
  server.failRecovery(false);
  await act(async () => {
    fireEvent.click(
      screen.getByRole("button", { name: "Repair audio and continue" }),
    );
  });
  expect(server.events).toHaveLength(1);
});

it("continues after successful repair even when refreshing history fails", async () => {
  const server = installServer();
  Object.assign(server.saved, {
    mode: "practice",
    canRecoverAudio: true,
    sourceVersionMatches: false,
  });
  await act(async () => {
    render(<App />);
  });
  server.failHistory();
  await act(async () => {
    fireEvent.click(
      screen.getByRole("button", { name: "Repair audio and continue" }),
    );
  });
  expect(server.saved.audioRecoveryApplied).toBe(true);
  expect(server.events.map((event) => event.reason)).toEqual([
    "session-restored",
  ]);
  expect(
    screen.queryByRole("heading", { name: "Restore listening audio" }),
  ).toBeNull();
  expect(screen.getByRole("timer", { name: "Time remaining" })).toBeTruthy();
});

it("starts a new setup instead of silently reopening a source-incompatible session", async () => {
  sessionStorage.removeItem("toefl-active-session");
  const server = installServer();
  server.saved.sourceVersionMatches = false;
  server.showHistory();
  server.catalog.exams.push({
    id: server.saved.examId,
    title: "Recovery source fixture",
    family: "user",
    strictEligible: false,
    sections: [{ id: "reading", questionCount: 1 }],
    warnings: [],
  });
  await act(async () => {
    render(<App />);
  });
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: "Start new practice" }));
  });
  expect(
    server.requests.some((r) => r.url === `/api/exams/${server.saved.examId}`),
  ).toBe(true);
  expect(
    server.requests.some((r) => r.url === `/api/sessions/${SESSION_ID}`),
  ).toBe(false);
  expect(server.events).toHaveLength(0);
  expect(screen.getByRole("dialog")).toBeTruthy();
});

async function restore() {
  await act(async () => {
    render(<App />);
  });
  expect(
    screen.getByRole("timer", { name: "Time remaining" }).textContent,
  ).toBe("00:01:00");
  expect(
    (
      screen.getByRole("radio", {
        name: /Previously saved fixture choice/,
      }) as HTMLInputElement
    ).checked,
  ).toBe(true);
}

it("restores a filtered all-scope objective selection without requesting a microphone", async () => {
  const server = installServer();
  server.saved.scope = "all";
  server.saved.filtered = true;
  server.saved.requiresMicrophone = false;
  const getUserMedia = vi.fn(async () => {
    throw new Error("An objective mistake retry must not request audio.");
  });
  vi.stubGlobal("navigator", { mediaDevices: { getUserMedia } });
  vi.stubGlobal("MediaRecorder", class {});
  await restore();
  expect(getUserMedia).not.toHaveBeenCalled();
  expect(
    server.events.some((event) => event.reason === "session-restored"),
  ).toBe(true);
});

describe("App recovery polling", () => {
  it("reports a clock gap on the next poll without clearing the answer or extending its original deadline", async () => {
    const server = installServer();
    await restore();
    expect(server.events.map((event) => event.reason)).toEqual([
      "session-restored",
    ]);

    // A sleep/resume jump changes wall time without delivering the skipped
    // interval callbacks. Advancing only one normal poll detects that gap.
    vi.setSystemTime(START + 6_500);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(400);
    });

    const gaps = server.events.filter((event) => event.reason === "clock-gap");
    expect(gaps).toHaveLength(1);
    expect(gaps[0]).toMatchObject({
      action: "interrupt",
      details: { gapMilliseconds: 6_900 },
    });
    expect(gaps[0].requestId).toEqual(expect.any(String));
    expect(server.requests.at(-1)).toEqual({
      url: `/api/sessions/${SESSION_ID}`,
      method: "GET",
    });
    expect(server.events.every((event) => event.action === "interrupt")).toBe(
      true,
    );
    expect(server.saved.answer).toBe("B");
    expect(server.saved.deadline).toBe(DEADLINE);
    expect(
      (
        screen.getByRole("radio", {
          name: /Previously saved fixture choice/,
        }) as HTMLInputElement
      ).checked,
    ).toBe(true);
    expect(
      screen.getByRole("timer", { name: "Time remaining" }).textContent,
    ).toBe("00:00:54");
    expect(sessionStorage.getItem("toefl-active-session")).toBe(SESSION_ID);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(400);
    });
    expect(
      server.events.filter((event) => event.reason === "clock-gap"),
    ).toHaveLength(1);
  });

  it("shows a strict-session 403 reason instead of misreporting a network disconnection", async () => {
    const server = installServer();
    await restore();
    server.lockPoll();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(400);
    });

    expect(screen.getByRole("alert").textContent).toBe(LOCK_REASON);
    expect(screen.queryByText(/Local server disconnected/)).toBeNull();
    const answer = screen.getByRole("radio", {
      name: /Previously saved fixture choice/,
    }) as HTMLInputElement;
    expect(answer.checked).toBe(true);
    expect(answer.disabled).toBe(true);
    expect(server.events.map((event) => event.reason)).toEqual([
      "session-restored",
    ]);
    expect(sessionStorage.getItem("toefl-active-session")).toBe(SESSION_ID);
  });
});
