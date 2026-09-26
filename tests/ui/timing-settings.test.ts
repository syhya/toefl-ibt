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
  expect([timing.readingCommon, timing.readingSecond]).toEqual([900, 900]);
  expect(timing.readingCommon + timing.readingSecond).toBe(1800);
  expect(rules.simulationDefaults.readingModuleSeconds).toEqual([900, 900]);
  expect(rules.verifiedRules.reading.exactModuleSeconds).toBeNull();
});

it("upgrades an unchanged old preset without keeping the old 20:30 total", () => {
  localStorage.setItem(
    "toefl-lab-settings",
    JSON.stringify({
      ...DEFAULT_TIMING,
      readingCommon: 690,
      readingSecond: 540,
    }),
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

it.each([690, 1260])(
  "preserves a deliberately saved %i-second old reading allocation",
  (first) => {
    const custom = {
      ...DEFAULT_TIMING,
      readingCommon: first,
      readingSecond: 540,
    };
    saveTimingSettings(custom);
    expect(loadTimingSettings()).toEqual(custom);
    saveTimingSettings(DEFAULT_TIMING);
    expect(loadTimingSettings().readingCommon).toBe(900);
  },
);

it.each([null, "2"])(
  "upgrades the previous 21+9 default (settings version %s)",
  (version) => {
    localStorage.setItem(
      "toefl-lab-settings",
      JSON.stringify({
        ...DEFAULT_TIMING,
        readingCommon: 1260,
        readingSecond: 540,
      }),
    );
    if (version) localStorage.setItem("toefl-lab-settings-version", version);
    expect(loadTimingSettings()).toEqual(DEFAULT_TIMING);
  },
);

it("preserves an 11:30 allocation explicitly saved under the previous settings version", () => {
  const custom = { ...DEFAULT_TIMING, readingCommon: 690, readingSecond: 540 };
  localStorage.setItem("toefl-lab-settings", JSON.stringify(custom));
  localStorage.setItem("toefl-lab-settings-version", "2");
  expect(loadTimingSettings()).toEqual(custom);
});
