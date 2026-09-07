import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { COLORS } from "../theme";

/** A "living" background: three softly glowing color orbs that drift slowly
 * (continuous motion, not just an entrance animation), plus a faint dot grid
 * for texture. Rendered behind every scene so nothing ever sits on a flat,
 * static panel. */
export const AnimatedBackground: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / 30;

  const orb = (
    color: string,
    baseX: number,
    baseY: number,
    speedX: number,
    speedY: number,
    phase: number,
    size: number
  ): React.CSSProperties => ({
    position: "absolute",
    width: size,
    height: size,
    borderRadius: "50%",
    background: `radial-gradient(circle, ${color}66 0%, transparent 70%)`,
    left: `${baseX + Math.sin(t * speedX + phase) * 12}%`,
    top: `${baseY + Math.cos(t * speedY + phase) * 12}%`,
    filter: "blur(50px)",
    transform: "translate(-50%, -50%)",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bg, overflow: "hidden" }}>
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage:
            "radial-gradient(rgba(255,255,255,0.055) 1.5px, transparent 1.5px)",
          backgroundSize: "42px 42px",
        }}
      />
      <div style={orb(COLORS.accent, 25, 30, 0.35, 0.28, 0, 620)} />
      <div style={orb(COLORS.accent2, 78, 68, 0.25, 0.32, 2, 560)} />
      <div style={orb(COLORS.accent3, 55, 15, 0.3, 0.22, 4, 420)} />
    </AbsoluteFill>
  );
};
