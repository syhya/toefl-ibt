import { describe, expect, it } from "vitest";
import { readingPresentation } from "../../src/reading-presentation";
import type { Question } from "../../src/types";

describe("source reading heading projection", () => {
  it("retains the entire notice text merged behind a short printed instruction", () => {
    const q: Question = {
      id: "teacher-notice",
      type: "choice",
      stemBlocks: [
        {
          type: "instruction",
          text: "Read a notice. The complete original notice remains available.",
        },
        { type: "question", text: "Original question" },
      ],
    };
    const before = JSON.stringify(q);
    const result = readingPresentation(q);
    expect(result.heading).toBe("Read a notice.");
    expect(result.question.stemBlocks).toEqual([
      {
        type: "paragraph",
        text: "The complete original notice remains available.",
      },
      { type: "question", text: "Original question" },
    ]);
    expect(JSON.stringify(q)).toBe(before);
  });
  it("preserves a merged advertisement title before the original paragraphs", () => {
    const q: Question = {
      id: "advertisement",
      type: "choice",
      stemBlocks: [
        {
          type: "instruction",
          text: "Read an advertisement. Effective Communication in the Modern Workplace",
        },
        { type: "paragraph", text: "Original workshop information." },
      ],
    };
    const result = readingPresentation(q);
    expect(result.heading).toBe("Read an advertisement.");
    expect(result.question.stemBlocks?.[0]).toEqual({
      type: "title",
      text: "Effective Communication in the Modern Workplace",
    });
    expect(result.question.stemBlocks?.[1]).toBe(q.stemBlocks?.[1]);
  });
  it("uses only source substrings for the verified notice title, subtitle and body", () => {
    const text =
      "Read a notice. Municipal Charter Sign up for paperless billing statements today. Safe, convenient, easy. Enroll in paperless billing.";
    const result = readingPresentation({
      id: "student-1-r1-11",
      type: "choice",
      stemBlocks: [{ type: "instruction", text }],
    });
    expect(result.question.stemBlocks?.map((block) => block.type)).toEqual([
      "title",
      "instruction",
      "paragraph",
    ]);
    expect(
      [
        result.heading,
        ...result.question.stemBlocks!.map((block) =>
          "text" in block ? block.text : "",
        ),
      ].join(" "),
    ).toBe(text);
  });
  it("does not chop a complete multi-sentence Essentials instruction", () => {
    const text =
      "Read the information about the event. Then select True, False, or Not Stated.";
    expect(
      readingPresentation({
        id: "essentials",
        type: "choice",
        stemBlocks: [{ type: "instruction", text }],
      }).heading,
    ).toBe(text);
  });
  it("does not reinterpret a different notice as the named source design", () => {
    const result = readingPresentation({
      id: "student-1-r1-11",
      type: "choice",
      stemBlocks: [
        {
          type: "instruction",
          text: "Read a notice. A different original notice.",
        },
      ],
    });
    expect(result.question.stemBlocks).toEqual([
      { type: "paragraph", text: "A different original notice." },
    ]);
  });
});
