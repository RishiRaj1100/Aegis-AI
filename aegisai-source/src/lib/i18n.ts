import type { Language } from "@/types/aegis";

type Dict = Record<string, string>;

const en: Dict = {
  appTagline: "Autonomous Decision Intelligence",
  systemNominal: "SYSTEM NOMINAL",
  agentsOnline: "v1.0 · 4 agents online",

  // Input panel
  missionIntake: "Mission Intake",
  describeTask: "Describe your decision or task",
  taskPlaceholder:
    "e.g. Evaluate the risk and expected impact of rolling out our new API gateway to all regions tonight…",
  voiceInput: "Voice input",
  listening: "Listening…",
  voiceHint: "Tap the mic to dictate. Your transcript will appear here before processing.",
  transcript: "Transcript",
  outputLanguage: "Output language",
  quickPrompts: "Quick prompts",
  recentTasks: "Recent missions",
  noRecent: "No missions yet — your history will appear here.",
  runAegis: "Run AegisAI",
  synthesizing: "Synthesizing decision…",
  clear: "Clear",

  // Output
  awaitingMission: "Awaiting your mission",
  awaitingDesc:
    "Submit a task on the left. AegisAI will deliberate across multiple agents, retrieve analogous missions from memory, and synthesize a decision with calibrated risk.",
  decisionSynthesis: "Decision Synthesis",
  decisionSummary: "Decision Summary",
  successProbability: "Success Probability",
  riskLevel: "Risk Level",
  explanation: "Explanation — why this decision",
  generatedSubtasks: "Generated Subtasks",
  similarMissions: "Similar Past Missions",
  multiAgentDebate: "Multi-Agent Debate",
  optimistAgent: "Optimist Agent",
  riskAgent: "Risk Agent",
  finalDecision: "Final Decision · Resolver",
  calibrated: "Calibrated against 142 analogous missions",
  riskComposite: "Composite of dependency, blast-radius and reversibility scores.",
  helpful: "Helpful",
  notHelpful: "Not helpful",
  feedbackSaved: "Feedback recorded — agents will recalibrate.",
  feedbackFailed: "Could not send feedback",
  decisionDone: "Decision synthesized",
  consensusReached: "Multi-agent consensus reached.",
  errorTitle: "AegisAI failed",

  // Intelligence
  intelligenceView: "Intelligence View",
  memoryGraph: "Memory Graph",
  workflow: "Workflow",
  executionLogs: "Execution Logs",
  noLogs: "No execution events yet.",

  // Risks
  lowRisk: "LOW RISK",
  mediumRisk: "MEDIUM RISK",
  highRisk: "HIGH RISK",

  outcomeSuccess: "SUCCESS",
  outcomePartial: "PARTIAL",
  outcomeFailed: "FAILED",
};

const hi: Dict = {
  appTagline: "स्वायत्त निर्णय बुद्धिमत्ता",
  systemNominal: "सिस्टम सामान्य",
  agentsOnline: "v1.0 · 4 एजेंट ऑनलाइन",

  missionIntake: "मिशन इनटेक",
  describeTask: "अपना निर्णय या कार्य लिखें",
  taskPlaceholder:
    "उदाहरण: हमारी नई API गेटवे रोलआउट के लिए जोखिम और अपेक्षित प्रभाव का मूल्यांकन करें…",
  voiceInput: "वॉइस इनपुट",
  listening: "सुन रहा है…",
  voiceHint: "रिकॉर्ड करने के लिए माइक दबाएँ। आपका ट्रांसक्रिप्ट यहाँ दिखाई देगा।",
  transcript: "ट्रांसक्रिप्ट",
  outputLanguage: "आउटपुट भाषा",
  quickPrompts: "त्वरित संकेत",
  recentTasks: "हाल के मिशन",
  noRecent: "अभी तक कोई मिशन नहीं — आपका इतिहास यहाँ दिखाई देगा।",
  runAegis: "AegisAI चलाएँ",
  synthesizing: "निर्णय संश्लेषित किया जा रहा है…",
  clear: "साफ़ करें",

  awaitingMission: "आपके मिशन की प्रतीक्षा है",
  awaitingDesc:
    "बाईं ओर एक कार्य सबमिट करें। AegisAI कई एजेंटों के बीच विचार-विमर्श करेगा और एक संतुलित निर्णय तैयार करेगा।",
  decisionSynthesis: "निर्णय संश्लेषण",
  decisionSummary: "निर्णय सारांश",
  successProbability: "सफलता संभावना",
  riskLevel: "जोखिम स्तर",
  explanation: "व्याख्या — यह निर्णय क्यों",
  generatedSubtasks: "उत्पन्न उप-कार्य",
  similarMissions: "समान पिछले मिशन",
  multiAgentDebate: "मल्टी-एजेंट बहस",
  optimistAgent: "आशावादी एजेंट",
  riskAgent: "जोखिम एजेंट",
  finalDecision: "अंतिम निर्णय · रिज़ॉल्वर",
  calibrated: "142 समान मिशनों के विरुद्ध कैलिब्रेट किया गया",
  riskComposite: "निर्भरता, ब्लास्ट-रेडियस और प्रतिवर्तीयता स्कोर का संयोजन।",
  helpful: "उपयोगी",
  notHelpful: "उपयोगी नहीं",
  feedbackSaved: "फीडबैक दर्ज — एजेंट पुनः कैलिब्रेट करेंगे।",
  feedbackFailed: "फीडबैक नहीं भेज सके",
  decisionDone: "निर्णय तैयार",
  consensusReached: "मल्टी-एजेंट सहमति प्राप्त।",
  errorTitle: "AegisAI विफल",

  intelligenceView: "बुद्धिमत्ता दृश्य",
  memoryGraph: "मेमोरी ग्राफ़",
  workflow: "वर्कफ़्लो",
  executionLogs: "निष्पादन लॉग्स",
  noLogs: "अभी तक कोई निष्पादन घटना नहीं।",

  lowRisk: "कम जोखिम",
  mediumRisk: "मध्यम जोखिम",
  highRisk: "उच्च जोखिम",

  outcomeSuccess: "सफल",
  outcomePartial: "आंशिक",
  outcomeFailed: "विफल",
};

const dicts: Record<Language, Dict> = { en, hi };

export function useT(language: Language) {
  return (key: keyof typeof en) => dicts[language][key] ?? en[key];
}

export type TFn = ReturnType<typeof useT>;
