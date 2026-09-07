import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../theme";
import { KeyPoints } from "../components/KeyPoints";
import { SceneLabel, WrappedText } from "../illustrations/primitives";

/** One proportion drawn as a share of a whole.
 *
 * Where stat_reveal isolates a number, this shows what the number is a
 * fraction *of* — the remainder stays visible as the unfilled arc, so "trente
 * deux pour cent des entreprises" reads as a part of a population rather than
 * a figure floating on screen. */
export const DonutShare: React.FC<{
  label?: string;
  primary: string;
  secondary?: string;
  items?: string[];
  accent?: string;
  durationInFrames: number;
}> = ({ label, primary, secondary, items = [], accent = COLORS.accent, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = frame / durationInFrames;
  const labelOpacity = interpolate(p, [0.02, 0.12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const match = primary.match(/([\d]+(?:[.,]\d+)?)/);
  const value = match ? parseFloat(match[1].replace(",", ".")) : 50;
  const suffix = primary.includes("%") ? "%" : primary.replace(match?.[0] ?? "", "").trim();

  const fill = interpolate(p, [0.08, 0.55], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const pop = spring({ frame: frame - 6, fps, config: { damping: 12 } });

  const radius = 190;
  const circumference = 2 * Math.PI * radius;
  const shown = Math.min(value, 100) / 100;
  const hasPoints = items.filter((t) => t && t.trim()).length > 0;

  return (
    <AbsoluteFill>
      {label && <SceneLabel text={label} opacity={labelOpacity} />}
      <svg width="100%" height="100%" viewBox="-960 -540 1920 1080">
        <g transform={hasPoints ? "translate(-420 50) scale(0.9)" : "translate(0 60)"}>
          {/* le tout */}
          <circle r={radius} fill="none" stroke="rgba(255,255,255,0.10)" strokeWidth={54} />
          {/* la part */}
          <circle
            r={radius}
            fill="none"
            stroke={accent}
            strokeWidth={54}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={circumference * (1 - shown * fill)}
            transform="rotate(-90)"
          />
          <text
            y={6}
            textAnchor="middle"
            fill={COLORS.text}
            fontFamily={FONT}
            fontSize={104}
            fontWeight={900}
            transform={`scale(${pop})`}
          >
            {`${Math.round(value * fill)}${suffix}`}
          </text>
          {secondary && (
            <WrappedText
              text={secondary}
              y={radius + 86}
              maxWidth={hasPoints ? 620 : 1100}
              fontSize={28}
              fontWeight={600}
              fill={COLORS.textDim}
              maxLines={2}
            />
          )}
        </g>
      </svg>
      <KeyPoints items={items} accent={accent} durationInFrames={durationInFrames} variant="panel" />
    </AbsoluteFill>
  );
};
