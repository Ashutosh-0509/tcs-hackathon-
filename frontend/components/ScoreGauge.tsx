"use client";

import { useEffect, useState } from "react";
import { toneFor } from "@/lib/labels";
import type { ReliabilityLabel } from "@/lib/types";

/** 240° radial arc, animated sweep, tabular number in the centre. */
export function ScoreGauge({
  score,
  label,
  size = 168,
}: {
  score: number;
  label: ReliabilityLabel;
  size?: number;
}) {
  const [shown, setShown] = useState(0);
  useEffect(() => {
    const start = performance.now();
    const dur = 650;
    let raf = 0;
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / dur);
      const eased = 1 - Math.pow(1 - p, 3);
      setShown(Math.round(eased * score));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [score]);

  const stroke = 10;
  const r = (size - stroke) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const sweep = 240;
  const startAngle = 150; // degrees, measured clockwise from +x
  const circ = 2 * Math.PI * r;
  const arcLen = (sweep / 360) * circ;
  const progress = (shown / 100) * arcLen;
  const tone = toneFor(label);

  return (
    <div className="relative grid place-items-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <g transform={`rotate(${startAngle} ${cx} ${cy})`}>
          <circle
            cx={cx}
            cy={cy}
            r={r}
            fill="none"
            strokeWidth={stroke}
            strokeLinecap="round"
            className="stroke-line"
            strokeDasharray={`${arcLen} ${circ}`}
          />
          <circle
            cx={cx}
            cy={cy}
            r={r}
            fill="none"
            strokeWidth={stroke}
            strokeLinecap="round"
            className={tone.ring}
            strokeDasharray={`${progress} ${circ}`}
            style={{ transition: "stroke-dasharray 60ms linear" }}
          />
        </g>
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="tnum text-4xl font-semibold leading-none tracking-tight">
          {shown}
        </span>
        <span className="mt-1 text-2xs font-medium uppercase tracking-widest text-ink-faint">
          / 100
        </span>
      </div>
    </div>
  );
}
