import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../theme";
import { SceneLabel, WrappedText } from "../illustrations/primitives";

/** A root box with branches drawing down to its children. Expresses
 * containment or hierarchy ("X comprises A, B, C"), which a flat list flattens
 * away. */
export const HierarchyTree: React.FC<{
  label?: string;
  items: string[];
  primary: string;
  accent: string;
  durationInFrames: number;
}> = ({ label, items, primary, accent, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = frame / durationInFrames;
  const children = items.slice(0, 4);
  const labelOpacity = interpolate(p, [0.02, 0.12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const rootIn = spring({ frame: frame - 6, fps, config: { damping: 13 } });
  const branchProgress = interpolate(p, [0.22, 0.48], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const spacing = children.length > 1 ? Math.min(430, 1500 / children.length) : 0;
  const startX = -((children.length - 1) * spacing) / 2;
  const childY = 210;

  return (
    <AbsoluteFill>
      {label && <SceneLabel text={label} opacity={labelOpacity} />}
      <svg width="100%" height="100%" viewBox="-960 -540 1920 1080">
        <g transform="translate(0 20)">
          {/* root */}
          <g opacity={rootIn} transform={`scale(${rootIn})`}>
            <rect x={-260} y={-165} width={520} height={104} rx={16} fill={`${accent}26`} stroke={accent} strokeWidth={4} />
            <WrappedText text={primary || "Ensemble"} y={-105} maxWidth={470} fontSize={32} fontWeight={800} maxLines={2} />
          </g>

          {/* trunk */}
          <line x1={0} y1={-61} x2={0} y2={-61 + 80 * branchProgress} stroke={accent} strokeWidth={4} />

          {children.map((child, i) => {
            const x = startX + i * spacing;
            const s = spring({ frame: frame - (26 + i * 12), fps, config: { damping: 13 } });
            const horiz = interpolate(branchProgress, [0.4, 1], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
            return (
              <g key={i}>
                {/* horizontal then vertical connector */}
                <line x1={0} y1={19} x2={x * horiz} y2={19} stroke={accent} strokeWidth={4} opacity={horiz} />
                <line x1={x} y1={19} x2={x} y2={19 + (childY - 19 - 62) * horiz} stroke={accent} strokeWidth={4} opacity={horiz} />
                <g opacity={s} transform={`translate(${x} ${childY}) scale(${s})`}>
                  <rect x={-185} y={-62} width={370} height={124} rx={14} fill="rgba(255,255,255,0.06)" stroke={accent} strokeWidth={3} />
                  <WrappedText text={child} y={10} maxWidth={336} fontSize={27} fontWeight={700} maxLines={3} />
                </g>
              </g>
            );
          })}
        </g>
      </svg>
    </AbsoluteFill>
  );
};
