import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../theme";
import { KeyPoints } from "../components/KeyPoints";
import { SceneLabel } from "../illustrations/primitives";

/** A key figure counting up inside a progress ring that fills as it counts,
 * with its context label underneath. */
export const StatReveal: React.FC<{
  label?: string;
  primary: string;
  secondary: string;
  items?: string[];
  accent?: string;
  durationInFrames: number;
}> = ({ label, primary, secondary, items = [], accent = COLORS.accent, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = frame / durationInFrames;
  const labelOpacity = interpolate(p, [0.02, 0.12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const numMatch = primary.match(/[\d.,]+/);
  const numeric = numMatch ? parseFloat(numMatch[0].replace(",", ".")) : null;
  const suffix = numeric !== null ? primary.slice(numMatch![0].length).trim() : "";
  const countProgress = interpolate(frame, [6, Math.max(20, durationInFrames * 0.45)], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const shown =
    numeric !== null
      ? `${Math.round(numeric * countProgress * 10) / 10}`.replace(/\.0$/, "") + suffix
      : primary;

  const ringR = 210;
  const circumference = 2 * Math.PI * ringR;
  const isPercent = suffix.includes("%") || primary.includes("%");
  const ringFill = isPercent && numeric !== null ? (numeric / 100) * countProgress : countProgress;
  const pop = spring({ frame: frame - 4, fps, config: { damping: 11 } });
  // With supporting points beside it, the ring moves off-centre and shrinks
  // so the two halves of the screen read as one composition.
  const hasPoints = items.filter((t) => t && t.trim()).length > 0;

  return (
    <AbsoluteFill>
      {label && <SceneLabel text={label} opacity={labelOpacity} />}
      <svg width="100%" height="100%" viewBox="-960 -540 1920 1080">
        <g transform={hasPoints ? "translate(-430 40) scale(0.82)" : "translate(0 70)"}>
          <circle r={ringR} fill="none" stroke="rgba(255,255,255,0.09)" strokeWidth={22} />
          <circle
            r={ringR}
            fill="none"
            stroke={COLORS.accent}
            strokeWidth={22}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={circumference * (1 - ringFill)}
            transform="rotate(-90)"
            opacity={0.95}
          />
          <text
            y={22}
            textAnchor="middle"
            fill={COLORS.text}
            fontFamily={FONT}
            fontSize={128}
            fontWeight={900}
            transform={`scale(${pop})`}
          >
            {shown}
          </text>
          {secondary && (
            <text y={ringR + 92} textAnchor="middle" fill={COLORS.textDim} fontFamily={FONT} fontSize={36} fontWeight={700}>
              {secondary}
            </text>
          )}
        </g>
      </svg>
      <KeyPoints items={items} accent={accent} durationInFrames={durationInFrames} variant="panel" />
    </AbsoluteFill>
  );
};
