import { setLocale } from "../../src/i18n";
import React from "react";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Mistakes, { type Mistake } from "../../src/Mistakes";

const LOCK_REASON =
  "Review, feedback and reference resources are locked while strict practice is active.";

function sourceRow(id: string, changes: Partial<Mistake> = {}): Mistake {
  return {
    mistakeId: `mistake-${id}`,
    questionId: `original-question-${id}`,
    examId: "original-exam",
    examTitle: `Original fixture exam ${id}`,
    section: "reading",
    taskType: "choice",
    number: 24,
    title: "Multiple Choice · 24",
    sourcePage: 17,
    wrongAttempts: 2,
    attempts: 3,
    lastAttemptAt: Date.UTC(2026, 8, 5, 8, 0, 0),
    lastSessionId: `latest-session-${id}`,
    lastWrongSessionId: `wrong-session-${id}`,
    lastGrade: { correct: 0, total: 1 },
    status: "needs_review",
    available: true,
    unavailableReason: null,
    ...changes,
  };
}

function installApi(items: Mistake[]) {
  let locked = false;
  const requests: URLSearchParams[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input), "http://localhost");
      if (url.pathname !== "/api/mistakes")
        throw new Error(`Unexpected endpoint: ${url.pathname}`);
      const params = url.searchParams;
      requests.push(params);
      if (locked)
        return new Response(JSON.stringify({ error: LOCK_REASON }), {
          status: 403,
        });
      const section = params.get("section") || "all";
      const status = params.get("status") || "needs_review";
      const query = (params.get("q") || "").toLowerCase();
      const matching = items.filter(
        (item) =>
          (section === "all" || item.section === section) &&
          (!query ||
            `${item.examTitle} ${item.title} ${item.questionId}`
              .toLowerCase()
              .includes(query)),
      );
      const filtered = matching.filter(
        (item) => status === "all" || item.status === status,
      );
      const page = Number(params.get("page") || 1),
        pageSize = Number(params.get("pageSize") || 24);
      return new Response(
        JSON.stringify({
          schemaVersion: 1,
          items: filtered.slice((page - 1) * pageSize, page * pageSize),
          total: filtered.length,
          page,
          pageSize,
          section,
          status,
          q: params.get("q") || "",
          summary: {
            total: matching.length,
            needsReview: matching.filter(
              (item) => item.status === "needs_review",
            ).length,
            mastered: matching.filter((item) => item.status === "mastered")
              .length,
            attempts: matching.reduce((sum, item) => sum + item.attempts, 0),
          },
          notice: "Objective practice history, not an ETS score.",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    }),
  );
  return {
    requests,
    latest: () => Object.fromEntries(requests.at(-1)!.entries()),
    lock: () => {
      locked = true;
    },
  };
}

async function settleListing() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(160);
  });
}

beforeEach(() => {
  setLocale("zh-CN");
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-09-05T08:00:00Z"));
});
afterEach(() => {
  setLocale("en");
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("local mistake collection", () => {
  it("pages the pending collection and resets to page one when switching sections or status", async () => {
    const reading = Array.from({ length: 26 }, (_, index) =>
      sourceRow(`reading-${index + 1}`),
    );
    const pendingListening = sourceRow("listening-pending", {
      section: "listening",
      taskType: "listen_response",
    });
    const masteredListening = sourceRow("listening-mastered", {
      section: "listening",
      status: "mastered",
      lastGrade: { correct: 1, total: 1 },
    });
    const server = installApi([
      ...reading,
      pendingListening,
      masteredListening,
    ]);
    render(<Mistakes practice={vi.fn()} review={vi.fn()} />);
    await settleListing();
    expect(server.latest()).toEqual({
      section: "all",
      status: "needs_review",
      q: "",
      page: "1",
      pageSize: "24",
    });
    expect(screen.getAllByRole("article")).toHaveLength(24);
    expect(
      (screen.getByRole("button", { name: "上一页" }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "下一页" }));
    await settleListing();
    expect(server.latest().page).toBe("2");
    expect(screen.getAllByRole("article")).toHaveLength(3);
    expect(
      screen.getByRole("heading", { name: /Original fixture exam reading-25/ }),
    ).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "听力", exact: true }));
    await settleListing();
    expect(server.latest()).toMatchObject({
      section: "listening",
      page: "1",
      status: "needs_review",
    });
    expect(screen.getAllByRole("article")).toHaveLength(1);
    expect(
      screen.getByRole("heading", {
        name: /Original fixture exam listening-pending/,
      }),
    ).toBeTruthy();
    fireEvent.click(
      screen.getByRole("button", { name: "已掌握", exact: true }),
    );
    await settleListing();
    expect(server.latest()).toMatchObject({
      section: "listening",
      status: "mastered",
      page: "1",
    });
    expect(
      screen.getByRole("heading", {
        name: /Original fixture exam listening-mastered/,
      }),
    ).toBeTruthy();
    expect(
      screen.queryByRole("heading", {
        name: /Original fixture exam listening-pending/,
      }),
    ).toBeNull();
    fireEvent.click(
      screen.getByRole("button", { name: "全部记录", exact: true }),
    );
    await settleListing();
    expect(screen.getAllByRole("article")).toHaveLength(2);
  });

  it("starts keyword searches at page one and preserves the requested source filter", async () => {
    const items = Array.from({ length: 25 }, (_, index) =>
      sourceRow(`source-${index + 1}`, {
        section: "writing",
        taskType: "build_sentence",
      }),
    );
    const server = installApi(items);
    render(<Mistakes practice={vi.fn()} review={vi.fn()} />);
    await settleListing();
    fireEvent.click(screen.getByRole("button", { name: "写作", exact: true }));
    await settleListing();
    fireEvent.click(screen.getByRole("button", { name: "下一页" }));
    await settleListing();
    expect(server.latest().page).toBe("2");
    fireEvent.change(screen.getByRole("textbox", { name: "搜索错题" }), {
      target: { value: "original-question-source-25" },
    });
    await settleListing();
    expect(server.latest()).toMatchObject({
      section: "writing",
      q: "original-question-source-25",
      page: "1",
    });
    expect(screen.getAllByRole("article")).toHaveLength(1);
    expect(
      screen.getByRole("heading", { name: /Original fixture exam source-25/ }),
    ).toBeTruthy();
  });

  it("passes the original exam and question identity to practice without constructing a replacement question", async () => {
    const original = sourceRow("source-cloze", {
      examId: "verified-source-exam",
      questionId: "original-cloze-screen-11-20",
      taskType: "cloze",
      number: 11,
      lastGrade: { correct: 7, total: 10 },
    });
    installApi([original]);
    const practice = vi.fn();
    render(<Mistakes practice={practice} review={vi.fn()} />);
    await settleListing();
    fireEvent.click(screen.getByRole("button", { name: "重新练习原题" }));
    expect(practice).toHaveBeenCalledExactlyOnceWith(original);
    expect(
      screen.getByText(/错误 2 次 \/ 作答 3 次 · 最近 7\/10/),
    ).toBeTruthy();
  });

  it("opens the last wrong attempt even after the latest answer has mastered the question", async () => {
    const original = sourceRow("mastered", {
      status: "mastered",
      lastSessionId: "correct-latest-session",
      lastWrongSessionId: "historical-wrong-session",
      lastGrade: { correct: 1, total: 1 },
    });
    installApi([original]);
    const review = vi.fn();
    render(<Mistakes practice={vi.fn()} review={review} />);
    await settleListing();
    fireEvent.click(
      screen.getByRole("button", { name: "已掌握", exact: true }),
    );
    await settleListing();
    fireEvent.click(screen.getByRole("button", { name: "查看错题复盘" }));
    expect(review).toHaveBeenCalledExactlyOnceWith("historical-wrong-session");
  });

  it("retains a review fallback for older records without lastWrongSessionId", async () => {
    installApi([
      sourceRow("legacy", {
        lastWrongSessionId: undefined,
        lastSessionId: "legacy-source-session",
      }),
    ]);
    const review = vi.fn();
    render(<Mistakes practice={vi.fn()} review={review} />);
    await settleListing();
    fireEvent.click(screen.getByRole("button", { name: "查看错题复盘" }));
    expect(review).toHaveBeenCalledExactlyOnceWith("legacy-source-session");
  });

  it("disables replaying changed sources while preserving the original mistake review", async () => {
    installApi([
      sourceRow("changed", {
        available: false,
        unavailableReason: "source_changed",
        lastWrongSessionId: "frozen-original-attempt",
      }),
    ]);
    const practice = vi.fn(),
      review = vi.fn();
    render(<Mistakes practice={practice} review={review} />);
    await settleListing();
    expect(screen.getByText(/原题版本已变更或来源待核验/)).toBeTruthy();
    const retry = screen.getByRole("button", {
      name: "重新练习原题",
    }) as HTMLButtonElement;
    expect(retry.disabled).toBe(true);
    fireEvent.click(retry);
    expect(practice).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "查看错题复盘" }));
    expect(review).toHaveBeenCalledExactlyOnceWith("frozen-original-attempt");
  });

  it("shows an empty collection without inserting example questions or invented practice actions", async () => {
    installApi([]);
    const practice = vi.fn(),
      review = vi.fn();
    render(<Mistakes practice={practice} review={review} />);
    await settleListing();
    expect(screen.getByText(/当前没有符合条件的错题/)).toBeTruthy();
    expect(screen.queryByRole("article")).toBeNull();
    expect(screen.queryByRole("button", { name: "重新练习原题" })).toBeNull();
    expect(screen.queryByRole("button", { name: "查看错题复盘" })).toBeNull();
    expect(practice).not.toHaveBeenCalled();
    expect(review).not.toHaveBeenCalled();
  });

  it("removes previously loaded mistakes, counts and pagination after a strict-session 403", async () => {
    const server = installApi([sourceRow("previously-visible")]);
    const { container } = render(
      <Mistakes practice={vi.fn()} review={vi.fn()} />,
    );
    await settleListing();
    expect(
      screen.getByRole("heading", {
        name: /Original fixture exam previously-visible/,
      }),
    ).toBeTruthy();
    server.lock();
    fireEvent.click(
      screen.getByRole("button", { name: "全部记录", exact: true }),
    );
    await settleListing();
    expect(
      screen.getByText("严格模考进行中，复盘、即时核对与参考资料暂时锁定。"),
    ).toBeTruthy();
    expect(screen.queryByRole("article")).toBeNull();
    expect(
      screen.queryByRole("heading", {
        name: /Original fixture exam previously-visible/,
      }),
    ).toBeNull();
    expect(screen.queryByRole("button", { name: "重新练习原题" })).toBeNull();
    expect(screen.queryByRole("button", { name: "查看错题复盘" })).toBeNull();
    expect(screen.queryByRole("button", { name: "下一页" })).toBeNull();
    expect(
      Array.from(container.querySelectorAll(".mistake-summary strong")).map(
        (node) => node.textContent,
      ),
    ).toEqual(["—", "—", "—"]);
  });
});
