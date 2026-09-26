import { DEFAULT_TIMING } from "./api";
import type { Timing } from "./types";

const SETTINGS_KEY = "toefl-lab-settings";
const VERSION_KEY = "toefl-lab-settings-version";
const VERSION = "2";

export function loadTimingSettings(): Timing {
  try {
    const saved = JSON.parse(localStorage.getItem(SETTINGS_KEY) || "{}");
    if (!saved || typeof saved !== "object" || Array.isArray(saved)) {
      return { ...DEFAULT_TIMING };
    }
    const timing = { ...DEFAULT_TIMING, ...saved };
    const legacy = { ...DEFAULT_TIMING, readingCommon: 690 };
    // Upgrade only the unchanged old preset. Explicit custom profiles, and
    // deliberate 11:30 settings saved by this version, must survive reloads.
    const unchangedLegacy =
      localStorage.getItem(VERSION_KEY) === null &&
      Object.keys(saved).every((key) => key in legacy) &&
      Object.entries(legacy).every(
        ([key, value]) =>
          JSON.stringify(timing[key as keyof Timing]) === JSON.stringify(value),
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
