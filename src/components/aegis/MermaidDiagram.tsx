import { useEffect, useRef } from "react";
import mermaid from "mermaid";

interface Props {
  chart: string;
  id?: string;
}

mermaid.initialize({
  startOnLoad: false,
  theme: "dark",
  securityLevel: "loose",
  fontFamily: "Inter, ui-sans-serif, system-ui",
  themeVariables: {
    primaryColor: "#0e1726",
    primaryTextColor: "#e6f1ff",
    primaryBorderColor: "#22d3ee",
    lineColor: "#64748b",
    secondaryColor: "#1e293b",
    tertiaryColor: "#0b1220",
    background: "transparent",
    mainBkg: "#0e1726",
    nodeBorder: "#22d3ee",
    clusterBkg: "#0b1220",
  },
});

export function MermaidDiagram({ chart, id = "mmd" }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    const render = async () => {
      if (!ref.current) return;
      try {
        const uid = `${id}-${Math.random().toString(36).slice(2, 8)}`;
        const { svg } = await mermaid.render(uid, chart);
        if (!cancelled && ref.current) ref.current.innerHTML = svg;
      } catch (e) {
        if (ref.current) ref.current.innerHTML = `<pre class="text-xs text-destructive">${String(e)}</pre>`;
      }
    };
    render();
    return () => {
      cancelled = true;
    };
  }, [chart, id]);

  return <div ref={ref} className="w-full overflow-x-auto [&_svg]:max-w-full [&_svg]:h-auto" />;
}
