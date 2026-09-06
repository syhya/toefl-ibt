import React, { useState } from "react";
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { AnswerInput, StructuredStem } from "../../src/Questions";
import type { Answer, Question } from "../../src/types";

afterEach(cleanup);

function Editor({
  id = "email",
  disabled = false,
}: {
  id?: string;
  disabled?: boolean;
}) {
  const [value, setValue] = useState<Answer>("");
  return (
    <AnswerInput
      question={{ id, type: "email" }}
      value={value}
      onChange={setValue}
      disabled={disabled}
      strict
      examStyle
    />
  );
}

const textarea = () =>
  screen.getByRole("textbox", {
    name: "Your written response",
  }) as HTMLTextAreaElement;

describe("source-style writing controls", () => {
  it("cuts and pastes the selected part of the current answer, including undo and redo", () => {
    render(<Editor />);
    const input = textarea();
    fireEvent.change(input, { target: { value: "My own response" } });
    input.setSelectionRange(3, 7);
    fireEvent.click(screen.getByRole("button", { name: "Cut", exact: true }));
    expect(input.value).toBe("My response");
    input.setSelectionRange(3, 3);
    fireEvent.click(screen.getByRole("button", { name: "Paste", exact: true }));
    expect(input.value).toBe("My own response");
    fireEvent.click(screen.getByRole("button", { name: "Undo", exact: true }));
    expect(input.value).toBe("My response");
    fireEvent.click(screen.getByRole("button", { name: "Redo", exact: true }));
    expect(input.value).toBe("My own response");
    expect(input.getAttribute("placeholder")).toBeNull();
  });

  it("blocks outside text and keeps keyboard clipboard content within this response only", () => {
    const { rerender } = render(<Editor />);
    const input = textarea();
    expect(
      fireEvent.paste(input, {
        clipboardData: { getData: () => "An outside answer" },
      }),
    ).toBe(false);
    expect(input.value).toBe("");
    fireEvent.change(input, { target: { value: "My own words" } });
    input.setSelectionRange(3, 6);
    expect(fireEvent.copy(input)).toBe(false);
    input.setSelectionRange(7, 12);
    expect(
      fireEvent.paste(input, {
        clipboardData: { getData: () => "External text must never appear" },
      }),
    ).toBe(false);
    expect(input.value).toBe("My own own");
    rerender(<Editor id="a-new-question" />);
    expect(
      (
        screen.getByRole("button", {
          name: "Paste",
          exact: true,
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(true);
    expect(
      fireEvent.paste(textarea(), {
        clipboardData: { getData: () => "An outside answer" },
      }),
    ).toBe(false);
    expect(textarea().value).not.toContain("outside");
  });

  it("never modifies the answer with toolbar actions after its response window is disabled", () => {
    const { rerender } = render(<Editor />);
    const input = textarea();
    fireEvent.change(input, { target: { value: "Saved response" } });
    input.setSelectionRange(0, 5);
    fireEvent.copy(input);
    rerender(<Editor disabled />);
    for (const name of ["Cut", "Paste", "Undo", "Redo"]) {
      const button = screen.getByRole("button", {
        name,
        exact: true,
      }) as HTMLButtonElement;
      expect(button.disabled).toBe(true);
      fireEvent.click(button);
    }
    expect(textarea().value).toBe("Saved response");
  });

  it("hides and restores the live word count without modifying the written answer", () => {
    const { container } = render(<Editor />);
    const input = textarea();
    fireEvent.change(input, { target: { value: "My first answer" } });
    const count = container.querySelector(".editor-word-count") as HTMLElement;
    expect(count.textContent).toBe("3");
    fireEvent.click(screen.getByRole("button", { name: "Hide Word Count" }));
    expect(count.hidden).toBe(true);
    fireEvent.change(input, { target: { value: "My first revised answer" } });
    fireEvent.click(screen.getByRole("button", { name: "Show Word Count" }));
    expect(count.hidden).toBe(false);
    expect(count.textContent).toBe("4");
    expect(input.value).toBe("My first revised answer");
    expect(container.querySelector(".editor-meta")).toBeNull();
  });
});

it("splits original email prompt and response metadata without rendering table column headings", () => {
  const question: Question = {
    id: "source-email",
    type: "email",
    stemBlocks: [
      { type: "paragraph", text: "The original source situation." },
      {
        type: "list",
        items: [
          "The first original instruction.",
          "The second original instruction.",
        ],
      },
      {
        type: "table",
        caption: "Your Response",
        headers: ["Field", "Text"],
        rows: [
          ["To", "Jake"],
          ["Subject", "Need your contribution to the group project"],
        ],
        rowHeaders: true,
      },
    ],
  };
  const { container, rerender } = render(
    <StructuredStem question={question} displayPart="email-prompt" />,
  );
  expect(screen.getByText("The original source situation.")).toBeTruthy();
  expect(screen.queryByText("Jake")).toBeNull();
  rerender(<StructuredStem question={question} displayPart="email-response" />);
  expect(screen.queryByText("The original source situation.")).toBeNull();
  expect(screen.getByText("Your Response:")).toBeTruthy();
  expect(screen.getByText("To:")).toBeTruthy();
  expect(screen.getByText("Jake")).toBeTruthy();
  expect(
    screen.getByText("Need your contribution to the group project"),
  ).toBeTruthy();
  expect(container.querySelector("table")).toBeNull();
  expect(screen.queryByText("Field")).toBeNull();
});
