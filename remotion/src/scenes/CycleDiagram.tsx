import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../theme";
import { SceneLabel, WrappedText } from "../illustrations/primitives";

/** A closed loop: steps arranged around a circle with arcs running between
 * them and a rotating highlight. Reads as "this repeats", which a straight
 * timeline cannot convey. */
export const CycleDiagram: React.FC<{
  label?: string;
  items: string[];
  primary: string;
  accent: string;
  durationInFrames: number;
}> = ({ label, items, primary, accent, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = frame / durationInFrames;
  const steps = items.slice(0, 5);
  const labelOpacity = interpolate(p, [0.02, 0.12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const radius = 235;
  const count = Math.max(1, steps.length);
  const angleFor = (i: number) => (i / count) * Math.PI * 2 - Math.PI / 2;

  // A marker travelling the loop, so the cycle reads as continuous.
  const travel = (p * count) % count;

  return (
    <AbsoluteFill>
      {label && <SceneLabel text={label} opacity={labelOpacity} />}
      <svg width="100%" height="100%" viewBox="-960 -540 1920 1080">
        <g transform="translate(0 90)">
          <circle r={radius} fill="none" stroke={accent} strokeWidth={3} strokeDasharray="10 12" opacity={0.4} />

          {steps.map((_, i) => {
            const a1 = angleFor(i);
            const a2 = angleFor(i + 1);
            const progress = interpolate(p, [0.15 + i * 0.1, 0.35 + i * 0.1], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            const arcR = radius;
            const x1 = Math.cos(a1) * arcR;
            const y1 = Math.sin(a1) * arcR;
            const x2 = Math.cos(a2) * arcR;
            const y2 = Math.sin(a2) * arcR;
            const arcLen = (2 * Math.PI * arcR) / count;
            return (
              <path
                key={`arc${i}`}
                d={`M ${x1} ${y1} A ${arcR} ${arcR} 0 0 1 ${x2} ${y2}`}
                fill="none"
                stroke={accent}
                strokeWidth={7}
                strokeLinecap="round"
                strokeDasharray={arcLen}
                strokeDashoffset={arcLen * (1 - progress)}
              />
            );
          })}

          {steps.map((item, i) => {
            const a = angleFor(i);
            const x = Math.cos(a) * radius;
            const y = Math.sin(a) * radius;
            const s = spring({ frame: frame - (10 + i * 12), fps, config: { damping: 12 } });
            const isLive = Math.floor(travel) === i;
            return (
              <g key={i} opacity={s} transform={`translate(${x} ${y}) scale(${s * (isLive ? 1.12 : 1)})`}>
                <circle r={62} fill="#0A0E1A" stroke={accent} strokeWidth={isLive ? 6 : 3} />
                <text
                  y={8}
                  textAnchor="middle"
                  fill={accent}
                  fontFamily={FONT}
                  fontSize={30}
                  fontWeight={800}
                >
                  {i + 1}
                </text>
                <WrappedText
                  text={item}
                  y={Math.sin(a) > 0.2 ? 122 : -88}
                  maxWidth={300}
                  fontSize={26}
                  fontWeight={700}
                  maxLines={2}
                />
              </g>
            );
          })}

          {primary && (
            <WrappedText text={primary} y={10} maxWidth={300} fontSize={34} fontWeight={800} maxLines={2} />
          )}
        </g>
      </svg>
    </AbsoluteFill>
  );
};
