import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { DEFAULT_TIMING } from "../../src/api";
import { loadTimingSettings, saveTimingSettings } from "../../src/timing";
import rules from "../../shared/rules.json";

beforeEach(() => {
  const values = new Map<string, string>();
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
  });
});
afterEach(() => vi.unstubAllGlobals());

it("loads the documented 30-minute reading profile on a new installation", () => {
  const timing = loadTimingSettings();
  expect([timing.readingCommon, timing.readingSecond]).toEqual([1260, 540]);
  expect(timing.readingCommon + timing.readingSecond).toBe(1800);
  expect(rules.simulationDefaults.readingModuleSeconds).toEqual([1260, 540]);
  expect(rules.verifiedRules.reading.exactModuleSeconds).toBeNull();
});

it("upgrades an unchanged old preset without keeping the old 20:30 total", () => {
  localStorage.setItem(
    "toefl-lab-settings",
    JSON.stringify({ ...DEFAULT_TIMING, readingCommon: 690 }),
  );
  expect(loadTimingSettings()).toEqual(DEFAULT_TIMING);
});

it("preserves existing custom profiles rather than assuming they are obsolete defaults", () => {
  const custom = {
    ...DEFAULT_TIMING,
    readingCommon: 690,
    listeningResponse: 25,
  };
  localStorage.setItem("toefl-lab-settings", JSON.stringify(custom));
  expect(loadTimingSettings()).toEqual(custom);
});

it("preserves a deliberately saved old reading limit on later reloads", () => {
  const custom = { ...DEFAULT_TIMING, readingCommon: 690 };
  saveTimingSettings(custom);
  expect(loadTimingSettings()).toEqual(custom);
  saveTimingSettings(DEFAULT_TIMING);
  expect(loadTimingSettings().readingCommon).toBe(1260);
});
