import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../theme";
import { KeyPoints } from "../components/KeyPoints";
import { AnimatedArrow, DeviceBox, Envelope, Figure, SceneLabel } from "../illustrations/primitives";

/** Character scenario: an attacker sends a malicious email, it travels to a
 * user's machine, the user reacts, and an alert fires. Staged across the
 * scene's whole duration so it plays out like a little story rather than
 * appearing all at once. */
export const ActorActionTarget: React.FC<{
  label?: string;
  primary: string;
  secondary: string;
  items?: string[];
  accent?: string;
  durationInFrames: number;
}> = ({ label, primary, secondary, items = [], accent = COLORS.accent, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = frame / durationInFrames; // 0..1 through the scene

  const attackerIn = spring({ frame, fps, config: { damping: 12 } });
  const victimIn = spring({ frame: frame - 12, fps, config: { damping: 12 } });

  // Envelope flies from attacker to the victim's laptop between 25% and 62%.
  const flight = interpolate(p, [0.25, 0.62], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const envX = interpolate(flight, [0, 1], [-470, 300]);
  const envY = interpolate(flight, [0, 0.5, 1], [-40, -120, -10]);
  const envVisible = flight > 0.01 && flight < 0.995;

  // Impact + alert after the envelope lands.
  const impact = interpolate(p, [0.62, 0.74], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const alertPulse = 1 + Math.sin(frame / 5) * 0.08 * impact;
  const labelOpacity = interpolate(p, [0.02, 0.12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const hasPoints = items.filter((t) => t && t.trim()).length > 0;

  return (
    <AbsoluteFill>
      {label && <SceneLabel text={label} opacity={labelOpacity} />}
      <svg width="100%" height="100%" viewBox="-960 -540 1920 1080">
        <g transform={hasPoints ? "translate(-330 20) scale(0.76)" : "translate(0 40)"}>
          <Figure x={-470} y={0} scale={1.15} variant="attacker" opacity={attackerIn} label={primary || "Source"} />

          <AnimatedArrow
            from={[-380, -60]}
            to={[170, -40]}
            progress={flight}
            color={COLORS.accent3}
            curve={110}
            dashed
          />

          {envVisible && <Envelope x={envX} y={envY} scale={1.05} danger rotate={interpolate(flight, [0, 1], [-12, 8])} />}

          <DeviceBox
            x={330}
            y={-20}
            w={210}
            h={140}
            label={secondary || "Destinataire"}
            color={impact > 0.4 ? COLORS.accent3 : COLORS.accent}
            opacity={victimIn}
            scale={victimIn * (1 + impact * 0.04)}
            glow={impact}
          />

          <Figure x={560} y={30} scale={1.05} variant={impact > 0.5 ? "worried" : "neutral"} opacity={victimIn} />

          {impact > 0.05 && (
            <g transform={`translate(330 -150) scale(${impact * alertPulse})`}>
              <circle r={44} fill={COLORS.accent3} opacity={0.22} />
              <polygon points="0,-34 30,20 -30,20" fill={COLORS.accent3} />
              <text y={14} textAnchor="middle" fill="#0A0E1A" fontFamily={FONT} fontSize={30} fontWeight={900}>
                !
              </text>
            </g>
          )}
        </g>
      </svg>
      <KeyPoints items={items} accent={accent} durationInFrames={durationInFrames} variant="panel" />
    </AbsoluteFill>
  );
};
