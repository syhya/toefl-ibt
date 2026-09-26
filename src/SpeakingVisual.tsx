import { useI18n } from "./i18n";

/** Neutral UI illustration, never presented as an original examiner video. */
export default function SpeakingVisual({
  interview,
  listening,
}: {
  interview: boolean;
  listening: boolean;
}) {
  const { t } = useI18n();
  return (
    <figure
      className={`speaking-role-visual ${listening ? "is-listening" : ""}`}
    >
      <svg viewBox="0 0 160 160" aria-hidden="true">
        <circle
          cx="80"
          cy="80"
          r="76"
          fill="#edf5f4"
          stroke="#8ab9b7"
          strokeWidth="2"
        />
        <circle cx="80" cy="61" r="24" fill="#467778" />
        <path d="M36 132c1-31 17-44 44-44s43 13 44 44" fill="#467778" />
        <path d="m62 90 18 20 18-20" fill="#edf5f4" />
      </svg>
      <figcaption>
        {interview ? t("Interviewer", "面试官") : t("Speaker", "说话人")}
      </figcaption>
      <div className="speaking-voice-bars" aria-hidden="true">
        {[0, 1, 2, 3, 4].map((i) => (
          <i key={i} style={{ animationDelay: `${i * 0.12}s` }} />
        ))}
      </div>
      <p>
        {listening
          ? t(
              "Listen to the original audio. Recording starts automatically afterward.",
              "请听原始录音，播放结束后自动开始录音。",
            )
          : t("Your turn. Speak now.", "轮到你了，请开始回答。")}
      </p>
    </figure>
  );
}
