import React from "react";
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { AnswerInput } from "../../src/Questions";
import type { Question } from "../../src/types";

afterEach(cleanup);

it("resets the selected gap when moving to a shorter sentence without losing saved answers", () => {
  const first: Question = {
    id: "long-sentence",
    type: "build_sentence",
    tokens: ["one", "two", "three"],
    slots: [{ id: "a" }, { id: "b" }, { id: "c" }],
  };
  const second: Question = {
    id: "short-sentence",
    type: "build_sentence",
    tokens: ["new", "sentence"],
    slots: [{ id: "a" }, { id: "b" }],
  };
  const onChange = vi.fn();
  const view = (q: Question, order: string[]) => (
    <AnswerInput
      question={q}
      value={{ tokenOrder: order }}
      onChange={onChange}
    />
  );
  const { rerender } = render(view(first, ["", "", "2"]));
  fireEvent.click(
    screen.getByRole("button", { name: "Gap 3: three. Click to remove." }),
  );
  rerender(view(second, ["", ""]));
  fireEvent.click(
    screen.getByRole("button", { name: "Use word block 1: new" }),
  );
  expect(onChange).toHaveBeenLastCalledWith({ tokenOrder: ["0", ""] });
  rerender(view(first, ["", "", "2"]));
  expect(
    screen.getByRole("button", { name: "Gap 3: three. Click to remove." }),
  ).toBeTruthy();
  fireEvent.click(
    screen.getByRole("button", { name: "Use word block 1: one" }),
  );
  expect(onChange).toHaveBeenLastCalledWith({ tokenOrder: ["0", "", "2"] });
});
