import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../theme";
import { SceneLabel, WrappedText } from "../illustrations/primitives";

const PALETTE = [COLORS.accent, COLORS.accent2, COLORS.accent3, COLORS.accent];

/** Diagram: pillars rise one by one and a roof settles on top — the classic
 * "three foundations" explainer beat (used here for the C-I-D triad, but
 * works for any 2-4 named pillars). */
export const PillarsDiagram: React.FC<{
  label?: string;
  items: string[];
  roof?: string;
  durationInFrames: number;
}> = ({ label, items, roof, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = frame / durationInFrames;

  const pillars = items.slice(0, 4);
  const spacing = 380;
  const startX = -((pillars.length - 1) * spacing) / 2;

  const labelOpacity = interpolate(p, [0.02, 0.12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const roofProgress = interpolate(p, [0.62, 0.8], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill>
      {label && <SceneLabel text={label} opacity={labelOpacity} />}
      <svg width="100%" height="100%" viewBox="-960 -540 1920 1080">
        <g transform="translate(0 130)">
          {/* ground line */}
          <rect
            x={-760}
            y={180}
            width={1520}
            height={7}
            rx={3.5}
            fill={COLORS.textDim}
            opacity={interpolate(p, [0.05, 0.2], [0, 0.5], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}
          />

          {pillars.map((item, i) => {
            const delayFrames = 14 + i * 16;
            const s = spring({ frame: frame - delayFrames, fps, config: { damping: 13, mass: 0.8 } });
            const height = 250 * s;
            const color = PALETTE[i % PALETTE.length];
            const x = startX + i * spacing;
            return (
              <g key={i}>
                <rect
                  x={x - 96}
                  y={180 - height}
                  width={192}
                  height={height}
                  rx={14}
                  fill={`${color}2E`}
                  stroke={color}
                  strokeWidth={4}
                />
                <WrappedText
                  text={item}
                  x={x}
                  y={252}
                  maxWidth={spacing - 34}
                  fontSize={30}
                  fontWeight={800}
                  opacity={s}
                  maxLines={3}
                />
                <circle cx={x} cy={180 - height + 44} r={20 * s} fill={color} opacity={0.85} />
              </g>
            );
          })}

          {roof && (
            <g opacity={roofProgress} transform={`translate(0 ${interpolate(roofProgress, [0, 1], [-120, 0])})`}>
              <rect x={startX - 130} y={-114} width={(pillars.length - 1) * spacing + 260} height={68} rx={14} fill={`${COLORS.accent}33`} stroke={COLORS.accent} strokeWidth={4} />
              <WrappedText
                text={roof}
                y={-68}
                maxWidth={(pillars.length - 1) * spacing + 200}
                fontSize={34}
                fontWeight={800}
                maxLines={1}
              />
            </g>
          )}
        </g>
      </svg>
    </AbsoluteFill>
  );
};
