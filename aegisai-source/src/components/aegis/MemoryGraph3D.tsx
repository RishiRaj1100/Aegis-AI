import { Suspense, useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Html } from "@react-three/drei";
import * as THREE from "three";
import type { MemoryNode } from "@/types/aegis";

interface Props {
  nodes: MemoryNode[];
}

const groupColor: Record<MemoryNode["group"], string> = {
  task: "#22d3ee", // primary cyan
  context: "#a855f7", // accent violet
  outcome: "#34d399", // success green
};

interface Positioned extends MemoryNode {
  pos: [number, number, number];
}

function layout(nodes: MemoryNode[]): Positioned[] {
  if (!nodes.length) return [];
  const center = nodes[0];
  const others = nodes.slice(1);
  const positioned: Positioned[] = [{ ...center, pos: [0, 0, 0] }];
  others.forEach((n, i) => {
    // Fibonacci-like sphere distribution
    const phi = Math.acos(1 - (2 * (i + 0.5)) / others.length);
    const theta = Math.PI * (1 + Math.sqrt(5)) * (i + 0.5);
    const r = 2.2 + (1 - n.weight) * 0.4;
    positioned.push({
      ...n,
      pos: [r * Math.cos(theta) * Math.sin(phi), r * Math.sin(theta) * Math.sin(phi), r * Math.cos(phi)],
    });
  });
  return positioned;
}

function Node({ data, index }: { data: Positioned; index: number }) {
  const ref = useRef<THREE.Mesh>(null);
  const color = groupColor[data.group];
  const radius = 0.12 + data.weight * 0.18;

  useFrame((state) => {
    if (!ref.current) return;
    const t = state.clock.getElapsedTime();
    const s = 1 + Math.sin(t * 1.6 + index) * 0.05;
    ref.current.scale.setScalar(s);
  });

  return (
    <group position={data.pos}>
      {/* glow halo */}
      <mesh>
        <sphereGeometry args={[radius * 2.2, 24, 24]} />
        <meshBasicMaterial color={color} transparent opacity={0.08} />
      </mesh>
      <mesh ref={ref}>
        <sphereGeometry args={[radius, 24, 24]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={0.9}
          roughness={0.25}
          metalness={0.15}
        />
      </mesh>
      <Html
        center
        distanceFactor={9}
        position={[0, radius + 0.18, 0]}
        style={{ pointerEvents: "none" }}
      >
        <span className="px-1.5 py-0.5 rounded bg-background/70 backdrop-blur text-[10px] font-mono text-foreground/80 border border-border/60 whitespace-nowrap">
          {data.label}
        </span>
      </Html>
    </group>
  );
}

function Edges({ nodes }: { nodes: Positioned[] }) {
  const geometry = useMemo(() => {
    const g = new THREE.BufferGeometry();
    if (nodes.length < 2) return g;
    const center = nodes[0].pos;
    const positions: number[] = [];
    nodes.slice(1).forEach((n) => {
      positions.push(...center, ...n.pos);
    });
    g.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
    return g;
  }, [nodes]);

  return (
    <lineSegments geometry={geometry}>
      <lineBasicMaterial color="#22d3ee" transparent opacity={0.35} />
    </lineSegments>
  );
}

function Scene({ nodes }: { nodes: MemoryNode[] }) {
  const positioned = useMemo(() => layout(nodes), [nodes]);
  const groupRef = useRef<THREE.Group>(null);

  useFrame((_, delta) => {
    if (groupRef.current) groupRef.current.rotation.y += delta * 0.08;
  });

  return (
    <>
      <ambientLight intensity={0.4} />
      <pointLight position={[5, 5, 5]} intensity={1.2} color="#22d3ee" />
      <pointLight position={[-5, -3, -5]} intensity={0.8} color="#a855f7" />
      <group ref={groupRef}>
        <Edges nodes={positioned} />
        {positioned.map((n, i) => (
          <Node key={n.id} data={n} index={i} />
        ))}
      </group>
      <OrbitControls
        enablePan={false}
        enableZoom
        zoomSpeed={0.6}
        rotateSpeed={0.6}
        minDistance={3}
        maxDistance={8}
      />
    </>
  );
}

export function MemoryGraph3D({ nodes }: Props) {
  return (
    <div className="relative h-[260px] w-full rounded-lg overflow-hidden border border-border/50 bg-gradient-to-b from-background/60 to-background/20">
      <Canvas
        dpr={[1, 1.5]}
        camera={{ position: [0, 0, 5.5], fov: 50 }}
        gl={{ antialias: true, alpha: true }}
      >
        <Suspense fallback={null}>
          <Scene nodes={nodes} />
        </Suspense>
      </Canvas>
      <div className="absolute bottom-2 right-2 text-[9px] font-mono text-muted-foreground/70 pointer-events-none">
        DRAG · ZOOM
      </div>
    </div>
  );
}
