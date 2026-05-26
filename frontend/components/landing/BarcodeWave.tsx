"use client";

import { useEffect, useRef } from "react";

const WAVE_INTERVAL = 3400;
const WAVE_SPEED = 0.32;
const WAVE_HALF_WIDTH = 140;
const BAR_DENSITY = 16;

const ns = (i: number, salt = 0) => {
  const x = Math.sin(i * 127.1 + salt * 311.7 + 19.3) * 43758.5453;
  return x - Math.floor(x);
};

const buildLayout = (totalW: number, numLines: number) => {
  const positions: number[] = [];
  const widths: number[] = [];
  let x = 0;
  for (let i = 0; i < numLines; i++) {
    const w = 1.3 + ns(i, 1) * 2.0;
    const gap = ns(i, 2) < 0.82 ? 7 + ns(i, 3) * 8 : 20 + ns(i, 3) * 12;
    positions.push(x + w / 2);
    widths.push(w);
    x += w + gap;
  }
  const scale = totalW / x;
  return {
    scale,
    positions: positions.map((p) => p * scale),
    widths: widths.map((w) => w * scale),
  };
};

export default function BarcodeWave() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    let numLines = 0;
    let layout: { positions: number[]; widths: number[] } | null = null;
    let lineChar: { restW: number; nudge: number; peakMod: number }[] = [];
    let lineWidths: number[] = [];
    let scale = 1;
    const state = {
      waves: [] as { x: number }[],
      lastWaveTime: -9999,
    };

    const resize = () => {
      const dpr = window.devicePixelRatio;
      canvas.width = canvas.offsetWidth * dpr;
      canvas.height = canvas.offsetHeight * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      numLines = Math.round(canvas.offsetWidth / BAR_DENSITY);

      const result = buildLayout(canvas.offsetWidth, numLines);
      layout = { positions: result.positions, widths: result.widths };
      scale = result.scale;

      lineChar = Array.from({ length: numLines }, (_, i) => ({
        restW: (1.3 + ns(i, 1) * 2.0) * scale,
        nudge: (ns(i, 4) - 0.5) * 18 * scale,
        peakMod: 0.78 + ns(i, 5) * 0.44,
      }));

      lineWidths = lineChar.map((c) => c.restW);
    };
    resize();
    window.addEventListener("resize", resize);

    let lastTime = 0;

    const draw = (timestamp: number) => {
      const dt = Math.min(timestamp - lastTime, 32);
      lastTime = timestamp;

      const W = canvas.offsetWidth;
      const H = canvas.offsetHeight;
      ctx.clearRect(0, 0, W, H);

      const halfWave = WAVE_HALF_WIDTH * scale;
      const bulgeMax = 11 * scale;

      if (timestamp - state.lastWaveTime > WAVE_INTERVAL) {
        const startX = layout ? layout.positions[0] - halfWave * 1.8 : -200;
        state.waves.push({ x: startX });
        state.lastWaveTime = timestamp;
      }

      const pxPerFrame = (W / 1400) * WAVE_SPEED * dt;
      const endX = layout ? layout.positions[numLines - 1] + halfWave * 1.8 : W + 200;
      state.waves = state.waves.filter((w) => {
        w.x += pxPerFrame;
        return w.x < endX;
      });

      if (!layout) {
        animId = requestAnimationFrame(draw);
        return;
      }

      for (let i = 0; i < numLines; i++) {
        const char = lineChar[i];
        const lx = layout.positions[i];
        let bulge = 0;

        for (const wave of state.waves) {
          const dist = lx + char.nudge - wave.x;

          if (Math.abs(dist) < halfWave) {
            const t = 1 - Math.abs(dist) / halfWave;
            const bell = t * t * (3 - 2 * t);
            bulge = Math.max(bulge, bell * bulgeMax * char.peakMod);
          }
        }

        const target = char.restW + bulge;
        lineWidths[i] += (target - lineWidths[i]) * 0.09;

        const w = lineWidths[i];
        const bulgeRatio = Math.min(1, (w - char.restW) / bulgeMax);
        const brightness = Math.round(80 + bulgeRatio * 52);
        const alpha = 0.2 + bulgeRatio * 0.45;

        const barTop = H * 0.1;
        const barH = H * 0.8;
        const cellSize = Math.max(2, char.restW);
        const noiseGap = 0.18 + ns(i, 7) * 0.06;

        for (let py = barTop; py < barTop + barH; py += cellSize) {
          const idx = Math.floor(py / cellSize);
          const seed = ns(i * 1021 + idx, 8);
          if (seed < noiseGap) continue;

          const pAlpha = alpha * (0.7 + seed * 0.55);
          const cx = lx;
          const cy = py + cellSize / 2;
          const sz = cellSize * 1.15 + bulge * 0.08;

          ctx.fillStyle = `rgba(${brightness},${brightness},${Math.round(brightness * 0.93)},${pAlpha})`;
          ctx.fillRect(cx - sz / 2, cy - sz / 2, sz, sz);
        }
      }

      animId = requestAnimationFrame(draw);
    };

    animId = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <div className="relative w-full h-full overflow-hidden">
      <canvas ref={canvasRef} className="absolute inset-0 w-full h-full" />
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: "radial-gradient(ellipse 80% 55% at center, transparent 25%, #111111 88%)",
        }}
      />
    </div>
  );
}
