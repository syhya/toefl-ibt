import type { Question, StemBlock } from "./types";

/** Separate source headings without dropping material merged into an OCR block. */
export function readingPresentation(question: Question): {
  heading?: string;
  question: Question;
} {
  const index =
    question.stemBlocks?.findIndex(
      (block) =>
        block.type === "title" ||
        (block.type === "instruction" && /^(Read |Fill in)/.test(block.text)),
    ) ?? -1;
  if (index < 0) return { question };
  const block = question.stemBlocks![index];
  if (!("text" in block)) return { question };
  let heading = block.text;
  const replacement: StemBlock[] = [];
  // These short printed instructions were merged with material in nine source
  // screens. Do not truncate other complete instructions (e.g. Essentials).
  const joined =
    block.type === "instruction" &&
    block.text.match(/^(Read (?:a notice|an advertisement)\.)\s+(.+)$/s);
  if (joined) {
    heading = joined[1];
    const body = joined[2];
    const municipal = body.match(
      /^(Municipal Charter) (Sign up for paperless billing statements today\.) (.+)$/s,
    );
    if (municipal && /^student-1-r1-(11|12)$/.test(question.id)) {
      // The displayed strings are slices of the source, not replacement copy.
      replacement.push(
        { type: "title", text: municipal[1] },
        { type: "instruction", text: municipal[2] },
        { type: "paragraph", text: municipal[3] },
      );
    } else {
      replacement.push({
        type: heading === "Read an advertisement." ? "title" : "paragraph",
        text: body,
      });
    }
  }
  const blocks = question.stemBlocks!.flatMap((source, i) =>
    i === index ? replacement : [source],
  );
  return { heading, question: { ...question, stemBlocks: blocks } };
}
