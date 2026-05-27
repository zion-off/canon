"use client";

const ns = (i: number, salt = 0) => {
  const x = Math.sin(i * 127.1 + salt * 311.7 + 19.3) * 43758.5453;
  return x - Math.floor(x);
};

function buildBars(): { width: string; gap: string; delay: string }[] {
  const bars = [];
  for (let i = 0; i < 120; i++) {
    bars.push({
      width: (1.2 + ns(i, 1) * 2.2).toFixed(2),
      gap: (ns(i, 2) < 0.8 ? 6 + ns(i, 3) * 7 : 18 + ns(i, 3) * 10).toFixed(2),
      delay: (ns(i, 4) * 3).toFixed(2),
    });
  }
  return bars;
}

// Pre-compute bars with fixed-precision strings — identical server and client,
// avoiding hydration mismatches.
const bars = buildBars();

export default function BarcodeWave() {
  return (
    <div className="relative w-full h-full overflow-hidden flex justify-center">
      <div className="flex items-center h-full gap-0" suppressHydrationWarning>
        {bars.map((bar, i) => (
          <div
            key={i}
            className="h-4/5 bg-[linear-gradient(to_bottom,_rgb(48,48,48)_0%,_rgb(48,48,48)_25%,_rgba(255,255,255,0.4)_50%,_rgb(48,48,48)_75%,_rgb(48,48,48)_100%)] bg-[length:100%_200%] [animation:shimmer_3s_linear_infinite]"
            style={{
              width: `${bar.width}px`,
              marginLeft: i > 0 ? `${bar.gap}px` : undefined,
              animationDelay: `${bar.delay}s`,
            }}
          />
        ))}
      </div>
    </div>
  );
}
