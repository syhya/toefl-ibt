import { useState } from "react";
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AnswerInput } from "../../src/Questions";
import type { Answer, Question } from "../../src/types";

afterEach(cleanup);

const question: Question = {
  id: "cloze-keyboard-fixture",
  type: "cloze",
  passageTemplate: "We mi{{b1}} think th{{b2}}.",
  blanks: [
    { id: "b1", prefix: "mi", length: 3 },
    { id: "b2", prefix: "th", length: 2 },
  ],
};

function Editor({
  initial = {},
  disabled = false,
  changed = () => {},
}: {
  initial?: Answer;
  disabled?: boolean;
  changed?: (value: Answer) => void;
}) {
  const [value, setValue] = useState<Answer>(initial);
  return (
    <div className="official-cloze">
      <AnswerInput
        question={question}
        value={value}
        disabled={disabled}
        strict
        examStyle
        onChange={(answer) => {
          setValue(answer);
          changed(answer);
        }}
      />
      <button>Outside the passage</button>
    </div>
  );
}

it("keeps the same input and saved letters when a completed word is focused, blurred and edited again", async () => {
  const user = userEvent.setup(),
    changed = vi.fn();
  render(<Editor changed={changed} />);
  const [first, second] = screen.getAllByRole<HTMLInputElement>("textbox");
  await user.type(first, "GHT");
  expect(first.value).toBe("ght");
  expect(document.activeElement).toBe(first);
  expect(changed).toHaveBeenLastCalledWith({ b1: "ght" });
  const saves = changed.mock.calls.length;
  await user.tab();
  expect(document.activeElement).toBe(second);
  expect(first.closest(".cloze-word")?.textContent).toBe("might");
  expect(
    first
      .closest(".cloze-word")
      ?.querySelector(".cloze-completed-text")
      ?.getAttribute("aria-hidden"),
  ).toBe("true");
  expect(changed).toHaveBeenCalledTimes(saves);
  await user.tab({ shift: true });
  expect(document.activeElement).toBe(first);
  expect(screen.getAllByRole("textbox")[0]).toBe(first);
  await user.keyboard("{End}{Backspace}");
  expect(first.value).toBe("gh");
  expect(
    first.closest(".cloze-word")?.querySelector(".cloze-completed-text"),
  ).toBeNull();
  expect(changed).toHaveBeenLastCalledWith({ b1: "gh" });
});

it("restores saved completed and partial responses without duplicate fields or a save on focus", async () => {
  const user = userEvent.setup(),
    changed = vi.fn();
  render(<Editor initial={{ b1: "ght", b2: "a" }} changed={changed} />);
  const [first, second] = screen.getAllByRole<HTMLInputElement>("textbox");
  expect(first.value).toBe("ght");
  expect(second.value).toBe("a");
  expect(document.querySelectorAll(".cloze-completed-text")).toHaveLength(1);
  await user.click(first);
  await user.click(screen.getByRole("button", { name: "Outside the passage" }));
  expect(changed).not.toHaveBeenCalled();
  expect(screen.getAllByRole("textbox")).toHaveLength(2);
  expect(first.value).toBe("ght");
});

it("enforces missing-letter length and lowercase without rewriting the fixed source prefix", () => {
  const changed = vi.fn();
  render(<Editor changed={changed} />);
  const first = screen.getAllByRole<HTMLInputElement>("textbox")[0];
  fireEvent.change(first, { target: { value: "G1H!Tmore" } });
  expect(first.value).toBe("ght");
  expect(first.maxLength).toBe(3);
  expect(first.closest(".cloze-word")?.textContent).toBe("might");
  expect(changed).toHaveBeenLastCalledWith({ b1: "ght" });
});

it("does not allow a completed presentation to bypass the disabled exam state", async () => {
  const user = userEvent.setup(),
    changed = vi.fn();
  render(<Editor initial={{ b1: "ght" }} disabled changed={changed} />);
  const first = screen.getAllByRole<HTMLInputElement>("textbox")[0];
  expect(first.disabled).toBe(true);
  await user.type(first, "x");
  await user.tab();
  expect(document.activeElement).toBe(
    screen.getByRole("button", { name: "Outside the passage" }),
  );
  expect(first.value).toBe("ght");
  expect(changed).not.toHaveBeenCalled();
});
