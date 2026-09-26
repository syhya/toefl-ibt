import { tr, useI18n, LanguageSwitch, localizeDynamic } from "./i18n";
import { useCallback, useEffect, useId, useRef, useState } from "react";
import type {
  Answer,
  Catalog,
  EventInput,
  Exam as ExamInfo,
  Question,
  Review,
  Session,
  SessionSummary,
  Timing,
} from "./types";
import {
  api,
  ApiError,
  post,
  sendEvent,
  ORDER,
  LABELS,
  sectionLabel,
} from "./api";
import {
  Button,
  Empty,
  Home,
  History,
  Layout,
  Library,
  Modal,
  Notice,
} from "./components";
import { Feedback, ReviewPage, Rules, Settings, Validation } from "./pages";
import Exam, { type ReferencePlayback } from "./Exam";
import QuestionLibrary, {
  practiceGroupTaskName,
  type PracticeGroup,
  type QuestionItem,
} from "./QuestionLibrary";
import Icon from "./Icons";
import Mistakes from "./Mistakes";
import VocabularyPage, {
  VocabularyEntryDialog,
  type VocabularyDraft,
} from "./Vocabulary";
import GettingStarted from "./GettingStarted";
import { loadTimingSettings, saveTimingSettings } from "./timing";
import {
  flushRecordings,
  pendingRecordings,
  retryRecordings,
  supportedMime,
  stopRecorders,
} from "./recording";

export default function App() {
  useI18n();
  const [catalog, setCatalog] = useState<Catalog | null>(null),
    [sessions, setSessions] = useState<SessionSummary[]>([]),
    [session, setSession] = useState<Session | null>(null),
    [review, setReview] = useState<Review | null>(null),
    [page, setPage] = useState("home"),
    [selected, setSelected] = useState<ExamInfo | null>(null),
    [timing, setTiming] = useState<Timing>(loadTimingSettings),
    [toast, setToast] = useState(""),
    [fatal, setFatal] = useState(""),
    [offline, setOffline] = useState(false),
    [offlineReason, setOfflineReason] = useState(""),
    [stream, setStream] = useState<MediaStream | null>(null),
    [feedback, setFeedback] = useState<{
      question: Question;
      answer?: Answer;
      grade?: unknown;
    } | null>(null),
    [wrongIds, setWrongIds] = useState<string[] | undefined>(),
    [pendingAudio, setPendingAudio] = useState(0),
    [selectedScope, setSelectedScope] = useState("all"),
    [selectionLabel, setSelectionLabel] = useState("");
  const [vocabularyDraft, setVocabularyDraft] =
    useState<VocabularyDraft | null>(null);
  const [selectedGroup, setSelectedGroup] = useState<PracticeGroup | null>(
    null,
  );
  // Leaving the exam keeps the one-pass state of untimed original audio.
  const referencePlayback = useRef(new Map<string, ReferencePlayback>());
  const [audioRecoveryTarget, setAudioRecoveryTarget] =
    useState<Session | null>(null);
  const [audioRecoveryBusy, setAudioRecoveryBusy] = useState(false);
  const [audioRecoveryError, setAudioRecoveryError] = useState("");
  const active = useRef<Session | null>(null),
    pageRef = useRef(page),
    streamRef = useRef<MediaStream | null>(null),
    lockRelease = useRef<(() => void) | null>(null),
    eventQueue = useRef<Promise<unknown>>(Promise.resolve()),
    pendingEvents = useRef(0),
    polling = useRef(false),
    reviewLoading = useRef(false),
    wantedSession = useRef<string | null>(null),
    micEpoch = useRef(0),
    micPromise = useRef<Promise<MediaStream> | null>(null),
    lastPollAt = useRef(Date.now());
  active.current = session;
  pageRef.current = page;
  streamRef.current = stream;
  const notice = useCallback((text: string) => setToast(text), []);
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [page]);
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(""), 6000);
    return () => clearTimeout(t);
  }, [toast]);
  const refreshHistory = useCallback(async () => {
    const data = await api<{ sessions: SessionSummary[] }>("/api/sessions");
    setSessions(data.sessions);
  }, []);
  const apply = useCallback((next: Session, force = false) => {
    if (force) wantedSession.current = next.id;
    if (wantedSession.current !== next.id) return;
    setSession((old) =>
      old?.id === next.id && old.revision > next.revision ? old : next,
    );
    setOffline(false);
    setOfflineReason("");
  }, []);
  const send = useCallback(
    async (input: EventInput): Promise<Session | undefined> => {
      const id = active.current?.id;
      if (!id) return;
      pendingEvents.current++;
      const operation = eventQueue.current
        .catch(() => {})
        .then(async () => {
          try {
            const next = await sendEvent(id, input);
            apply(next);
            return next;
          } catch (error) {
            if (error instanceof ApiError && error.session)
              apply(error.session);
            if (!(error instanceof ApiError) || error.status === 403) {
              setOffline(true);
              setOfflineReason(error instanceof ApiError ? error.message : "");
            }
            notice(error instanceof Error ? error.message : String(error));
            return undefined;
          } finally {
            pendingEvents.current--;
          }
        });
      eventQueue.current = operation;
      return operation;
    },
    [apply, notice],
  );
  const release = useCallback(() => {
    micEpoch.current++;
    micPromise.current = null;
    if (lockRelease.current) {
      lockRelease.current();
      lockRelease.current = null;
    }
    streamRef.current?.getTracks().forEach((t) => t.stop());
    setStream(null);
  }, []);
  const acquireLock = useCallback(async (id: string) => {
    if (lockRelease.current) {
      lockRelease.current();
      lockRelease.current = null;
    }
    if (!navigator.locks) return;
    await new Promise<void>((resolve, reject) => {
      navigator.locks
        .request(
          `toefl-local-session:${id}`,
          { ifAvailable: true },
          async (lock) => {
            if (!lock) {
              reject(
                new Error(
                  tr(
                    "This practice is open in another tab. Close that tab first.",
                    "该练习已在另一个标签页打开。请先关闭另一页。",
                  ),
                ),
              );
              return;
            }
            await new Promise<void>((done) => {
              lockRelease.current = done;
              resolve();
            });
          },
        )
        .catch(reject);
    });
  }, []);
  const acquireMic = useCallback(async () => {
    if (streamRef.current?.active) return streamRef.current;
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder)
      throw new Error(
        tr(
          "Recording is unavailable. Open localhost or 127.0.0.1 in Chrome or Edge on this computer.",
          "浏览器不支持录音。请在本机 Chrome / Edge 中使用 localhost 或127.0.0.1打开。",
        ),
      );
    if (micPromise.current) return micPromise.current;
    const epoch = micEpoch.current;
    const request = navigator.mediaDevices
      .getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
        video: false,
      })
      .then((media) => {
        if (epoch !== micEpoch.current) {
          media.getTracks().forEach((track) => track.stop());
          throw new Error(tr("Microphone check canceled.", "录音检查已取消。"));
        }
        media.getAudioTracks()[0].addEventListener("ended", () => {
          if (streamRef.current === media) {
            streamRef.current = null;
            setStream(null);
          }
          if (
            active.current?.status === "active" &&
            pageRef.current === "exam"
          ) {
            setToast(
              tr(
                "Microphone disconnected. Recording segments are preserved; reconnecting does not reset the timer.",
                "麦克风连接中断，已保留录音片段。重新连接不会重置作答时间。",
              ),
            );
            void sendEvent(active.current.id, {
              action: "interrupt",
              reason: "microphone-disconnected",
            }).catch(() => {});
          }
        });
        streamRef.current = media;
        setStream(media);
        return media;
      })
      .catch((error) => {
        if (error?.name === "NotAllowedError")
          throw new Error(
            tr(
              "Microphone permission was denied. Allow microphone access in browser or system settings, or choose Reading or Writing.",
              "麦克风权限未获允许。请在浏览器地址栏或系统隐私设置中允许麦克风，或先选择阅读 / 写作练习。",
            ),
          );
        if (error?.name === "NotFoundError")
          throw new Error(
            tr(
              "No microphone found. Connect one and try again.",
              "没有找到麦克风设备，请连接麦克风后重试。",
            ),
          );
        if (error?.name === "NotReadableError")
          throw new Error(
            tr(
              "The microphone is unavailable. Another application may be using it.",
              "麦克风暂时无法使用，可能正被其他应用占用。",
            ),
          );
        throw error;
      })
      .finally(() => {
        if (micPromise.current === request) micPromise.current = null;
      });
    micPromise.current = request;
    return request;
  }, []);
  useEffect(() => {
    Promise.all([api<Catalog>("/api/catalog"), refreshHistory()])
      .then(async ([cat]) => {
        setCatalog(cat);
        const id = sessionStorage.getItem("toefl-active-session");
        if (id) {
          const s = await api<Session>(`/api/sessions/${id}`).catch(() => null);
          if (s) await openSession(s);
          else sessionStorage.removeItem("toefl-active-session");
        }
      })
      .catch((error) => setFatal(error.message));
    void retryRecordings().catch(() => {});
  }, [refreshHistory]);
  useEffect(() => {
    const interval = setInterval(async () => {
      const now = Date.now(),
        gapMilliseconds = now - lastPollAt.current;
      lastPollAt.current = now;
      const current = active.current;
      if (
        pageRef.current !== "exam" ||
        !current ||
        current.status !== "active" ||
        polling.current ||
        pendingEvents.current
      )
        return;
      polling.current = true;
      try {
        if (
          gapMilliseconds > 5000 &&
          ["audio", "response"].includes(current.phase)
        ) {
          apply(
            await sendEvent(current.id, {
              action: "interrupt",
              reason: "clock-gap",
              details: { gapMilliseconds },
            }),
          );
        }
        apply(await api<Session>(`/api/sessions/${current.id}`));
      } catch (error) {
        setOffline(true);
        setOfflineReason(error instanceof ApiError ? error.message : "");
      } finally {
        polling.current = false;
      }
    }, 400);
    return () => clearInterval(interval);
  }, [apply]);
  useEffect(() => {
    const interval = setInterval(() => {
      void retryRecordings()
        .then(async (count) => {
          setPendingAudio(count);
          const id = wantedSession.current;
          if (!count && id && pageRef.current === "result") {
            const updated = await api<Review>(`/api/sessions/${id}/review`);
            if (wantedSession.current === id) setReview(updated);
          }
        })
        .catch(() => {});
    }, 10000);
    return () => clearInterval(interval);
  }, []);
  useEffect(() => {
    if (
      !session ||
      session.status === "active" ||
      page !== "exam" ||
      reviewLoading.current
    )
      return;
    reviewLoading.current = true;
    const id = session.id;
    // MediaRecorder emits its last dataavailable before stop. Wait for that
    // event, then flush the uploads; a fixed delay can silently lose the tail.
    void stopRecorders()
      .then(() => {
        release();
        return flushRecordings();
      })
      .then(async () => {
        setPendingAudio(await pendingRecordings().catch(() => 0));
        return api<Review>(`/api/sessions/${id}/review`);
      })
      .then((data) => {
        sessionStorage.removeItem("toefl-active-session");
        setReview(data);
        setPage("result");
        release();
        return refreshHistory();
      })
      .catch(() => {
        setOffline(true);
        notice(
          tr(
            "Practice has ended. Waiting for the local service to reconnect and load your review.",
            "练习已结束，正在等待本机服务恢复以加载复盘。",
          ),
        );
        setTimeout(
          () => setSession((old) => (old?.id === id ? { ...old } : old)),
          2000,
        );
      })
      .finally(() => {
        reviewLoading.current = false;
      });
  }, [session, page, refreshHistory, release, notice]);
  useEffect(() => {
    const visibility = () => {
      const s = active.current;
      if (
        s?.status === "active" &&
        pageRef.current === "exam" &&
        document.hidden
      )
        void sendEvent(s.id, {
          action: "interrupt",
          reason: "background-tab",
          details: { at: Date.now() },
        }).catch(() => {});
    };
    const unload = (event: BeforeUnloadEvent) => {
      const s = active.current;
      if (s?.status === "active" && pageRef.current === "exam") {
        try {
          localStorage.setItem(`toefl-interrupted:${s.id}`, String(Date.now()));
        } catch {}
        event.preventDefault();
        event.returnValue = "";
      }
    };
    document.addEventListener("visibilitychange", visibility);
    window.addEventListener("beforeunload", unload);
    return () => {
      document.removeEventListener("visibilitychange", visibility);
      window.removeEventListener("beforeunload", unload);
    };
  }, []);
  const go = async (next: string) => {
    setPage(next);
    if (next === "history")
      await refreshHistory().catch((error) => notice(error.message));
  };
  const choose = async (exam: ExamInfo, scope = "all") => {
    try {
      // Test/section entry always opens setup. Only explicit Continue actions
      // resume an existing attempt, whose saved aid preference stays unchanged.
      setSelectedScope(scope);
      setSelectionLabel("");
      const detail = await api<ExamInfo>(`/api/exams/${exam.id}`);
      setSelected({ ...exam, ...detail });
      setWrongIds(undefined);
      setSelectedGroup(null);
    } catch (error) {
      notice(String(error));
    }
  };
  const singlePractice = async (
    item: Pick<QuestionItem, "examId" | "section" | "questionId">,
    label = tr("Single-question practice", "单题专项练习"),
  ) => {
    try {
      const exam = await api<ExamInfo>(`/api/exams/${item.examId}`);
      setSelectedScope(item.section);
      setSelectionLabel(label);
      setWrongIds([item.questionId]);
      setSelectedGroup(null);
      setSelected(exam);
    } catch (error) {
      notice(String(error));
    }
  };
  const groupPractice = async (group: PracticeGroup) => {
    try {
      const exam = await api<ExamInfo>(`/api/exams/${group.examId}`);
      setSelectedScope(group.section);
      setSelectionLabel("");
      setWrongIds(undefined);
      setSelectedGroup(group);
      setSelected(exam);
    } catch (error) {
      notice(error instanceof Error ? error.message : String(error));
    }
  };
  const openSession = async (summary: Pick<SessionSummary, "id">) => {
    try {
      const s = await api<Session>(`/api/sessions/${summary.id}`);
      if (s.status === "active") {
        if (s.canRecoverAudio) {
          setAudioRecoveryTarget(s);
          setAudioRecoveryError("");
          return;
        }
        await acquireLock(s.id);
        const resumed = await sendEvent(s.id, {
          action: "interrupt",
          reason: "session-restored",
        });
        apply(resumed, true);
        if (
          s.requiresMicrophone ??
          (s.scope === "all" || s.scope === "speaking")
        )
          await acquireMic().catch((error) => notice(error.message));
        await retryRecordings(s.id).catch(() => {});
        setPage("exam");
        sessionStorage.setItem("toefl-active-session", s.id);
        notice(
          tr(
            "Practice restored with the original deadline. This recovery is recorded as an interruption.",
            "已恢复练习，原截止时间继续有效。本次恢复会标记为中断。",
          ),
        );
      } else {
        sessionStorage.removeItem("toefl-active-session");
        setReview(await api<Review>(`/api/sessions/${s.id}/review`));
        apply(s, true);
        setPage("result");
      }
    } catch (error) {
      notice(error instanceof Error ? error.message : String(error));
    }
  };
  const recoverAudio = async (id: string) => {
    const recovered = await post<Session>(
      `/api/sessions/${id}/recover-audio`,
      {},
    );
    if (active.current?.id === id) apply(recovered);
    // A history refresh must not turn a successful repair into a failed
    // playback retry after the server has already withdrawn the repair action.
    await refreshHistory().catch(() => {});
    notice(
      tr(
        "Audio access repaired. Your answers and progress were kept.",
        "音频加载已修复，已答内容和练习进度均已保留。",
      ),
    );
  };
  const start = async (options: {
    mode: string;
    scope: string;
    taskType?: string;
    routeMode: string;
    route: string;
    allowPracticeAids: boolean;
  }) => {
    if (
      options.scope === "speaking" ||
      (options.scope === "all" &&
        !wrongIds?.length &&
        selected?.sections?.some((s) => s.id === "speaking"))
    )
      await acquireMic();
    const s = await post<Session>("/api/sessions", {
      examId: selected!.id,
      ...options,
      allowPracticeAids:
        options.allowPracticeAids === true &&
        options.mode === "practice" &&
        (options.scope !== "all" || !!options.taskType || !!wrongIds?.length),
      timing,
      ...(selectedGroup
        ? {
            practiceGroupId: selectedGroup.groupId,
            expectedGroupContentId: selectedGroup.groupContentId,
            mode: "practice",
            scope: selectedGroup.section,
            routeMode: "fixed",
            route: selectedGroup.route === "lower" ? "lower" : "upper",
            taskType: undefined,
          }
        : { questionIds: wrongIds }),
    });
    await acquireLock(s.id);
    apply(s, true);
    sessionStorage.setItem("toefl-active-session", s.id);
    setSelected(null);
    setPage("exam");
    await refreshHistory();
  };
  const leave = async () => {
    await send({ action: "interrupt", reason: "left-session" });
    await stopRecorders();
    await flushRecordings();
    const pending = await pendingRecordings().catch(() => 0);
    if (pending)
      notice(
        tr(
          "{count} recording segments are saved in this browser and will retry next time.",
          "{count} 个录音分段仍在本机浏览器草稿中，下次打开时自动重试。",
          { count: pending },
        ),
      );
    sessionStorage.removeItem("toefl-active-session");
    wantedSession.current = null;
    setPage("history");
    setSession(null);
    release();
    await refreshHistory().catch((error) => notice(error.message));
  };
  const finish = async () => {
    await send({ action: "interrupt", reason: "ended-early" });
    await stopRecorders();
    await flushRecordings();
    await send({ action: "finish", reason: "user" });
  };
  const wrongPractice = (ids: string[]) => {
    const exam = catalog?.exams.find((e) => e.id === review?.session.examId);
    if (exam) {
      setSelectedScope("all");
      setSelectionLabel(tr("Mistake review", "错题复习"));
      setSelected(exam);
      setWrongIds(ids);
      setSelectedGroup(null);
    }
  };
  useEffect(
    () => setFeedback(null),
    [
      session?.id,
      session?.question?.id,
      session?.status,
      session?.mode,
      session?.allowPracticeAids,
    ],
  );
  const showFeedback = async () => {
    const current = active.current;
    if (
      !current?.question ||
      current.mode !== "practice" ||
      current.allowPracticeAids !== true
    )
      return;
    try {
      const result = await api<{
        question: Question;
        answer?: Answer;
        grade?: unknown;
      }>(
        `/api/sessions/${current.id}/feedback?questionId=${encodeURIComponent(current.question.id)}`,
      );
      if (
        active.current?.id === current.id &&
        active.current.question?.id === current.question.id &&
        active.current.mode === "practice" &&
        active.current.allowPracticeAids === true
      )
        setFeedback(result);
    } catch (error) {
      notice(String(error));
    }
  };
  let content;
  if (fatal)
    content = (
      <main className="error-screen">
        <h1>{tr("Your local library is not ready", "本地题库尚未就绪")}</h1>
        <p>{localizeDynamic(fatal)}</p>
        <p>
          {tr(
            "Run the installation script and start the local service. Refresh after importing your resources.",
            "请运行安装脚本并启动本地服务。首次导入完成后，再刷新此页。",
          )}
        </p>
        <Button onClick={() => location.reload()}>
          {tr("Reload", "重新加载")}
        </Button>
      </main>
    );
  else if (!catalog)
    content = (
      <div className="loading">
        {tr("Opening your practice space…", "正在打开你的本地练习空间…")}
      </div>
    );
  else if (page === "exam" && session?.status === "active")
    content = (
      <Exam
        session={session}
        referencePlayback={referencePlayback.current}
        stream={stream}
        send={send}
        onLeave={() => void leave().catch((error) => notice(error.message))}
        onFinish={() => void finish().catch((error) => notice(error.message))}
        onNotice={notice}
        offline={offline}
        offlineReason={offlineReason}
        acquireMic={acquireMic}
        onFeedback={() => void showFeedback()}
        onRecoverAudio={() => recoverAudio(session.id)}
      />
    );
  else if (page === "exam")
    content = (
      <div className="loading">
        {tr(
          "Saving the final recording segments and preparing your review…",
          "正在保存最后的录音分段并生成复盘…",
        )}
      </div>
    );
  else
    content = (
      <Layout
        page={page}
        go={(next) => void go(next)}
        materialCount={catalog.materials.length}
      >
        {page === "help" || (page === "home" && !catalog.exams.length) ? (
          <GettingStarted
            compact={page === "home"}
            onImported={async () => {
              setCatalog(await api<Catalog>("/api/catalog"));
              setPage("home");
            }}
          />
        ) : page === "home" ? (
          <Home
            exams={catalog.exams}
            materials={catalog.materials}
            sessions={sessions}
            choose={(exam, scope) => void choose(exam, scope)}
            resume={(summary) => void openSession(summary)}
            go={(next) => void go(next)}
          />
        ) : page === "drills" ? (
          <QuestionLibrary practice={(group) => void groupPractice(group)} />
        ) : page === "mistakes" ? (
          <Mistakes
            practice={(item) =>
              void singlePractice(item, tr("Mistake review", "错题复习"))
            }
            review={(id) => void openSession({ id })}
          />
        ) : page === "vocabulary" ? (
          <VocabularyPage onNotice={notice} />
        ) : page === "library" ? (
          <Library materials={catalog.materials} />
        ) : page === "history" ? (
          <History
            sessions={sessions}
            open={(summary) => void openSession(summary)}
          />
        ) : page === "rules" ? (
          <Rules />
        ) : page === "settings" ? (
          <Settings
            timing={timing}
            onSave={(next) => {
              setTiming(next);
              saveTimingSettings(next);
              notice(
                tr(
                  "Settings saved. They apply to new practice sessions.",
                  "练习设置已保存，仅用于新练习。",
                ),
              );
            }}
          />
        ) : page === "validation" ? (
          <Validation />
        ) : page === "result" && review ? (
          <ReviewPage
            review={review}
            materials={catalog.materials}
            onHistory={() => void go("history")}
            onWrongPractice={wrongPractice}
            onNotice={notice}
            onAddWord={setVocabularyDraft}
          />
        ) : (
          <Empty>
            {tr("Choose a practice session or resource.", "请选择练习或资料。")}
          </Empty>
        )}
      </Layout>
    );
  return (
    <>
      {(fatal || !catalog) && (
        <div className="startup-language">
          <LanguageSwitch />
        </div>
      )}
      {content}
      {pendingAudio > 0 && page !== "exam" && (
        <div className="pending-audio-banner" role="alert">
          {" "}
          {tr("There are", "有")} {pendingAudio}{" "}
          {tr(
            "recording segments or completion markers pending in this browser. Keep site data until they are saved to the local service.",
            "项录音数据或完成标记仍保留在浏览器草稿中，尚未同步到本机服务。请勿清除站点数据。",
          )}{" "}
          <Button
            kind="outline small"
            onClick={() =>
              void retryRecordings()
                .then((count) => {
                  setPendingAudio(count);
                  notice(
                    count
                      ? tr(
                          "Recordings are still waiting to retry. Keep the local service running.",
                          "仍有录音数据等待重试，请保持本地服务运行。",
                        )
                      : tr("All recordings saved.", "录音数据全部保存成功。"),
                  );
                })
                .catch((error) => notice(error.message))
            }
          >
            {" "}
            {tr("Retry saving", "重试保存")}{" "}
          </Button>
        </div>
      )}
      {selected && catalog && (
        <Prepare
          key={`${selected.id}:${selectedScope}:${selectedGroup?.groupId || ""}:${selectedGroup?.groupContentId || ""}:${wrongIds?.join("|") || ""}`}
          exam={selected}
          practiceGroup={selectedGroup || undefined}
          initialScope={selectedScope}
          selectionLabel={selectionLabel}
          materials={catalog.materials}
          stream={stream}
          acquireMic={acquireMic}
          start={start}
          close={() => {
            setSelected(null);
            if (pageRef.current !== "exam") release();
          }}
          wrongCount={wrongIds?.length}
        />
      )}{" "}
      {feedback && (
        <Feedback data={feedback} onClose={() => setFeedback(null)} />
      )}
      {vocabularyDraft && (
        <VocabularyEntryDialog
          draft={vocabularyDraft}
          onClose={() => setVocabularyDraft(null)}
          onSaved={() => setVocabularyDraft(null)}
          onNotice={notice}
        />
      )}
      {audioRecoveryTarget && (
        <Modal
          onClose={() => {
            if (audioRecoveryBusy) return;
            setAudioRecoveryTarget(null);
            sessionStorage.removeItem("toefl-active-session");
          }}
          actions={
            <>
              <Button
                kind="outline"
                disabled={audioRecoveryBusy}
                onClick={() => {
                  setAudioRecoveryTarget(null);
                  sessionStorage.removeItem("toefl-active-session");
                }}
              >
                {tr("Later", "稍后处理")}
              </Button>
              <Button
                disabled={audioRecoveryBusy}
                onClick={async () => {
                  if (audioRecoveryBusy) return;
                  const id = audioRecoveryTarget.id;
                  setAudioRecoveryBusy(true);
                  setAudioRecoveryError("");
                  try {
                    await recoverAudio(id);
                    setAudioRecoveryTarget(null);
                    await openSession({ id });
                  } catch (error) {
                    setAudioRecoveryError(
                      error instanceof Error ? error.message : String(error),
                    );
                  } finally {
                    setAudioRecoveryBusy(false);
                  }
                }}
              >
                {audioRecoveryBusy
                  ? tr("Repairing…", "正在修复…")
                  : tr("Repair audio and continue", "修复音频并继续")}
              </Button>
            </>
          }
        >
          <h2>{tr("Restore listening audio", "恢复听力音频")}</h2>
          <p>
            {tr(
              "This older practice has no audio verification record. Its questions match the current materials. Repair will verify and bind the current audio while keeping your answers, position, and original timing. The recovery will be recorded; earlier playback remains unverified.",
              "这份旧版练习缺少音频校验记录，题目内容与当前资料一致。修复会校验并关联当前音频，保留已答内容、当前题号和原计时设置，同时记录本次恢复；不会把此前的播放补记为已校验。",
            )}
          </p>
          {audioRecoveryError && (
            <p className="error-message" role="alert">
              {localizeDynamic(audioRecoveryError)}
            </p>
          )}
        </Modal>
      )}
      <div
        id="toast"
        className={toast ? "visible" : ""}
        role="status"
        aria-live="polite"
      >
        {localizeDynamic(toast)}
      </div>
    </>
  );
}

export function Prepare({
  exam,
  initialScope = "all",
  selectionLabel,
  materials,
  stream,
  acquireMic,
  start,
  close,
  wrongCount,
  practiceGroup,
}: {
  exam: ExamInfo;
  initialScope?: string;
  selectionLabel?: string;
  materials: Catalog["materials"];
  stream: MediaStream | null;
  acquireMic: () => Promise<MediaStream>;
  start: (o: {
    mode: string;
    scope: string;
    taskType?: string;
    routeMode: string;
    route: string;
    allowPracticeAids: boolean;
  }) => Promise<void>;
  close: () => void;
  wrongCount?: number;
  practiceGroup?: PracticeGroup;
}) {
  const { locale } = useI18n();
  const practiceAidsHintId = useId();
  const [mode, setMode] = useState(
      exam.strictEligible && !wrongCount && !practiceGroup
        ? "strict"
        : "practice",
    ),
    [scope, setScope] = useState(practiceGroup?.section || initialScope),
    [taskType, setTaskType] = useState(""),
    [allowPracticeAids, setAllowPracticeAids] = useState(false),
    [routeMode, setRouteMode] = useState("fixed"),
    [route, setRoute] = useState(
      practiceGroup?.route === "lower" ? "lower" : "upper",
    ),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [micMessage, setMicMessage] = useState(
      stream?.active
        ? tr("Microphone connected", "麦克风已连接")
        : tr("Microphone not checked", "麦克风尚未检测"),
    ),
    [preview, setPreview] = useState("");
  const practiceAidsEligible =
      mode === "practice" &&
      (scope !== "all" || !!taskType || !!wrongCount || !!practiceGroup),
    canStrict = exam.strictEligible || !!exam.scopedEligibility?.[scope],
    canAdaptive =
      scope === "all"
        ? exam.adaptiveEligible
        : exam.adaptiveEligibility?.[scope],
    needsSound =
      ["listening", "speaking"].includes(scope) ||
      (scope === "all" &&
        exam.sections?.some(
          (s) => s.id === "listening" || s.id === "speaking",
        )),
    needsMic =
      scope === "speaking" ||
      (scope === "all" &&
        !wrongCount &&
        exam.sections?.some((s) => s.id === "speaking"));
  useEffect(() => {
    if ((!canStrict || practiceGroup) && mode === "strict") setMode("practice");
  }, [canStrict, mode, practiceGroup]);
  useEffect(
    () => setAllowPracticeAids(false),
    [
      mode,
      scope,
      taskType,
      exam.id,
      initialScope,
      wrongCount,
      selectionLabel,
      practiceGroup?.groupId,
      practiceGroup?.groupContentId,
    ],
  );
  useEffect(
    () => () => {
      if (preview) URL.revokeObjectURL(preview);
    },
    [preview],
  );
  const testMic = async () => {
    setMicMessage(
      tr(
        "Requesting microphone access. Allow it in the browser or system prompt…",
        "正在请求麦克风权限，请在浏览器或系统提示中允许访问…",
      ),
    );
    try {
      const mic = await acquireMic(),
        mime = supportedMime(),
        recorder = new MediaRecorder(
          mic,
          mime ? { mimeType: mime } : undefined,
        ),
        chunks: Blob[] = [];
      setMicMessage(
        tr(
          "Recording a 3-second check. Say a sentence…",
          "正在录制3秒测试音频，请说一句话…",
        ),
      );
      recorder.ondataavailable = (e) => {
        if (e.data.size) chunks.push(e.data);
      };
      recorder.onstop = () => {
        setPreview(
          URL.createObjectURL(new Blob(chunks, { type: recorder.mimeType })),
        );
        setMicMessage(
          tr(
            "Microphone connected. Play the check to confirm clear sound. The check is not saved.",
            "麦克风已连接。请回放确认声音清晰，测试音频不会保存。",
          ),
        );
      };
      recorder.start();
      setTimeout(() => {
        if (recorder.state !== "inactive") recorder.stop();
      }, 3000);
    } catch (error) {
      setMicMessage(tr("Microphone check incomplete", "麦克风检测未完成"));
      setError(error instanceof Error ? error.message : String(error));
    }
  };
  const sound = () => {
    const c = new AudioContext(),
      g = c.createGain();
    g.connect(c.destination);
    g.gain.value = 0.08;
    [440, 554, 659].forEach((hz, i) => {
      const o = c.createOscillator();
      o.frequency.value = hz;
      o.connect(g);
      o.start(c.currentTime + i * 0.2);
      o.stop(c.currentTime + i * 0.2 + 0.18);
    });
    setTimeout(() => void c.close(), 1000);
  };
  const available = exam.sections?.map((s) => s.id) || ORDER;
  const submit = async () => {
    setBusy(true);
    setError("");
    if (needsMic)
      setMicMessage(
        tr(
          "Connecting the microphone. Allow access if prompted.",
          "正在连接麦克风；如有权限提示，请允许后继续。",
        ),
      );
    try {
      await start({
        mode: practiceGroup ? "practice" : mode,
        scope: practiceGroup?.section || scope,
        taskType: practiceGroup ? undefined : taskType || undefined,
        routeMode: practiceGroup ? "fixed" : routeMode,
        route: practiceGroup
          ? practiceGroup.route === "lower"
            ? "lower"
            : "upper"
          : route,
        allowPracticeAids: practiceAidsEligible && allowPracticeAids,
      });
    } catch (error) {
      setError(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  };
  const sources = materials.filter(
    (m) =>
      exam.sourceMaterialIds?.includes(m.id) || m.examIds?.includes(exam.id),
  );
  return (
    <Modal
      onClose={close}
      actions={
        <>
          <Button kind="outline" onClick={close} disabled={busy}>
            {" "}
            {tr("Cancel", "取消")}{" "}
          </Button>
          {!exam.resourcesOnly && (
            <Button onClick={() => void submit()} disabled={busy}>
              {busy
                ? tr("Preparing…", "正在准备…")
                : tr("Start practice", "进入练习")}
              <Icon name="arrow" />
            </Button>
          )}
        </>
      }
    >
      <div className="dialog-top">
        <span className="eyebrow">{tr("LET’S GET READY", "准备开始")}</span>
        <button onClick={close} aria-label={tr("Close", "关闭")}>
          <Icon name="close" />
        </button>
      </div>
      <h2>{localizeDynamic(exam.title)}</h2>
      <p>
        {practiceGroup
          ? tr(
              "{module} · {task} · {count} items in source order.",
              "{module} · {task} · 按原始顺序练习 {count} 道小题。",
              {
                module: localizeDynamic(practiceGroup.module, locale),
                task: practiceGroupTaskName(practiceGroup.taskType, locale),
                count: practiceGroup.itemCount,
              },
            )
          : wrongCount
            ? tr(
                "{label} · {count} selected questions in original source order.",
                "{label} · 本次选择 {count} 道题，保持原始资料来源。",
                {
                  label:
                    localizeDynamic(selectionLabel) ||
                    tr("Guided practice", "专项练习"),
                  count: wrongCount,
                },
              )
            : tr(
                "Choose a section, check your equipment, and read the directions. Answers and recordings stay on this computer.",
                "选择练习范围，检查设备，然后进入考试说明。你的作答与录音只在本机处理。",
              )}
      </p>
      {practiceGroup && (
        <p className="muted" style={{ fontSize: 12 }}>
          {practiceGroup.numberStart != null &&
            `${
              practiceGroup.numberEnd != null &&
              practiceGroup.numberEnd !== practiceGroup.numberStart
                ? tr("Questions {start}–{end}", "第 {start}–{end} 题", {
                    start: practiceGroup.numberStart,
                    end: practiceGroup.numberEnd,
                  })
                : tr("Question {number}", "第 {number} 题", {
                    number: practiceGroup.numberStart,
                  })
            } · `}
          {tr(
            "The source module and branch are fixed for this group.",
            "本组固定使用所选原卷模块与分支。",
          )}
          {practiceGroup.route !== "common" &&
            ` ${practiceGroup.route === "lower" ? tr("Lower branch", "较低难度分支") : tr("Upper branch", "较高难度分支")}`}
          {!!practiceGroup.unavailableCount &&
            ` ${tr("Some source questions are unavailable; only available questions are included.", "部分原题暂不可练习，本组仅包含可用题目。")}`}
        </p>
      )}
      {exam.resourcesOnly ? (
        <>
          <Notice>
            {" "}
            {tr(
              "This resource is available for reference. Its question presentation has not been verified for strict practice.",
              "这份材料保留为补充资料。尚未核验的题面不冒充可执行的严格模考。",
            )}{" "}
          </Notice>
          {sources.map((m) => (
            <p key={m.id}>
              {m.url ? (
                <a href={m.url} target="_blank" rel="noopener">
                  {m.name} ↗
                </a>
              ) : (
                <span>
                  {m.name} · {tr("Original not installed", "未安装原文件")}
                </span>
              )}
            </p>
          ))}
        </>
      ) : (
        <>
          <div className="choice-mode">
            <label
              className={`mode-option ${!canStrict || wrongCount || practiceGroup ? "disabled" : ""}`}
            >
              <input
                type="radio"
                name="mode"
                checked={mode === "strict"}
                disabled={!canStrict || !!wrongCount || !!practiceGroup}
                onChange={() => {
                  setMode("strict");
                  setTaskType("");
                }}
              />
              <b>{tr("Strict practice", "严格模考")}</b>
              <small>
                {" "}
                {tr(
                  "No pause · Original audio plays once",
                  "无暂停 · 原音单次播放",
                )}{" "}
                <br />{" "}
                {tr(
                  "Server timer · Automatic submission at expiry",
                  "服务端计时 · 到时自动提交",
                )}{" "}
              </small>
            </label>
            <label className="mode-option">
              <input
                type="radio"
                name="mode"
                checked={mode === "practice"}
                onChange={() => {
                  setMode("practice");
                  setRouteMode("fixed");
                }}
              />
              <b>{tr("Guided practice", "专项练习")}</b>
              <small>
                {" "}
                {tr(
                  "Pause responses; optional replay and instant answers for targeted practice",
                  "答题时可暂停；专项练习可自行开启重播与即时解析",
                )}{" "}
                <br />{" "}
                {tr(
                  "Practice a section or task type",
                  "按部分或题型定向练习",
                )}{" "}
              </small>
            </label>
          </div>
          <label className="check-row">
            <input
              type="checkbox"
              checked={practiceAidsEligible && allowPracticeAids}
              disabled={!practiceAidsEligible || busy}
              aria-describedby={practiceAidsHintId}
              onChange={(event) => setAllowPracticeAids(event.target.checked)}
            />
            <span>
              {tr(
                "Enable audio replay and instant answers",
                "允许重播音频和即时查看答案与解析",
              )}
            </span>
          </label>
          <p
            id={practiceAidsHintId}
            className="muted"
            style={{ marginTop: 5, fontSize: 12 }}
          >
            {tr(
              "Off by default. Available only for specialized guided practice; full tests show answers after finishing.",
              "默认关闭，仅专项练习可勾选；完整考试结束后统一查看答案与解析。",
            )}
          </p>
          <div className={`settings-grid ${mode === "strict" ? "two" : "one"}`}>
            <label className="field">
              {" "}
              {tr("Practice scope", "练习范围")}{" "}
              <select
                value={scope}
                disabled={!!wrongCount || !!practiceGroup}
                onChange={(e) => {
                  setScope(e.target.value);
                  setTaskType("");
                }}
              >
                <option value="all">
                  {wrongCount
                    ? tr(
                        "Selected questions · Original section order",
                        "所选题目 · 按原科目顺序",
                      )
                    : exam.supplemental || exam.family === "essentials"
                      ? tr(
                          "Full supplemental resource (untimed)",
                          "整套补充资料研读（不计时）",
                        )
                      : tr(
                          "Full test · R → L → W → S",
                          "完整流程 · R → L → W → S",
                        )}
                </option>
                {available.map((id) => (
                  <option key={id} value={id}>
                    {sectionLabel(id)}
                  </option>
                ))}
              </select>
            </label>
            {mode === "strict" && (
              <label className="field">
                {" "}
                {tr("Test path", "试卷路径")}{" "}
                <select
                  value={routeMode}
                  onChange={(e) => setRouteMode(e.target.value)}
                >
                  <option value="fixed">
                    {tr("Original fixed path", "原套题固定路径")}
                  </option>
                  <option value="adaptive" disabled={!canAdaptive}>
                    {" "}
                    {tr(
                      "Simulated adaptive · Local 70% threshold",
                      "模拟自适应 · 本地70%阈值",
                    )}{" "}
                    {!canAdaptive
                      ? tr(" (branches incomplete)", "（分支未完备）")
                      : ""}
                  </option>
                </select>
              </label>
            )}
          </div>
          {canAdaptive && routeMode === "fixed" && !practiceGroup && (
            <label className="field" style={{ marginTop: 15 }}>
              {" "}
              {tr("Fixed second-module branch", "固定第二模块分支")}{" "}
              <select value={route} onChange={(e) => setRoute(e.target.value)}>
                <option value="upper">Upper</option>
                <option value="lower">Lower</option>
              </select>
            </label>
          )}
          <details className="prep-disclosure">
            <summary>
              {tr(
                "Resource status and simulation details",
                "资料状态与本地模拟说明",
              )}
            </summary>
            <div className="warning-list">
              {exam.warnings?.map((w, i) => (
                <div key={i}>• {localizeDynamic(w)}</div>
              ))}
              {exam.supplemental || exam.family === "essentials" ? (
                <div>
                  {tr(
                    "• This resource is untimed, without iBT routing or official scores.",
                    "• 本组不限时，不套用 iBT 计时、分流或官方分数。",
                  )}
                </div>
              ) : (
                <>
                  <div>
                    {tr(
                      "• The six-minute sentence task and some timings are documented local presets.",
                      "• 造句6分钟及部分计时是公开标注的本地预设。",
                    )}
                  </div>
                  <div>
                    {tr(
                      "• Simulated routing and results do not reproduce ETS algorithms or official scores.",
                      "• 模拟分流和结果不等于 ETS 算法或官方成绩。",
                    )}
                  </div>
                </>
              )}
            </div>
          </details>
          <p className="prep-summary">
            {" "}
            {tr(
              "Local timed practice · Documented approximations · No official ETS scores",
              "本地计时练习 · 含明确标注的近似设置 · 不生成 ETS 官方成绩",
            )}{" "}
          </p>
          {needsSound && (
            <div className="equipment-block">
              <div className="equipment">
                <Icon name={needsMic ? "mic" : "headphones"} />
                <p>
                  {needsMic
                    ? tr("Sound and microphone", "声音与麦克风")
                    : tr("Sound check", "声音检查")}
                </p>
                <Button kind="outline small" onClick={sound}>
                  {" "}
                  {tr("Test sound", "试听")}{" "}
                </Button>
                {needsMic && (
                  <Button kind="outline small" onClick={() => void testMic()}>
                    {" "}
                    {tr("Check microphone", "检测麦克风")}{" "}
                  </Button>
                )}
              </div>
              {needsMic && (
                <div className="equipment-status">
                  {localizeDynamic(micMessage)}
                </div>
              )}
              {preview && needsMic && (
                <audio
                  controls
                  src={preview}
                  aria-label={tr(
                    "Microphone check recording",
                    "麦克风测试录音",
                  )}
                />
              )}
            </div>
          )}
        </>
      )}
      {error && (
        <p className="error-message" role="alert">
          {localizeDynamic(error)}
        </p>
      )}
    </Modal>
  );
}
