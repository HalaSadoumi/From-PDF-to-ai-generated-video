import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../theme";
import { SceneLabel, ServerStack, WrappedText } from "../illustrations/primitives";

const PALETTE = [COLORS.accent, COLORS.accent2, COLORS.accent3];

/** Network segmentation: zones appear side by side and a firewall barrier
 * drops between them, blocking lateral movement. */
export const SeparatedGroups: React.FC<{
  label?: string;
  items: string[];
  secondary: string;
  durationInFrames: number;
}> = ({ label, items, secondary, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = frame / durationInFrames;
  const zones = items.slice(0, 3);
  const labelOpacity = interpolate(p, [0.02, 0.12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const spacing = zones.length > 2 ? 580 : 640;
  const startX = -((zones.length - 1) * spacing) / 2;
  const barrierProgress = interpolate(p, [0.45, 0.68], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill>
      {label && <SceneLabel text={label} opacity={labelOpacity} />}
      <svg width="100%" height="100%" viewBox="-960 -540 1920 1080">
        <g transform="translate(0 90)">
          {zones.map((zone, i) => {
            const s = spring({ frame: frame - (10 + i * 14), fps, config: { damping: 13 } });
            const x = startX + i * spacing;
            const color = PALETTE[i % PALETTE.length];
            return (
              <g key={i} opacity={s} transform={`translate(${x} 0) scale(${s})`}>
                <rect x={-230} y={-215} width={460} height={430} rx={22} fill={`${color}14`} stroke={color} strokeWidth={4} strokeDasharray="16 10" />
                <ServerStack x={0} y={-30} color={color} />
                <WrappedText text={zone} y={185} maxWidth={420} fontSize={30} fontWeight={800} maxLines={3} />
              </g>
            );
          })}

          {/* Firewall barriers dropping between adjacent zones */}
          {zones.slice(0, -1).map((_, i) => {
            const x = startX + i * spacing + spacing / 2;
            const h = 470 * barrierProgress;
            return (
              <g key={`b${i}`} opacity={barrierProgress}>
                <rect x={x - 13} y={-235} width={26} height={h} rx={13} fill={COLORS.accent3} opacity={0.85} />
                {[0, 1, 2, 3].map((k) => (
                  <rect key={k} x={x - 30} y={-215 + k * 115} width={60} height={16} rx={8} fill={COLORS.accent3} opacity={barrierProgress * 0.9} />
                ))}
              </g>
            );
          })}

          {secondary && (
            <text y={280} textAnchor="middle" fill={COLORS.textDim} fontFamily={FONT} fontSize={30} fontWeight={700} opacity={barrierProgress}>
              {secondary}
            </text>
          )}
        </g>
      </svg>
    </AbsoluteFill>
  );
};
