import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import App from "../../src/App";
import { setLocale } from "../../src/i18n";

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
function storage(): Storage {
  const values = new Map<string, string>();
  return {
    length: 0,
    clear: () => values.clear(),
    getItem: (k) => values.get(k) || null,
    setItem: (k, v) => {
      values.set(k, v);
    },
    removeItem: (k) => {
      values.delete(k);
    },
    key: () => null,
  };
}
beforeEach(() => {
  vi.stubGlobal("localStorage", storage());
  vi.stubGlobal("sessionStorage", storage());
  setLocale("en");
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
  setLocale("en");
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

it("takes an empty public checkout through bilingual demo import and starts a text-only full pack without microphone access", async () => {
  let imported = false;
  const getUserMedia = vi.fn();
  vi.stubGlobal("navigator", { mediaDevices: { getUserMedia } });
  const exam = {
    id: "user-welcome-demo",
    title: "Original demo",
    family: "user",
    supplemental: true,
    timingPolicy: "untimed",
    strictEligible: false,
    structuredReady: true,
    questionCount: 2,
    sections: [
      { id: "reading", questionCount: 1 },
      { id: "writing", questionCount: 1 },
    ],
  };
  const create = vi.fn();
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input, options = {}) => {
      const url = String(input);
      let body: unknown;
      if (url === "/api/catalog")
        body = { exams: imported ? [exam] : [], materials: [], stats: {} };
      else if (url === "/api/resource-packs/demo") {
        imported = true;
        body = { id: exam.id };
      } else if (url === `/api/exams/${exam.id}`) body = exam;
      else if (url === "/api/sessions" && options.method === "POST") {
        create(JSON.parse(options.body));
        body = {
          id: "demo-session",
          examId: exam.id,
          title: "Original demo",
          status: "active",
          mode: "practice",
          scope: "all",
          phase: "directions",
          stageIndex: 0,
          questionIndex: 0,
          revision: 1,
          serverNow: 1000,
          deadline: null,
          remainingSeconds: null,
          allowedActions: ["begin"],
          stage: {
            id: "reading-practice",
            title: "Reading",
            section: "reading",
            timer: "untimed",
            questionCount: 1,
            seconds: 0,
            canBack: true,
          },
          progress: {
            stageIndex: 0,
            totalStages: 2,
            totalQuestions: 2,
            questionIndex: 0,
          },
          integrity: { interrupted: false },
          question: null,
        };
      } else if (url === "/api/sessions") body = { sessions: [] };
      else throw new Error(`Unexpected onboarding request: ${url}`);
      return new Response(JSON.stringify(body), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }),
  );
  await act(async () => {
    render(<App />);
  });
  expect(
    screen.getByRole("heading", {
      name: "Welcome. Make this your practice space.",
    }),
  ).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "中文" }));
  expect(document.documentElement.lang).toBe("zh-CN");
  expect(localStorage.getItem("toefl-lab-language")).toBe("zh-CN");
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: "体验演示题" }));
  });
  expect(screen.getByRole("heading", { name: "Original demo" })).toBeTruthy();
  expect(
    (screen.getByRole("button", { name: "练习 听力" }) as HTMLButtonElement)
      .disabled,
  ).toBe(true);
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: "整套" }));
  });
  expect(screen.queryByRole("button", { name: "检测麦克风" })).toBeNull();
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: "进入练习" }));
  });
  expect(create).toHaveBeenCalledWith(
    expect.objectContaining({
      examId: exam.id,
      scope: "all",
      mode: "practice",
    }),
  );
  expect(getUserMedia).not.toHaveBeenCalled();
  expect(screen.getByRole("button", { name: "开始阅读" })).toBeTruthy();
});
