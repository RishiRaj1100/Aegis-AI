import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { GitBranch } from 'lucide-react';
import type { AegisResponse, Subtask } from '@/types/aegis';

interface ExecutionGraphProps {
  data: AegisResponse;
}

function buildMermaidDef(subtasks: Subtask[]): string {
  if (!subtasks.length) return 'graph TD\n  A["No subtasks"]';

  const nodes = subtasks.slice(0, 10).map((task, i) => {
    // Robustly sanitize labels: replace double quotes with single, remove newlines
    const label = (task.title || task.name || `Task ${i + 1}`)
      .replace(/"/g, "'")
      .replace(/\n/g, " ")
      .replace(/\r/g, "")
      .trim();
    
    const score = task.trust_score ?? task.confidence ?? 0;
    
    // Pictorial shapes with quoted labels for safety:
    let shape = `["${label}"]`;
    if (i === 0) shape = `(["${label}"])`;
    else if (score < 60) shape = `{"${label}"}`;
    else if (i === subtasks.length - 1) shape = `[["${label}"]]`;

    return `  T${i}${shape}`;
  });

  const edges: string[] = [];
  subtasks.slice(0, 10).forEach((task, i) => {
    if (task.dependencies && task.dependencies.length > 0) {
      task.dependencies.forEach(dep => {
        const depIdx = subtasks.findIndex(t => t.id === dep || t.title === dep);
        if (depIdx !== -1 && depIdx < 10) {
          edges.push(`  T${depIdx} --> T${i}`);
        }
      });
    } else if (i > 0) {
      edges.push(`  T${i-1} --> T${i}`);
    }
  });

  const styles = subtasks.slice(0, 10).map((task, i) => {
    const score = task.trust_score ?? task.confidence ?? 0;
    const color = score >= 80 ? '#10B981' : score >= 60 ? '#F59E0B' : '#7C3AED';
    return `  style T${i} fill:${color}15,stroke:${color},stroke-width:2px,color:#0F0A2E`;
  });

  const layout = subtasks.length > 5 ? 'flowchart LR' : 'flowchart TD';
  return [layout, ...nodes, ...edges, ...styles].join('\n');
}

export default function ExecutionGraph({ data }: ExecutionGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const plan = data.plan || data;
  const subtasks: Subtask[] = plan.subtasks || data.subtasks || [];

  useEffect(() => {
    if (!containerRef.current) return;

    const render = async () => {
      try {
        const mermaid = (await import('mermaid')).default;
        mermaid.initialize({
          startOnLoad: false,
          theme: 'base',
          securityLevel: 'loose',
          themeVariables: {
            primaryColor: '#EEF2FF',
            primaryTextColor: '#0F0A2E',
            primaryBorderColor: '#7C3AED',
            lineColor: '#A78BFA',
            secondaryColor: '#F5F3FF',
            background: 'transparent',
            fontFamily: 'Inter',
            fontSize: '13px',
          },
        });

        const def = buildMermaidDef(subtasks);
        const id = `execution-graph-${Date.now()}`;
        
        // Pass container for dimension calculation
        const { svg } = await mermaid.render(id, def, containerRef.current);
        
        if (containerRef.current) {
          containerRef.current.innerHTML = svg;
          const svgEl = containerRef.current.querySelector('svg');
          if (svgEl) {
            svgEl.style.width = '100%';
            svgEl.style.height = 'auto';
            svgEl.style.maxHeight = '500px';
            svgEl.style.filter = 'drop-shadow(0 4px 6px rgba(0,0,0,0.05))';
          }
        }
      } catch (e) {
        console.error("Execution graph render failed:", e);
        if (containerRef.current) {
          containerRef.current.innerHTML = `<div style="color:#9CA3AF;font-size:12px;text-align:center;padding:24px;border:1px dashed #E5E7EB;border-radius:12px;">Graph synthesis failed. Sequential view maintained.</div>`;
        }
      }
    };

    render();
  }, [subtasks]);

  return (
    <motion.div
      className="glass p-6"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.3 }}
    >
      <div className="flex items-center gap-2 mb-4">
        <GitBranch size={16} style={{ color: '#7C3AED' }} />
        <h3 className="text-sm font-bold" style={{ fontFamily: 'Syne', color: '#0F0A2E' }}>
          Execution Graph
        </h3>
        <span className="badge badge-violet ml-auto">Mermaid.js</span>
      </div>

      {subtasks.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-10 gap-2">
          <GitBranch size={32} style={{ color: 'rgba(124,58,237,0.2)' }} />
          <p className="text-sm" style={{ color: '#9CA3AF' }}>Submit a goal to generate the workflow graph.</p>
        </div>
      ) : (
        <div
          ref={containerRef}
          className="w-full overflow-x-auto rounded-xl p-2"
          style={{ background: 'rgba(255,255,255,0.5)', minHeight: '200px' }}
        />
      )}
    </motion.div>
  );
}
