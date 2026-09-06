import { LanguageSwitch, localizeDynamic, useI18n } from "./i18n";
import { examText as tx } from "./locales/exam";
import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import type { Answer, EventInput, Session, Media } from "./types";
import { ORDER, LABELS, taskName, time } from "./api";
import { Button, Modal } from "./components";
import Icon, { sectionIcon } from "./Icons";
import { AnswerInput, StemAssets, StructuredStem } from "./Questions";
import OfficialChrome, { OfficialDirections } from "./OfficialChrome";
import OfficialViewport from "./OfficialViewport";
import { referenceMaterialLayout } from "./reference-material-layout";
import { readingPresentation } from "./reading-presentation";
import {
  saveChunk,
  saveFinalization,
  supportedMime,
  trackRecorder,
  stopRecorders,
  flushRecordings,
} from "./recording";

const DIRECTIONS = {
  reading: [
    "Read each text and answer the questions.",
    "You may use Back, Next and Review within this module. Once you submit a module, you cannot return to it.",
    "The clock runs continuously during the module. Your responses are submitted when time expires.",
  ],
  listening: [
    "Listen carefully. Each recording plays once in strict mode.",
    "The response clock starts after the recording finishes. Each question has its own time limit.",
    "You cannot return to an earlier question. Use paper for notes if you need it.",
  ],
  writing: [
    "Complete the sentence-building tasks, write an email, and contribute to an academic discussion.",
    "The email task is 7 minutes. The academic discussion is 10 minutes. Unused time does not transfer.",
    "Spelling assistance is off. Your responses are automatically saved on this computer.",
  ],
  speaking: [
    "Listen and repeat 7 sentences, then answer 4 interview questions.",
    "There is no preparation time. Recording starts automatically after each prompt finishes.",
    "Speak clearly into your microphone. Recording stops when your response time expires.",
  ],
};
type Props = {
  session: Session;
  stream: MediaStream | null;
  send: (e: EventInput) => Promise<Session | undefined>;
  onLeave: () => void;
  onFinish: () => void;
  onNotice: (s: string) => void;
  offline: boolean;
  offlineReason?: string;
  acquireMic: () => Promise<MediaStream>;
  onFeedback: () => void;
};
export default function Exam({
  session: s,
  stream,
  send,
  onLeave,
  onFinish,
  onNotice,
  offline,
  offlineReason,
  acquireMic,
  onFeedback,
}: Props) {
  useI18n();
  const q = s.question!,
    st = s.stage!,
    [draft, setDraft] = useState<Answer | undefined>(s.answer),
    [review, setReview] = useState(false),
    [modal, setModal] = useState<
      "submit" | "leave" | "help" | "mustAnswer" | null
    >(null),
    [clock, setClock] = useState(Date.now()),
    [busy, setBusy] = useState(false),
    [recordState, setRecordState] = useState(""),
    [saveState, setSaveState] = useState("Saved locally"),
    [manualRecording, setManualRecording] = useState(false),
    [videoFrame, setVideoFrame] = useState<{
      questionId: string;
      url: string;
    } | null>(null);
  const latest = useRef(s),
    draftRef = useRef(draft),
    draftOwner = useRef(s.question?.id),
    dirty = useRef(false),
    saveTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined),
    record = useRef<MediaRecorder | null>(null),
    sendRef = useRef(send),
    noticeRef = useRef(onNotice),
    serverOffset = useRef(s.serverNow - Date.now()),
    lastServerTime = useRef(s.serverNow);
  latest.current = s;
  sendRef.current = send;
  noticeRef.current = onNotice;
  if (lastServerTime.current !== s.serverNow) {
    serverOffset.current = s.serverNow - Date.now();
    lastServerTime.current = s.serverNow;
  }
  const seconds =
    s.deadline === null
      ? s.remainingSeconds
      : Math.min(
          s.remainingSeconds ?? Infinity,
          Math.max(
            0,
            Math.ceil((s.deadline - (clock + serverOffset.current)) / 1000),
          ),
        );
  const disabled =
    busy ||
    offline ||
    s.phase !== "response" ||
    (s.deadline !== null && seconds === 0);
  useEffect(() => {
    const t = setInterval(() => setClock(Date.now()), 100);
    return () => clearInterval(t);
  }, []);
  useLayoutEffect(() => {
    let value = s.answer,
      recovered = false;
    try {
      const backup = JSON.parse(
        localStorage.getItem(`toefl-draft:${s.id}:${s.question?.id}`) || "null",
      );
      if (backup?.value !== undefined) {
        value = backup.value;
        recovered = true;
      }
    } catch {}
    window.scrollTo(0, 0);
    draftOwner.current = s.question?.id;
    setDraft(value);
    draftRef.current = value;
    dirty.current = recovered;
    setManualRecording(false);
    setVideoFrame(null);
    setReview(false);
    setModal(null);
    setSaveState(
      recovered ? "Browser draft recovered · saving…" : "Saved locally",
    );
    clearTimeout(saveTimer.current);
    if (recovered) saveTimer.current = setTimeout(() => void flush(), 100);
  }, [s.question?.id]);
  // Save the exact draft owned by the current question. A late server response
  // must not clear a newer draft or overwrite edits on a different question.
  const flush = useCallback(async () => {
    clearTimeout(saveTimer.current);
    if (!dirty.current || draftRef.current === undefined) return;
    const current = latest.current,
      id = current.question?.id;
    if (!id || current.phase !== "response") return;
    const answer = draftRef.current;
    setSaveState("Saving…");
    const saved = await sendRef.current({
      action: "answer",
      questionId: id,
      answer,
    });
    if (saved) {
      if (answer === draftRef.current && latest.current.question?.id === id) {
        dirty.current = false;
        setSaveState("Saved locally");
        try {
          localStorage.removeItem(`toefl-draft:${current.id}:${id}`);
        } catch {}
      } else if (latest.current.question?.id === id) {
        setSaveState("Saving newer response…");
        clearTimeout(saveTimer.current);
        saveTimer.current = setTimeout(() => void flush(), 100);
      }
    } else setSaveState("Saved in browser · retry needed");
  }, []);
  const change = (value: Answer) => {
    draftRef.current = value;
    setDraft(value);
    dirty.current = true;
    setSaveState("Saving…");
    const current = latest.current;
    try {
      localStorage.setItem(
        `toefl-draft:${s.id}:${q.id}`,
        JSON.stringify({ value, at: Date.now() }),
      );
    } catch {
      onNotice(
        tx("Browser backup storage is full. Keep the local server running."),
      );
    }
    clearTimeout(saveTimer.current);
    const nearDeadline =
      current.deadline !== null &&
      current.deadline - (Date.now() + serverOffset.current) < 2000;
    if (
      q.type === "choice" ||
      q.type === "cloze" ||
      q.type === "build_sentence" ||
      nearDeadline
    )
      void flush();
    else saveTimer.current = setTimeout(() => void flush(), 400);
  };
  useEffect(() => {
    if (s.deadline === null || s.phase !== "response") return;
    const remaining = s.deadline - (Date.now() + serverOffset.current);
    if (remaining <= 0) return;
    const finalFlush = setTimeout(
      () => void flush(),
      Math.max(0, remaining - 150),
    );
    return () => clearTimeout(finalFlush);
  }, [s.deadline, s.phase, flush]);
  useEffect(() => {
    const helpShortcut = (event: KeyboardEvent) => {
      if (
        event.key === "Escape" &&
        !modal &&
        latest.current.phase !== "expired"
      )
        setModal("help");
    };
    window.addEventListener("keydown", helpShortcut);
    return () => window.removeEventListener("keydown", helpShortcut);
  }, [modal]);
  const doAction = async (action: string, index?: number) => {
    if (busy) return;
    if (
      action === "next" &&
      st.section === "listening" &&
      st.timer !== "untimed" &&
      (draftRef.current === undefined ||
        draftRef.current === null ||
        draftRef.current === "" ||
        (Array.isArray(draftRef.current) && draftRef.current.length === 0))
    ) {
      setModal("mustAnswer");
      return;
    }
    setBusy(true);
    try {
      await flush();
      if (
        st.section === "speaking" &&
        st.timer === "untimed" &&
        ["next", "back", "jump"].includes(action)
      ) {
        await stopRecorders();
        setManualRecording(false);
        await flushRecordings();
      }
      await send({ action, questionId: q?.id, index });
    } finally {
      setBusy(false);
    }
  };
  // One recording take per response entry. Each second is persisted as an ordered chunk.
  useEffect(() => {
    if (
      s.phase !== "response" ||
      st.section !== "speaking" ||
      (st.timer === "untimed" && !manualRecording)
    )
      return;
    if (!stream?.active) {
      setRecordState(
        "Microphone unavailable. This response is marked interrupted.",
      );
      void sendRef.current({
        action: "interrupt",
        reason: "microphone-unavailable",
        details: { questionId: q.id },
      });
      return;
    }
    const takeId = crypto.randomUUID(),
      sessionId = s.id,
      questionId = q.id;
    let index = 0,
      stoppedAtDeadline = false;
    try {
      const mime = supportedMime(),
        recorder = new MediaRecorder(
          stream,
          mime ? { mimeType: mime } : undefined,
        );
      record.current = recorder;
      recorder.ondataavailable = (e) => {
        if (e.data.size)
          void saveChunk(
            {
              sessionId,
              questionId,
              takeId,
              index: index++,
              blob: e.data,
              mimeType: recorder.mimeType,
            },
            (message) => noticeRef.current(message),
          );
      };
      recorder.onstop = () => {
        void saveFinalization(
          {
            sessionId,
            questionId,
            takeId,
            segmentCount: index,
            mimeType: recorder.mimeType,
            endedReason:
              st.timer === "untimed"
                ? "user-stop"
                : stoppedAtDeadline ||
                    (s.deadline !== null &&
                      (latest.current.serverNow >= s.deadline ||
                        Date.now() + serverOffset.current >= s.deadline))
                  ? "time-limit"
                  : "stopped-early",
          },
          (message) => noticeRef.current(message),
        );
      };
      recorder.onerror = () => {
        setRecordState("Recording error. The interruption has been saved.");
        void sendRef.current({
          action: "interrupt",
          reason: "recording-error",
          details: { questionId },
        });
      };
      recorder.start(1000);
      trackRecorder(recorder);
      setRecordState("Recording · saved in local segments");
      const stopAtDeadline =
        st.timer === "untimed"
          ? undefined
          : setTimeout(
              () => {
                // The timer itself proves why we stopped. A later server clock
                // synchronization may move the display offset a few ms back;
                // it must not turn a natural deadline into an early-stop event.
                stoppedAtDeadline = true;
                if (recorder.state !== "inactive") recorder.stop();
                setRecordState("Response time finished · saving final segment");
              },
              Math.max(
                0,
                (s.deadline || Date.now()) -
                  (Date.now() + serverOffset.current),
              ),
            );
      return () => {
        clearTimeout(stopAtDeadline);
        if (recorder.state !== "inactive") recorder.stop();
        if (record.current === recorder) record.current = null;
      };
    } catch (error) {
      setRecordState("Could not start recording. Check your microphone.");
      void sendRef.current({
        action: "interrupt",
        reason: "recording-start-failed",
        details: String(error),
      });
    }
  }, [s.id, q?.id, s.phase, st.section, stream, manualRecording]);
  useEffect(() => {
    if (offline) {
      setSaveState(
        offlineReason || "Local server disconnected · timer continues",
      );
    } else if (dirty.current) void flush();
  }, [offline, offlineReason, flush]);
  useEffect(
    () => () => {
      clearTimeout(saveTimer.current);
    },
    [],
  );
  const sectionDirections =
    st.timer === "untimed"
      ? [
          tx(
            "This is untimed supplemental source practice, not a TOEFL iBT 2026 mock exam.",
          ),
          tx(
            "Work with the original material at your own pace. Reference audio may contain explanations or sample answers.",
          ),
          tx(
            "For speaking, use Record and Stop to save your response. There is no automatic official time limit in this mode.",
          ),
        ]
      : DIRECTIONS[st.section].map((text) => tx(text));
  const currentFlag = s.questionMap?.find(
    (i) => i.questionId === q?.id,
  )?.flagged;
  const section = st.section,
    can = s.allowedActions || [],
    has = (action: string) => can.includes(action),
    writing = q && ["email", "academic_discussion"].includes(q.type),
    structured =
      q?.presentationSchema === "structured-v1" &&
      q.structuredContentStatus === "source-verified" &&
      !!q.stemBlocks?.length,
    structuredStem =
      structured && q.stemBlocks!.some((block) => block.type !== "question"),
    discussion = structuredStem && q.type === "academic_discussion",
    audioDiagram = q?.stemBlocks?.some(
      (block) => block.type === "form_diagram",
    ),
    sentenceSelectionInStem =
      structuredStem &&
      q.interaction === "select_sentence" &&
      !!q.choices?.length &&
      q.choices.every((choice) =>
        q.stemBlocks!.some(
          (block) => "text" in block && block.text.includes(choice.text),
        ),
      ),
    split =
      q &&
      !(q.type === "cloze" && q.passageTemplate) &&
      (structuredStem ||
        !!q.passage ||
        !!q.assets?.length ||
        writing ||
        !!q.displayTranscriptDuringPractice);
  const officialStyle =
    st.timer !== "untimed" && !s.examId.startsWith("essentials-");
  const confirmWriting =
    officialStyle &&
    s.phase === "response" &&
    (q?.type === "email" || q?.type === "academic_discussion") &&
    modal === "submit";
  const readingView =
    officialStyle && section === "reading" && q
      ? readingPresentation(q)
      : undefined;
  const mediaTitle =
    section === "speaking"
      ? q?.type === "interview"
        ? tx("Please answer the interviewer's questions.")
        : tx("Listen and repeat only once.")
      : section === "listening"
        ? {
            listen_response: tx("Choose the best response."),
            conversation: tx("Listen to a conversation."),
            announcement: tx("Listen to an announcement."),
            academic_talk: tx("Listen to an academic talk."),
          }[q?.taskType || ""] || tx("Listen carefully.")
        : null;
  const screenHeading =
    mediaTitle ||
    (q?.type === "build_sentence"
      ? tx("Make an appropriate sentence.")
      : readingView?.heading ||
        (q?.type === "cloze" ? q.prompt : tx(taskName(q?.type || ""))));
  const displayQuestion = readingView?.question || q;
  const displayedAnswer =
    s.phase === "expired"
      ? s.answer
      : draftOwner.current === q?.id
        ? draft
        : s.answer;
  const directionAudio = s.phase === "audio" && q?.audio?.kind === "directions";
  const shortResponseAudio =
    officialStyle &&
    s.phase === "audio" &&
    q?.taskType === "listen_response" &&
    !directionAudio &&
    !!q?.choices?.length;
  const hideListeningHeading =
    officialStyle &&
    section === "listening" &&
    s.phase === "response" &&
    q?.taskType !== "listen_response";
  const audioInstructionText =
    officialStyle && s.phase === "audio"
      ? q?.audio?.instructions ||
        (directionAudio &&
        (q?.audio?.scope === "module-directions" || section === "speaking")
          ? st.instructions
          : undefined) ||
        (!st.hasDirectionsAudio &&
        s.stageIndex > 0 &&
        s.questionIndex === 0 &&
        (s.mediaCount || 1) === 1
          ? st.instructions
          : undefined)
      : undefined;
  // Short group labels are already the source task heading above the image.
  const audioInstructions =
    audioInstructionText &&
    !/^Listen to (?:a conversation|an announcement|an academic talk)[.!]?$/i.test(
      audioInstructionText.trim(),
    )
      ? audioInstructionText
      : undefined;
  const materialLayout =
    officialStyle && q ? referenceMaterialLayout(q.id) : undefined;
  const materialVars = materialLayout
    ? ({
        "--material-frame": materialLayout.frameColor,
        "--material-border": materialLayout.borderColor,
        "--material-border-width": `${materialLayout.borderWidthPx}px`,
        "--material-radius": `${materialLayout.borderRadiusPx}px`,
        "--material-font":
          materialLayout.fontFamily === "serif"
            ? '"Times New Roman", Times, serif'
            : "Arial, Helvetica, sans-serif",
        "--material-size": `${materialLayout.fontSizePx}px`,
        "--material-leading": materialLayout.lineHeight,
        "--material-padding": `${materialLayout.framePaddingPx}px`,
        "--material-body-padding": `${materialLayout.bodyPaddingPx}px`,
        "--material-body-radius": `${materialLayout.bodyBorderRadiusPx}px`,
        "--material-body-height": materialLayout.bodyHeightPx
          ? `${materialLayout.bodyHeightPx}px`
          : undefined,
        "--material-width": `${materialLayout.widthPercent}%`,
      } as CSSProperties)
    : undefined;
  return (
    <OfficialViewport active={officialStyle}>
      <div
        className={`exam-shell ${officialStyle ? `official-exam official-section-${section} official-phase-${s.phase} official-${q?.type === "choice" ? q.taskType : q?.type || "directions"}` : ""}`}
      >
        {officialStyle && (
          <OfficialChrome
            session={s}
            seconds={seconds}
            disabled={disabled}
            busy={busy || offline}
            confirmWriting={confirmWriting}
            onHelp={() => setModal("help")}
            onReview={() => setReview(!review)}
            onBack={() =>
              confirmWriting ? setModal(null) : void doAction("back")
            }
            onNext={() =>
              confirmWriting
                ? void doAction("next")
                : section !== "listening" &&
                    s.questionIndex === st.questionCount - 1
                  ? setModal("submit")
                  : void doAction("next")
            }
            onBegin={() => void doAction("begin")}
            onPause={() =>
              void doAction(s.phase === "paused" ? "resume" : "pause")
            }
          />
        )}
        {!officialStyle && (
          <>
            <header className="exam-header">
              <div className="exam-brand">
                <div className="brand-icon">T</div>
                <div>
                  <strong>
                    {tx(LABELS[section])}{" "}
                    <span className="muted">/ {tx(st.title)}</span>
                  </strong>
                  <small>
                    {localizeDynamic(s.title)} ·{" "}
                    {st.timer === "untimed"
                      ? tx("UNTIMED SUPPLEMENTAL PRACTICE")
                      : s.mode === "strict"
                        ? tx("STRICT LOCAL PRACTICE")
                        : tx("GUIDED PRACTICE")}
                  </small>
                </div>
              </div>
              <div className="exam-controls">
                <LanguageSwitch />
                <div
                  className={`timer-box ${seconds !== null && seconds < 30 ? "urgent" : ""}`}
                >
                  <Icon name="clock" />
                  <div>
                    <small>
                      {st.timer === "untimed"
                        ? tx("UNTIMED PRACTICE")
                        : s.phase === "audio"
                          ? tx("LISTENING · TIMER WAITS")
                          : s.phase === "directions"
                            ? tx("DIRECTIONS")
                            : s.phase === "paused"
                              ? tx("PRACTICE PAUSED")
                              : st.timer === "shared"
                                ? tx("MODULE TIME LEFT")
                                : tx("RESPONSE TIME LEFT")}
                    </small>
                    <b
                      className="mono"
                      role="timer"
                      aria-label={tx("Time remaining")}
                    >
                      {time(seconds)}
                    </b>
                  </div>
                </div>
                {s.mode === "practice" && (
                  <Button
                    kind="small"
                    onClick={() =>
                      void doAction(s.phase === "paused" ? "resume" : "pause")
                    }
                    disabled={
                      busy || offline || (!has("pause") && !has("resume"))
                    }
                    aria-label={
                      s.phase === "paused" ? tx("Resume") : tx("Pause")
                    }
                  >
                    <Icon name={s.phase === "paused" ? "play" : "pause"} />
                  </Button>
                )}
                <Button
                  kind="small"
                  onClick={() => setModal("help")}
                  aria-label={tx("Help")}
                >
                  <Icon name="info" />
                  <span className="label">{tx("Help")}</span>
                </Button>
                <Button
                  kind="small"
                  onClick={() => setModal("leave")}
                  aria-label={tx("Leave practice")}
                >
                  <Icon name="close" />
                  <span className="label">{tx("Save & Exit")}</span>
                </Button>
              </div>
            </header>
            <nav className="exam-progress" aria-label={tx("Section progress")}>
              {ORDER.map((id, i) => (
                <div
                  key={id}
                  className={`progress-section ${section === id ? "current" : ORDER.indexOf(id) < ORDER.indexOf(section) ? "done" : ""}`}
                >
                  <span className="progress-index">{i + 1}</span>
                  {tx(LABELS[id])}
                </div>
              ))}
            </nav>
          </>
        )}
        {offline && (
          <div className="connection-banner" role="alert">
            {offlineReason ||
              tx(
                "Local server disconnected. Your response is backed up in this browser. Reconnect to continue; strict timers keep running.",
              )}
          </div>
        )}
        <main
          className={`exam-content ${confirmWriting ? "writing-confirmation-open" : ""}`}
        >
          {confirmWriting && (
            <section className="official-directions official-writing-confirmation">
              <h1>{tx("Time Remaining")}</h1>
              <p>
                {tx(
                  "You still have time to respond. As long as there is time remaining, you can keep writing or revise your response.",
                )}
              </p>
              <p>{tx("Select Back to keep writing or revising.")}</p>
              <p>{tx("Select Continue to leave this question.")}</p>
              <p>
                {tx(
                  "Once you leave this question, you WILL NOT be able to return to it.",
                )}
              </p>
            </section>
          )}
          {s.phase === "directions" ? (
            officialStyle ? (
              <OfficialDirections session={s} />
            ) : (
              <section className="direction-card">
                <div className="big-icon">
                  <Icon name={sectionIcon(section)} />
                </div>
                <div className="eyebrow muted">{tx("SECTION DIRECTIONS")}</div>
                <h1 style={{ marginTop: 13 }}>{tx(st.title)}</h1>
                <ul>
                  {sectionDirections.map((d) => (
                    <li key={d}>{d}</li>
                  ))}
                </ul>
                {st.instructions && (
                  <p lang="en" style={{ whiteSpace: "pre-wrap" }}>
                    {st.instructions}
                  </p>
                )}
                {st.directionsAudio && (
                  <PromptMedia
                    media={st.directionsAudio}
                    onEnded={() => {}}
                    onError={() =>
                      onNotice(tx("Task directions audio could not play."))
                    }
                    label={tx("Task directions")}
                  />
                )}
                <div className="direction-meta">
                  <div>
                    <b>
                      {st.timer === "untimed"
                        ? tx("Untimed")
                        : st.timer === "shared"
                          ? time(st.seconds)
                          : tx("Per question")}
                    </b>
                    <span>{tx("RESPONSE TIMER")}</span>
                  </div>
                  <div>
                    <b>{st.questionCount}</b>
                    <span>{tx("QUESTION SCREENS")}</span>
                  </div>
                  <div>
                    <b>{s.mode === "strict" ? tx("Strict") : tx("Guided")}</b>
                    <span>{tx("LOCAL PRACTICE")}</span>
                  </div>
                </div>
                <p style={{ fontSize: 11 }}>
                  {tx(
                    "Directions are untimed. Your local timing profile is frozen for this session. This practice does not reproduce ETS’s proprietary adaptive algorithm or score scale.",
                  )}
                </p>
                {section === "speaking" && !stream?.active && (
                  <Button
                    kind="outline"
                    onClick={() =>
                      void acquireMic().catch((e) => onNotice(e.message))
                    }
                  >
                    {tx("Connect microphone")}
                  </Button>
                )}
              </section>
            )
          ) : s.phase === "paused" ? (
            <section className="direction-card">
              <div className="big-icon">
                <Icon name="pause" />
              </div>
              <h1>{tx("Practice paused")}</h1>
              <p>
                {tx(
                  "Pause is available only in guided practice. Resume when you are ready.",
                )}
              </p>
              <Button onClick={() => void doAction("resume")}>
                {tx("Resume practice")}
                <Icon name="play" />
              </Button>
            </section>
          ) : q ? (
            <>
              <div
                hidden={hideListeningHeading}
                className={`exam-question-heading ${officialStyle && (writing || audioInstructions) ? "official-writing-heading" : ""}`}
              >
                <h2
                  lang={
                    officialStyle &&
                    !mediaTitle &&
                    q.type !== "build_sentence" &&
                    (readingView?.heading || q.type === "cloze")
                      ? "en"
                      : undefined
                  }
                >
                  {officialStyle ? screenHeading : tx(taskName(q.type))}
                </h2>
                <span className="question-number">
                  {tx("Question {number}", {
                    number: `${q.number || s.questionIndex + 1}${q.numberEnd ? `–${q.numberEnd}` : ""}`,
                  })}{" "}
                  <span style={{ color: "#b3bba5" }}>
                    ·{" "}
                    {tx("Screen {current} / {total}", {
                      current: s.questionIndex + 1,
                      total: st.questionCount,
                    })}
                  </span>
                </span>
              </div>
              {st.timer === "untimed" && !!q.practiceMediaSequence?.length && (
                <div className="panel supplemental-audio">
                  <div className="pane-label">
                    {tx("Original question media · untimed practice")}
                  </div>
                  {q.practiceMediaSequence.map((media, index) => (
                    <ReferenceMedia
                      key={`${q.id}:${media.url}`}
                      media={media}
                      label={tx("Original prompt {number}", {
                        number: index + 1,
                      })}
                    />
                  ))}
                </div>
              )}
              {st.timer === "untimed" &&
                (Array.isArray(st.practiceAudio)
                  ? st.practiceAudio.length > 0
                  : !!st.practiceAudio) && (
                  <details className="panel supplemental-audio">
                    <summary className="pane-label">
                      {tx("Full reference track · may include examples")}
                    </summary>
                    {(Array.isArray(st.practiceAudio)
                      ? st.practiceAudio
                      : st.practiceAudio
                        ? [st.practiceAudio]
                        : []
                    ).map((media) => (
                      <ReferenceMedia
                        key={media.url}
                        media={media}
                        label={tx("Supplemental reference track")}
                      />
                    ))}
                  </details>
                )}
              {s.phase === "audio" ? (
                <div
                  className={`question-layout single official-audio-layout ${shortResponseAudio ? "official-short-response-audio" : ""}`}
                >
                  <div className="question-pane">
                    <div className="audio-stage">
                      {!officialStyle && !q.assets?.length && !audioDiagram && (
                        <div className="audio-ring">
                          <Icon
                            name={section === "speaking" ? "mic" : "headphones"}
                          />
                        </div>
                      )}
                      {!officialStyle && (
                        <>
                          <h3>{tx("Listen carefully.")}</h3>
                          <p>
                            {q.type === "listen_repeat"
                              ? tx(
                                  "Repeat what you hear when recording begins.",
                                )
                              : q.type === "interview"
                                ? tx(
                                    "Answer the interviewer when recording begins.",
                                  )
                                : tx(
                                    "You will answer the question after the recording.",
                                  )}
                          </p>
                        </>
                      )}
                      {audioInstructions && (
                        <OfficialDirections
                          session={{
                            ...s,
                            stage: { ...st, instructions: audioInstructions },
                          }}
                        />
                      )}
                      {!audioInstructions && audioDiagram && (
                        <StructuredStem question={q} />
                      )}
                      {q.context && (
                        <p
                          lang="en"
                          style={{ whiteSpace: "pre-wrap", textAlign: "left" }}
                        >
                          {q.context}
                        </p>
                      )}
                      {!!q.assets?.length && (
                        <div className="audio-context-visual">
                          <StemAssets question={q} />
                        </div>
                      )}
                      {q.audio ? (
                        <PromptMedia
                          key={`${q.id}:${s.mediaIndex || 0}:${q.audio.url}`}
                          media={q.audio}
                          label={tx("Question audio")}
                          onVideoFrame={(url) =>
                            setVideoFrame({ questionId: q.id, url })
                          }
                          onStarted={() =>
                            void send({
                              action: "audio-started",
                              questionId: q.id,
                              mediaIndex: s.mediaIndex,
                            })
                          }
                          onEnded={() =>
                            void send({
                              action: "audio-ended",
                              questionId: q.id,
                              mediaIndex: s.mediaIndex,
                            })
                          }
                          onError={() =>
                            void send({
                              action: "interrupt",
                              reason: "media-error",
                              details: { questionId: q.id },
                            })
                          }
                        />
                      ) : (
                        <p className="error-message">
                          {tx(
                            "No verified audio is available for this question.",
                          )}
                        </p>
                      )}
                      {!officialStyle && (
                        <>
                          <Wave />
                          <p>
                            {tx(
                              "Audio plays once · response clock starts afterwards",
                            )}
                          </p>
                        </>
                      )}
                    </div>
                  </div>
                  {shortResponseAudio && (
                    <section className="answer-pane">
                      <AnswerInput
                        question={q}
                        value={undefined}
                        onChange={() => {}}
                        disabled
                        strict={s.mode === "strict"}
                        examStyle
                      />
                    </section>
                  )}
                </div>
              ) : officialStyle && section === "speaking" ? (
                <div className="official-speaking-response">
                  <div className="official-speaking-visual">
                    {q.assets?.length ? (
                      <StemAssets question={q} />
                    ) : videoFrame?.questionId === q.id ? (
                      <img
                        className="stem-image"
                        src={videoFrame.url}
                        alt={tx("Last frame of the original interviewer video")}
                      />
                    ) : null}
                  </div>
                  <div className="official-response-clock">
                    <strong>{tx("RESPONSE TIME")}</strong>
                    <div>
                      <Icon name="mic" />
                      <b role="timer" aria-label={tx("Time remaining")}>
                        {seconds === null ? "—:—" : `00:${time(seconds)}`}
                      </b>
                    </div>
                  </div>
                  <p className="sr-only" role="status">
                    {tx(recordState)}
                  </p>
                  {!stream?.active && (
                    <Button
                      kind="outline"
                      onClick={() =>
                        void acquireMic().catch((error) =>
                          onNotice(String(error)),
                        )
                      }
                    >
                      {tx("Reconnect microphone")}
                    </Button>
                  )}
                </div>
              ) : officialStyle && q.type === "build_sentence" ? (
                <div
                  className={`official-build ${q.assets?.length ? "" : "without-portraits"}`}
                >
                  <div className="official-build-prompt" lang="en">
                    {q.assets?.[0] && (
                      <img
                        src={q.assets[0].url}
                        alt={q.assets[0].alt || tx("Source speaker portrait")}
                      />
                    )}
                    <p>
                      {q.context ||
                        q.stemBlocks
                          ?.filter((block) => block.type === "paragraph")
                          .map((block) => ("text" in block ? block.text : ""))
                          .join("\n")}
                    </p>
                  </div>
                  <div className="official-build-answer">
                    {q.assets?.[1] && (
                      <img
                        src={q.assets[1].url}
                        alt={
                          q.assets[1].alt || tx("Source respondent portrait")
                        }
                      />
                    )}
                    <AnswerInput
                      question={q}
                      value={displayedAnswer}
                      onChange={change}
                      disabled={disabled}
                      strict={s.mode === "strict"}
                    />
                  </div>
                </div>
              ) : (
                <div
                  className={`question-layout ${discussion ? "academic-discussion-layout" : !split || q.sourceImageContainsQuestionAndChoices || section !== "listening" ? "single" : ""}`}
                >
                  {split && (
                    <section
                      className="question-pane"
                      style={materialVars}
                      data-reference-kind={materialLayout?.kind}
                      data-reference-theme={materialLayout?.theme}
                      data-reference-header={materialLayout?.headerStyle}
                      data-reference-scroll={materialLayout?.bodyScroll}
                    >
                      <div className="pane-label">
                        {q.displayTranscriptDuringPractice
                          ? tx("Source transcript · no matching original audio")
                          : section === "speaking"
                            ? tx("Speaking prompt")
                            : section === "listening"
                              ? tx("Listening context")
                              : writing
                                ? tx("Writing task")
                                : q.type === "build_sentence"
                                  ? tx("Original question")
                                  : tx("Reading material")}
                      </div>
                      {structuredStem ? (
                        <StructuredStem
                          question={displayQuestion}
                          value={displayedAnswer}
                          onChange={change}
                          disabled={disabled}
                          discussionPart={discussion ? "professor" : undefined}
                          displayPart={
                            officialStyle && q.type === "email"
                              ? "email-prompt"
                              : undefined
                          }
                        />
                      ) : q.assets?.length &&
                        !q.displayTranscriptDuringPractice ? (
                        <StemAssets question={q} />
                      ) : (
                        <div className="passage" lang="en">
                          {q.passage ||
                            (q.displayTranscriptDuringPractice
                              ? q.transcript
                              : writing
                                ? q.prompt
                                : "")}
                        </div>
                      )}
                    </section>
                  )}
                  <section
                    className={`answer-pane ${discussion ? "discussion-response-pane" : ""}`}
                  >
                    {discussion && (
                      <StructuredStem
                        question={q}
                        value={displayedAnswer}
                        onChange={change}
                        disabled={disabled}
                        discussionPart="students"
                      />
                    )}
                    {officialStyle && q.type === "email" && (
                      <StructuredStem
                        question={q}
                        displayPart="email-response"
                      />
                    )}
                    <div
                      className="pane-label"
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                      }}
                    >
                      <span>
                        {writing
                          ? tx("Your response")
                          : tx("Question & response")}
                      </span>
                      {st.canBack && (
                        <button
                          onClick={() =>
                            void send({ action: "flag", questionId: q.id })
                          }
                          aria-label={tx("Flag question")}
                          style={{ color: currentFlag ? "#b18b47" : "inherit" }}
                        >
                          <Icon name="flag" />
                        </button>
                      )}
                    </div>
                    {!writing && (
                      <div
                        className="prompt"
                        lang={q.type === "build_sentence" ? undefined : "en"}
                      >
                        {q.type === "build_sentence"
                          ? tx("Make an appropriate sentence.")
                          : q.prompt}
                      </div>
                    )}
                    {!sentenceSelectionInStem && (
                      <AnswerInput
                        key={q.id}
                        question={q}
                        value={displayedAnswer}
                        onChange={change}
                        disabled={disabled}
                        strict={s.mode === "strict"}
                        examStyle={officialStyle}
                      />
                    )}
                    {section === "speaking" && (
                      <div className="audio-stage">
                        <div className="audio-ring">
                          <Icon name="mic" />
                        </div>
                        <h3>
                          {st.timer === "untimed" && !manualRecording
                            ? tx("Record your response.")
                            : tx("Speak now.")}
                        </h3>
                        {(st.timer !== "untimed" || manualRecording) && (
                          <Wave />
                        )}
                        {st.timer === "untimed" && (
                          <div style={{ margin: "15px 0" }}>
                            <Button
                              kind={manualRecording ? "outline" : "primary"}
                              onClick={async () => {
                                if (manualRecording) {
                                  await stopRecorders();
                                  setManualRecording(false);
                                  setRecordState(
                                    "Recording saved in local segments",
                                  );
                                } else {
                                  await acquireMic();
                                  setManualRecording(true);
                                }
                              }}
                            >
                              {manualRecording
                                ? tx("Stop recording")
                                : tx("Record response")}
                              <Icon name={manualRecording ? "pause" : "mic"} />
                            </Button>
                          </div>
                        )}
                        <div className="recording-message" role="status">
                          {(st.timer !== "untimed" || manualRecording) && (
                            <i className="recording-dot" />
                          )}
                          {tx(recordState || "Ready when you are.")}
                        </div>
                        {!stream?.active && (
                          <Button
                            kind="outline small"
                            onClick={() =>
                              void acquireMic().catch((error) =>
                                onNotice(error.message),
                              )
                            }
                          >
                            {tx("Reconnect microphone")}
                          </Button>
                        )}
                        <p>
                          {st.timer === "untimed"
                            ? tx(
                                "This supplemental task has no official iBT countdown. Stop recording before moving on.",
                              )
                            : tx(
                                "Recording stops automatically when time expires.",
                              )}
                        </p>
                      </div>
                    )}
                    {s.mode === "practice" && (
                      <div
                        style={{
                          display: "flex",
                          gap: 8,
                          marginTop: 20,
                          flexWrap: "wrap",
                        }}
                      >
                        {has("replay") && (
                          <Button
                            kind="outline small"
                            onClick={() => void doAction("replay")}
                          >
                            {tx("Replay audio")}
                          </Button>
                        )}
                        <Button
                          kind="outline small"
                          onClick={async () => {
                            await flush();
                            onFeedback();
                          }}
                        >
                          {tx("Check answer & explanation")}
                        </Button>
                      </div>
                    )}
                  </section>
                </div>
              )}
              {review && st.canBack && (
                <div className="panel" style={{ marginTop: 20 }}>
                  <div className="eyebrow muted">{tx("THIS MODULE ONLY")}</div>
                  <div className="question-map">
                    {s.questionMap?.map((item) => (
                      <button
                        key={item.questionId}
                        disabled={busy || offline}
                        onClick={() => void doAction("jump", item.index)}
                        aria-label={tx("Go to screen {number}", {
                          number: item.index + 1,
                        })}
                        className={`${item.answered ? "answered" : ""} ${item.index === s.questionIndex ? "current" : ""} ${item.flagged ? "flagged" : ""}`}
                      >
                        {item.index + 1}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : null}
        </main>
        {!officialStyle && (
          <footer className="exam-footer">
            <div className="save-status">
              <Icon name="shield" />
              <span aria-live="polite">{tx(saveState)}</span>
            </div>
            <div className="footer-actions">
              {s.phase === "directions" ? (
                <Button
                  disabled={offline || busy}
                  onClick={async () => {
                    if (section === "speaking") await acquireMic();
                    await doAction("begin");
                  }}
                >
                  {tx("Begin {section}", { section: tx(LABELS[section]) })}
                  <Icon name="arrow" />
                </Button>
              ) : s.phase === "response" ? (
                <>
                  {st.canBack && (
                    <Button kind="outline" onClick={() => setReview(!review)}>
                      {tx("Review")}
                    </Button>
                  )}
                  {st.canBack && (
                    <Button
                      kind="outline"
                      disabled={disabled || !has("back")}
                      onClick={() => void doAction("back")}
                    >
                      <Icon name="back" />
                      {tx("Back")}
                    </Button>
                  )}
                  {section === "speaking" && st.timer !== "untimed" ? (
                    <span className="pill amber">
                      {tx("Recording · auto-submit")}
                    </span>
                  ) : (
                    <Button
                      disabled={disabled || !has("next")}
                      onClick={() =>
                        s.questionIndex === st.questionCount - 1
                          ? setModal("submit")
                          : void doAction("next")
                      }
                    >
                      {s.questionIndex === st.questionCount - 1
                        ? tx("Submit")
                        : tx("Next")}
                      <Icon name="arrow" />
                    </Button>
                  )}
                </>
              ) : null}
            </div>
          </footer>
        )}
        {s.phase === "expired" && (
          <Modal
            className="official-time-expired"
            onClose={() => {}}
            actions={
              <Button
                disabled={busy || offline || !has("continue")}
                onClick={() => void doAction("continue")}
              >
                {tx("Continue")}
              </Button>
            }
          >
            <h2>
              <Icon name="info" />
              {tx("Writing Time Expired")}
            </h2>
            <p>{tx("Your time for answering this question has ended.")}</p>
          </Modal>
        )}
        {modal && !confirmWriting && s.phase !== "expired" && (
          <Modal
            onClose={() => setModal(null)}
            actions={
              modal === "mustAnswer" ? (
                <Button onClick={() => setModal(null)}>
                  {tx("Return to Question")}
                </Button>
              ) : modal === "help" ? (
                <>
                  {officialStyle && (
                    <Button kind="outline" onClick={() => setModal("leave")}>
                      {tx("Save & Exit")}
                    </Button>
                  )}
                  <Button onClick={() => setModal(null)}>{tx("Close")}</Button>
                </>
              ) : modal === "submit" ? (
                <>
                  <Button kind="outline" onClick={() => setModal(null)}>
                    {tx("Keep working")}
                  </Button>
                  <Button
                    onClick={() => {
                      setModal(null);
                      void doAction("next");
                    }}
                  >
                    {tx("Submit")}
                  </Button>
                </>
              ) : (
                <>
                  <Button kind="outline" onClick={() => setModal(null)}>
                    {tx("Keep working")}
                  </Button>
                  <Button
                    kind="outline"
                    onClick={async () => {
                      await flush();
                      record.current?.state === "recording" &&
                        record.current.stop();
                      setModal(null);
                      onFinish();
                    }}
                  >
                    {tx("End & review")}
                  </Button>
                  <Button
                    onClick={async () => {
                      await flush();
                      record.current?.state === "recording" &&
                        record.current.stop();
                      setModal(null);
                      onLeave();
                    }}
                  >
                    {tx("Save & leave")}
                  </Button>
                </>
              )
            }
          >
            {modal === "mustAnswer" ? (
              <>
                <h2>{tx("Must Answer")}</h2>
                <p>
                  {tx(
                    "You must enter an answer before you can leave this question.",
                  )}
                </p>
              </>
            ) : modal === "help" ? (
              <>
                <h2>
                  {tx("{section} · Help", { section: tx(LABELS[section]) })}
                </h2>
                <ul>
                  {sectionDirections.map((d) => (
                    <li key={d} style={{ fontSize: 13, lineHeight: 1.8 }}>
                      {d}
                    </li>
                  ))}
                </ul>
                <div className="warning-list">
                  {tx(
                    "The response timer keeps running while this window is open.",
                  )}
                </div>
              </>
            ) : modal === "submit" ? (
              <>
                <h2>{tx("Submit this task?")}</h2>
                <p>
                  {tx(
                    "You cannot return after submission. Unanswered items remain blank, and unused time does not transfer.",
                  )}
                </p>
              </>
            ) : (
              <>
                <h2>{tx("Leave this practice?")}</h2>
                <p>
                  {tx(
                    "Strict response timers keep running after you leave. Leaving during audio or recording marks this session as interrupted. Completed recording segments are preserved.",
                  )}
                </p>
              </>
            )}
          </Modal>
        )}
      </div>
    </OfficialViewport>
  );
}
function Wave() {
  return (
    <div className="waveform" aria-hidden="true">
      {Array.from({ length: 19 }, (_, i) => (
        <i key={i} />
      ))}
    </div>
  );
}
function PromptMedia({
  media,
  onEnded,
  onError,
  onStarted,
  label,
  onVideoFrame,
}: {
  media: Media;
  onEnded: () => void;
  onError: () => void;
  onStarted?: () => void;
  label: string;
  onVideoFrame?: (url: string) => void;
}) {
  useI18n();
  const ref = useRef<HTMLMediaElement | null>(null),
    [blocked, setBlocked] = useState(false),
    [failed, setFailed] = useState(false),
    [stalled, setStalled] = useState(false),
    [volume, setVolume] = useState(() => {
      const stored = Number(
        sessionStorage.getItem("toefl-exam-volume") || "0.8",
      );
      return Number.isFinite(stored) ? Math.min(1, Math.max(0, stored)) : 0.8;
    }),
    endRef = useRef(onEnded),
    errorRef = useRef(onError),
    started = useRef(false),
    alive = useRef(true),
    reportedInterruption = useRef(false),
    stallTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  endRef.current = onEnded;
  errorRef.current = onError;
  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    alive.current = true;
    element.volume = volume;
    element.play().catch(() => setBlocked(true));
    return () => {
      alive.current = false;
      clearTimeout(stallTimer.current);
      element.pause();
    };
  }, [media.url]);
  const reportInterruption = () => {
    if (!alive.current || reportedInterruption.current) return;
    reportedInterruption.current = true;
    errorRef.current();
  };
  const watchStall = () => {
    if (!started.current || !alive.current) return;
    clearTimeout(stallTimer.current);
    stallTimer.current = setTimeout(() => {
      if (
        alive.current &&
        !ref.current?.ended &&
        (ref.current?.readyState || 0) < 3
      ) {
        setStalled(true);
        reportInterruption();
      }
    }, 3000);
  };
  const props = {
    src: media.url,
    preload: "auto",
    onEnded: () => {
      clearTimeout(stallTimer.current);
      const video = ref.current;
      if (
        video instanceof HTMLVideoElement &&
        video.videoWidth &&
        video.videoHeight &&
        onVideoFrame
      ) {
        // Retain this already-authorized source frame during the response;
        // there is no replay and no image borrowed from a different question.
        try {
          const canvas = document.createElement("canvas");
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          const context = canvas.getContext("2d");
          if (context) {
            context.drawImage(video, 0, 0);
            onVideoFrame(canvas.toDataURL("image/png"));
          }
        } catch {
          /* A frame failure must never postpone the response clock. */
        }
      }
      endRef.current();
    },
    onError: () => {
      setFailed(true);
      setBlocked(true);
      reportInterruption();
    },
    onWaiting: watchStall,
    onStalled: watchStall,
    onPlaying: () => {
      clearTimeout(stallTimer.current);
      setStalled(false);
      setBlocked(false);
      if (!started.current) {
        started.current = true;
        onStarted?.();
      }
    },
    "aria-label": label,
  };
  return (
    <>
      <div className="media-mount">
        {media.mediaType === "video" ? (
          <video
            {...props}
            ref={(e) => {
              ref.current = e;
            }}
            playsInline
          />
        ) : (
          <audio
            {...props}
            ref={(e) => {
              ref.current = e;
            }}
          />
        )}
      </div>
      {stalled && (
        <p className="error-message">
          {tx(
            "Audio playback stalled. The interruption is recorded; your response timer has not started.",
          )}
        </p>
      )}
      {blocked && (
        <>
          <p>
            {failed
              ? tx("Audio could not load. Check your local server and retry.")
              : tx("Your browser requires a click before playing audio.")}
          </p>
          <Button
            kind="outline"
            onClick={() => {
              if (failed) {
                ref.current?.load();
                setFailed(false);
              }
              ref.current?.play().catch(() => setBlocked(true));
            }}
          >
            {tx("Play audio")}
            <Icon name="play" />
          </Button>
        </>
      )}
      <label className="field" style={{ maxWidth: 190, margin: "20px auto 0" }}>
        {tx("Volume")}
        <input
          type="range"
          min="0"
          max="1"
          step="0.05"
          value={volume}
          onChange={(e) => {
            const v = Number(e.target.value);
            setVolume(v);
            if (ref.current) ref.current.volume = v;
          }}
          aria-label={tx("Playback volume")}
        />
      </label>
    </>
  );
}
function ReferenceMedia({ media, label }: { media: Media; label: string }) {
  useI18n();
  const ref = useRef<HTMLMediaElement | null>(null);
  useEffect(() => {
    const node = ref.current;
    return () => node?.pause();
  }, [media.url]);
  return media.mediaType === "video" ? (
    <video
      ref={(node) => {
        ref.current = node;
      }}
      src={media.url}
      controls
      preload="metadata"
      aria-label={label}
    />
  ) : (
    <audio
      ref={(node) => {
        ref.current = node;
      }}
      src={media.url}
      controls
      preload="metadata"
      aria-label={label}
    />
  );
}
