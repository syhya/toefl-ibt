import { useSyncExternalStore } from "react";
import { commonMessages } from "./locales/common";
import { localizeServerMessage } from "./locales/server";

export type Locale = "en" | "zh-CN";
export type TranslationValues = Record<string, string | number>;
const STORAGE_KEY = "toefl-lab-language";
const listeners = new Set<() => void>();
// Language is presentation state. It must never be written into exam answers,
// frozen timing profiles, or the imported source text.
let currentLocale: Locale = readPreference();

function readPreference(): Locale {
  try {
    return localStorage.getItem(STORAGE_KEY) === "zh-CN" ? "zh-CN" : "en";
  } catch {
    return "en";
  }
}
export function getLocale(): Locale {
  return currentLocale;
}
export function setLocale(locale: Locale) {
  if (locale !== "en" && locale !== "zh-CN") return;
  currentLocale = locale;
  try {
    localStorage.setItem(STORAGE_KEY, locale);
  } catch {
    /* Private browsing can disable storage. */
  }
  if (typeof document !== "undefined") {
    document.documentElement.lang = locale;
    document.title =
      locale === "en"
        ? "TOEFL Local Lab · Personal practice"
        : "TOEFL Local Lab · 个人练习";
  }
  listeners.forEach((listener) => listener());
}
export function tr(
  en: string,
  zh: string,
  values: TranslationValues = {},
  locale: Locale = currentLocale,
): string {
  return (locale === "zh-CN" ? zh : en).replace(/\{(\w+)\}/g, (token, key) =>
    Object.prototype.hasOwnProperty.call(values, key)
      ? String(values[key])
      : token,
  );
}
function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
export function useI18n() {
  const locale = useSyncExternalStore(
    subscribe,
    getLocale,
    () => "en" as Locale,
  );
  return { locale, t: tr, setLocale };
}
export function LanguageSwitch() {
  const { locale, t } = useI18n();
  return (
    <div
      className="language-switch"
      role="group"
      aria-label={t("Interface language", "界面语言")}
    >
      <button
        type="button"
        lang="en"
        aria-pressed={locale === "en"}
        onClick={() => setLocale("en")}
      >
        EN
      </button>
      <button
        type="button"
        lang="zh-CN"
        aria-pressed={locale === "zh-CN"}
        onClick={() => setLocale("zh-CN")}
      >
        中文
      </button>
    </div>
  );
}

// Only product-authored status text belongs here. Unrecognized source passages,
// names and explanations pass through verbatim rather than being paraphrased.
export function localizeDynamic(
  text: unknown,
  locale: Locale = currentLocale,
): string {
  if (text == null) return "";
  const value = String(text);
  const server = localizeServerMessage(value, locale);
  if (server !== undefined) return server;
  if (locale === "en") return commonMessages[value] || value;
  return (
    Object.entries(commonMessages).find(([, en]) => en === value)?.[0] || value
  );
}

if (typeof window !== "undefined") {
  window.addEventListener("storage", (event) => {
    if (event.key === STORAGE_KEY)
      setLocale(event.newValue === "zh-CN" ? "zh-CN" : "en");
  });
  if (typeof document !== "undefined") {
    document.documentElement.lang = currentLocale;
    document.title =
      currentLocale === "zh-CN"
        ? "TOEFL Local Lab · 个人练习"
        : "TOEFL Local Lab · Personal practice";
  }
}
