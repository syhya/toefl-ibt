/** Durable recorder outbox: chunks and finalization markers retry independently.
 * IndexedDB preserves unsent data across reloads; the in-memory fallback covers
 * restricted browser storage. Upload keys are stable so retries are idempotent.
 */
import { api } from "./api";
type Chunk = {
  kind?: "chunk";
  id: string;
  sessionId: string;
  questionId: string;
  takeId: string;
  index: number;
  blob: Blob;
  mimeType: string;
};
type Finalization = {
  kind: "final";
  id: string;
  sessionId: string;
  questionId: string;
  takeId: string;
  segmentCount: number;
  endedReason: string;
  mimeType: string;
};
type OutboxItem = Chunk | Finalization;
const pending = new Map<string, Promise<void>>();
const memoryDrafts = new Map<string, OutboxItem>();
const activeRecorders = new Set<{
  recorder: MediaRecorder;
  done: Promise<void>;
}>();
export function trackRecorder(recorder: MediaRecorder) {
  let resolve!: () => void;
  const item = {
    recorder,
    done: new Promise<void>((done) => {
      resolve = done;
    }),
  };
  activeRecorders.add(item);
  recorder.addEventListener(
    "stop",
    () => {
      activeRecorders.delete(item);
      resolve();
    },
    { once: true },
  );
  return item.done;
}
export async function stopRecorders() {
  const active = [...activeRecorders];
  for (const { recorder } of active)
    if (recorder.state !== "inactive") recorder.stop();
  await Promise.all(active.map((item) => item.done));
}
let database: Promise<IDBDatabase> | undefined;
function db() {
  return (database ??= new Promise<IDBDatabase>((resolve, reject) => {
    const r = indexedDB.open("toefl-local-recording-drafts", 1);
    r.onupgradeneeded = () =>
      r.result.createObjectStore("chunks", { keyPath: "id" });
    r.onsuccess = () => resolve(r.result);
    r.onerror = () => reject(r.error);
  }));
}
async function store(c: OutboxItem) {
  const d = await db();
  await new Promise<void>((resolve, reject) => {
    const t = d.transaction("chunks", "readwrite");
    t.objectStore("chunks").put(c);
    t.oncomplete = () => resolve();
    t.onerror = () => reject(t.error);
  });
}
async function remove(id: string) {
  const d = await db();
  await new Promise<void>((resolve, reject) => {
    const t = d.transaction("chunks", "readwrite");
    t.objectStore("chunks").delete(id);
    t.oncomplete = () => resolve();
    t.onerror = () => reject(t.error);
  });
}
async function chunks() {
  const d = await db();
  return new Promise<OutboxItem[]>((resolve, reject) => {
    const r = d.transaction("chunks").objectStore("chunks").getAll();
    r.onsuccess = () => resolve(r.result);
    r.onerror = () => reject(r.error);
  });
}
async function upload(c: OutboxItem) {
  if (c.kind === "final") {
    await api(
      `/api/sessions/${c.sessionId}/recordings/takes/${c.takeId}/finalize`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          questionId: c.questionId,
          segmentCount: c.segmentCount,
          endedReason: c.endedReason,
          mimeType: c.mimeType,
        }),
      },
    );
  } else {
    const params = new URLSearchParams({
      segmentId: c.id,
      takeId: c.takeId,
      index: String(c.index),
    });
    await api(
      `/api/sessions/${c.sessionId}/recordings/${c.questionId}?${params}`,
      { method: "POST", headers: { "Content-Type": c.mimeType }, body: c.blob },
    );
  }
  await remove(c.id).catch(() => {});
  memoryDrafts.delete(c.id);
}
export function saveChunk(c: Omit<Chunk, "id">, onError: (s: string) => void) {
  return saveOutbox({ ...c, id: crypto.randomUUID() }, onError);
}
export function saveFinalization(
  c: Omit<Finalization, "id" | "kind">,
  onError: (s: string) => void,
) {
  return saveOutbox({ ...c, kind: "final", id: `final-${c.takeId}` }, onError);
}
function saveOutbox(chunk: OutboxItem, onError: (s: string) => void) {
  if (pending.has(chunk.id)) return pending.get(chunk.id)!;
  memoryDrafts.set(chunk.id, chunk);
  const task = store(chunk)
    .catch(() => {
      onError("浏览器录音草稿保存失败，正在直接保存到本机服务。请勿关闭此页。");
    })
    .then(() => upload(chunk))
    .catch((error) => {
      onError(`录音数据待重试：${error.message}。请勿清除浏览器数据。`);
    })
    .finally(() => pending.delete(chunk.id));
  pending.set(chunk.id, task);
  return task;
}
async function drafts() {
  const list = await chunks().catch(() => []);
  return [
    ...new Map(
      [...list, ...memoryDrafts.values()].map((c) => [c.id, c]),
    ).values(),
  ];
}
export async function retryRecordings(sessionId?: string) {
  const list = await drafts();
  await Promise.allSettled(
    list
      .filter(
        (c) => (!sessionId || c.sessionId === sessionId) && !pending.has(c.id),
      )
      .map(upload),
  );
  return (await drafts()).filter((c) => !sessionId || c.sessionId === sessionId)
    .length;
}
export async function flushRecordings() {
  await Promise.allSettled([...pending.values()]);
}
export async function pendingRecordings() {
  return (await drafts()).length;
}
export function supportedMime() {
  return ["audio/webm;codecs=opus", "audio/mp4", "audio/ogg;codecs=opus"].find(
    (type) => MediaRecorder.isTypeSupported(type),
  );
}
