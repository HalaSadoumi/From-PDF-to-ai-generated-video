import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../theme";
import { SceneLabel, WrappedText } from "../illustrations/primitives";

/** A 2x2 matrix: axes draw themselves, then each quadrant fills in. Suits
 * "there are four cases" content, which neither a list nor a flow expresses
 * well. */
export const QuadrantMatrix: React.FC<{
  label?: string;
  items: string[];
  primary: string;
  secondary: string;
  accent: string;
  durationInFrames: number;
}> = ({ label, items, primary, secondary, accent, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = frame / durationInFrames;
  const cells = items.slice(0, 4);
  const labelOpacity = interpolate(p, [0.02, 0.12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const half = 250;
  const axes = interpolate(p, [0.06, 0.3], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const positions = [
    { x: -half / 1.0, y: -half / 1.0 },
    { x: half / 1.0, y: -half / 1.0 },
    { x: -half / 1.0, y: half / 1.0 },
    { x: half / 1.0, y: half / 1.0 },
  ];

  return (
    <AbsoluteFill>
      {label && <SceneLabel text={label} opacity={labelOpacity} />}
      <svg width="100%" height="100%" viewBox="-960 -540 1920 1080">
        <g transform="translate(0 100)">
          {/* axes */}
          <line x1={-half * 2 * axes} y1={0} x2={half * 2 * axes} y2={0} stroke={accent} strokeWidth={4} opacity={0.7} />
          <line x1={0} y1={-half * 2 * axes} x2={0} y2={half * 2 * axes} stroke={accent} strokeWidth={4} opacity={0.7} />

          {cells.map((item, i) => {
            const s = spring({ frame: frame - (16 + i * 11), fps, config: { damping: 13 } });
            const pos = positions[i];
            return (
              <g key={i} opacity={s} transform={`translate(${pos.x} ${pos.y}) scale(${s})`}>
                <rect
                  x={-220}
                  y={-105}
                  width={440}
                  height={210}
                  rx={16}
                  fill={`${accent}1A`}
                  stroke={accent}
                  strokeWidth={3}
                />
                <WrappedText text={item} y={10} maxWidth={400} fontSize={28} fontWeight={700} maxLines={4} />
              </g>
            );
          })}

          {/* axis captions */}
          {primary && (
            <text x={0} y={-half * 2 - 34} textAnchor="middle" fill={COLORS.textDim} fontFamily={FONT} fontSize={25} fontWeight={700} opacity={axes}>
              {primary}
            </text>
          )}
          {secondary && (
            <text x={half * 2 + 26} y={8} textAnchor="start" fill={COLORS.textDim} fontFamily={FONT} fontSize={25} fontWeight={700} opacity={axes}>
              {secondary}
            </text>
          )}
        </g>
      </svg>
    </AbsoluteFill>
  );
};
