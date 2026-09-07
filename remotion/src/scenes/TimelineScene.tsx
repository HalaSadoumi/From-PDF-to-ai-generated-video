import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../theme";
import { SceneLabel, WrappedText } from "../illustrations/primitives";

const PALETTE = [COLORS.accent, COLORS.accent2, COLORS.accent3, COLORS.accent];

/** Sequential steps along a track that draws itself left to right, each step
 * popping in as the line reaches it. */
export const TimelineScene: React.FC<{ label?: string; items: string[]; durationInFrames: number }> = ({
  label,
  items,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = frame / durationInFrames;
  const steps = items.slice(0, 4);
  // La boîte s'agrandit avec le libellé : les étapes ne tiennent plus toujours
  // sur une ligne depuis que le planificateur écrit des formulations completes.
  const boxHeight = (t: string) => 62 + 30 * Math.min(2, Math.floor(t.length / 19));
  const labelOpacity = interpolate(p, [0.02, 0.12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const trackW = 1400;
  const startX = -trackW / 2;
  const lineProgress = interpolate(p, [0.08, 0.72], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const gap = steps.length > 1 ? trackW / (steps.length - 1) : 0;

  return (
    <AbsoluteFill>
      {label && <SceneLabel text={label} opacity={labelOpacity} />}
      <svg width="100%" height="100%" viewBox="-960 -540 1920 1080">
        <g transform="translate(0 90)">
          <rect x={startX} y={-5} width={trackW} height={10} rx={5} fill="rgba(255,255,255,0.10)" />
          <rect x={startX} y={-5} width={trackW * lineProgress} height={10} rx={5} fill={COLORS.accent} />

          {steps.map((item, i) => {
            const x = steps.length > 1 ? startX + i * gap : 0;
            const reach = steps.length > 1 ? i / (steps.length - 1) : 0;
            const active = lineProgress >= reach - 0.02;
            const s = spring({
              frame: frame - (durationInFrames * (0.08 + 0.64 * reach)),
              fps,
              config: { damping: 12 },
            });
            const color = PALETTE[i % PALETTE.length];
            const above = i % 2 === 0;
            return (
              <g key={i} opacity={active ? s : 0}>
                <circle cx={x} cy={0} r={30 * s} fill={color} stroke="#0A0E1A" strokeWidth={5} />
                <text
                  x={x}
                  y={9}
                  textAnchor="middle"
                  fill="#0A0E1A"
                  fontFamily={FONT}
                  fontSize={26}
                  fontWeight={900}
                  opacity={s}
                >
                  {i + 1}
                </text>
                <g transform={`translate(${x} ${above ? -70 : 70})`}>
                  <rect
                    x={-150}
                    y={above ? -40 - boxHeight(item) : 4}
                    width={300}
                    height={boxHeight(item)}
                    rx={14}
                    fill="#0A0E1A"
                    stroke={color}
                    strokeWidth={3}
                    opacity={s}
                  />
                  <WrappedText
                    text={item}
                    y={above ? -40 - boxHeight(item) / 2 : 4 + boxHeight(item) / 2}
                    maxWidth={272}
                    fontSize={26}
                    fontWeight={700}
                    opacity={s}
                    maxLines={3}
                  />
                </g>
              </g>
            );
          })}
        </g>
      </svg>
    </AbsoluteFill>
  );
};
