import { LanguageSwitch, useI18n } from "./i18n";
import { examText as tx } from "./locales/exam";
import { useState } from "react";
import type { Session, Stage } from "./types";
import { LABELS, time } from "./api";
import Icon from "./Icons";

export default function OfficialChrome({
  session,
  seconds,
  disabled,
  busy,
  onHelp,
  onReview,
  onBack,
  onNext,
  onBegin,
  onPause,
  confirmWriting = false,
}: {
  session: Session;
  seconds: number | null;
  disabled: boolean;
  busy: boolean;
  onHelp: () => void;
  onReview: () => void;
  onBack: () => void;
  onNext: () => void;
  onBegin: () => void;
  onPause: () => void;
  confirmWriting?: boolean;
}) {
  useI18n();
  const [hideTime, setHideTime] = useState(false),
    [volumeOpen, setVolumeOpen] = useState(false),
    [volume, setVolume] = useState(() => {
      const saved = Number(
        sessionStorage.getItem("toefl-exam-volume") ?? "0.8",
      );
      return Number.isFinite(saved) ? Math.min(1, Math.max(0, saved)) : 0.8;
    });
  const st = session.stage;
  if (!st) return null;
  const q = session.question,
    active = session.status === "active",
    allowed = session.allowedActions || [],
    directions = session.phase === "directions",
    listeningAudio = st.section === "listening" && session.phase === "audio",
    speakingWindow =
      st.section === "speaking" &&
      ["audio", "response"].includes(session.phase),
    volumeOnly = listeningAudio || speakingWindow,
    canNavigate = active && session.phase === "response" && !!q,
    navigationDisabled = disabled || busy || !canNavigate,
    writingLong =
      !session.filtered &&
      (q?.type === "email" || q?.type === "academic_discussion"),
    total = writingLong
      ? 2
      : st.section === "speaking"
        ? st.sectionItemCount || st.itemCount || st.questionCount
        : st.itemCount || st.questionCount,
    start = writingLong
      ? q?.type === "email"
        ? 1
        : 2
      : st.section === "speaking"
        ? (st.sectionQuestionOffset || 0) + session.questionIndex + 1
        : session.filtered
          ? (st.currentQuestionUnitStart ?? session.questionIndex + 1)
          : q?.number || session.questionIndex + 1,
    end = session.filtered
      ? q?.type === "cloze" && (q.blanks?.length || 0) > 1
        ? start + q.blanks!.length - 1
        : undefined
      : q?.numberEnd,
    clock =
      seconds ??
      (directions &&
      st.timer === "shared" &&
      (st.section === "reading" || /Build a Sentence/i.test(st.title))
        ? st.seconds
        : null),
    clockText =
      clock === null
        ? ""
        : `${String(Math.floor(clock / 3600)).padStart(2, "0")}:${time(clock % 3600)}`;
  return (
    <header className="official-chrome">
      <div className="official-topbar">
        <div className="official-app-brand">
          TOEFL <small>Local Lab</small>
        </div>
        <LanguageSwitch />
        <div className="official-top-actions">
          {confirmWriting ? (
            <>
              <button onClick={onBack} disabled={disabled || busy}>
                <Icon name="chevron-left" />
                {tx("Back")}
              </button>
              <button
                className="official-next"
                onClick={onNext}
                disabled={disabled || busy}
              >
                {tx("Continue")}
                <Icon name="chevron-right" />
              </button>
            </>
          ) : (
            <>
              {st.section !== "writing" && (
                <div className="official-volume">
                  <button
                    onClick={() => setVolumeOpen(!volumeOpen)}
                    aria-expanded={volumeOpen}
                  >
                    {tx("Volume")}
                    <Icon name="volume" />
                  </button>
                  {volumeOpen && (
                    <label className="official-volume-popover">
                      {tx("Volume")}
                      <input
                        aria-label={tx("Exam volume")}
                        type="range"
                        min="0"
                        max="1"
                        step="0.05"
                        value={volume}
                        onChange={(e) => {
                          const next = Number(e.target.value);
                          setVolume(next);
                          sessionStorage.setItem(
                            "toefl-exam-volume",
                            String(next),
                          );
                          document
                            .querySelectorAll<HTMLMediaElement>("audio,video")
                            .forEach((media) => (media.volume = next));
                        }}
                      />
                    </label>
                  )}
                </div>
              )}
              {!volumeOnly && (
                <button onClick={onHelp}>
                  {tx("Help")}
                  <Icon name="question" />
                </button>
              )}
              {!volumeOnly && !directions && st.canBack && (
                <button
                  onClick={onReview}
                  disabled={navigationDisabled || !allowed.includes("jump")}
                >
                  {tx("Review")}
                  <Icon name="bookmark" />
                </button>
              )}
              {!volumeOnly && !directions && allowed.includes("back") && (
                <button onClick={onBack} disabled={navigationDisabled}>
                  <Icon name="chevron-left" />
                  {tx("Back")}
                </button>
              )}
              {directions ? (
                <button
                  className="official-next"
                  onClick={onBegin}
                  disabled={busy || !active || !allowed.includes("begin")}
                  aria-label={tx("Begin {section}", {
                    section: tx(LABELS[st.section]),
                  })}
                >
                  {tx("Begin")}
                  <Icon name="chevron-right" />
                </button>
              ) : !volumeOnly ? (
                <button
                  className="official-next"
                  onClick={onNext}
                  disabled={navigationDisabled || !allowed.includes("next")}
                >
                  {tx("Next")}
                  <Icon name="chevron-right" />
                </button>
              ) : null}
              {!volumeOnly && session.mode === "practice" && (
                <button
                  onClick={onPause}
                  disabled={
                    busy ||
                    !active ||
                    !allowed.includes(
                      session.phase === "paused" ? "resume" : "pause",
                    )
                  }
                  aria-label={
                    session.phase === "paused" ? tx("Resume") : tx("Pause")
                  }
                >
                  <Icon name={session.phase === "paused" ? "play" : "pause"} />
                </button>
              )}
            </>
          )}
        </div>
      </div>
      <div className="official-statusbar">
        <div className="official-question-position">
          <strong>{tx(LABELS[st.section])}</strong>
          {!directions &&
            (!listeningAudio || q?.taskType === "listen_response") &&
            q?.audio?.kind !== "directions" &&
            q && (
              <>
                <span className="official-divider">|</span>
                <span>
                  {end
                    ? tx("Questions {start}–{end} of {total}", {
                        start,
                        end,
                        total,
                      })
                    : tx("Question {number} of {total}", {
                        number: start,
                        total,
                      })}
                </span>
              </>
            )}
        </div>
        {clock !== null &&
          st.section !== "speaking" &&
          !listeningAudio &&
          session.phase !== "expired" && (
            <div className="official-clock">
              <span
                role="timer"
                aria-label={tx("Time remaining")}
                className={clock < 30 ? "time-urgent" : ""}
              >
                {hideTime ? "" : clockText}
              </span>
              <button
                onClick={() => setHideTime(!hideTime)}
                aria-pressed={hideTime}
              >
                <Icon name={hideTime ? "eye" : "eye-off"} />
                {hideTime ? tx("Show Time") : tx("Hide Time")}
              </button>
            </div>
          )}
      </div>
    </header>
  );
}

// Verbatim task instructions from Pack 1 physical pages 2, 18, 74, 85, 87,
// 90 and 99; Listening navigation from Teacher Practice Test 1 printed page 15.
export function OfficialDirections({ session }: { session: Session }) {
  useI18n();
  const st = session.stage;
  if (!st) return null;
  const reading = st.section === "reading",
    listening = st.section === "listening",
    speaking = st.section === "speaking",
    second = /(?:module\s*2|m2|second|upper|lower)/i.test(
      st.id + " " + st.title,
    ),
    build = /build|sentence/i.test(st.id + " " + st.title),
    discussion = /discussion/i.test(st.id + " " + st.title),
    interview = /interview/i.test(st.id + " " + st.title),
    title = listening
      ? st.title || "Listening"
      : speaking
        ? interview
          ? "Take an Interview"
          : "Listen and Repeat"
        : reading
          ? `Module ${second ? 2 : 1}`
          : build
            ? "Build a Sentence"
            : discussion
              ? "Write for an Academic Discussion"
              : "Write an Email",
    sourceInstructions = st.instructions
      ?.split(/\n\s*\n/)
      .filter(
        (paragraph) =>
          paragraph.trim() &&
          paragraph.trim().toLocaleLowerCase() !== title.toLocaleLowerCase(),
      );
  return (
    <section className="official-directions">
      <h1>
        {reading
          ? tx("Module {number}", { number: second ? 2 : 1 })
          : tx(title)}
      </h1>
      {(listening || speaking) && sourceInstructions?.length ? (
        sourceInstructions.map((paragraph, index) => {
          const lines = paragraph.split("\n").filter((line) => line.trim());
          if (lines.length > 1 && lines.every((line) => line.includes("|"))) {
            const rows = lines.map((line) =>
              line.split("|").map((cell) => cell.trim()),
            );
            return (
              <table lang="en" className="source-directions-table" key={index}>
                <thead>
                  <tr>
                    {rows[0].map((cell, i) => (
                      <th key={i}>{cell}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.slice(1).map((row, i) => (
                    <tr key={i}>
                      {row.map((cell, j) => (
                        <td key={j}>{cell}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            );
          }
          return (
            <p lang="en" key={index}>
              {paragraph}
            </p>
          );
        })
      ) : listening ? (
        <>
          <p>
            {tx(
              "In an actual test, the clock will show you how much time you have to complete each question.",
            )}
          </p>
          <p>{tx("You can use Next to move to the next question.")}</p>
          <p>{tx("You WILL NOT be able to return to previous questions.")}</p>
        </>
      ) : speaking ? (
        <>
          {interview ? (
            <p>
              {tx(
                "An interviewer will ask you questions. Answer the questions and be sure to say as much as you can in the time allowed.",
              )}
            </p>
          ) : (
            <p>
              {tx(
                "You will listen as someone speaks to you. Listen carefully and then repeat what you have heard. The clock will indicate how much time you have to speak.",
              )}
            </p>
          )}
          <p>{tx("No time for preparation will be provided.")}</p>
        </>
      ) : reading ? (
        <>
          <p>
            {tx(
              "The clock will show you how much time you have to complete Module {number}.",
              { number: second ? 2 : 1 },
            )}
          </p>
          {!second && (
            <p>
              {tx(
                "You can use Next and Back to move to the next question or return to previous questions within the same module.",
              )}
            </p>
          )}
          {!second && (
            <p>
              {tx(
                "You WILL NOT be able to return to Module 1 once you have begun Module 2.",
              )}
            </p>
          )}
        </>
      ) : build ? (
        <>
          <p>
            {tx("Move the words in the boxes to create grammatical sentences.")}
          </p>
          <p>
            {tx(
              "A clock will show you how much time you have to complete this task.",
            )}
          </p>
        </>
      ) : discussion ? (
        <>
          <p>
            {tx(
              "A professor has posted a question about a topic and students have responded with their thoughts and ideas. Make a contribution to the discussion.",
            )}
          </p>
          <p>{tx("You will have 10 minutes to write.")}</p>
        </>
      ) : (
        <>
          <p>
            {tx(
              "You will read some information and use the information to write an email.",
            )}
          </p>
          <p>{tx("You will have 7 minutes to write the email.")}</p>
        </>
      )}
      {session.phase === "directions" && <TimingNotice stage={st} />}
    </section>
  );
}

export function TimingNotice({ stage: st }: { stage: Stage }) {
  const { t } = useI18n();
  // Older saved sessions keep their frozen plan; do not infer new evidence.
  if (!st.timingBasis) return null;
  const windows = st.responseWindows || [];
  const displayed = st.section === "speaking" ? windows : [...new Set(windows)];
  const duration =
    st.timer === "shared"
      ? t(
          "{time} shared across this task/module.",
          "本任务／模块共用 {time}。",
          { time: time(st.seconds) },
        )
      : st.timer === "item"
        ? t(
            "Response windows: {times}. The clock starts after the audio ends.",
            "逐题作答时限：{times}。音频结束后开始计时。",
            { times: displayed.map(time).join(" / ") },
          )
        : t(
            "This source-study stage has no countdown.",
            "此资料研读阶段不计时。",
          );
  const basis =
    st.timingBasis === "official"
      ? t("ETS-specified limit", "ETS 明确规定时限")
      : st.timingBasis === "source"
        ? t("Source-configured limit", "题包配置时限")
        : st.timingBasis === "untimed"
          ? t("Untimed source study", "不限时资料研读")
          : t(
              "Local practice setting — exact limit unverified for this sample",
              "本地练习设置——本套样题的精确时限尚未核实",
            );
  return (
    <aside
      className="timing-notice"
      aria-label={t("Timing for this stage", "本阶段计时说明")}
    >
      <strong>{basis}</strong>
      <span>{duration}</span>
      {st.partialModule && (
        <span>
          {t(
            "Selected questions retain the full task/module budget, not a separate official per-question limit.",
            "专项所选题目仍共用完整任务／模块时长，并非官方单题时限。",
          )}
        </span>
      )}
    </aside>
  );
}
