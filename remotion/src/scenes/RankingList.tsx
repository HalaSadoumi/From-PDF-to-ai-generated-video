import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../theme";
import { SceneLabel, WrappedText } from "../illustrations/primitives";

/** An ordered ranking: positions, names, and the value that ranks them.
 *
 * Distinct from a checklist, where order carries no meaning, and from a bar
 * chart, where the comparison is the point: here the rank itself is the
 * information — "premier pays africain", "deuxième pour les rançongiciels". */
export const RankingList: React.FC<{
  label?: string;
  items: string[];
  secondary?: string;
  accent?: string;
  durationInFrames: number;
}> = ({ label, items, secondary, accent = COLORS.accent, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = frame / durationInFrames;
  const labelOpacity = interpolate(p, [0.02, 0.12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const rows = items.slice(0, 5).filter((t) => t && t.trim());
  if (!rows.length) return null;

  const rowHeight = 104;
  const top = -((rows.length - 1) * rowHeight) / 2;

  return (
    <AbsoluteFill>
      {label && <SceneLabel text={label} opacity={labelOpacity} />}
      <svg width="100%" height="100%" viewBox="-960 -540 1920 1080">
        <g transform="translate(0 50)">
          {rows.map((row, i) => {
            const enter = spring({ frame: frame - (10 + i * 13), fps, config: { damping: 14 } });
            const y = top + i * rowHeight;
            const first = i === 0;
            // "18 000 détections au Maroc" — la valeur ouvre la ligne quand
            // elle existe, sinon toute la ligne est le libellé.
            const match = row.match(/^\s*([\d][\d\s.,]*\s*%?)\s+(.*)$/);
            const value = match ? match[1].trim() : "";
            const text = match ? match[2].trim() : row;

            return (
              <g key={i} opacity={enter} transform={`translate(${(1 - enter) * -60} ${y})`}>
                <rect
                  x={-620}
                  y={-40}
                  width={1240}
                  height={80}
                  rx={14}
                  fill={first ? `${accent}1F` : "rgba(255,255,255,0.05)"}
                  stroke={first ? accent : COLORS.cardBorder}
                  strokeWidth={first ? 3 : 2}
                />
                <circle cx={-560} cy={0} r={27} fill={first ? accent : "rgba(255,255,255,0.10)"} />
                <text
                  x={-560}
                  y={10}
                  textAnchor="middle"
                  fill={first ? "#0A0E1A" : COLORS.text}
                  fontFamily={FONT}
                  fontSize={27}
                  fontWeight={900}
                >
                  {i + 1}
                </text>
                <WrappedText
                  text={text}
                  x={-506}
                  y={2}
                  maxWidth={value ? 820 : 1080}
                  fontSize={27}
                  fontWeight={700}
                  anchor="start"
                  maxLines={2}
                />
                {value && (
                  <text
                    x={596}
                    y={11}
                    textAnchor="end"
                    fill={first ? accent : COLORS.textDim}
                    fontFamily={FONT}
                    fontSize={30}
                    fontWeight={900}
                  >
                    {value}
                  </text>
                )}
              </g>
            );
          })}
          {secondary && (
            <WrappedText
              text={secondary}
              y={top + rows.length * rowHeight + 34}
              maxWidth={1300}
              fontSize={26}
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
