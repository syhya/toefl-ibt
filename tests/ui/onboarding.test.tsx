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

type OnboardingExam = {
  id: string;
  title: string;
  family: string;
  supplemental?: boolean;
  timingPolicy?: string;
  strictEligible: boolean;
  scopedEligibility?: Record<string, boolean>;
  structuredReady: boolean;
  questionCount: number;
  sections: { id: string; questionCount: number }[];
};

function serveOnboarding(exam: OnboardingExam, initiallyImported = false) {
  let imported = initiallyImported;
  const getUserMedia = vi.fn();
  vi.stubGlobal("navigator", { mediaDevices: { getUserMedia } });
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
        body = {
          id: exam.id,
          examIds: [exam.id],
          questions: exam.questionCount,
          screens: 79,
        };
      } else if (url === `/api/exams/${exam.id}`) body = exam;
      else if (url === "/api/sessions" && options.method === "POST") {
        const request = JSON.parse(options.body);
        create(request);
        body = {
          id: "onboarding-session",
          examId: exam.id,
          title: exam.title,
          status: "active",
          mode: request.mode,
          scope: request.scope,
          phase: "directions",
          stageIndex: 0,
          questionIndex: 0,
          revision: 1,
          serverNow: 1000,
          deadline: null,
          remainingSeconds: null,
          allowedActions: ["begin"],
          stage: {
            id: "reading-first-module",
            title: "Reading",
            section: "reading",
            timer: request.mode === "strict" ? "module" : "untimed",
            questionCount: exam.sections[0].questionCount,
            seconds: request.mode === "strict" ? 690 : 0,
            canBack: true,
          },
          progress: {
            stageIndex: 0,
            totalStages: exam.sections.length,
            totalQuestions: exam.questionCount,
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
  return { create, getUserMedia };
}

it("imports Practice Test 1 with strict R/L/W scopes, guided speaking, and speaking equipment checks", async () => {
  const exam = {
    id: "student-1",
    title: "TOEFL iBT Practice Test 1",
    family: "student",
    strictEligible: false,
    scopedEligibility: {
      reading: true,
      listening: true,
      writing: true,
      speaking: false,
    },
    structuredReady: true,
    questionCount: 97,
    sections: [
      { id: "reading", questionCount: 22 },
      { id: "listening", questionCount: 34 },
      { id: "writing", questionCount: 12 },
      { id: "speaking", questionCount: 11 },
    ],
  };
  const { create, getUserMedia } = serveOnboarding(exam);
  await act(async () => {
    render(<App />);
  });
  expect(
    screen.getByRole("heading", {
      name: "Welcome. Make this your practice space.",
    }),
  ).toBeTruthy();
  expect(
    screen.getByRole("button", { name: "Try Practice Test 1" }),
  ).toBeTruthy();
  expect(screen.getByText(/97 items across 79 screens/)).toBeTruthy();
  expect(
    screen.getByText(
      /Speaking uses guided practice because Interview question 1/,
    ),
  ).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "中文" }));
  expect(document.documentElement.lang).toBe("zh-CN");
  expect(localStorage.getItem("toefl-lab-language")).toBe("zh-CN");
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: "体验官方样题第1套" }));
  });
  expect(
    screen.getByRole("heading", { name: "TOEFL iBT Practice Test 1" }),
  ).toBeTruthy();
  expect(screen.getByText("单项计时")).toBeTruthy();
  expect(screen.queryByText("辅助练习")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "EN" }));
  expect(screen.getByText("Per-section timing")).toBeTruthy();
  expect(screen.queryByText("Guided only")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "中文" }));
  for (const section of ["阅读", "听力", "写作", "口语"])
    expect(
      (
        screen.getByRole("button", {
          name: `练习 ${section}`,
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(false);
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: "整套" }));
  });
  expect(screen.getByRole("button", { name: "检测麦克风" })).toBeTruthy();
  const strictMode = screen.getByRole("radio", {
    name: /严格模考/,
  }) as HTMLInputElement;
  expect(strictMode.disabled).toBe(true);
  expect(strictMode.checked).toBe(false);
  expect(getUserMedia).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "取消" }));
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: "练习 口语" }));
  });
  expect(screen.getByRole("button", { name: "检测麦克风" })).toBeTruthy();
  expect(
    (screen.getByRole("radio", { name: /严格模考/ }) as HTMLInputElement)
      .disabled,
  ).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "取消" }));
  for (const section of ["听力", "写作"]) {
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: `练习 ${section}` }));
    });
    expect(
      (screen.getByRole("radio", { name: /严格模考/ }) as HTMLInputElement)
        .disabled,
    ).toBe(false);
    expect(screen.queryByRole("button", { name: "检测麦克风" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "取消" }));
  }
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: "练习 阅读" }));
  });
  expect(screen.queryByRole("button", { name: "检测麦克风" })).toBeNull();
  const readingStrictMode = screen.getByRole("radio", {
    name: /严格模考/,
  }) as HTMLInputElement;
  expect(readingStrictMode.disabled).toBe(false);
  fireEvent.click(readingStrictMode);
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: "进入练习" }));
  });
  expect(create).toHaveBeenCalledWith(
    expect.objectContaining({
      examId: "student-1",
      scope: "reading",
      mode: "strict",
    }),
  );
  expect(getUserMedia).not.toHaveBeenCalled();
  expect(screen.getByRole("button", { name: "开始阅读" })).toBeTruthy();
});

it("keeps custom text-only packs untimed and starts their full flow without microphone access", async () => {
  const exam = {
    id: "user-personal-pack",
    title: "Personal text practice",
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
  const { create, getUserMedia } = serveOnboarding(exam, true);
  await act(async () => {
    render(<App />);
  });
  expect(screen.getByText("Guided only")).toBeTruthy();
  expect(screen.queryByText("Per-section timing")).toBeNull();
  expect(
    (
      screen.getByRole("button", {
        name: "Practice Listening",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: "Full test" }));
  });
  expect(screen.queryByRole("button", { name: "Check microphone" })).toBeNull();
  expect(
    (screen.getByRole("radio", { name: /Strict practice/ }) as HTMLInputElement)
      .disabled,
  ).toBe(true);
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: "Start practice" }));
  });
  expect(create).toHaveBeenCalledWith(
    expect.objectContaining({
      examId: exam.id,
      scope: "all",
      mode: "practice",
    }),
  );
  expect(getUserMedia).not.toHaveBeenCalled();
  expect(screen.getByRole("button", { name: "Begin Reading" })).toBeTruthy();
});
