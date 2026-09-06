import type { EventInput, Session } from "./types";
import { getLocale, localizeDynamic, tr, type Locale } from "./i18n";
export class ApiError extends Error {
  session?: Session;
  status: number;
  constructor(message: string, status: number, session?: Session) {
    super(message);
    this.status = status;
    this.session = session;
  }
}
export async function api<T>(
  url: string,
  options: RequestInit = {},
): Promise<T> {
  // Only presentation headers follow the selected locale. Session IDs, answer
  // values and requestId keys remain identical when the interface is switched.
  const headers = new Headers(options.headers);
  headers.set("Accept-Language", getLocale());
  const response = await fetch(url, { ...options, headers });
  const body = await response
    .json()
    .catch(() => ({ error: `HTTP ${response.status}` }));
  if (!response.ok)
    throw new ApiError(
      typeof body.error === "string"
        ? localizeDynamic(body.error)
        : typeof body.detail === "string"
          ? localizeDynamic(body.detail)
          : tr("Local request failed", "本地请求失败"),
      response.status,
      body.session,
    );
  return body;
}
export const post = <T>(url: string, data: unknown) =>
  api<T>(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
export const sendEvent = (id: string, event: EventInput) =>
  post<Session>(`/api/sessions/${id}/events`, {
    requestId: crypto.randomUUID(),
    ...event,
  });
export const ORDER = ["reading", "listening", "writing", "speaking"] as const;
export const LABELS = {
  reading: "Reading",
  listening: "Listening",
  writing: "Writing",
  speaking: "Speaking",
};
export const DEFAULT_TIMING = {
  readingCommon: 690,
  readingSecond: 540,
  listeningResponse: 20,
  listeningAcademic: 30,
  buildSentence: 360,
  email: 420,
  academicDiscussion: 600,
  repeat: [8, 8, 10, 10, 10, 12, 12],
  interview: 45,
};
export const sectionLabel = (id: string, locale: Locale = getLocale()) =>
  locale === "zh-CN"
    ? { reading: "阅读", listening: "听力", writing: "写作", speaking: "口语" }[
        id
      ] || id
    : LABELS[id as keyof typeof LABELS] || id;
export const taskName = (type: string, locale?: Locale) =>
  (locale === "zh-CN"
    ? (
        {
          choice: "选择答案",
          cloze: "补全单词",
          build_sentence: "组句",
          email: "邮件写作",
          academic_discussion: "学术讨论",
          listen_repeat: "听后复述",
          interview: "模拟访谈",
          short_answer: "选择句子",
          source_page: "原始资料练习",
          daily_life: "日常阅读",
          academic_passage: "学术阅读",
          listen_response: "听后选择回应",
          conversation: "听对话",
          announcement: "听通知",
          academic_talk: "听学术讲座",
          read_aloud: "朗读",
          picture_writing: "看图写作",
        } as Record<string, string>
      )[type]
    : undefined) ||
  {
    choice: "Choose an answer",
    cloze: "Complete the Words",
    build_sentence: "Build a Sentence",
    email: "Write an Email",
    academic_discussion: "Academic Discussion",
    listen_repeat: "Listen and Repeat",
    interview: "Take an Interview",
    short_answer: "Select a sentence",
    source_page: "Source practice",
    daily_life: "Read in Daily Life",
    academic_passage: "Academic Passage",
    listen_response: "Listen and Choose a Response",
    conversation: "Listen to a Conversation",
    announcement: "Listen to an Announcement",
    academic_talk: "Listen to an Academic Talk",
    read_aloud: "Read Aloud",
    picture_writing: "Picture Writing",
  }[type] ||
  type;
export const time = (n: number | null | undefined) =>
  n == null
    ? "—:—"
    : `${Math.floor(Math.max(0, n) / 60)
        .toString()
        .padStart(
          2,
          "0",
        )}:${(Math.max(0, n) % 60).toString().padStart(2, "0")}`;
export const date = (
  value: string | number | undefined,
  locale: Locale = getLocale(),
) =>
  value
    ? new Date(value).toLocaleString(locale, {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      })
    : tr("Local practice", "本地练习", {}, locale);
export const wordCount = (s: string) => s.trim().match(/\S+/g)?.length || 0;
export const size = (n: number = 0) =>
  n >= 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.ceil(n / 1024)} KB`;
