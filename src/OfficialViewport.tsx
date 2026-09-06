import { useEffect, useState, type CSSProperties, type ReactNode } from "react";

/** ETS compat CSS fixes 1024px width; 50+30+2+686px make the 768px canvas. */
export default function OfficialViewport({
  active,
  children,
}: {
  active: boolean;
  children: ReactNode;
}) {
  const measure = () =>
    Math.min(1, window.innerWidth / 1024, window.innerHeight / 768);
  const [scale, setScale] = useState(measure);
  useEffect(() => {
    const resize = () => setScale(measure());
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
  }, []);
  return (
    <div
      className={active ? "official-viewport" : undefined}
      style={
        active ? ({ "--official-scale": scale } as CSSProperties) : undefined
      }
    >
      {children}
    </div>
  );
}
