import type { DocumentId } from "./Documentation";
import { lazy, Suspense, useRef, useState } from "react";
import { Button, Heading } from "./components";
import { post } from "./api";
import { localizeDynamic, useI18n } from "./i18n";

// Markdown tooling is loaded only when the reader is opened, keeping the
// practice interface quick to load on a fresh offline installation.
const Documentation = lazy(() => import("./Documentation"));

/** The public checkout has no private study bank. This is its first-run path. */
export default function GettingStarted({
  onImported,
  compact = false,
}: {
  onImported: () => Promise<void>;
  compact?: boolean;
}) {
  const { t, locale } = useI18n();
  const [document, setDocument] = useState<DocumentId | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const file = useRef<HTMLInputElement>(null);
  const run = async (operation: () => Promise<unknown>) => {
    setBusy(true);
    setError("");
    try {
      await operation();
      await onImported();
    } catch (error) {
      setError(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
      if (file.current) file.current.value = "";
    }
  };
  const readPack = async (pack: File) => {
    if (pack.size > 2 * 1024 * 1024)
      throw new Error(
        t(
          "Choose a JSON file smaller than 2 MB.",
          "请选择小于 2 MB 的 JSON 文件。",
        ),
      );
    let manifest: unknown;
    try {
      manifest = JSON.parse(await pack.text());
    } catch {
      throw new Error(
        t(
          "This file is not valid JSON. Check the resource import guide.",
          "文件不是有效的 JSON，请参考资源导入指南。",
        ),
      );
    }
    return post("/api/resource-packs", manifest);
  };
  if (document)
    return (
      <Suspense
        fallback={
          <p role="status">{t("Loading documentation…", "正在加载文档…")}</p>
        }
      >
        <Documentation
          initialDocument={document}
          onBack={() => setDocument(null)}
        />
      </Suspense>
    );
  return (
    <div className="getting-started">
      <Heading
        title={
          compact
            ? t(
                "Welcome. Make this your practice space.",
                "欢迎，开始你的个人练习。",
              )
            : t("Help & setup", "使用与导入指南")
        }
        subtitle={t(
          "Choose a demo or import your own material. Everything runs on this computer.",
          "先体验演示题，或导入自己的资料。所有操作都在本机完成。",
        )}
      />
      <section className="onboarding-card">
        <h2>{t("1. Add a practice resource", "1. 添加练习资料")}</h2>
        <p>
          {t(
            "Try a short, original reading and writing demo to learn the controls. It is an untimed tutorial, not an official TOEFL test.",
            "可先用原创的阅读和写作演示熟悉操作。演示不限时，用于学习软件使用方式。",
          )}
        </p>
        <div className="onboarding-actions">
          <Button
            disabled={busy}
            onClick={() => void run(() => post("/api/resource-packs/demo", {}))}
          >
            {busy
              ? t("Importing…", "正在导入…")
              : t("Try the demo", "体验演示题")}
          </Button>
          <Button
            kind="outline"
            disabled={busy}
            onClick={() => file.current?.click()}
          >
            {t("Import JSON resource pack", "导入 JSON 资源包")}
          </Button>
          <input
            ref={file}
            type="file"
            accept=".json,application/json"
            className="sr-only"
            aria-label={t("Choose a resource pack", "选择资源包")}
            disabled={busy}
            onChange={(event) => {
              const selected = event.target.files?.[0];
              if (selected) void run(() => readPack(selected));
            }}
          />
        </div>
        <p className="guide-detail">
          {t(
            "The file picker imports text-only packs. For PDF, image, audio, or video attachments, keep the pack folder together and use the command below.",
            "文件选择器支持纯文字资源包。含 PDF、图片、音频或视频的资源包，请保持文件夹完整，并使用以下命令。",
          )}
        </p>
        <pre>
          <code>npm run import:pack -- /path/to/pack.json</code>
        </pre>
        <p>
          {t(
            "Start with examples/demo/pack.json and edit its English questions. Image and audio file paths are relative to that JSON file. Arbitrary PDFs require transcription into the resource-pack format.",
            "可以复制 examples/demo/pack.json 并编辑其中的英文题目。图片和音频路径相对于该 JSON 文件。任意 PDF 需先将题目整理为资源包格式。",
          )}
        </p>
        {error && (
          <p className="error-message" role="alert">
            {localizeDynamic(error, locale)}
          </p>
        )}
      </section>
      <section className="onboarding-card">
        <h2>{t("2. Choose how to practice", "2. 选择练习方式")}</h2>
        <p>
          {t(
            "Open Practice, select a test, and choose R, L, W, or S for a single section. Full test follows Reading → Listening → Writing → Speaking. Personal packs appear under Supplemental or All and use untimed guided practice.",
            "在模考练习中选择套题，点击 R、L、W、S 可单科练习。整套按阅读 → 听力 → 写作 → 口语进行。个人资源包在“补充资料”或“全部”中显示，采用不限时辅助练习。",
          )}
        </p>
        <p>
          {t(
            "Strict practice is available only for verified complete source sets. Guided practice lets you pause, replay audio, and check visited questions. Before speaking, use Check microphone and play back the test recording.",
            "只有通过核验的完整套题可使用严格模考。专项练习允许暂停、重听及查看已访问题目的解析。口语前请检测麦克风并回放测试录音。",
          )}
        </p>
      </section>
      <section className="onboarding-card">
        <h2>{t("3. Answer, save, and review", "3. 作答、保存与复盘")}</h2>
        <p>
          {t(
            "Select choices, type missing letters, arrange sentence blocks, or write in the editor. Answers save automatically. After submitting, open History to review answers, essays, and recordings; use Mistakes for targeted practice.",
            "选择答案、补全缺失字母、排列词块，或在编辑器写作。答案自动保存。提交后在练习记录中查看答案、作文和录音，也可使用错题集定向复习。",
          )}
        </p>
        <p>
          {t(
            "Keep the local server terminal open. Strict timers continue while you are away. To back up your work, stop the server and copy the entire storage/ directory. Keep data/ and generated/ with it to preserve the source resources.",
            "请保持本地服务终端运行。严格模式离开后仍计时。备份时先停止服务，再复制整个 storage/ 目录；同时保留 data/ 与 generated/，确保来源资料完整。",
          )}
        </p>
      </section>
      <section className="onboarding-card">
        <h2>{t("Language and detailed documentation", "语言与详细文档")}</h2>
        <p>
          {t(
            "Use EN / 中文 in the header to switch the entire interface, including exam controls. Your choice is remembered. Source passages, answer options, written responses, and recordings retain their original language.",
            "使用顶部 EN / 中文切换整个操作界面，包括考试控制按钮，软件会记住选择。文章、题目选项、你的作答和录音保留原语言。",
          )}
        </p>
        <div className="guide-links">
          {[
            ["DOCUMENTATION_INDEX", t("Documentation index", "文档索引")],
            ["USER_GUIDE", t("User guide", "使用指南")],
            ["IMPORTING", t("Resource import guide", "资源导入指南")],
            ["TROUBLESHOOTING", t("Troubleshooting", "常见问题")],
            ["ARCHITECTURE", t("Developer documentation", "开发者文档")],
          ].map(([id, label]) => (
            <a
              key={id}
              href={`/api/documentation/${locale}/${id}`}
              onClick={(event) => {
                event.preventDefault();
                setDocument(id as DocumentId);
              }}
            >
              {label} →
            </a>
          ))}
        </div>
        <details>
          <summary>
            {t(
              "Restoring the original private PDF collection",
              "恢复原有私有 PDF 题库",
            )}
          </summary>
          <p>
            {t(
              "The collection-specific importer needs the original data/ folder and its matching scripts/verified_*.json curation files. Those copyrighted resources and private manifests are not included with the open-source code. Use portable packs if you do not have that collection.",
              "原题库导入器需要原始 data/ 目录及匹配的 scripts/verified_*.json 校对清单。受版权保护的资料和私有清单不随开源代码提供；没有该资料集时请使用通用资源包。",
            )}
          </p>
          <pre>
            <code>npm run import -- --jobs 4</code>
          </pre>
        </details>
      </section>
    </div>
  );
}
