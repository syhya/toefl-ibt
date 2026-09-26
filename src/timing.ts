import { DEFAULT_TIMING } from "./api";
import type { Timing } from "./types";

const SETTINGS_KEY = "toefl-lab-settings";
const VERSION_KEY = "toefl-lab-settings-version";
const VERSION = "3";

export function loadTimingSettings(): Timing {
  try {
    const saved = JSON.parse(localStorage.getItem(SETTINGS_KEY) || "{}");
    if (!saved || typeof saved !== "object" || Array.isArray(saved)) {
      return { ...DEFAULT_TIMING };
    }
    const timing = { ...DEFAULT_TIMING, ...saved };
    const version = localStorage.getItem(VERSION_KEY);
    const legacy = [
      ...(version === null
        ? [{ ...DEFAULT_TIMING, readingCommon: 690, readingSecond: 540 }]
        : []),
      ...(version === null || version === "2"
        ? [{ ...DEFAULT_TIMING, readingCommon: 1260, readingSecond: 540 }]
        : []),
    ];
    // Upgrade only the unchanged old preset. Explicit custom profiles, and
    // deliberate older allocations saved by this version, survive reloads.
    const unchangedLegacy =
      Object.keys(saved).every((key) => key in DEFAULT_TIMING) &&
      legacy.some((preset) =>
        Object.entries(preset).every(
          ([key, value]) =>
            JSON.stringify(timing[key as keyof Timing]) ===
            JSON.stringify(value),
        ),
      );
    return unchangedLegacy ? { ...DEFAULT_TIMING } : timing;
  } catch {
    return { ...DEFAULT_TIMING };
  }
}

export function saveTimingSettings(timing: Timing) {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(timing));
  localStorage.setItem(VERSION_KEY, VERSION);
}
