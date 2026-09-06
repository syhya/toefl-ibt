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
import VocabularyPage, {
  VocabularyEntryDialog,
  type VocabularyEntry,
} from "../../src/Vocabulary";
import { setLocale } from "../../src/i18n";

function entry(
  word: string,
  changes: Partial<VocabularyEntry> = {},
): VocabularyEntry {
  return {
    id: `word-${word}`,
    word,
    meaning: `Meaning of ${word}`,
    context: `This sentence uses ${word}.`,
    sourceLabel: "Reading · Question 3",
    sourceQuestionId: "original-question-3",
    sourceSessionId: "completed-session",
    status: "learning",
    createdAt: Date.UTC(2026, 8, 6, 8),
    updatedAt: Date.UTC(2026, 8, 6, 8),
    ...changes,
  };
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function listing(items: VocabularyEntry[], params = new URLSearchParams()) {
  const query = (params.get("q") || "").toLowerCase();
  const status = params.get("status") || "all";
  const matching = items.filter((item) =>
    `${item.word} ${item.meaning} ${item.context} ${item.sourceLabel}`
      .toLowerCase()
      .includes(query),
  );
  const filtered = matching.filter(
    (item) => status === "all" || item.status === status,
  );
  const page = Number(params.get("page") || 1);
  const pageSize = Number(params.get("pageSize") || 24);
  return {
    items: filtered.slice((page - 1) * pageSize, page * pageSize),
    total: filtered.length,
    page,
    pageSize,
    summary: {
      learning: matching.filter((item) => item.status === "learning").length,
      mastered: matching.filter((item) => item.status === "mastered").length,
    },
  };
}

function installApi(initial: VocabularyEntry[]) {
  const items = structuredClone(initial);
  const requests: {
    method: string;
    url: URL;
    body?: Record<string, unknown>;
  }[] = [];
  const failures = new Map<string, string>();
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, options?: RequestInit) => {
      const url = new URL(String(input), "http://localhost");
      const method = options?.method || "GET";
      const body = options?.body ? JSON.parse(String(options.body)) : undefined;
      requests.push({ method, url, body });
      if (failures.has(method)) {
        const error = failures.get(method);
        failures.delete(method);
        return json({ error }, 503);
      }
      if (url.pathname === "/api/vocabulary" && method === "GET")
        return json(listing(items, url.searchParams));
      if (url.pathname === "/api/vocabulary" && method === "POST") {
        const existing = items.find(
          (item) => item.word.toLowerCase() === body.word.trim().toLowerCase(),
        );
        if (existing) return json({ entry: existing, created: false });
        const created = entry(body.word, {
          ...body,
          id: `created-${items.length}`,
        });
        items.unshift(created);
        return json({ entry: created, created: true });
      }
      const id = decodeURIComponent(
        url.pathname.replace("/api/vocabulary/", ""),
      );
      const index = items.findIndex((item) => item.id === id);
      if (index >= 0 && method === "PATCH") {
        items[index] = { ...items[index], ...body };
        return json({ entry: items[index] });
      }
      if (index >= 0 && method === "DELETE") {
        items.splice(index, 1);
        return json({ ok: true });
      }
      throw new Error(`Unexpected request: ${method} ${url.pathname}`);
    }),
  );
  return {
    items,
    requests,
    failNext: (method: string, message: string) =>
      failures.set(method, message),
    latestQuery: () =>
      Object.fromEntries(
        requests.filter((request) => request.method === "GET").at(-1)!.url
          .searchParams,
      ),
  };
}

async function settleListing() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(160);
  });
}

async function clickAndSettle(button: HTMLElement) {
  await act(async () => {
    fireEvent.click(button);
  });
}

beforeEach(() => {
  const values = new Map<string, string>();
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
  });
  setLocale("en");
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-09-06T08:00:00Z"));
  Object.defineProperty(HTMLDialogElement.prototype, "showModal", {
    configurable: true,
    value: function (this: HTMLDialogElement) {
      this.setAttribute("open", "");
    },
  });
  Object.defineProperty(HTMLDialogElement.prototype, "close", {
    configurable: true,
    value: function (this: HTMLDialogElement) {
      this.removeAttribute("open");
    },
  });
});

afterEach(() => {
  cleanup();
  setLocale("en");
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("local vocabulary", () => {
  it("pages records, searches context and resets the page when filters change", async () => {
    const items = Array.from({ length: 26 }, (_, index) =>
      entry(`word ${index + 1}`),
    );
    items.push(
      entry("reticent", {
        status: "mastered",
        context: "A quiet personality.",
      }),
    );
    const server = installApi(items);
    render(<VocabularyPage />);
    await settleListing();
    expect(server.latestQuery()).toEqual({
      q: "",
      status: "all",
      page: "1",
      pageSize: "24",
    });
    expect(screen.getAllByRole("article")).toHaveLength(24);
    fireEvent.click(screen.getByRole("button", { name: "Next page" }));
    await settleListing();
    expect(screen.getAllByRole("article")).toHaveLength(3);
    expect(server.latestQuery().page).toBe("2");
    fireEvent.change(
      screen.getByRole("searchbox", { name: "Search vocabulary" }),
      { target: { value: "quiet personality" } },
    );
    await settleListing();
    expect(server.latestQuery()).toMatchObject({
      page: "1",
      q: "quiet personality",
    });
    expect(screen.getAllByRole("article")).toHaveLength(1);
    expect(screen.getByRole("heading", { name: "reticent" })).toBeTruthy();
    fireEvent.click(
      screen.getByRole("button", { name: "Learning", exact: true }),
    );
    await settleListing();
    expect(screen.queryByRole("article")).toBeNull();
    expect(screen.getByText(/No matching words/)).toBeTruthy();
    fireEvent.click(
      screen.getByRole("button", { name: "Mastered", exact: true }),
    );
    await settleListing();
    expect(server.latestQuery()).toMatchObject({
      status: "mastered",
      page: "1",
    });
    expect(screen.getByRole("heading", { name: "reticent" })).toBeTruthy();
  });

  it("validates a word, retains every input on a failed save and reloads persisted entries", async () => {
    const server = installApi([]);
    const onNotice = vi.fn();
    const view = render(<VocabularyPage onNotice={onNotice} />);
    await settleListing();
    expect(screen.getByText(/Your vocabulary is empty/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Add a word" }));
    await clickAndSettle(
      screen.getByRole("button", { name: "Add to vocabulary" }),
    );
    expect(screen.getByRole("alert").textContent).toBe(
      "Enter a word or phrase.",
    );
    expect(server.requests.some((request) => request.method === "POST")).toBe(
      false,
    );
    const word = screen.getByRole("textbox", {
      name: "Word or phrase (required)",
    });
    fireEvent.change(word, { target: { value: "  resilient  " } });
    fireEvent.change(
      screen.getByRole("textbox", { name: "Meaning (optional)" }),
      { target: { value: "able to recover" } },
    );
    fireEvent.change(
      screen.getByRole("textbox", { name: "Context (optional)" }),
      { target: { value: "The forest was resilient." } },
    );
    fireEvent.change(
      screen.getByRole("textbox", { name: "Source (optional)" }),
      { target: { value: "My reading notes" } },
    );
    server.failNext("POST", "Could not write vocabulary file.");
    await clickAndSettle(
      screen.getByRole("button", { name: "Add to vocabulary" }),
    );
    expect(screen.getByRole("alert").textContent).toBe(
      "Could not write vocabulary file.",
    );
    expect((word as HTMLInputElement).value).toBe("  resilient  ");
    expect(
      (
        screen.getByRole("textbox", {
          name: "Context (optional)",
        }) as HTMLTextAreaElement
      ).value,
    ).toBe("The forest was resilient.");
    await clickAndSettle(
      screen.getByRole("button", { name: "Add to vocabulary" }),
    );
    await settleListing();
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.getByRole("heading", { name: "resilient" })).toBeTruthy();
    expect(screen.getByText("My reading notes")).toBeTruthy();
    expect(server.items[0]).toMatchObject({
      word: "resilient",
      meaning: "able to recover",
      context: "The forest was resilient.",
    });
    expect(onNotice).toHaveBeenCalledWith("Added to your vocabulary.");
    view.unmount();
    render(<VocabularyPage />);
    await settleListing();
    expect(screen.getByRole("heading", { name: "resilient" })).toBeTruthy();
  });

  it("submits review source identity and leaves the original entry intact when a duplicate is returned", async () => {
    const original = entry("resilient", {
      meaning: "Original meaning",
      context: "Original context.",
    });
    const server = installApi([original]);
    const onSaved = vi.fn(),
      onNotice = vi.fn(),
      onClose = vi.fn();
    render(
      <VocabularyEntryDialog
        draft={{
          word: "Resilient",
          meaning: "Different meaning",
          context: "New passage.",
          sourceLabel: "Listening · Question 9",
          sourceQuestionId: "new-source-question",
          sourceSessionId: "new-source-session",
        }}
        onSaved={onSaved}
        onNotice={onNotice}
        onClose={onClose}
      />,
    );
    expect(
      (
        screen.getByRole("textbox", {
          name: "Context (optional)",
        }) as HTMLTextAreaElement
      ).value,
    ).toBe("New passage.");
    await clickAndSettle(
      screen.getByRole("button", { name: "Add to vocabulary" }),
    );
    expect(server.requests[0].body).toMatchObject({
      sourceQuestionId: "new-source-question",
      sourceSessionId: "new-source-session",
      sourceLabel: "Listening · Question 9",
    });
    expect(server.items).toEqual([original]);
    expect(onSaved).toHaveBeenCalledExactlyOnceWith(original, false);
    expect(onNotice).toHaveBeenCalledWith(
      "This word is already in your vocabulary. Your existing entry was kept.",
    );
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("edits an entry and updates both learning filters after status changes", async () => {
    const original = entry("salient");
    const server = installApi([original]);
    render(<VocabularyPage />);
    await settleListing();
    fireEvent.click(screen.getByRole("button", { name: "Edit", exact: true }));
    fireEvent.change(
      screen.getByRole("textbox", { name: "Meaning (optional)" }),
      { target: { value: "most noticeable" } },
    );
    fireEvent.change(
      screen.getByRole("textbox", { name: "Context (optional)" }),
      { target: { value: "The most salient detail." } },
    );
    await clickAndSettle(screen.getByRole("button", { name: "Save changes" }));
    await settleListing();
    expect(server.items[0]).toEqual({
      ...original,
      meaning: "most noticeable",
      context: "The most salient detail.",
    });
    expect(screen.getByText("most noticeable")).toBeTruthy();
    fireEvent.click(
      screen.getByRole("button", { name: "Learning", exact: true }),
    );
    await settleListing();
    server.failNext("PATCH", "Status update failed.");
    await clickAndSettle(screen.getByRole("button", { name: "Mark mastered" }));
    expect(screen.getByRole("alert").textContent).toBe("Status update failed.");
    expect(screen.getByRole("heading", { name: "salient" })).toBeTruthy();
    expect(server.items[0].status).toBe("learning");
    await clickAndSettle(screen.getByRole("button", { name: "Mark mastered" }));
    await settleListing();
    expect(screen.queryByRole("article")).toBeNull();
    fireEvent.click(
      screen.getByRole("button", { name: "Mastered", exact: true }),
    );
    await settleListing();
    expect(screen.getByRole("heading", { name: "salient" })).toBeTruthy();
    await clickAndSettle(screen.getByRole("button", { name: "Keep learning" }));
    await settleListing();
    expect(server.items[0].status).toBe("learning");
    expect(screen.queryByRole("article")).toBeNull();
  });

  it("confirms deletion, retains a failed deletion for retry and corrects an emptied last page", async () => {
    const server = installApi(
      Array.from({ length: 25 }, (_, index) => entry(`word ${index + 1}`)),
    );
    render(<VocabularyPage />);
    await settleListing();
    fireEvent.click(screen.getByRole("button", { name: "Next page" }));
    await settleListing();
    fireEvent.click(
      screen.getByRole("button", { name: "Delete", exact: true }),
    );
    expect(
      screen.getByRole("dialog", { name: "Delete this word?" }),
    ).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(server.requests.some((request) => request.method === "DELETE")).toBe(
      false,
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Delete", exact: true }),
    );
    server.failNext("DELETE", "Deletion failed. Try again.");
    await clickAndSettle(screen.getByRole("button", { name: "Delete word" }));
    expect(
      within(screen.getByRole("dialog")).getByRole("alert").textContent,
    ).toBe("Deletion failed. Try again.");
    expect(server.items).toHaveLength(25);
    await clickAndSettle(screen.getByRole("button", { name: "Delete word" }));
    await settleListing();
    await settleListing();
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(server.items).toHaveLength(24);
    expect(server.latestQuery().page).toBe("1");
    expect(screen.getAllByRole("article")).toHaveLength(24);
    expect(screen.queryByRole("heading", { name: "word 25" })).toBeNull();
  });

  it("retries loading failures while preserving the query and status", async () => {
    const server = installApi([entry("reticent", { status: "mastered" })]);
    render(<VocabularyPage />);
    await settleListing();
    fireEvent.click(
      screen.getByRole("button", { name: "Mastered", exact: true }),
    );
    fireEvent.change(screen.getByRole("searchbox"), {
      target: { value: "reticent" },
    });
    server.failNext("GET", "Vocabulary service unavailable.");
    await settleListing();
    expect(screen.getByRole("alert").textContent).toContain(
      "Vocabulary service unavailable.",
    );
    expect(screen.queryByRole("article")).toBeNull();
    expect((screen.getByRole("searchbox") as HTMLInputElement).value).toBe(
      "reticent",
    );
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    await settleListing();
    expect(server.latestQuery()).toMatchObject({
      q: "reticent",
      status: "mastered",
    });
    expect(screen.getByRole("heading", { name: "reticent" })).toBeTruthy();
  });

  it("ignores a superseded list response even if the server does not honor abort", async () => {
    let resolveOld: (response: Response) => void = () => {};
    let oldSignal: AbortSignal | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, options?: RequestInit) => {
        const url = new URL(String(input), "http://localhost");
        if (!url.searchParams.get("q")) {
          oldSignal = options?.signal || undefined;
          return new Promise<Response>((resolve) => {
            resolveOld = resolve;
          });
        }
        return Promise.resolve(json(listing([entry("newer")])));
      }),
    );
    render(<VocabularyPage />);
    await settleListing();
    fireEvent.change(screen.getByRole("searchbox"), {
      target: { value: "newer" },
    });
    await settleListing();
    expect(oldSignal?.aborted).toBe(true);
    expect(screen.getByRole("heading", { name: "newer" })).toBeTruthy();
    await act(async () => {
      resolveOld(json(listing([entry("stale")])));
    });
    expect(screen.getByRole("heading", { name: "newer" })).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "stale" })).toBeNull();
  });

  it("switches product copy to Chinese without translating saved words or losing dialog input", async () => {
    installApi([entry("resilient", { meaning: "Original meaning" })]);
    render(<VocabularyPage />);
    await settleListing();
    fireEvent.click(screen.getByRole("button", { name: "Add a word" }));
    fireEvent.change(
      screen.getByRole("textbox", { name: "Word or phrase (required)" }),
      { target: { value: "persistent" } },
    );
    act(() => setLocale("zh-CN"));
    expect(screen.getByRole("dialog", { name: "新增生词" })).toBeTruthy();
    expect(
      (
        screen.getByRole("textbox", {
          name: "词语或短语（必填）",
        }) as HTMLInputElement
      ).value,
    ).toBe("persistent");
    fireEvent.click(screen.getByRole("button", { name: "取消" }));
    expect(screen.getByRole("heading", { name: "单词本" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "resilient" })).toBeTruthy();
    expect(screen.getByText("Original meaning")).toBeTruthy();
    expect(screen.getByRole("button", { name: "标为已掌握" })).toBeTruthy();
  });

  it("focuses the word field, restores the opener after Escape and blocks closing during a save", async () => {
    installApi([]);
    render(<VocabularyPage />);
    await settleListing();
    const opener = screen.getByRole("button", { name: "Add a word" });
    opener.focus();
    fireEvent.click(opener);
    expect(document.activeElement).toBe(
      screen.getByRole("textbox", { name: "Word or phrase (required)" }),
    );
    fireEvent(
      screen.getByRole("dialog"),
      new Event("cancel", { bubbles: true, cancelable: true }),
    );
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.activeElement).toBe(opener);
    fireEvent.click(opener);
    fireEvent.change(
      screen.getByRole("textbox", { name: "Word or phrase (required)" }),
      { target: { value: "patient" } },
    );
    let resolveSave: (response: Response) => void = () => {};
    vi.stubGlobal(
      "fetch",
      vi.fn(
        () =>
          new Promise<Response>((resolve) => {
            resolveSave = resolve;
          }),
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: "Add to vocabulary" }));
    expect(
      (screen.getByRole("button", { name: "Cancel" }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
    fireEvent(
      screen.getByRole("dialog"),
      new Event("cancel", { bubbles: true, cancelable: true }),
    );
    expect(screen.getByRole("dialog")).toBeTruthy();
    await act(async () => {
      resolveSave(json({ entry: entry("patient"), created: true }));
    });
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
