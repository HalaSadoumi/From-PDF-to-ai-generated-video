import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS } from "../theme";
import { SceneLabel, WrappedText } from "../illustrations/primitives";

const PALETTE = ["#34D399", COLORS.accent, COLORS.accent2, COLORS.accent3];

/** Levels stacked by weight: a base that carries the rest, a summit that
 * depends on it.
 *
 * `pillars` shows components standing side by side, `hierarchy` shows what
 * belongs to what; this shows precedence — foundations first, then what they
 * make possible. Items are read from the base upwards, so items[0] is the
 * widest level.
 */
export const PyramidLevels: React.FC<{
  label?: string;
  items: string[];
  primary?: string;
  secondary?: string;
  accent?: string;
  durationInFrames: number;
}> = ({ label, items, secondary, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = frame / durationInFrames;
  const labelOpacity = interpolate(p, [0.02, 0.12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const levels = items.slice(0, 4).filter((t) => t && t.trim());
  if (!levels.length) return null;

  const height = 96;
  const gap = 12;
  const base = 980;
  const step = base / (levels.length + 1);
  const bottom = ((levels.length - 1) * (height + gap)) / 2 + 40;

  return (
    <AbsoluteFill>
      {label && <SceneLabel text={label} opacity={labelOpacity} />}
      <svg width="100%" height="100%" viewBox="-960 -540 1920 1080">
        <g transform="translate(0 40)">
          {levels.map((level, i) => {
            // La base apparaît en premier : on construit du sol vers le sommet.
            const enter = spring({ frame: frame - (10 + i * 16), fps, config: { damping: 14 } });
            const width = base - i * step;
            const y = bottom - i * (height + gap);
            const colour = PALETTE[i % PALETTE.length];

            return (
              <g key={i} opacity={enter} transform={`translate(0 ${(1 - enter) * 30})`}>
                <polygon
                  points={[
                    `${-width / 2},${y}`,
                    `${width / 2},${y}`,
                    `${(width - step) / 2},${y - height}`,
                    `${-(width - step) / 2},${y - height}`,
                  ].join(" ")}
                  fill={`${colour}26`}
                  stroke={colour}
                  strokeWidth={3}
                />
                <WrappedText
                  text={level}
                  y={y - height / 2 + 6}
                  maxWidth={width - step - 50}
                  fontSize={26}
                  fontWeight={700}
                  maxLines={2}
                />
              </g>
            );
          })}
          {secondary && (
            <WrappedText
              text={secondary}
              y={bottom + 84}
              maxWidth={1200}
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
