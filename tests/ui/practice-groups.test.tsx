import React from "react";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import QuestionLibrary, { type PracticeGroup } from "../../src/QuestionLibrary";
import App, { Prepare } from "../../src/App";
import { setLocale } from "../../src/i18n";
import type { Exam, Session } from "../../src/types";

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

function group(changes: Partial<PracticeGroup> = {}): PracticeGroup {
  return {
    groupId: "source-module-category",
    examId: "source-test",
    examTitle: "Source test A",
    section: "reading",
    moduleId: "reading-m1",
    module: "Source module 1",
    route: "common",
    taskType: "academic_passage",
    questionIds: Array.from(
      { length: 20 },
      (_, index) => `source-q${index + 1}`,
    ),
    numberStart: 1,
    numberEnd: 20,
    screenCount: 20,
    itemCount: 20,
    completedCount: 3,
    status: "in_progress",
    hasAudio: false,
    audioCount: 0,
    duplicateCount: 1,
    groupContentId: "revision-original",
    sourcePages: [1, 2],
    ...changes,
  };
}
const json = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
const listing = (
  items: PracticeGroup[],
  options: Record<string, unknown> = {},
) => ({ items, total: items.length, page: 1, pageSize: 18, ...options });
function row(id: string) {
  return document.querySelector(
    `[data-practice-group-id="${id}"]`,
  ) as HTMLElement;
}
async function settle() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(170);
  });
}
function memoryStorage() {
  const values = new Map<string, string>();
  return {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, String(value)),
    removeItem: (key: string) => values.delete(key),
    clear: () => values.clear(),
  };
}
beforeEach(() => {
  vi.useFakeTimers();
  vi.stubGlobal("localStorage", memoryStorage());
  vi.stubGlobal("sessionStorage", memoryStorage());
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
  Object.defineProperty(HTMLDialogElement.prototype, "showModal", {
    configurable: true,
    value: function (this: HTMLDialogElement) {
      this.setAttribute("open", "");
    },
  });
  setLocale("en");
});
afterEach(() => {
  cleanup();
  setLocale("en");
  vi.useRealTimers();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("grouped task library", () => {
  it("renders source tests, modules, and category rows without splitting a group larger than one question page", async () => {
    const first = group();
    const second = group({
      groupId: "daily",
      taskType: "daily_life",
      questionIds: ["q21", "q22"],
      numberStart: 21,
      numberEnd: 22,
      screenCount: 2,
      itemCount: 2,
      completedCount: 2,
      status: "completed",
    });
    const third = group({
      groupId: "lower",
      moduleId: "reading-m2-lower",
      module: "Source module 2",
      route: "lower",
      questionIds: ["lower-1"],
      screenCount: 1,
      itemCount: 10,
      numberStart: 1,
      numberEnd: 10,
      taskType: "cloze",
    });
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => json(listing([first, second, third]))),
    );
    const practice = vi.fn();
    render(<QuestionLibrary practice={practice} />);
    await settle();
    expect(
      screen
        .getAllByRole("heading", { level: 3 })
        .map((heading) => heading.textContent),
    ).toEqual(["Source test A"]);
    expect(
      screen
        .getAllByRole("heading", { level: 4 })
        .map((heading) => heading.textContent),
    ).toEqual(["Source module 1", "Source module 2"]);
    expect(document.querySelectorAll(".practice-category-row")).toHaveLength(3);
    expect(within(row(first.groupId)).getByText("20 items")).toBeTruthy();
    expect(
      within(row(first.groupId)).getByText("Completed 3 / 20 questions"),
    ).toBeTruthy();
    expect(within(row(second.groupId)).getByText("Completed")).toBeTruthy();
    expect(screen.getByText("Lower branch")).toBeTruthy();
    expect(within(row(third.groupId)).getByText("10 items")).toBeTruthy();
    expect(
      within(row(third.groupId)).getByText("1 response screens"),
    ).toBeTruthy();
    fireEvent.click(
      within(row(first.groupId)).getByRole("button", {
        name: /Start group:.*Questions 1–20/,
      }),
    );
    expect(practice).toHaveBeenCalledExactlyOnceWith(first);
    expect(practice.mock.calls[0][0].questionIds).toHaveLength(20);
  });

  it("searches and deduplicates whole groups while preserving every returned member and its source identity", async () => {
    const original = group({ duplicateCount: 2 });
    const requests: URLSearchParams[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = new URL(String(input), "http://localhost");
        expect(url.pathname).toBe("/api/practice-groups");
        requests.push(url.searchParams);
        return json(listing([original]));
      }),
    );
    const practice = vi.fn();
    render(<QuestionLibrary practice={practice} />);
    await settle();
    fireEvent.change(screen.getByRole("searchbox"), {
      target: { value: "topic from one member" },
    });
    await settle();
    fireEvent.click(
      screen.getByRole("checkbox", { name: "Combine duplicate groups" }),
    );
    await settle();
    expect(requests.at(-1)?.get("q")).toBe("topic from one member");
    expect(requests.at(-1)?.get("deduplicate")).toBe("true");
    expect(requests.at(-1)?.get("page")).toBe("1");
    expect(screen.getByText("Same group in 2 sources")).toBeTruthy();
    fireEvent.click(within(row(original.groupId)).getByRole("button"));
    expect(practice).toHaveBeenCalledExactlyOnceWith(original);
    expect(practice.mock.calls[0][0].groupContentId).toBe("revision-original");
  });

  it("paginates groups and resets the page when the category or section changes", async () => {
    const requests: URLSearchParams[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const params = new URL(String(input), "http://localhost").searchParams;
        requests.push(params);
        return json(
          listing([group({ groupId: `group-page-${params.get("page")}` })], {
            total: 30,
            page: Number(params.get("page")),
          }),
        );
      }),
    );
    render(<QuestionLibrary practice={vi.fn()} />);
    await settle();
    fireEvent.click(screen.getByRole("button", { name: "Next page" }));
    await settle();
    expect(requests.at(-1)?.get("page")).toBe("2");
    fireEvent.click(
      within(screen.getByRole("group", { name: "Task type" })).getByRole(
        "button",
        { name: "Academic Passage" },
      ),
    );
    await settle();
    expect(requests.at(-1)?.get("page")).toBe("1");
    expect(requests.at(-1)?.get("taskType")).toBe("academic_passage");
    fireEvent.click(screen.getByRole("tab", { name: /Listening/ }));
    await settle();
    expect(requests.at(-1)?.get("section")).toBe("listening");
    expect(requests.at(-1)?.has("taskType")).toBe(false);
  });

  it("includes additional imported task types in filters and never drops them from All", async () => {
    const extra = group({
      groupId: "vocabulary",
      taskType: "essentials_vocabulary",
    });
    const unknown = group({
      groupId: "custom",
      taskType: "custom_reading_task",
    });
    const requests: URLSearchParams[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        requests.push(new URL(String(input), "http://localhost").searchParams);
        return json(
          listing([extra, unknown], {
            taskCounts: { essentials_vocabulary: 1, custom_reading_task: 1 },
          }),
        );
      }),
    );
    render(<QuestionLibrary practice={vi.fn()} />);
    await settle();
    expect(row("vocabulary")).toBeTruthy();
    expect(row("custom")).toBeTruthy();
    fireEvent.click(
      within(screen.getByRole("group", { name: "Task type" })).getByRole(
        "button",
        { name: "Vocabulary" },
      ),
    );
    await settle();
    expect(requests.at(-1)?.get("taskType")).toBe("essentials_vocabulary");
  });

  it("distinguishes repeated category runs by range and uses a group ordinal when source numbers are absent", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        json(
          listing([
            group({ groupId: "first", numberStart: 1, numberEnd: 3 }),
            group({ groupId: "second", numberStart: 8, numberEnd: 10 }),
            group({
              groupId: "unnumbered",
              numberStart: undefined,
              numberEnd: undefined,
            }),
          ]),
        ),
      ),
    );
    render(<QuestionLibrary practice={vi.fn()} />);
    await settle();
    expect(
      screen.getByRole("button", { name: /Start group:.*Questions 1–3/ }),
    ).toBeTruthy();
    expect(
      screen.getByRole("button", { name: /Start group:.*Questions 8–10/ }),
    ).toBeTruthy();
    expect(
      screen.getByRole("button", { name: /Start group:.*Group 3/ }),
    ).toBeTruthy();
    expect(screen.queryByText(/Part 3/)).toBeNull();
  });

  it("shows partial availability only for affected groups and keeps the available member list intact", async () => {
    const partial = group({
      groupId: "partial",
      unavailableCount: 1,
      sourceScreenCount: 21,
    });
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => json(listing([group(), partial]))),
    );
    const practice = vi.fn();
    render(<QuestionLibrary practice={practice} />);
    await settle();
    expect(
      screen.getAllByText(
        "Some source questions are unavailable. This group contains the available questions.",
      ),
    ).toHaveLength(1);
    fireEvent.click(within(row("partial")).getByRole("button"));
    expect(practice).toHaveBeenCalledExactlyOnceWith(partial);
  });

  it("ignores a superseded response even when the fetch implementation ignores abort", async () => {
    let resolveOld!: (response: Response) => void;
    let oldSignal: AbortSignal | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, options?: RequestInit) => {
        if (!String(input).includes("q=new")) {
          oldSignal = options?.signal || undefined;
          return new Promise<Response>((resolve) => {
            resolveOld = resolve;
          });
        }
        return Promise.resolve(
          json(listing([group({ examTitle: "New source" })])),
        );
      }),
    );
    render(<QuestionLibrary practice={vi.fn()} />);
    await settle();
    fireEvent.change(screen.getByRole("searchbox"), {
      target: { value: "new" },
    });
    await settle();
    expect(oldSignal?.aborted).toBe(true);
    await act(async () => {
      resolveOld(json(listing([group({ examTitle: "Stale source" })])));
    });
    expect(screen.getByRole("heading", { name: "New source" })).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Stale source" })).toBeNull();
  });
});

const sourceExam: Exam = {
  id: "source-test",
  title: "Source test A",
  family: "user",
  strictEligible: true,
  warnings: [],
  adaptiveEligible: true,
  adaptiveEligibility: { reading: true },
  sections: [{ id: "reading", questionCount: 40 }],
};
it("Prepare shows the group item count, locks source scope/branch, and resets its optional aids on each new group", async () => {
  const selected = group({
    groupId: "lower-cloze",
    route: "lower",
    taskType: "cloze",
    screenCount: 2,
    itemCount: 20,
    questionIds: ["first", "second"],
  });
  const start = vi.fn(async () => {});
  const props = {
    exam: sourceExam,
    materials: [],
    stream: null,
    acquireMic: vi.fn(),
    close: vi.fn(),
    start,
    practiceGroup: selected,
  };
  const view = render(<Prepare {...props} />);
  expect(
    screen.getByText(
      "Source module 1 · Complete the Words · 20 items in source order.",
    ),
  ).toBeTruthy();
  expect(screen.queryByText(/2 selected questions/)).toBeNull();
  expect(
    (
      screen.getByRole("combobox", {
        name: "Practice scope",
      }) as HTMLSelectElement
    ).disabled,
  ).toBe(true);
  expect(
    screen.queryByRole("combobox", { name: "Fixed second-module branch" }),
  ).toBeNull();
  expect(
    (screen.getByRole("radio", { name: /Strict practice/ }) as HTMLInputElement)
      .disabled,
  ).toBe(true);
  const checkbox = screen.getByRole("checkbox", {
    name: "Enable audio replay and instant answers",
  }) as HTMLInputElement;
  expect(checkbox.checked).toBe(false);
  expect(checkbox.disabled).toBe(false);
  fireEvent.click(checkbox);
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: "Start practice" }));
  });
  expect(start).toHaveBeenCalledWith(
    expect.objectContaining({
      mode: "practice",
      scope: "reading",
      route: "lower",
      routeMode: "fixed",
      allowPracticeAids: true,
    }),
  );
  view.rerender(
    <Prepare
      {...props}
      practiceGroup={{
        ...selected,
        groupId: "another-group",
        groupContentId: "new-revision",
      }}
    />,
  );
  expect(checkbox.checked).toBe(false);
});

it.each([false, true])(
  "App starts the selected lower group by stable id and expected revision, without single-question filters (aids=%s)",
  async (aids) => {
    const selected = group({
      route: "lower",
      moduleId: "reading-m2-lower",
      module: "Source module 2",
      taskType: "cloze",
      screenCount: 2,
      itemCount: 20,
      questionIds: ["first", "second"],
    });
    const sent: Record<string, unknown>[] = [];
    const created: Session = {
      id: "group-session",
      examId: sourceExam.id,
      title: sourceExam.title,
      mode: "practice",
      scope: "reading",
      routeMode: "fixed",
      route: "lower",
      filtered: true,
      allowPracticeAids: aids,
      status: "active",
      phase: "response",
      stageIndex: 0,
      questionIndex: 0,
      revision: 1,
      serverNow: Date.now(),
      deadline: Date.now() + 60000,
      remainingSeconds: 60,
      stage: {
        id: selected.moduleId,
        title: selected.module,
        section: "reading",
        timer: "shared",
        seconds: 60,
        questionCount: 2,
        canBack: true,
      },
      question: {
        id: "first",
        type: "cloze",
        prompt: "Complete the word.",
        passageTemplate: "wo{{b1}}",
        blanks: [{ id: "b1", prefix: "wo", length: 2 }],
      },
      integrity: { interrupted: false },
      allowedActions: ["answer", "next"],
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, options: RequestInit = {}) => {
        const url = String(input);
        if (url === "/api/catalog")
          return json({ exams: [sourceExam], materials: [] });
        if (url === "/api/sessions" && options.method === "POST") {
          sent.push(JSON.parse(String(options.body)));
          return json(created);
        }
        if (url === "/api/sessions") return json({ sessions: [] });
        if (url === `/api/exams/${sourceExam.id}`) return json(sourceExam);
        if (url.startsWith("/api/practice-groups?"))
          return json(listing([selected]));
        if (url === `/api/sessions/${created.id}`) return json(created);
        throw new Error(`Unexpected request ${url}`);
      }),
    );
    await act(async () => {
      render(<App />);
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Task library", exact: true }),
    );
    await settle();
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /^Start group:/ }));
    });
    const setup = screen.getByRole("dialog");
    const checkbox = within(setup).getByRole("checkbox", {
      name: "Enable audio replay and instant answers",
    }) as HTMLInputElement;
    expect(checkbox.checked).toBe(false);
    if (aids) fireEvent.click(checkbox);
    await act(async () => {
      fireEvent.click(
        within(setup).getByRole("button", { name: "Start practice" }),
      );
    });
    expect(sent).toHaveLength(1);
    expect(sent[0]).toMatchObject({
      practiceGroupId: selected.groupId,
      expectedGroupContentId: selected.groupContentId,
      mode: "practice",
      scope: "reading",
      routeMode: "fixed",
      route: "lower",
      allowPracticeAids: aids,
    });
    for (const field of ["questionIds", "taskType", "types", "questionTypes"])
      expect(sent[0]).not.toHaveProperty(field);
    expect(selected.questionIds).toEqual(["first", "second"]);
    expect(screen.queryByRole("dialog")).toBeNull();
  },
);
