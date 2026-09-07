import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { COLORS, FONT } from "../theme";
import { SceneLabel, WrappedText } from "../illustrations/primitives";

const PALETTE = [COLORS.accent, COLORS.accent2, COLORS.accent3, "#34D399", "#FBBF24"];

/** Several measured values compared as bars that grow to their share.
 *
 * The diagrams that came first all place text in boxes; a chapter citing
 * figures needs a shape that shows magnitude, not just names them. Each bar
 * grows in turn and its number counts up with it, so the comparison is read
 * rather than deduced.
 *
 * Items arrive as "84% Rançongiciel" — value first, then what it measures. */
export const BarChart: React.FC<{
  label?: string;
  items: string[];
  secondary?: string;
  accent?: string;
  durationInFrames: number;
}> = ({ label, items, secondary, durationInFrames }) => {
  const frame = useCurrentFrame();
  const p = frame / durationInFrames;
  const labelOpacity = interpolate(p, [0.02, 0.12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const entries = items
    .slice(0, 5)
    .map((raw) => {
      const match = raw.match(/^\s*([\d]+(?:[.,]\d+)?)\s*(%|)\s*[-:—]?\s*(.*)$/);
      const literal = match ? match[1] : "";
      const value = match ? parseFloat(literal.replace(",", ".")) : null;
      // Keep the source's precision. Rounding to an integer turned "0,86
      // mille milliards" into 1 and "10,93 millions" into 11 — the figure on
      // screen no longer matched the document it came from.
      const decimals = literal.includes(",") || literal.includes(".")
        ? literal.split(/[.,]/)[1].length
        : 0;
      const suffix = match ? match[2] : "";
      const caption = match && match[3] ? match[3].trim() : raw;
      return { value, decimals, suffix, caption };
    })
    .filter((e) => e.caption);

  if (!entries.length) return null;

  const largest = Math.max(...entries.map((e) => e.value ?? 0), 1);
  const rowHeight = 92;
  const top = -((entries.length - 1) * rowHeight) / 2;
  const trackX = -170;
  const trackW = 860;

  return (
    <AbsoluteFill>
      {label && <SceneLabel text={label} opacity={labelOpacity} />}
      <svg width="100%" height="100%" viewBox="-960 -540 1920 1080">
        <g transform="translate(-120 60)">
          {entries.map((entry, i) => {
            const start = 0.08 + i * 0.11;
            const grow = interpolate(p, [start, start + 0.28], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            const share = (entry.value ?? largest * 0.6) / largest;
            const width = trackW * share * grow;
            const colour = PALETTE[i % PALETTE.length];
            const shown =
              entry.value !== null
                ? `${(entry.value * grow).toFixed(entry.decimals).replace(".", ",")}${entry.suffix}`
                : "";
            const y = top + i * rowHeight;

            return (
              <g key={i} opacity={interpolate(grow, [0, 0.15], [0, 1], { extrapolateRight: "clamp" })}>
                <WrappedText
                  text={entry.caption}
                  x={trackX - 26}
                  y={y + 6}
                  maxWidth={470}
                  fontSize={27}
                  fontWeight={700}
                  anchor="end"
                  maxLines={2}
                />
                <rect x={trackX} y={y - 24} width={trackW} height={48} rx={10} fill="rgba(255,255,255,0.06)" />
                <rect
                  x={trackX}
                  y={y - 24}
                  width={Math.max(0, width)}
                  height={48}
                  rx={10}
                  fill={`${colour}55`}
                  stroke={colour}
                  strokeWidth={3}
                />
                {shown && (
                  <text
                    x={trackX + Math.max(width, 66) - 16}
                    y={y + 11}
                    textAnchor="end"
                    fill={COLORS.text}
                    fontFamily={FONT}
                    fontSize={30}
                    fontWeight={900}
                  >
                    {shown}
                  </text>
                )}
              </g>
            );
          })}
        </g>
        {secondary && (
          <WrappedText
            text={secondary}
            y={top + entries.length * rowHeight + 110}
            maxWidth={1400}
            fontSize={26}
            fontWeight={600}
            fill={COLORS.textDim}
            maxLines={2}
          />
        )}
      </svg>
    </AbsoluteFill>
  );
};
