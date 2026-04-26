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
        // Clear previous content
        if (ref.current) ref.current.innerHTML = "";
        
        const uid = `mermaid-${id}-${Math.random().toString(36).slice(2, 6)}`;
        // For Mermaid 10/11, passing the element as 3rd arg helps with dimension calculations
        const { svg } = await mermaid.render(uid, chart, ref.current);
        
        if (!cancelled && ref.current) {
          ref.current.innerHTML = svg;
          const svgEl = ref.current.querySelector("svg");
          if (svgEl) {
            svgEl.style.width = "100%";
            svgEl.style.height = "auto";
          }
        }
      } catch (e) {
        console.error("Mermaid render error:", e);
        if (!cancelled && ref.current) {
          ref.current.innerHTML = `<div class="text-[10px] text-muted-foreground p-4 border border-dashed border-border rounded-lg text-center">
            Graph synthesis failed. Using fallback view.
          </div>`;
        }
      }
    };
    render();
    return () => {
      cancelled = true;
    };
  }, [chart, id]);

  return <div ref={ref} className="w-full overflow-x-auto [&_svg]:max-w-full [&_svg]:h-auto" />;
}
