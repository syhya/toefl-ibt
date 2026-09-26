import { useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "./components";
import { localizeDynamic, useI18n, type Locale } from "./i18n";
import "./documentation.css";

/** Public documents only; IDs mirror the backend's explicit file allowlist. */
const documents = {
  DOCUMENTATION_INDEX: ["docs/README", "Documentation index", "文档索引"],
  USER_GUIDE: ["docs/USER_GUIDE", "User guide", "使用指南"],
  IMPORTING: ["docs/IMPORTING", "Resource import guide", "资源导入指南"],
  TROUBLESHOOTING: ["docs/TROUBLESHOOTING", "Troubleshooting", "故障排查"],
  ARCHITECTURE: ["docs/ARCHITECTURE", "Architecture", "架构说明"],
  TESTING: ["docs/TESTING", "Testing", "测试指南"],
  MATERIALS: ["docs/MATERIALS", "Materials", "资料说明"],
  OFFICIAL_RULES: ["docs/OFFICIAL_RULES", "Rules and evidence", "规则与依据"],
  DATA_QA: ["docs/DATA_QA", "Source-data audit", "来源数据审核"],
  TEXT_FIDELITY: [
    "docs/TEXT_FIDELITY",
    "Source text corrections",
    "原题文字修正",
  ],
  ACCEPTANCE: ["docs/ACCEPTANCE", "Acceptance record", "验收记录"],
  DESIGN_REFERENCES: [
    "docs/DESIGN_REFERENCES",
    "Design references",
    "设计参考",
  ],
  EXAM_UI_REFERENCE: [
    "docs/EXAM_UI_REFERENCE",
    "Exam interface reference",
    "考试界面参考",
  ],
  GOAL_COMPLETION_AUDIT: [
    "docs/GOAL_COMPLETION_AUDIT",
    "Completion audit",
    "完成情况审核",
  ],
  MEDIA_SEGMENTS: ["docs/MEDIA_SEGMENTS", "Media segmentation", "媒体分段"],
  "ets-2026-verification": [
    "docs/ets-2026-verification",
    "ETS 2026 verification",
    "ETS 2026 核验",
  ],
  PROJECT_HISTORY: ["docs/PROJECT_HISTORY", "Project history", "项目历史"],
  STRICT_MODE_SECURITY_REVIEW: [
    "docs/STRICT_MODE_SECURITY_REVIEW",
    "Strict-mode security review",
    "严格模式安全审查",
  ],
  BUNDLED_ETS_PRACTICE_TEST_1: [
    "examples/ets-practice-test-1/README",
    "TOEFL iBT Practice Test 1 example",
    "TOEFL iBT Practice Test 1 示例",
  ],
  BUNDLED_ETS_PRACTICE_TEST_1_NOTICE: [
    "examples/ets-practice-test-1/NOTICE",
    "TOEFL iBT Practice Test 1 source notice",
    "TOEFL iBT Practice Test 1 来源声明",
  ],
  README: ["README", "Project overview", "项目介绍"],
  CONTRIBUTING: ["CONTRIBUTING", "Contributing", "贡献指南"],
  SECURITY: ["SECURITY", "Security policy", "安全政策"],
  CODE_OF_CONDUCT: ["CODE_OF_CONDUCT", "Code of conduct", "行为准则"],
  CHANGELOG: ["CHANGELOG", "Changelog", "变更记录"],
} as const;
export type DocumentId = keyof typeof documents;
type DocumentLocation = { id: DocumentId; hash: string };

function documentLocale(id: DocumentId, requested: Locale): Locale {
  return id === "README" ? requested : "en";
}

/** Resolve repository-relative Markdown links against a public logical path.
 * Never build a fetch path from unchecked Markdown text or a local filesystem URL.
 */
export function resolveDocumentationLink(
  href: string,
  current: DocumentId,
): { id: DocumentId; hash: string; locale?: Locale } | undefined {
  if (href.startsWith("#")) return { id: current, hash: href.slice(1) };
  if (/^[a-z][a-z\d+.-]*:|^\/\//i.test(href)) return undefined;
  try {
    const base = new URL(
      `https://documentation.invalid/${documents[current][0]}.md`,
    );
    const link = new URL(href, base);
    const path = decodeURIComponent(link.pathname).replace(/^\//, "");
    const apiRoute = path.match(/^api\/documentation\/(en|zh-CN)\/([^/]+)$/);
    if (apiRoute && Object.hasOwn(documents, apiRoute[2]))
      return {
        id: apiRoute[2] as DocumentId,
        locale: documentLocale(
          apiRoute[2] as DocumentId,
          apiRoute[1] as Locale,
        ),
        hash: link.hash.slice(1),
      };
    const suffix = path.endsWith(".zh-CN.md")
      ? ".zh-CN.md"
      : path.endsWith(".md")
        ? ".md"
        : "";
    if (!suffix) return undefined;
    const canonical = path.slice(0, -suffix.length);
    const id = (Object.keys(documents) as DocumentId[]).find(
      (key) => documents[key][0] === canonical,
    );
    return id
      ? {
          id,
          locale: documentLocale(id, suffix === ".zh-CN.md" ? "zh-CN" : "en"),
          hash: link.hash.slice(1),
        }
      : undefined;
  } catch {
    return undefined;
  }
}

type MarkdownNode = {
  type?: string;
  value?: string;
  children?: MarkdownNode[];
  data?: { hProperties?: Record<string, unknown> };
};
function textContent(node: MarkdownNode): string {
  return node.value || node.children?.map(textContent).join("") || "";
}
/** Give headings stable local anchors without enabling raw Markdown HTML. */
function documentationHeadings() {
  return (tree: MarkdownNode) => {
    const seen = new Map<string, number>();
    function visit(node: MarkdownNode) {
      if (node.type === "heading") {
        const base = textContent(node)
          .trim()
          .toLowerCase()
          .replace(/[^\p{L}\p{N}\s_-]/gu, "")
          .replace(/\s/g, "-");
        const count = seen.get(base) || 0;
        seen.set(base, count + 1);
        node.data = {
          ...node.data,
          hProperties: {
            ...node.data?.hProperties,
            id: `doc-${base}${count ? `-${count}` : ""}`,
          },
        };
      }
      node.children?.forEach(visit);
    }
    visit(tree);
  };
}

export default function Documentation({
  initialDocument,
  onBack,
}: {
  initialDocument: DocumentId;
  onBack: () => void;
}) {
  const { locale, t, setLocale } = useI18n();
  const [location, setLocation] = useState<DocumentLocation>({
    id: initialDocument,
    hash: "",
  });
  const [history, setHistory] = useState<DocumentLocation[]>([]);
  const [content, setContent] = useState<{
    id: DocumentId;
    locale: Locale;
    markdown: string;
  } | null>(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const article = useRef<HTMLElement>(null);
  const contentLocale = documentLocale(location.id, locale);
  const loaded =
    content?.id === location.id && content.locale === contentLocale;

  useEffect(() => {
    const controller = new AbortController();
    setError("");
    setContent(null);
    fetch(`/api/documentation/${contentLocale}/${location.id}`, {
      signal: controller.signal,
    })
      .then(async (response) => {
        const text = await response.text();
        if (!response.ok) {
          let message = "Documentation not found.";
          try {
            message = JSON.parse(text).error || message;
          } catch {
            /* Keep the readable fallback for non-JSON failures. */
          }
          throw new Error(message);
        }
        if (!controller.signal.aborted)
          setContent({
            id: location.id,
            locale: contentLocale,
            markdown: text,
          });
      })
      .catch((error) => {
        if (!controller.signal.aborted)
          setError(error instanceof Error ? error.message : String(error));
      });
    return () => controller.abort();
  }, [location.id, contentLocale, retry]);

  useEffect(() => {
    if (!loaded) return;
    let anchor = location.hash;
    try {
      anchor = decodeURIComponent(anchor);
    } catch {
      /* Malformed source anchors should not break reading. */
    }
    if (!anchor) {
      window.scrollTo({ top: 0, behavior: "instant" });
      return;
    }
    const target = document.getElementById(
      `doc-${anchor.replace(/^doc-/, "")}`,
    );
    target?.scrollIntoView?.({ block: "start", behavior: "instant" });
  }, [loaded, location, locale]);

  const navigate = (next: {
    id: DocumentId;
    hash: string;
    locale?: Locale;
  }) => {
    if (next.id !== location.id || next.hash !== location.hash) {
      setHistory((previous) => [...previous, location]);
      setLocation({ id: next.id, hash: next.hash });
    }
    if (next.id === "README" && next.locale) setLocale(next.locale);
  };
  const back = () => {
    const previous = history.at(-1);
    if (!previous) return onBack();
    setHistory((items) => items.slice(0, -1));
    setLocation(previous);
  };
  const title = documents[location.id][locale === "zh-CN" ? 2 : 1];
  return (
    <section
      className="documentation-view"
      aria-label={t("Documentation", "文档")}
    >
      <div className="documentation-toolbar">
        <Button kind="outline small" onClick={back}>
          {t("← Back", "← 返回")}
        </Button>
        <span className="documentation-breadcrumb">
          {t("Help & setup", "使用与导入指南")}{" "}
          <span aria-hidden="true">/</span> {title}
        </span>
        <button
          className="documentation-index-link"
          onClick={() => navigate({ id: "DOCUMENTATION_INDEX", hash: "" })}
        >
          {t("All documents", "全部文档")}
        </button>
      </div>
      {error ? (
        <div className="documentation-state" role="alert">
          <p>{localizeDynamic(error, locale)}</p>
          <Button kind="outline" onClick={() => setRetry((value) => value + 1)}>
            {t("Try again", "重试")}
          </Button>
        </div>
      ) : !loaded ? (
        <p className="documentation-state" role="status">
          {t("Loading documentation…", "正在读取文档…")}
        </p>
      ) : (
        <article
          className="documentation-markdown"
          ref={article}
          lang={contentLocale}
        >
          <Markdown
            skipHtml
            remarkPlugins={[remarkGfm, documentationHeadings]}
            components={{
              a: ({ href, children }) => {
                if (!href) return <span>{children}</span>;
                const target = resolveDocumentationLink(href, location.id);
                if (target)
                  return (
                    <a
                      href={`/api/documentation/${target.locale || locale}/${target.id}${target.hash ? `#${target.hash}` : ""}`}
                      onClick={(event) => {
                        event.preventDefault();
                        navigate(target);
                      }}
                    >
                      {children}
                    </a>
                  );
                if (/^https?:\/\/|^mailto:/i.test(href))
                  return (
                    <a href={href} target="_blank" rel="noopener noreferrer">
                      {children}
                    </a>
                  );
                return (
                  <span
                    className="documentation-local-reference"
                    title={t(
                      "Open this file in your local project folder.",
                      "请在本地项目文件夹中打开此文件。",
                    )}
                  >
                    {children}{" "}
                    <small>{t("(local file)", "（本地文件）")}</small>
                  </span>
                );
              },
              table: ({ children }) => (
                <div className="documentation-table">
                  <table>{children}</table>
                </div>
              ),
              img: ({ src, alt }) =>
                typeof src === "string" && /^https?:\/\//i.test(src) ? (
                  <img src={src} alt={alt || ""} loading="lazy" />
                ) : (
                  <span className="documentation-local-reference">
                    {alt || t("Local image", "本地图片")}
                  </span>
                ),
            }}
          >
            {content!.markdown}
          </Markdown>
        </article>
      )}
    </section>
  );
}
