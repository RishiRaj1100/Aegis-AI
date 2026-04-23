import type { DecisionResponse, Language, TaskRequest } from "@/types/aegis";

// Configure your FastAPI base URL via Vite env var, fallback empty (mock mode).
const API_BASE = (import.meta as any).env?.VITE_API_BASE_URL ?? "";

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function mockResponse(task: string, language: Language): DecisionResponse {
  const isHi = language === "hi";
  const probability = 0.62 + Math.random() * 0.3;
  const riskLevel = probability > 0.8 ? "low" : probability > 0.6 ? "medium" : "high";

  return {
    decision: isHi
      ? `कार्य "${task.slice(0, 60)}" को नियंत्रित रोलआउट के साथ आगे बढ़ाने की अनुशंसा।`
      : `Proceed with "${task.slice(0, 80)}" under a controlled, staged rollout.`,
    success_probability: Number(probability.toFixed(2)),
    risk_level: riskLevel,
    explanation: isHi
      ? "ऐतिहासिक डेटा और एजेंटों की सहमति के आधार पर, यह निर्णय उच्च प्रभाव और प्रबंधनीय जोखिम प्रदान करता है। प्रमुख चर अनुकूल हैं और निर्भरताएँ स्थिर हैं।"
      : "Based on 142 analogous historical missions and consensus across the optimist and risk agents, this decision yields high expected impact with manageable downside. Key dependencies are stable and rollback paths are well-defined.",
    similar_tasks: [
      { id: "t-1042", title: isHi ? "क्षेत्रीय API रोलआउट Q3" : "Regional API rollout Q3", outcome: "success", similarity: 0.92 },
      { id: "t-0987", title: isHi ? "स्कीमा माइग्रेशन v4" : "Schema migration v4", outcome: "partial", similarity: 0.81 },
      { id: "t-0911", title: isHi ? "बैच ETL अनुकूलन" : "Batch ETL optimization", outcome: "success", similarity: 0.74 },
      { id: "t-0865", title: isHi ? "लाइव ट्रैफ़िक शिफ्ट" : "Live traffic shift experiment", outcome: "failed", similarity: 0.69 },
    ],
    agent_debate: {
      optimist: isHi
        ? "मेट्रिक्स मजबूत हैं, टीम तैयार है, और बाजार खिड़की अनुकूल है। तेजी से कदम उठाएं।"
        : "Signals are strong, the team is prepared, and the market window is favorable. Move decisively — expected uplift is +18%.",
      risk: isHi
        ? "तृतीय-पक्ष निर्भरता पर ध्यान दें; एक स्टेज्ड रोलआउट और स्पष्ट रोलबैक आवश्यक है।"
        : "Third-party dependency variance is non-trivial. Insist on staged rollout, automated canary, and a clear rollback within 9 minutes.",
      final_decision: isHi
        ? "स्टेज्ड रोलआउट के साथ आगे बढ़ें — 10% → 50% → 100%, स्वचालित रोलबैक सक्षम।"
        : "Proceed with a staged rollout — 10% → 50% → 100% with automated rollback armed at every gate.",
    },
    workflow: `flowchart TD
  A([Intake]) --> B{Validate Inputs}
  B -- ok --> C[Retrieve Context]
  B -- invalid --> X([Reject])
  C --> D[Optimist Agent]
  C --> E[Risk Agent]
  D --> F{Debate Resolver}
  E --> F
  F --> G[Decision Synthesis]
  G --> H[Stage 10%]
  H --> I[Stage 50%]
  I --> J([Full Rollout])`,
    logs: [
      { ts: new Date().toISOString(), level: "info", source: "intake", message: "Task accepted, language=" + language },
      { ts: new Date().toISOString(), level: "info", source: "memory", message: "Retrieved 142 analogous missions" },
      { ts: new Date().toISOString(), level: "success", source: "agent.optimist", message: "Argument generated (conf 0.84)" },
      { ts: new Date().toISOString(), level: "warn", source: "agent.risk", message: "Flagged dependency: payments-svc latency" },
      { ts: new Date().toISOString(), level: "info", source: "resolver", message: "Consensus reached after 2 rounds" },
      { ts: new Date().toISOString(), level: "success", source: "synthesis", message: "Decision finalized" },
    ],
    memory_nodes: [
      { id: "n1", label: "Mission Intent", weight: 1, group: "task" },
      { id: "n2", label: "Historical Wins", weight: 0.86, group: "context" },
      { id: "n3", label: "Risk Patterns", weight: 0.71, group: "context" },
      { id: "n4", label: "Team Capacity", weight: 0.62, group: "context" },
      { id: "n5", label: "Market Window", weight: 0.78, group: "context" },
      { id: "n6", label: "Predicted Outcome", weight: 0.9, group: "outcome" },
    ],
    subtasks: [
      isHi ? "स्कोप परिभाषित करें और हितधारकों से पुष्टि करें" : "Define scope and confirm with stakeholders",
      isHi ? "रोलबैक रनबुक तैयार करें" : "Prepare rollback runbook",
      isHi ? "कैनरी डिप्लॉयमेंट कॉन्फ़िगर करें" : "Configure canary deployment (10% traffic)",
      isHi ? "एसएलओ डैशबोर्ड संलग्न करें" : "Attach SLO dashboard with alert thresholds",
      isHi ? "जोखिम एजेंट निष्कर्षों की समीक्षा करें" : "Review risk-agent findings with on-call",
      isHi ? "गेट 1: 10% → 50% प्रचार करें" : "Gate 1: promote 10% → 50%",
      isHi ? "गेट 2: 50% → 100% प्रचार करें" : "Gate 2: promote 50% → 100%",
      isHi ? "पोस्ट-डिप्लॉय निगरानी 24 घंटे" : "Post-deploy monitoring window: 24 hours",
      isHi ? "सीखे गए सबक दर्ज करें" : "Record lessons learned in mission memory",
    ],
  };
}

export async function submitTask(req: TaskRequest): Promise<DecisionResponse> {
  if (!API_BASE) {
    await sleep(900);
    return mockResponse(req.task, req.language);
  }
  const res = await fetch(`${API_BASE}/task`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`Task failed: ${res.status}`);
  return res.json();
}

export async function submitVoice(blob: Blob, language: Language): Promise<{ transcript: string; detected_language: Language }> {
  if (!API_BASE) {
    await sleep(700);
    return {
      transcript:
        language === "hi"
          ? "नई भुगतान प्रणाली को उत्पादन में रोलआउट करें"
          : "Roll out the new payments system to production",
      detected_language: language,
    };
  }
  const fd = new FormData();
  fd.append("audio", blob, "voice.webm");
  fd.append("language", language);
  const res = await fetch(`${API_BASE}/voice-input`, { method: "POST", body: fd });
  if (!res.ok) throw new Error(`Voice failed: ${res.status}`);
  return res.json();
}

export async function sendFeedback(payload: { decision: string; rating: "up" | "down"; note?: string }): Promise<void> {
  if (!API_BASE) {
    await sleep(300);
    return;
  }
  await fetch(`${API_BASE}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
