import { GraphStyle } from "./graph-style";

interface NodeRenderInput {
  id: string;
  name: string;
  tags: string[];
  connections: number;
  superseded: boolean;
  deprecated: boolean;
  pulse: boolean;
}

/** Base colour channels parsed from tagColor */
interface ColorChannels {
  r: number;
  g: number;
  b: number;
}

function getColorChannels(node: { tags: string[] }): ColorChannels {
  const hex = GraphStyle.nodeBaseColor(node);
  return {
    r: parseInt(hex.slice(1, 3), 16),
    g: parseInt(hex.slice(3, 5), 16),
    b: parseInt(hex.slice(5, 7), 16),
  };
}

/** Pulse value 0–1 given timing params and current time */
export function pulseValue(time: number, alphaMin: number, alphaMax: number, periodMs: number): number {
  const t = (time % periodMs) / periodMs;
  const ease = 0.5 - 0.5 * Math.cos(2 * Math.PI * t);
  return alphaMin + ease * (alphaMax - alphaMin);
}

/** Draw a radial-gradient orb at (x,y) */
export function drawNodeOrb(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  radius: number,
  node: NodeRenderInput,
  time: number,
): void {
  const { r, g, b } = getColorChannels(node);

  const dimAlpha = node.superseded
    ? GraphStyle.SUPERSEDED_ALPHA
    : node.deprecated
      ? GraphStyle.DEPRECATED_ALPHA
      : 1;

  const highlightMix = 0.25;
  const hlR = Math.round(r + (255 - r) * highlightMix);
  const hlG = Math.round(g + (255 - g) * highlightMix);
  const hlB = Math.round(b + (255 - b) * highlightMix);
  const rimR = Math.round(r * 0.55);
  const rimG = Math.round(g * 0.55);
  const rimB = Math.round(b * 0.55);

  const grad = ctx.createRadialGradient(
    x - radius * GraphStyle.SPECULAR_OFFSET_RATIO,
    y - radius * GraphStyle.SPECULAR_OFFSET_RATIO,
    0,
    x,
    y,
    radius,
  );

  if (node.pulse) {
    const { ALPHA_MIN, ALPHA_MAX, PERIOD_MS } = GraphStyle.IN_PROGRESS;
    const p = pulseValue(time, ALPHA_MIN, ALPHA_MAX, PERIOD_MS);
    grad.addColorStop(0, `rgba(${hlR}, ${hlG}, ${hlB}, ${p})`);
    grad.addColorStop(0.5, `rgba(${r}, ${g}, ${b}, ${p})`);
    grad.addColorStop(1, `rgba(${rimR}, ${rimG}, ${rimB}, ${p})`);
  } else {
    grad.addColorStop(0, `rgba(${hlR}, ${hlG}, ${hlB}, ${dimAlpha})`);
    grad.addColorStop(0.5, `rgba(${r}, ${g}, ${b}, ${dimAlpha})`);
    grad.addColorStop(1, `rgba(${rimR}, ${rimG}, ${rimB}, ${dimAlpha})`);
  }

  ctx.beginPath();
  ctx.arc(x, y, radius, 0, 2 * Math.PI);
  ctx.fillStyle = grad;
  ctx.fill();

  // Specular highlight dot
  const specR = radius * GraphStyle.SPECULAR_DOT_RATIO;
  if (specR > 0.8) {
    const sx = x - radius * GraphStyle.SPECULAR_OFFSET_RATIO;
    const sy = y - radius * GraphStyle.SPECULAR_OFFSET_RATIO;
    ctx.beginPath();
    ctx.arc(sx, sy, specR, 0, 2 * Math.PI);
    const specAlpha = node.superseded ? 0.05 : 0.2;
    ctx.fillStyle = `rgba(255, 255, 255, ${specAlpha})`;
    ctx.fill();
  }
}

/** Draw a breathing ring around the node */
export function drawBreathingRing(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  radius: number,
  time: number,
  alphaMin: number,
  alphaMax: number,
  periodMs: number,
  ringOffset: number,
): void {
  const p = pulseValue(time, alphaMin, alphaMax, periodMs);
  const ringOuter = radius + ringOffset;

  // Use the ring's own colour — caller sets it via globalAlpha
  const ringGrad = ctx.createRadialGradient(x, y, radius, x, y, ringOuter);
  ringGrad.addColorStop(0, `rgba(255, 255, 255, ${p})`);
  ringGrad.addColorStop(1, "rgba(0,0,0,0)");
  ctx.beginPath();
  ctx.arc(x, y, ringOuter, 0, 2 * Math.PI);
  ctx.fillStyle = ringGrad;
  ctx.fill();
}

/** Draw a node label below the orb */
export function drawNodeLabel(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  radius: number,
  name: string,
  superseded: boolean,
  maxChars: number,
  globalScale: number,
): void {
  const label = name.length > maxChars ? name.slice(0, maxChars - 1) + "…" : name;
  ctx.font = `${11 / globalScale}px sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  ctx.fillStyle = superseded
    ? `rgba(212, 212, 212, ${GraphStyle.SUPERSEDED_ALPHA})`
    : GraphStyle.LABEL.COLOR;
  ctx.fillText(label, x, y + radius + 2 / globalScale);
}
