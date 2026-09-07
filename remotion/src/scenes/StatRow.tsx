import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../theme";
import { SceneLabel, WrappedText } from "../illustrations/primitives";

const PALETTE = [COLORS.accent, COLORS.accent2, COLORS.accent3, "#34D399"];

/** Several figures side by side, each counting up with a bar beneath it.
 * Where stat_reveal isolates one number, this is for passages that cite
 * several in a row. */
export const StatRow: React.FC<{
  label?: string;
  items: string[];
  secondary: string;
  durationInFrames: number;
}> = ({ label, items, secondary, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = frame / durationInFrames;
  const entries = items.slice(0, 4);
  const labelOpacity = interpolate(p, [0.02, 0.12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const spacing = entries.length > 1 ? Math.min(460, 1560 / entries.length) : 0;
  const startX = -((entries.length - 1) * spacing) / 2;

  return (
    <AbsoluteFill>
      {label && <SceneLabel text={label} opacity={labelOpacity} />}
      <svg width="100%" height="100%" viewBox="-960 -540 1920 1080">
        <g transform="translate(0 110)">
          {entries.map((entry, i) => {
            // "61% messagerie" -> value 61%, caption "messagerie"
            const match = entry.match(/^\s*([\d]+(?:[.,]\d+)?\s*%?)\s*[-:—]?\s*(.*)$/);
            const rawValue = match ? match[1].trim() : entry;
            const caption = match && match[2] ? match[2].trim() : "";

            const numMatch = rawValue.match(/[\d.,]+/);
            const numeric = numMatch ? parseFloat(numMatch[0].replace(",", ".")) : null;
            const suffix = numeric !== null ? rawValue.slice(numMatch![0].length) : "";

            const delay = 10 + i * 12;
            const s = spring({ frame: frame - delay, fps, config: { damping: 13 } });
            const count = interpolate(frame - delay, [0, 34], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            const shown =
              numeric !== null
                ? `${Math.round(numeric * count)}${suffix}`
                : rawValue;

            const color = PALETTE[i % PALETTE.length];
            const x = startX + i * spacing;
            const barMax = 180;
            const barH = numeric !== null ? barMax * count * Math.min(1, numeric / 100 || 0.6) : barMax * count * 0.6;

            return (
              <g key={i} opacity={s} transform={`translate(${x} 0)`}>
                <rect
                  x={-42}
                  y={60 - barH}
                  width={84}
                  height={barH}
                  rx={10}
                  fill={`${color}44`}
                  stroke={color}
                  strokeWidth={3}
                />
                <text
                  y={-10}
                  textAnchor="middle"
                  fill={color}
                  fontFamily={FONT}
                  fontSize={62}
                  fontWeight={900}
                  transform={`scale(${s})`}
                >
                  {shown}
                </text>
                {caption && (
                  <WrappedText
                    text={caption}
                    y={138}
                    maxWidth={(spacing || 460) - 30}
                    fontSize={25}
                    fontWeight={600}
                    maxLines={3}
                  />
                )}
              </g>
            );
          })}

          {secondary && (
            <WrappedText
              text={secondary}
              y={244}
              maxWidth={1500}
              fontSize={27}
              fontWeight={600}
              fill={COLORS.textDim}
              maxLines={2}
            />
          )}
        </g>
      </svg>
    </AbsoluteFill>
  );
};
