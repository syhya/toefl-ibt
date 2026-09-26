import React from "react";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import Documentation, {
  resolveDocumentationLink,
} from "../../src/Documentation";
import GettingStarted from "../../src/GettingStarted";
import { setLocale } from "../../src/i18n";

const originalCode =
  'npm run import:pack -- "/path/with spaces/pack.json"\nconst text = "<script>not executable</script>";\n';
const pages: Record<string, string> = {
  "/api/documentation/en/USER_GUIDE":
    "# User guide\n\n## First steps\n\n[Import resources](IMPORTING.md) · [Project overview](../README.md)\n\n```sh\n" +
    originalCode +
    "```\n\n| Setting | Value |\n| --- | --- |\n| Mode | Practice |\n\n<script>window.untrusted = true</script>\n\n[Source code](../backend/packs.py) · [Official site](https://www.ets.org/toefl)\n",
  "/api/documentation/en/IMPORTING":
    "# Resource imports\n\n[User guide](USER_GUIDE.md)\n",
  "/api/documentation/en/README":
    "# Project overview\n\nEnglish | [简体中文](README.zh-CN.md)\n\n[User guide](docs/USER_GUIDE.md)\n",
  "/api/documentation/zh-CN/README":
    "# 项目介绍\n\n[English](README.md) | 简体中文\n\n[User guide](docs/USER_GUIDE.md)\n",
};

beforeEach(() => {
  setLocale("en");
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const value = pages[String(input)];
      return value
        ? new Response(value)
        : new Response(JSON.stringify({ error: "Documentation not found." }), {
            status: 404,
          });
    }),
  );
});
afterEach(() => {
  cleanup();
  setLocale("en");
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

it("opens rendered documentation inside Help, follows relative links, and returns through reading history", async () => {
  render(<GettingStarted onImported={vi.fn()} />);
  fireEvent.click(screen.getByRole("link", { name: "User guide →" }));
  await screen.findByRole("heading", { name: "User guide" });
  expect(screen.getByRole("table")).toBeTruthy();
  fireEvent.click(screen.getByRole("link", { name: "Import resources" }));
  await screen.findByRole("heading", { name: "Resource imports" });
  fireEvent.click(screen.getByRole("button", { name: "← Back" }));
  await screen.findByRole("heading", { name: "User guide" });
  fireEvent.click(screen.getByRole("button", { name: "← Back" }));
  expect(screen.getByRole("heading", { name: "Help & setup" })).toBeTruthy();
});

it("keeps documentation in English when the interface changes language, preserving code and safe Markdown", async () => {
  const { container } = render(
    <Documentation initialDocument="USER_GUIDE" onBack={vi.fn()} />,
  );
  await screen.findByRole("heading", { name: "User guide" });
  expect(container.querySelector("pre code")?.textContent).toBe(originalCode);
  expect(container.querySelector("script")).toBeNull();
  expect(screen.queryByRole("link", { name: /Source code/ })).toBeNull();
  expect(
    (screen.getByRole("link", { name: "Official site" }) as HTMLAnchorElement)
      .href,
  ).toBe("https://www.ets.org/toefl");
  act(() => setLocale("zh-CN"));
  await screen.findByRole("button", { name: "← 返回" });
  expect(screen.getByRole("heading", { name: "User guide" })).toBeTruthy();
  expect(container.querySelector("article")?.lang).toBe("en");
  expect(container.querySelector("pre code")?.textContent).toBe(originalCode);
  fireEvent.click(screen.getByRole("link", { name: "Import resources" }));
  await screen.findByRole("heading", { name: "Resource imports" });
  expect(document.documentElement.lang).toBe("zh-CN");
  expect(fetch).toHaveBeenCalledWith(
    "/api/documentation/en/IMPORTING",
    expect.anything(),
  );
});

it("keeps the root README bilingual without changing UI language when navigating to English-only guides", async () => {
  const { container } = render(
    <Documentation initialDocument="README" onBack={vi.fn()} />,
  );
  await screen.findByRole("heading", { name: "Project overview" });
  fireEvent.click(screen.getByRole("link", { name: "简体中文" }));
  await screen.findByRole("heading", { name: "项目介绍" });
  expect(container.querySelector("article")?.lang).toBe("zh-CN");
  expect(document.documentElement.lang).toBe("zh-CN");
  fireEvent.click(screen.getByRole("link", { name: "User guide" }));
  await screen.findByRole("heading", { name: "User guide" });
  expect(container.querySelector("article")?.lang).toBe("en");
  expect(document.documentElement.lang).toBe("zh-CN");
  fireEvent.click(screen.getByRole("button", { name: "← 返回" }));
  await screen.findByRole("heading", { name: "项目介绍" });
  fireEvent.click(screen.getByRole("link", { name: "English" }));
  await screen.findByRole("heading", { name: "Project overview" });
  expect(document.documentElement.lang).toBe("en");
});

it("does not serve arbitrary Markdown paths and offers a readable retry for missing documents", async () => {
  expect(
    resolveDocumentationLink("../storage/answers.md", "USER_GUIDE"),
  ).toBeUndefined();
  expect(
    resolveDocumentationLink("file:///etc/passwd", "USER_GUIDE"),
  ).toBeUndefined();
  expect(
    resolveDocumentationLink("javascript:alert(1)", "USER_GUIDE"),
  ).toBeUndefined();
  expect(
    resolveDocumentationLink("https://example.com/README.md", "USER_GUIDE"),
  ).toBeUndefined();
  expect(
    resolveDocumentationLink("../README.zh-CN.md#安装", "USER_GUIDE"),
  ).toEqual({ id: "README", locale: "zh-CN", hash: "%E5%AE%89%E8%A3%85" });
  expect(
    resolveDocumentationLink(
      "../examples/ets-practice-test-1/README.md",
      "IMPORTING",
    ),
  ).toEqual({ id: "BUNDLED_ETS_PRACTICE_TEST_1", locale: "en", hash: "" });
  expect(
    resolveDocumentationLink("NOTICE.zh-CN.md", "BUNDLED_ETS_PRACTICE_TEST_1"),
  ).toEqual({
    id: "BUNDLED_ETS_PRACTICE_TEST_1_NOTICE",
    locale: "en",
    hash: "",
  });
  expect(
    resolveDocumentationLink(
      "../../docs/IMPORTING.md",
      "BUNDLED_ETS_PRACTICE_TEST_1",
    ),
  ).toEqual({ id: "IMPORTING", locale: "en", hash: "" });
  expect(
    resolveDocumentationLink("/api/documentation/zh-CN/USER_GUIDE", "README"),
  ).toEqual({ id: "USER_GUIDE", locale: "en", hash: "" });
  render(<Documentation initialDocument="TESTING" onBack={vi.fn()} />);
  await screen.findByRole("alert");
  expect(screen.getByRole("button", { name: "Try again" })).toBeTruthy();
  act(() => setLocale("zh-CN"));
  await waitFor(() =>
    expect(screen.getByRole("alert").textContent).toContain("未找到文档"),
  );
});
