import { expect, it } from "vitest";
import { localizeServerMessage } from "../../src/locales/server";

it("renders actionable server errors in both languages without changing resource paths", () => {
  for (const message of [
    "You must answer this question before selecting Next.",
    "Review, feedback and reference resources are locked while strict practice is active.",
    "Some recording chunks have not arrived yet. Retry pending uploads before playback.",
    "Cloze placeholders must match each blank exactly once.",
    "The frontend is not built. Run npm run build, or use the Vite development server.",
  ]) {
    expect(localizeServerMessage(message, "en")).toBe(message);
    const chinese = localizeServerMessage(message, "zh-CN");
    expect(chinese).toMatch(/[\u3400-\u9fff]/);
    expect(localizeServerMessage(chinese!, "en")).toBe(message);
  }
  expect(
    localizeServerMessage(
      "The demo pack is missing. Restore examples/demo/pack.json.",
      "zh-CN",
    ),
  ).toContain("examples/demo/pack.json");
  expect(
    localizeServerMessage("Unknown timing setting: readingCommon", "zh-CN"),
  ).toBe("未知的计时设置：readingCommon");
});

it("translates generated cloze scaffolding while preserving prefix, answer, suffix, and length", () => {
  expect(
    localizeServerMessage(
      "第 2 空：已给「sa」 + 补入「ve」 → save（缺失片段 2 个字符）。",
      "en",
    ),
  ).toBe("Blank 2: given “sa” + enter “ve” → save (2 missing characters).");
  expect(
    localizeServerMessage(
      "第 3 空：无前缀 + 补入「conserv」 + 已给后缀「ation」 → conservation（缺失片段 7 个字符）。",
      "en",
    ),
  ).toBe(
    "Blank 3: no prefix + enter “conserv” + given suffix “ation” → conservation (7 missing characters).",
  );
  expect(
    localizeServerMessage(
      "第 4 空的来源答案仍有冲突，不给出正确结论，也不计入自动评分。",
      "en",
    ),
  ).toContain("Blank 4 has conflicting source answers");
});

it("preserves stable duplicate token indices and quoted evidence in translated review guidance", () => {
  expect(
    localizeServerMessage(
      "一种与参考句一致的空格词序：do〔词块 2〕 → you〔词块 1〕 → do〔词块 3〕",
      "en",
    ),
  ).toBe(
    "One gap order matching the reference: do[token 2] → you[token 1] → do[token 3]",
  );
  expect(
    localizeServerMessage(
      "原题上下文片段（未改写）：This source quotation includes 中文 and must remain exact.",
      "en",
    ),
  ).toBe(
    "Original question context (verbatim): This source quotation includes 中文 and must remain exact.",
  );
  expect(
    localizeServerMessage(
      "资料参考键为 B。原资料未提供可用解析，且本地关键词方法没有定位到可靠依据；请结合完整原文或原音自行核对，不据此补写理由。",
      "en",
    ),
  ).toContain("The source reference key is B.");
  expect(
    localizeServerMessage("资料附带解析（非 ETS 官方） · 存在校核差异", "en"),
  ).toBe(
    "Source explanation (not official ETS) · Verification differences recorded",
  );
});

it("leaves unknown source text untouched and localizes validation metadata", () => {
  expect(
    localizeServerMessage("作者原文：这是一段资料附带解析。", "en"),
  ).toBeUndefined();
  expect(
    localizeServerMessage("Original source passage: The answer is B.", "zh-CN"),
  ).toBeUndefined();
  expect(localizeServerMessage("answerKeyVerification", "zh-CN")).toBe(
    "答案键核验",
  );
  expect(localizeServerMessage("answerKeyVerification", "en")).toBe(
    "Answer-key verification",
  );
  expect(localizeServerMessage("source-verified", "zh-CN")).toBe("来源已核实");
});

it("localizes generated collection and module titles without rewriting original resource names", () => {
  expect(localizeServerMessage("体验日官方练习 2", "en")).toBe(
    "Official Experience Day 2",
  );
  expect(localizeServerMessage("官方学生版样题 1", "en")).toBe(
    "Official Student Sample 1",
  );
  expect(localizeServerMessage("补充套题 1 · lower / upper 双分支", "en")).toBe(
    "Supplemental Set 1 · Lower / Upper branches",
  );
  expect(
    localizeServerMessage("Reading · Module 2 · Lower · 21", "zh-CN"),
  ).toBe("阅读 · 模块 2 · 较低分支 · 21");
  expect(localizeServerMessage("Write an Email · 11", "zh-CN")).toBe(
    "邮件写作 · 11",
  );
  expect(
    localizeServerMessage("我的资料/官方学生版样题 1.pdf", "en"),
  ).toBeUndefined();
  expect(
    localizeServerMessage("Conservation and Wildlife", "zh-CN"),
  ).toBeUndefined();
});
