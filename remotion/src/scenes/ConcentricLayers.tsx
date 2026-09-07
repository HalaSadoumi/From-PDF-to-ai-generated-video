import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../theme";
import { SceneLabel, WrappedText } from "../illustrations/primitives";

const PALETTE = [COLORS.accent3, COLORS.accent2, COLORS.accent, COLORS.accent2];

/** Concentric protection layers building outward from the asset at the
 * centre — the "defense in depth" beat. */
export const ConcentricLayers: React.FC<{
  label?: string;
  items: string[];
  primary: string;
  durationInFrames: number;
}> = ({ label, items, primary, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = frame / durationInFrames;
  const layers = items.slice(0, 4);
  // Pastille de largeur variable : un libellé de plusieurs mots ne tient pas
  // dans une pastille de largeur fixe.
  const chipWidth = (t: string) => Math.min(560, Math.max(236, t.length * 14 + 44));
  const labelOpacity = interpolate(p, [0.02, 0.12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const corePulse = 1 + Math.sin(frame / 11) * 0.05;

  return (
    <AbsoluteFill>
      {label && <SceneLabel text={label} opacity={labelOpacity} />}
      <svg width="100%" height="100%" viewBox="-960 -540 1920 1080">
        <g transform="translate(0 80)">
          {layers
            .map((item, i) => ({ item, i }))
            .reverse()
            .map(({ item, i }) => {
              const delay = 12 + (layers.length - 1 - i) * 15;
              const s = spring({ frame: frame - delay, fps, config: { damping: 13 } });
              const radius = 120 + (i + 1) * 82;
              const color = PALETTE[i % PALETTE.length];
              return (
                <g key={i} opacity={s}>
                  <circle
                    cx={0}
                    cy={0}
                    r={radius * s}
                    fill="none"
                    stroke={color}
                    strokeWidth={4}
                    strokeDasharray="14 10"
                    opacity={0.85}
                  />
                  <rect
                    x={-chipWidth(item) / 2}
                    y={-radius * s - 22}
                    width={chipWidth(item)}
                    height={44}
                    rx={22}
                    fill="#0A0E1A"
                    stroke={color}
                    strokeWidth={3}
                  />
                  <WrappedText
                    text={item}
                    y={-radius * s}
                    maxWidth={chipWidth(item) - 26}
                    fontSize={24}
                    fontWeight={700}
                    maxLines={1}
                  />
                </g>
              );
            })}
          <g transform={`scale(${corePulse})`}>
            <circle r={94} fill={`${COLORS.accent}33`} stroke={COLORS.accent} strokeWidth={5} />
            <WrappedText text={primary || "Coeur"} y={10} maxWidth={168} fontSize={28} fontWeight={800} maxLines={2} />
          </g>
        </g>
      </svg>
    </AbsoluteFill>
  );
};
