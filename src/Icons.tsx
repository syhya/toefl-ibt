const paths: Record<string, string> = {
  "chevron-right": "M9 5l7 7-7 7",
  "chevron-left": "M15 5l-7 7 7 7",
  bookmark: "M6 3h12v18l-6-4-6 4V3z",
  question:
    "M12 3a9 9 0 110 18 9 9 0 010-18zM9 9a3 3 0 116 0c0 2-3 2-3 5M12 17v.1",
  eye: "M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12zM12 9a3 3 0 110 6 3 3 0 010-6z",
  "eye-off":
    "M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12zM12 9a3 3 0 110 6 3 3 0 010-6zM3 21L21 3",
  grid: "M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z",
  book: "M12 5c-3-2-6-2-9-1v15c3-1 6-1 9 1 3-2 6-2 9-1V4c-3-1-6-1-9 1zm0 0v15",
  headphones: "M3 13v-1a9 9 0 0118 0v1M3 12h3v8H3zM18 12h3v8h-3z",
  pen: "M14 5l5 5M4 20l4-1L20 7a2 2 0 00-5-4L3 15l-1 7z",
  mic: "M9 5a3 3 0 016 0v7a3 3 0 01-6 0V5zM5 11v1a7 7 0 0014 0v-1M12 19v3M8 22h8",
  clock: "M12 3a9 9 0 110 18 9 9 0 010-18zM12 7v5l3 2",
  folder: "M3 5h7l2 3h9v12H3V5z",
  chart: "M4 3v18h17M8 16v-4M13 16V8M18 16V5",
  settings:
    "M12 8a4 4 0 110 8 4 4 0 010-8zM9 2h6l1 4 4 1 2 5-3 3v4l-5 3-3-3H7l-4-4 1-4-2-4 4-3z",
  shield: "M12 2l9 4v6c0 5-9 10-9 10S3 17 3 12V6l9-4zM8 12l3 3 5-6",
  arrow: "M4 12h16M14 6l6 6-6 6",
  check: "M5 12l4 4L19 6",
  search: "M10 3a7 7 0 110 14 7 7 0 010-14zM15 15l6 6",
  file: "M5 2h9l5 5v15H5V2zM14 2v6h5M8 13h8M8 17h6",
  info: "M12 3a9 9 0 110 18 9 9 0 010-18zM12 11v6M12 7v.1",
  external: "M14 3h7v7M21 3L10 14M10 3H3v18h18v-7",
  play: "M8 4l12 8-12 8V4z",
  close: "M5 5l14 14M19 5L5 19",
  flag: "M5 22V3h14l-3 5 3 5H5",
  volume: "M3 9h4l5-5v16l-5-5H3V9zM16 8a6 6 0 010 8M19 5a10 10 0 010 14",
  download: "M12 3v12M7 10l5 5 5-5M3 16v5h18v-5",
  back: "M20 12H4M10 6l-6 6 6 6",
  pause: "M8 4v16M16 4v16",
  undo: "M8 4L3 9l5 5M3 9h11a7 7 0 017 7v3",
  redo: "M16 4l5 5-5 5M21 9H10a7 7 0 00-7 7v3",
};
export default function Icon({ name }: { name: string }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d={paths[name] || paths.file} />
    </svg>
  );
}
export const sectionIcon = (id: string) =>
  ({
    reading: "book",
    listening: "headphones",
    writing: "pen",
    speaking: "mic",
  })[id] || "book";
