import React from "react";
import { COLORS, FONT } from "../theme";

/** Vector building blocks for the animated explainer scenes. All are plain
 * SVG groups positioned by the caller, so scenes can compose them freely and
 * animate their props per frame (no external assets, nothing to license). */

export const Figure: React.FC<{
  x: number;
  y: number;
  scale?: number;
  variant?: "neutral" | "attacker" | "worried";
  opacity?: number;
  label?: string;
}> = ({ x, y, scale = 1, variant = "neutral", opacity = 1, label }) => {
  const bodyColor =
    variant === "attacker" ? "#1E293B" : variant === "worried" ? "#F59E0B" : COLORS.accent;
  const skin = variant === "attacker" ? "#334155" : "#FBCFE8";

  return (
    <g transform={`translate(${x} ${y}) scale(${scale})`} opacity={opacity}>
      {/* head */}
      <circle cx={0} cy={-58} r={26} fill={skin} stroke={bodyColor} strokeWidth={4} />
      {variant === "attacker" && (
        /* hood */
        <path d="M -32 -58 A 32 32 0 0 1 32 -58 L 32 -70 A 32 40 0 0 0 -32 -70 Z" fill="#0F172A" />
      )}
      {/* eyes */}
      <circle cx={-9} cy={-62} r={3.4} fill="#0F172A" />
      <circle cx={9} cy={-62} r={3.4} fill="#0F172A" />
      {variant === "worried" ? (
        <path d="M -10 -46 Q 0 -53 10 -46" stroke="#0F172A" strokeWidth={3} fill="none" strokeLinecap="round" />
      ) : (
        <path d="M -10 -50 Q 0 -43 10 -50" stroke="#0F172A" strokeWidth={3} fill="none" strokeLinecap="round" />
      )}
      {/* torso */}
      <path d="M -30 44 Q -30 -18 0 -18 Q 30 -18 30 44 Z" fill={bodyColor} />
      {label && (
        <text
          x={0}
          y={78}
          textAnchor="middle"
          fill={COLORS.text}
          fontFamily={FONT}
          fontSize={22}
          fontWeight={700}
        >
          {label}
        </text>
      )}
    </g>
  );
};

export const DeviceBox: React.FC<{
  x: number;
  y: number;
  w?: number;
  h?: number;
  label?: string;
  color?: string;
  opacity?: number;
  scale?: number;
  glow?: number;
}> = ({ x, y, w = 150, h = 100, label, color = COLORS.accent, opacity = 1, scale = 1, glow = 0 }) => (
  <g transform={`translate(${x} ${y}) scale(${scale})`} opacity={opacity}>
    {glow > 0 && (
      <rect
        x={-w / 2 - 8}
        y={-h / 2 - 8}
        width={w + 16}
        height={h + 16}
        rx={16}
        fill={color}
        opacity={glow * 0.28}
      />
    )}
    <rect x={-w / 2} y={-h / 2} width={w} height={h} rx={12} fill="rgba(255,255,255,0.07)" stroke={color} strokeWidth={3} />
    {/* screen glare line */}
    <rect x={-w / 2 + 14} y={-h / 2 + 14} width={w - 28} height={8} rx={4} fill={color} opacity={0.5} />
    {/* stand */}
    <rect x={-26} y={h / 2} width={52} height={9} rx={4} fill={color} opacity={0.75} />
    {label && (
      <WrappedText text={label} y={h / 2 + 42} maxWidth={Math.max(w + 120, 300)} fontSize={22} maxLines={3} />
    )}
  </g>
);

export const ServerStack: React.FC<{
  x: number;
  y: number;
  label?: string;
  color?: string;
  opacity?: number;
  scale?: number;
}> = ({ x, y, label, color = COLORS.accent2, opacity = 1, scale = 1 }) => (
  <g transform={`translate(${x} ${y}) scale(${scale})`} opacity={opacity}>
    {[0, 1, 2].map((i) => (
      <g key={i}>
        <rect x={-58} y={-66 + i * 46} width={116} height={38} rx={8} fill="rgba(255,255,255,0.07)" stroke={color} strokeWidth={3} />
        <circle cx={-38} cy={-47 + i * 46} r={6} fill={color} />
        <rect x={-20} y={-51 + i * 46} width={62} height={7} rx={3.5} fill={color} opacity={0.45} />
      </g>
    ))}
    {label && <WrappedText text={label} y={112} maxWidth={300} fontSize={22} maxLines={3} />}
  </g>
);

/** An arrow that draws itself: pass progress 0..1. */
export const AnimatedArrow: React.FC<{
  from: [number, number];
  to: [number, number];
  progress: number;
  color?: string;
  curve?: number;
  width?: number;
  dashed?: boolean;
}> = ({ from, to, progress, color = COLORS.accent, curve = 0, width = 5, dashed = false }) => {
  const [x1, y1] = from;
  const [x2, y2] = to;
  const mx = (x1 + x2) / 2;
  const my = (y1 + y2) / 2 - curve;
  const d = `M ${x1} ${y1} Q ${mx} ${my} ${x2} ${y2}`;
  const len = Math.hypot(x2 - x1, y2 - y1) * 1.35 + Math.abs(curve) * 2;
  const clamped = Math.max(0, Math.min(1, progress));

  // Point along the quadratic curve, for the arrowhead position/angle.
  const t = clamped;
  const px = (1 - t) * (1 - t) * x1 + 2 * (1 - t) * t * mx + t * t * x2;
  const py = (1 - t) * (1 - t) * y1 + 2 * (1 - t) * t * my + t * t * y2;
  const dx = 2 * (1 - t) * (mx - x1) + 2 * t * (x2 - mx);
  const dy = 2 * (1 - t) * (my - y1) + 2 * t * (y2 - my);
  const angle = (Math.atan2(dy, dx) * 180) / Math.PI;

  return (
    <g>
      <path
        d={d}
        stroke={color}
        strokeWidth={width}
        fill="none"
        strokeLinecap="round"
        strokeDasharray={dashed ? "12 10" : len}
        strokeDashoffset={dashed ? 0 : len * (1 - clamped)}
        opacity={dashed ? clamped : 1}
      />
      {clamped > 0.06 && (
        <polygon points="0,-9 20,0 0,9" fill={color} transform={`translate(${px} ${py}) rotate(${angle})`} />
      )}
    </g>
  );
};

export const Envelope: React.FC<{
  x: number;
  y: number;
  scale?: number;
  opacity?: number;
  danger?: boolean;
  rotate?: number;
}> = ({ x, y, scale = 1, opacity = 1, danger = false, rotate = 0 }) => {
  const color = danger ? COLORS.accent3 : COLORS.accent;
  return (
    <g transform={`translate(${x} ${y}) scale(${scale}) rotate(${rotate})`} opacity={opacity}>
      <rect x={-46} y={-32} width={92} height={64} rx={8} fill="rgba(255,255,255,0.1)" stroke={color} strokeWidth={4} />
      <path d="M -46 -28 L 0 8 L 46 -28" stroke={color} strokeWidth={4} fill="none" strokeLinejoin="round" />
      {danger && (
        <g transform="translate(38 -32)">
          <circle r={17} fill={COLORS.accent3} />
          <text y={7} textAnchor="middle" fill="#0A0E1A" fontFamily={FONT} fontSize={24} fontWeight={900}>
            !
          </text>
        </g>
      )}
    </g>
  );
};

export const ShieldShape: React.FC<{
  x: number;
  y: number;
  scale?: number;
  opacity?: number;
  color?: string;
  filled?: boolean;
  cracked?: boolean;
}> = ({ x, y, scale = 1, opacity = 1, color = COLORS.accent, filled = false, cracked = false }) => (
  <g transform={`translate(${x} ${y}) scale(${scale})`} opacity={opacity}>
    <path
      d="M 0 -62 L 52 -40 L 52 8 Q 52 52 0 74 Q -52 52 -52 8 L -52 -40 Z"
      fill={filled ? `${color}44` : "rgba(255,255,255,0.05)"}
      stroke={color}
      strokeWidth={5}
      strokeLinejoin="round"
    />
    {cracked ? (
      <path d="M -8 -34 L 8 -4 L -10 8 L 10 44" stroke={COLORS.accent3} strokeWidth={5} fill="none" strokeLinecap="round" />
    ) : (
      <path d="M -22 4 L -6 22 L 24 -18" stroke={color} strokeWidth={7} fill="none" strokeLinecap="round" strokeLinejoin="round" />
    )}
  </g>
);

export const LockShape: React.FC<{
  x: number;
  y: number;
  scale?: number;
  opacity?: number;
  open?: boolean;
  color?: string;
}> = ({ x, y, scale = 1, opacity = 1, open = false, color = COLORS.accent }) => (
  <g transform={`translate(${x} ${y}) scale(${scale})`} opacity={opacity}>
    <path
      d={open ? "M -22 -14 L -22 -34 A 22 22 0 0 1 22 -34" : "M -22 -14 L -22 -34 A 22 22 0 0 1 22 -34 L 22 -14"}
      stroke={color}
      strokeWidth={7}
      fill="none"
      strokeLinecap="round"
    />
    <rect x={-34} y={-14} width={68} height={54} rx={9} fill={`${color}33`} stroke={color} strokeWidth={5} />
    <circle cx={0} cy={12} r={7} fill={color} />
  </g>
);

export const SceneLabel: React.FC<{ text: string; opacity?: number; y?: number }> = ({
  text,
  opacity = 1,
  y = 96,
}) => (
  <div
    style={{
      position: "absolute",
      top: y,
      left: 0,
      right: 0,
      textAlign: "center",
      fontFamily: FONT,
      fontSize: 52,
      fontWeight: 800,
      color: COLORS.text,
      opacity,
      textShadow: "0 4px 24px rgba(0,0,0,0.5)",
      padding: "0 8%",
    }}
  >
    {text}
  </div>
);

/** SVG text that wraps to its slot instead of running past it.
 *
 * Every diagram places its labels in fixed-width boxes, and SVG `<text>` does
 * not wrap: once the planner started producing meaningful phrases rather than
 * single words, labels overlapped their neighbours or were hard-truncated.
 * This lays the text out for the space actually available — wrapping first,
 * then shrinking the type, and only truncating when even the smallest size
 * cannot fit — so a diagram stays readable whatever the planner writes.
 *
 * Widths are estimated from the character count rather than measured: the
 * renderer must stay deterministic, so two runs of the same scene produce
 * byte-identical frames. */
const AVG_CHAR_WIDTH_RATIO = 0.55;

function wrapLines(text: string, maxChars: number): string[] {
  const words = text.split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let current = "";
  for (const word of words) {
    const candidate = current ? `${current} ${word}` : word;
    if (candidate.length <= maxChars || !current) {
      current = candidate;
    } else {
      lines.push(current);
      current = word;
    }
  }
  if (current) lines.push(current);
  return lines;
}

export const WrappedText: React.FC<{
  text: string;
  x?: number;
  y: number;
  maxWidth: number;
  fontSize?: number;
  minFontSize?: number;
  maxLines?: number;
  fontWeight?: number;
  fill?: string;
  opacity?: number;
  anchor?: "start" | "middle" | "end";
  transform?: string;
}> = ({
  text,
  x = 0,
  y,
  maxWidth,
  fontSize = 30,
  minFontSize,
  maxLines = 2,
  fontWeight = 700,
  fill = COLORS.text,
  opacity = 1,
  anchor = "middle",
  transform,
}) => {
  if (!text || !text.trim()) return null;
  const floor = minFontSize ?? Math.max(14, Math.round(fontSize * 0.62));

  let size = fontSize;
  let lines = wrapLines(text, Math.max(4, Math.floor(maxWidth / (fontSize * AVG_CHAR_WIDTH_RATIO))));
  while (lines.length > maxLines && size > floor) {
    size -= 2;
    lines = wrapLines(text, Math.max(4, Math.floor(maxWidth / (size * AVG_CHAR_WIDTH_RATIO))));
  }
  if (lines.length > maxLines) {
    lines = lines.slice(0, maxLines);
    lines[maxLines - 1] = lines[maxLines - 1].replace(/\s+\S*$/, "") + "…";
  }

  const lineHeight = size * 1.16;
  const firstBaseline = y - ((lines.length - 1) * lineHeight) / 2;

  return (
    <text
      x={x}
      y={firstBaseline}
      textAnchor={anchor}
      fill={fill}
      fontFamily={FONT}
      fontSize={size}
      fontWeight={fontWeight}
      opacity={opacity}
      transform={transform}
    >
      {lines.map((line, i) => (
        <tspan key={i} x={x} dy={i === 0 ? 0 : lineHeight}>
          {line}
        </tspan>
      ))}
    </text>
  );
};
