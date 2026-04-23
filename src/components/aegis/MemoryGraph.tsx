import { useMemo } from "react";
import type { MemoryNode } from "@/types/aegis";

interface Props {
  nodes: MemoryNode[];
}

const groupColor: Record<MemoryNode["group"], string> = {
  task: "hsl(var(--primary))",
  context: "hsl(var(--accent))",
  outcome: "hsl(var(--success))",
};

export function MemoryGraph({ nodes }: Props) {
  const layout = useMemo(() => {
    const W = 320;
    const H = 220;
    const cx = W / 2;
    const cy = H / 2;
    const center = nodes[0];
    const others = nodes.slice(1);
    const positioned = [
      { ...center, x: cx, y: cy, r: 22 },
      ...others.map((n, i) => {
        const angle = (i / others.length) * Math.PI * 2 - Math.PI / 2;
        const radius = 78 + (1 - n.weight) * 10;
        return {
          ...n,
          x: cx + Math.cos(angle) * radius,
          y: cy + Math.sin(angle) * radius,
          r: 9 + n.weight * 7,
        };
      }),
    ];
    return { positioned, W, H, cx, cy };
  }, [nodes]);

  return (
    <svg viewBox={`0 0 ${layout.W} ${layout.H}`} className="w-full h-auto">
      <defs>
        <radialGradient id="memglow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.25" />
          <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity="0" />
        </radialGradient>
      </defs>
      <circle cx={layout.cx} cy={layout.cy} r="90" fill="url(#memglow)" />
      {layout.positioned.slice(1).map((n) => (
        <line
          key={`l-${n.id}`}
          x1={layout.cx}
          y1={layout.cy}
          x2={n.x}
          y2={n.y}
          stroke="hsl(var(--border))"
          strokeWidth={0.8}
          strokeDasharray="2 3"
          opacity={0.5 + n.weight * 0.4}
        />
      ))}
      {layout.positioned.map((n, i) => (
        <g key={n.id}>
          <circle
            cx={n.x}
            cy={n.y}
            r={n.r}
            fill={groupColor[n.group]}
            opacity={0.18}
          />
          <circle
            cx={n.x}
            cy={n.y}
            r={n.r * 0.55}
            fill={groupColor[n.group]}
          >
            <animate
              attributeName="opacity"
              values="0.7;1;0.7"
              dur={`${2 + (i % 3)}s`}
              repeatCount="indefinite"
            />
          </circle>
          <text
            x={n.x}
            y={n.y + n.r + 11}
            textAnchor="middle"
            fontSize="8.5"
            fill="hsl(var(--muted-foreground))"
            fontFamily="Inter"
          >
            {n.label}
          </text>
        </g>
      ))}
    </svg>
  );
}
