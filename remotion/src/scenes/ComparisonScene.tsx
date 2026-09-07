import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../theme";
import { Figure, SceneLabel, WrappedText } from "../illustrations/primitives";

/** Two opposed situations side by side — bad practice (left, red, cross)
 * vs good practice (right, blue, check). Slides in from both edges. */
export const ComparisonScene: React.FC<{ label?: string; items: string[]; durationInFrames: number }> = ({
  label,
  items,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = frame / durationInFrames;
  const left = items[0] ?? "À éviter";
  const right = items[1] ?? "À faire";

  const sLeft = spring({ frame: frame - 8, fps, config: { damping: 13 } });
  const sRight = spring({ frame: frame - 22, fps, config: { damping: 13 } });
  const labelOpacity = interpolate(p, [0.02, 0.12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const side = (
    x: number,
    s: number,
    text: string,
    color: string,
    good: boolean,
    fromLeft: boolean
  ) => (
    <g transform={`translate(${x + (1 - s) * (fromLeft ? -320 : 320)} 60)`} opacity={s}>
      <rect x={-300} y={-210} width={600} height={420} rx={24} fill={`${color}1A`} stroke={color} strokeWidth={4} />
      <Figure x={0} y={-10} scale={1.15} variant={good ? "neutral" : "worried"} />
      <g transform="translate(0 130)">
        <circle r={38} fill={color} />
        {good ? (
          <path d="M -17 2 L -5 16 L 18 -12" stroke="#0A0E1A" strokeWidth={7} fill="none" strokeLinecap="round" strokeLinejoin="round" />
        ) : (
          <path d="M -14 -14 L 14 14 M 14 -14 L -14 14" stroke="#0A0E1A" strokeWidth={7} strokeLinecap="round" />
        )}
      </g>
      <WrappedText text={text} y={200} maxWidth={548} fontSize={30} fontWeight={800} maxLines={3} />
    </g>
  );

  return (
    <AbsoluteFill>
      {label && <SceneLabel text={label} opacity={labelOpacity} />}
      <svg width="100%" height="100%" viewBox="-960 -540 1920 1080">
        {side(-340, sLeft, left, COLORS.accent3, false, true)}
        {side(340, sRight, right, COLORS.accent, true, false)}
      </svg>
    </AbsoluteFill>
  );
};
