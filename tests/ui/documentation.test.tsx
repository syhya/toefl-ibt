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
    "# User guide\n\nEnglish | [简体中文](USER_GUIDE.zh-CN.md)\n\n## First steps\n\n[Import resources](IMPORTING.md) · [Project overview](../README.md)\n\n```sh\n" +
    originalCode +
    "```\n\n| Setting | Value |\n| --- | --- |\n| Mode | Practice |\n\n<script>window.untrusted = true</script>\n\n[Source code](../backend/packs.py) · [Official site](https://www.ets.org/toefl)\n",
  "/api/documentation/zh-CN/USER_GUIDE":
    "# 使用指南\n\n[English](USER_GUIDE.md) | 简体中文\n\n## 开始使用\n\n[资源导入](IMPORTING.zh-CN.md)\n\n```sh\n" +
    originalCode +
    "```\n",
  "/api/documentation/en/IMPORTING":
    "# Resource imports\n\n[User guide](USER_GUIDE.md)\n",
  "/api/documentation/zh-CN/IMPORTING":
    "# 资源导入\n\n[使用指南](USER_GUIDE.zh-CN.md)\n",
  "/api/documentation/en/README":
    "# Project overview\n\n[User guide](docs/USER_GUIDE.md)\n",
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

it("switches the currently open document while preserving code fences and original command text", async () => {
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
  await screen.findByRole("heading", { name: "使用指南" });
  expect(container.querySelector("pre code")?.textContent).toBe(originalCode);
  fireEvent.click(screen.getByRole("link", { name: "资源导入" }));
  await screen.findByRole("heading", { name: "资源导入" });
  expect(fetch).toHaveBeenCalledWith(
    "/api/documentation/zh-CN/IMPORTING",
    expect.anything(),
  );
});

it("lets Markdown language links switch the interface and resolves root documentation correctly", async () => {
  render(<Documentation initialDocument="USER_GUIDE" onBack={vi.fn()} />);
  await screen.findByRole("heading", { name: "User guide" });
  fireEvent.click(screen.getByRole("link", { name: "简体中文" }));
  await screen.findByRole("heading", { name: "使用指南" });
  expect(document.documentElement.lang).toBe("zh-CN");
  fireEvent.click(screen.getByRole("link", { name: "English" }));
  await screen.findByRole("heading", { name: "User guide" });
  fireEvent.click(screen.getByRole("link", { name: "Project overview" }));
  await screen.findByRole("heading", { name: "Project overview" });
  fireEvent.click(screen.getByRole("link", { name: "User guide" }));
  await screen.findByRole("heading", { name: "User guide" });
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
  render(<Documentation initialDocument="TESTING" onBack={vi.fn()} />);
  await screen.findByRole("alert");
  expect(screen.getByRole("button", { name: "Try again" })).toBeTruthy();
  act(() => setLocale("zh-CN"));
  await waitFor(() =>
    expect(screen.getByRole("alert").textContent).toContain("未找到文档"),
  );
});
