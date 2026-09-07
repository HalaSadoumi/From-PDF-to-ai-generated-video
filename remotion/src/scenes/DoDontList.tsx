import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../theme";
import { SceneLabel, WrappedText } from "../illustrations/primitives";

const GREEN = "#34D399";
const RED = "#F87171";

/** Two facing columns — what to do, what to avoid — items appearing in
 * alternation. Distinct from a two-panel comparison: several points per side,
 * and the ticks/crosses carry the meaning. */
export const DoDontList: React.FC<{
  label?: string;
  items: string[];
  primary: string;
  secondary: string;
  durationInFrames: number;
}> = ({ label, items, primary, secondary, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = frame / durationInFrames;
  const labelOpacity = interpolate(p, [0.02, 0.12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  // Odd indices go to the "avoid" column, even to the "do" column.
  const dos = items.filter((_, i) => i % 2 === 0).slice(0, 3);
  const donts = items.filter((_, i) => i % 2 === 1).slice(0, 3);

  const column = (
    entries: string[],
    x: number,
    color: string,
    heading: string,
    good: boolean,
    delayBase: number
  ) => (
    <g transform={`translate(${x} 0)`}>
      <g transform="translate(0 -190)">
        <rect x={-250} y={-40} width={500} height={72} rx={14} fill={`${color}22`} stroke={color} strokeWidth={3} />
        <text y={8} textAnchor="middle" fill={color} fontFamily={FONT} fontSize={30} fontWeight={800}>
          {heading}
        </text>
      </g>
      {entries.map((entry, i) => {
        const s = spring({ frame: frame - (delayBase + i * 16), fps, config: { damping: 13 } });
        return (
          <g key={i} opacity={s} transform={`translate(0 ${-70 + i * 118}) scale(${s})`}>
            <rect x={-250} y={-44} width={500} height={92} rx={13} fill="rgba(255,255,255,0.05)" stroke={COLORS.cardBorder} strokeWidth={2} />
            <g transform="translate(-198 2)">
              <circle r={25} fill={color} />
              {good ? (
                <path d="M -11 1 L -2 11 L 12 -9" stroke="#0A0E1A" strokeWidth={6} fill="none" strokeLinecap="round" strokeLinejoin="round" />
              ) : (
                <path d="M -9 -9 L 9 9 M 9 -9 L -9 9" stroke="#0A0E1A" strokeWidth={6} strokeLinecap="round" />
              )}
            </g>
            <WrappedText
              text={entry}
              x={-152}
              y={11}
              maxWidth={390}
              fontSize={25}
              fontWeight={600}
              anchor="start"
              maxLines={2}
            />
          </g>
        );
      })}
    </g>
  );

  return (
    <AbsoluteFill>
      {label && <SceneLabel text={label} opacity={labelOpacity} />}
      <svg width="100%" height="100%" viewBox="-960 -540 1920 1080">
        <g transform="translate(0 120)">
          {column(dos, -290, GREEN, primary || "À faire", true, 12)}
          {column(donts, 290, RED, secondary || "À éviter", false, 20)}
        </g>
      </svg>
    </AbsoluteFill>
  );
};
