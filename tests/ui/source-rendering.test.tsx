import { afterEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { AnswerInput, StemAssets, StructuredStem } from "../../src/Questions";
import type { Question } from "../../src/types";

afterEach(cleanup);
describe("source-preserving question rendering", () => {
  it("renders verified source blocks as semantic text, dialogue, table, and essential visual", () => {
    const question: Question = {
      id: "structured-source",
      type: "choice",
      presentationSchema: "structured-v1",
      structuredContentStatus: "source-verified",
      stemBlocks: [
        { type: "title", text: "Campus schedule" },
        { type: "paragraph", text: "The office opens at nine." },
        {
          type: "dialogue",
          turns: [{ speaker: "Student", text: "Is it open today?" }],
        },
        {
          type: "message",
          sender: "Campus Office",
          recipient: "Students",
          subject: "Hours update",
          paragraphs: ["The office opens at nine."],
        },
        {
          type: "list",
          items: ["Bring your campus ID."],
          marker: "lower-alpha",
        },
        {
          type: "table",
          caption: "Office hours",
          headers: ["Day", "Time"],
          rows: [["Monday", "9:00"]],
          rowHeaders: true,
        },
        { type: "form_diagram", highlightedPosition: 4 },
        { type: "essential_visual", assetIndex: 0, alt: "Verified map" },
      ],
      assets: [
        {
          assetId: "map",
          url: "/api/test/map.png",
          role: "essentialVisual",
          highResolution: true,
        },
      ],
    };
    render(<StructuredStem question={question} />);
    expect(
      screen.getByRole("heading", { name: "Campus schedule" }),
    ).toBeTruthy();
    expect(screen.getByText("Is it open today?")).toBeTruthy();
    expect(screen.getByText("Hours update")).toBeTruthy();
    expect(
      screen
        .getByText("Bring your campus ID.")
        .closest("ol")
        ?.classList.contains("lower-alpha"),
    ).toBe(true);
    expect(screen.getByRole("table", { name: "Office hours" })).toBeTruthy();
    expect(screen.getByRole("rowheader", { name: "Monday" })).toBeTruthy();
    expect(
      screen.getByRole("img", {
        name: "Form layout with position 4 highlighted",
      }),
    ).toBeTruthy();
    expect(screen.getByRole("img", { name: "Verified map" })).toBeTruthy();
  });
  it("does not discard an authorized passage image when there is no OCR passage", () => {
    const question: Question = {
      id: "source-passage",
      type: "choice",
      passage: "",
      assets: [
        {
          assetId: "passage-image",
          url: "/api/test/passage.png",
          role: "passage",
          alt: "Original academic passage",
        },
      ],
    };
    render(<StemAssets question={question} />);
    expect(
      screen
        .getByRole("img", { name: "Original academic passage" })
        .getAttribute("src"),
    ).toBe("/api/test/passage.png");
  });
  it("splits an academic discussion into professor and student columns with source avatars", () => {
    const question: Question = {
      id: "discussion-source",
      type: "academic_discussion",
      presentationSchema: "structured-v1",
      structuredContentStatus: "source-verified",
      stemBlocks: [
        {
          type: "paragraph",
          text: "Your professor is teaching a class on sociology.",
        },
        {
          type: "dialogue",
          turns: [
            {
              speaker: "Dr. Gupta",
              text: "Which viewpoint do you agree with?",
              avatarAssetIndex: 0,
            },
            {
              speaker: "Kelly",
              text: "Education creates opportunity.",
              avatarAssetIndex: 1,
            },
            {
              speaker: "Andrew",
              text: "Connections also matter.",
              avatarAssetIndex: 2,
            },
          ],
        },
      ],
      assets: ["professor", "student-one", "student-two"].map(
        (name, index) => ({
          assetId: name,
          url: `/api/test/${name}.png`,
          role: "essentialVisual",
          highResolution: true,
          alt: `Source portrait ${index + 1}`,
        }),
      ),
    };
    render(
      <>
        <section aria-label="Professor column">
          <StructuredStem question={question} discussionPart="professor" />
        </section>
        <section aria-label="Student column">
          <StructuredStem question={question} discussionPart="students" />
        </section>
      </>,
    );
    const professor = within(screen.getByLabelText("Professor column")),
      students = within(screen.getByLabelText("Student column"));
    expect(professor.getByText("Dr. Gupta")).toBeTruthy();
    expect(professor.getByText(/teaching a class/)).toBeTruthy();
    expect(professor.queryByText("Kelly")).toBeNull();
    expect(students.getByText("Kelly")).toBeTruthy();
    expect(students.getByText("Andrew")).toBeTruthy();
    expect(students.queryByText("Dr. Gupta")).toBeNull();
    expect(students.queryByText(/teaching a class/)).toBeNull();
    expect(document.querySelectorAll("img.discussion-avatar")).toHaveLength(3);
    expect(
      document.querySelectorAll("img.discussion-avatar[alt='']"),
    ).toHaveLength(3);
    expect(document.querySelectorAll("img.essential-visual")).toHaveLength(0);
  });
  it("places a missing-letter field in source context and saves only those letters", () => {
    const changed = vi.fn();
    const question: Question = {
      id: "inline-fixture",
      type: "cloze",
      passageTemplate: "He pre{{b1}}ed the notice.",
      blanks: [{ id: "b1", number: 1, prefix: "pre", suffix: "ed", length: 2 }],
    };
    render(
      <AnswerInput
        question={question}
        value={{}}
        onChange={changed}
        disabled={false}
        strict
      />,
    );
    expect(screen.getByText("He")).toBeTruthy();
    const input = screen.getByRole("textbox", {
      name: "Missing letters for word 1, 2 letters required",
    });
    const word = input.closest(".cloze-word");
    expect(word).toBeTruthy();
    expect(word?.textContent).toBe("preed");
    expect(word?.querySelectorAll(".cloze-word-part")).toHaveLength(2);
    expect(input.getAttribute("maxlength")).toBe("2");
    expect(input.getAttribute("style")).toContain("--blank-slots: 2");
    expect(screen.getByText("One blue slot = one letter")).toBeTruthy();
    expect(screen.getByText(/Blank 1/).textContent).toContain("0 / 2 letters");
    fireEvent.change(input, { target: { value: "d1s" } });
    expect(changed).toHaveBeenCalledWith({ b1: "ds" });
  });
  it("keeps the original True/False/Not stated identifiers", () => {
    const changed = vi.fn();
    const question: Question = {
      id: "supplemental-fixture",
      type: "choice",
      choices: ["True", "False", "Not stated"].map((id) => ({ id, text: id })),
    };
    render(
      <AnswerInput
        question={question}
        value={undefined}
        onChange={changed}
        disabled={false}
        strict={false}
      />,
    );
    fireEvent.click(
      screen.getByRole("radio", { name: "Not stated", exact: true }),
    );
    expect(changed).toHaveBeenCalledWith("Not stated");
    expect(screen.getAllByText("Not stated")).toHaveLength(1);
  });
  it("selects an original sentence without inventing visible A–D options", () => {
    const changed = vi.fn();
    const question: Question = {
      id: "sentence-fixture",
      type: "choice",
      interaction: "select_sentence",
      choices: [
        { id: "A", text: "The first source sentence." },
        { id: "B", text: "The second source sentence." },
      ],
    };
    render(
      <AnswerInput
        question={question}
        value={undefined}
        onChange={changed}
        disabled={false}
        strict
      />,
    );
    fireEvent.click(
      screen.getByRole("button", {
        name: "Select sentence 2: The second source sentence.",
      }),
    );
    expect(changed).toHaveBeenCalledWith("B");
    expect(screen.queryByText("A")).toBeNull();
    expect(screen.queryByText("B")).toBeNull();
  });
  it("selects a verified sentence directly inside a structured passage", () => {
    const changed = vi.fn();
    const question: Question = {
      id: "structured-sentence",
      type: "choice",
      interaction: "select_sentence",
      prompt: "Select a sentence.",
      presentationSchema: "structured-v1",
      structuredContentStatus: "source-verified",
      stemBlocks: [
        {
          type: "paragraph",
          text: "The first source sentence. The second source sentence.",
        },
      ],
      choices: [
        { id: "A", text: "The first source sentence." },
        { id: "B", text: "The second source sentence." },
      ],
    };
    render(
      <StructuredStem
        question={question}
        onChange={changed}
        disabled={false}
      />,
    );
    fireEvent.click(
      screen.getByRole("button", {
        name: "Select sentence 2: The second source sentence.",
      }),
    );
    expect(changed).toHaveBeenCalledWith("B");
    expect(screen.queryByText("A")).toBeNull();
    expect(screen.queryByText("B")).toBeNull();
  });
});
