import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS } from "../theme";
import { SceneLabel, WrappedText } from "../illustrations/primitives";

/** Two notions and how they relate: one contained in the other, or the two
 * overlapping.
 *
 * `comparison` sets two things side by side as alternatives; this shows a
 * relationship of scope — "la cybersécurité est une sous-partie de la sécurité
 * des systèmes d'information" is a containment, not a choice, and drawing it
 * as two facing cards said the opposite of what was meant.
 *
 * items[0] is the larger set, items[1] the one inside or overlapping it. */
export const VennOverlap: React.FC<{
  label?: string;
  items: string[];
  primary?: string;
  secondary?: string;
  accent?: string;
  durationInFrames: number;
}> = ({ label, items, primary, secondary, accent = COLORS.accent, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = frame / durationInFrames;
  const labelOpacity = interpolate(p, [0.02, 0.12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const outer = items[0] || primary || "Ensemble";
  const inner = items[1] || secondary || "Sous-ensemble";
  const bigIn = spring({ frame: frame - 8, fps, config: { damping: 14 } });
  const smallIn = spring({ frame: frame - 26, fps, config: { damping: 13 } });

  return (
    <AbsoluteFill>
      {label && <SceneLabel text={label} opacity={labelOpacity} />}
      <svg width="100%" height="100%" viewBox="-960 -540 1920 1080">
        <g transform="translate(0 60)">
          <g opacity={bigIn} transform={`scale(${0.9 + 0.1 * bigIn})`}>
            <circle r={280} fill={`${COLORS.accent2}18`} stroke={COLORS.accent2} strokeWidth={4} />
            <WrappedText
              text={outer}
              y={-198}
              maxWidth={470}
              fontSize={30}
              fontWeight={800}
              fill={COLORS.accent2}
              maxLines={2}
            />
          </g>

          <g opacity={smallIn} transform={`translate(0 60) scale(${0.9 + 0.1 * smallIn})`}>
            <circle r={148} fill={`${accent}30`} stroke={accent} strokeWidth={4} />
            <WrappedText
              text={inner}
              y={4}
              maxWidth={252}
              fontSize={27}
              fontWeight={800}
              maxLines={3}
            />
          </g>

          {items[2] && (
            <WrappedText
              text={items[2]}
              y={370}
              maxWidth={1200}
              fontSize={26}
              fontWeight={600}
              fill={COLORS.textDim}
              opacity={smallIn}
              maxLines={2}
            />
          )}
        </g>
      </svg>
    </AbsoluteFill>
  );
};
