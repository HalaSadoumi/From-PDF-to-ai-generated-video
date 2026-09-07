import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS } from "../theme";
import { SceneLabel, WrappedText } from "../illustrations/primitives";

const PALETTE = [COLORS.accent, COLORS.accent2, COLORS.accent3, "#34D399"];

/** Successive stages that narrow: a filter, a selection, a defence in depth.
 *
 * A timeline says "then"; this says "and fewer get through". It suits any
 * passage where each step keeps only part of what the previous one passed —
 * filtering suspicious mail, granting access, qualifying a risk. */
export const FunnelStages: React.FC<{
  label?: string;
  items: string[];
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

  const stages = items.slice(0, 4).filter((t) => t && t.trim());
  if (!stages.length) return null;

  const widest = 940;
  const narrowest = 380;
  const stageHeight = 108;
  const gap = 18;
  const top = -((stages.length * (stageHeight + gap) - gap) / 2);

  return (
    <AbsoluteFill>
      {label && <SceneLabel text={label} opacity={labelOpacity} />}
      <svg width="100%" height="100%" viewBox="-960 -540 1920 1080">
        <g transform="translate(0 60)">
          {stages.map((stage, i) => {
            const enter = spring({ frame: frame - (10 + i * 15), fps, config: { damping: 14 } });
            const ratio = stages.length === 1 ? 0 : i / (stages.length - 1);
            const width = widest - (widest - narrowest) * ratio;
            const nextRatio = stages.length === 1 ? 0 : (i + 1) / (stages.length - 1);
            const nextWidth = widest - (widest - narrowest) * Math.min(nextRatio, 1);
            const y = top + i * (stageHeight + gap);
            const colour = PALETTE[i % PALETTE.length];

            // Trapèze : le bas est plus étroit que le haut, ce qui donne
            // l'entonnoir sans dessiner de flèches.
            const points = [
              `${-width / 2},${y}`,
              `${width / 2},${y}`,
              `${nextWidth / 2},${y + stageHeight}`,
              `${-nextWidth / 2},${y + stageHeight}`,
            ].join(" ");

            return (
              <g key={i} opacity={enter} transform={`translate(0 ${(1 - enter) * -24})`}>
                <polygon points={points} fill={`${colour}26`} stroke={colour} strokeWidth={3} />
                <WrappedText
                  text={stage}
                  y={y + stageHeight / 2 + 4}
                  maxWidth={nextWidth - 60}
                  fontSize={27}
                  fontWeight={700}
                  maxLines={2}
                />
              </g>
            );
          })}
          {secondary && (
            <WrappedText
              text={secondary}
              y={top + stages.length * (stageHeight + gap) + 54}
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
