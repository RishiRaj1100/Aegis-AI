import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, LineChart, Orbit, RefreshCcw, Save, ShieldAlert, Workflow, Wand2 } from "lucide-react";
import { useAuth, withAuth } from "@/contexts/AuthContext";
import { useMission } from "@/contexts/MissionContext";
import { APIError, intelligenceAPI } from "@/services/api";
import { useToast } from "@/components/ui/use-toast";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import mermaid from "mermaid";

const pretty = (value: unknown) => JSON.stringify(value, null, 2);

const safeDiagramId = (prefix: string, value: string) => {
  const slug = value.replace(/[^a-zA-Z0-9_]/g, "_").replace(/_+/g, "_").replace(/^_+|_+$/g, "");
  return `${prefix}-${slug || "diagram"}`;
};

const Intelligence = () => {
  const navigate = useNavigate();
  const { logout, user } = useAuth();
  const { toast } = useToast();
  const { mission } = useMission();

  const [overview, setOverview] = useState<any>(null);
  const [profile, setProfile] = useState<any>(null);
  const [drift, setDrift] = useState<any>(null);
  const [models, setModels] = useState<any[]>([]);
  const [reflection, setReflection] = useState<any>(null);
  const [taskId, setTaskId] = useState("");
  const [graph, setGraph] = useState<any>(null);
  const [similar, setSimilar] = useState<any[]>([]);
  const [goal, setGoal] = useState("");
  const [prediction, setPrediction] = useState<any>(null);
  const [simulation, setSimulation] = useState<any>(null);
  const [workflowTitle, setWorkflowTitle] = useState("Launch workflow");
  const [workflow, setWorkflow] = useState("Research -> Build -> Review\nReview -> Ship");
  const [parsedWorkflow, setParsedWorkflow] = useState<any>(null);
  const [graphError, setGraphError] = useState<string | null>(null);
  const [workflowError, setWorkflowError] = useState<string | null>(null);
  const [modelName, setModelName] = useState("Catalyst Heuristic v1");
  const [modelVersion, setModelVersion] = useState("1.0.0");
  const [modelDescription, setModelDescription] = useState("Baseline heuristic predictor for route, risk, and confidence calibration.");
  const graphContainerRef = useRef<HTMLDivElement | null>(null);
  const workflowContainerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [overviewResult, profileResult, driftResult, modelResult, reflectionResult] = await Promise.all([
          intelligenceAPI.getOverview(),
          intelligenceAPI.getProfile(),
          intelligenceAPI.getDrift(),
          intelligenceAPI.listModels(),
          intelligenceAPI.getReflectionReport(),
        ]);
        setOverview(overviewResult);
        setProfile(profileResult);
        setDrift(driftResult);
        setModels(modelResult);
        setReflection(reflectionResult);
      } catch (error) {
        const message = error instanceof APIError ? error.detail : "Failed to load intelligence data";
        toast({ title: "Error", description: message, variant: "destructive" });
      }
    };

    load();
  }, [toast]);

  useEffect(() => {
    if (!mission?.goal) {
      return;
    }

    setGoal(mission.goal);
  }, [mission?.goal]);

  useEffect(() => {
    if (!mission?.taskId) {
      return;
    }

    setTaskId(mission.taskId);
    void loadGraph(mission.taskId);
  }, [mission?.taskId]);

  useEffect(() => {
    mermaid.initialize({ startOnLoad: false, theme: 'dark' });
  }, []);

  useEffect(() => {
    const render = async () => {
      if (!graph?.mermaid || !graphContainerRef.current) {
        return;
      }

      try {
        const id = safeDiagramId("graph", String(graph.task_id || "mission"));
        const { svg } = await mermaid.render(id, graph.mermaid);
        if (graphContainerRef.current) {
          graphContainerRef.current.innerHTML = svg;
        }
      } catch (error) {
        console.error('Failed to render execution graph:', error);
      }
    };

    void render();
  }, [graph?.mermaid]);

  useEffect(() => {
    const render = async () => {
      if (!parsedWorkflow?.mermaid || !workflowContainerRef.current) {
        return;
      }

      try {
        const id = safeDiagramId("workflow", workflowTitle || "workflow");
        const { svg } = await mermaid.render(id, parsedWorkflow.mermaid);
        if (workflowContainerRef.current) {
          workflowContainerRef.current.innerHTML = svg;
        }
      } catch (error) {
        console.error('Failed to render workflow diagram:', error);
      }
    };

    void render();
  }, [parsedWorkflow?.mermaid, workflowTitle]);

  const showError = (error: unknown, fallback: string) => {
    const message = error instanceof APIError ? error.detail : fallback;
    toast({ title: "Error", description: message, variant: "destructive" });
  };

  const refreshAll = async () => {
    try {
      const [overviewResult, profileResult, driftResult, modelResult, reflectionResult] = await Promise.all([
        intelligenceAPI.getOverview(),
        intelligenceAPI.getProfile(),
        intelligenceAPI.getDrift(),
        intelligenceAPI.listModels(),
        intelligenceAPI.getReflectionReport(),
      ]);
      setOverview(overviewResult);
      setProfile(profileResult);
      setDrift(driftResult);
      setModels(modelResult);
      setReflection(reflectionResult);
      toast({ title: "Refreshed", description: "Intelligence layer reloaded." });
    } catch (error) {
      showError(error, "Failed to refresh intelligence data");
    }
  };

  const loadGraph = async (taskIdOverride?: string) => {
    const activeTaskId = (taskIdOverride || taskId).trim();

    if (!activeTaskId) {
      toast({ title: "Task ID required", description: "Enter a task ID to load a graph.", variant: "destructive" });
      return;
    }
    try {
      setGraphError(null);
      const result = await intelligenceAPI.getGraph(activeTaskId);
      setGraph(result);
      const similarResult = await intelligenceAPI.getSimilarTasks(activeTaskId);
      setSimilar(similarResult);
    } catch (error) {
      setGraph(null);
      setSimilar([]);
      setGraphError(error instanceof APIError ? error.detail : "Failed to load execution graph");
      showError(error, "Failed to load execution graph");
    }
  };

  const predictGoal = async (goalOverride?: string) => {
    const activeGoal = (goalOverride || goal).trim();

    if (!activeGoal) {
      toast({ title: "Goal required", description: "Enter a goal to predict outcomes.", variant: "destructive" });
      return;
    }
    try {
      const [predictionResult, simulationResult] = await Promise.all([
        intelligenceAPI.predict(activeGoal),
        intelligenceAPI.simulate(activeGoal, "baseline"),
      ]);
      setPrediction(predictionResult);
      setSimulation(simulationResult);
    } catch (error) {
      showError(error, "Failed to predict outcome");
    }
  };

  const parseWorkflow = async () => {
    try {
      setWorkflowError(null);
      const result = await intelligenceAPI.parseWorkflow(workflow, workflowTitle);
      setParsedWorkflow(result);
      toast({ title: "Workflow parsed", description: "Mermaid graph generated from the workflow text." });
    } catch (error) {
      setParsedWorkflow(null);
      setWorkflowError(error instanceof APIError ? error.detail : "Failed to parse workflow");
      showError(error, "Failed to parse workflow");
    }
  };

  const saveModel = async () => {
    try {
      const result = await intelligenceAPI.registerModel({
        name: modelName,
        version: modelVersion,
        description: modelDescription,
        status: "active",
      });
      setModels((current) => [result, ...current.filter((model) => model.model_id !== result.model_id)]);
      toast({ title: "Model saved", description: `${modelName} ${modelVersion} is now in the registry.` });
    } catch (error) {
      showError(error, "Failed to register model");
    }
  };

  const rollbackModel = async (modelId: string) => {
    try {
      await intelligenceAPI.rollbackModel(modelId);
      await refreshAll();
      toast({ title: "Rollback complete", description: "Model registry switched to the selected version." });
    } catch (error) {
      showError(error, "Failed to rollback model");
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="mx-auto max-w-7xl px-6 py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate("/dashboard")} className="btn-ghost !px-3 !py-2">
              <ArrowLeft size={16} />
            </button>
            <div>
              <h1 className="text-2xl font-bold text-foreground">Intelligence Lab</h1>
              <p className="text-sm text-muted-foreground">Working agent system plus the next-phase execution intelligence layer.</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="secondary" onClick={refreshAll} className="gap-2">
              <RefreshCcw size={16} />
              Refresh
            </Button>
            <button
              onClick={() => {
                logout();
              }}
              className="btn-ghost !px-4 !py-2 flex items-center gap-2 text-aegis-rose hover:text-aegis-rose"
            >
              Sign Out
            </button>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-6 py-8 space-y-8">
        {mission ? (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mission-shell mission-orbit rounded-2xl border border-white/10 bg-white/5 p-5"
          >
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Live mission</p>
                <h2 className="mt-1 text-xl font-semibold text-foreground">{mission.goal}</h2>
                <p className="text-sm text-muted-foreground">Task {mission.taskId || "pending"} · {mission.status} · {mission.riskLevel}</p>
              </div>
              <div className="flex gap-2 text-sm">
                <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-muted-foreground">{Math.round(mission.confidence)}% confidence</span>
                <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-muted-foreground">{mission.subtasks} subtasks</span>
              </div>
            </div>
          </motion.div>
        ) : null}

        <div className="grid gap-4 md:grid-cols-4">
          {[
            { label: "Tasks", value: overview?.total_tasks ?? 0, icon: Orbit },
            { label: "Models", value: overview?.total_models ?? 0, icon: Save },
            { label: "Reports", value: overview?.total_reports ?? 0, icon: LineChart },
            { label: "Drift", value: `${Math.round((overview?.drift_score ?? 0) * 100)}%`, icon: ShieldAlert },
          ].map((card) => (
            <motion.div key={card.label} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="glass-card rounded-lg p-5">
              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <span>{card.label}</span>
                <card.icon size={16} />
              </div>
              <div className="mt-3 text-3xl font-bold text-foreground">{card.value}</div>
            </motion.div>
          ))}
        </div>

        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList className="grid w-full grid-cols-5 lg:grid-cols-6">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="graph">Graph</TabsTrigger>
            <TabsTrigger value="predict">Predict</TabsTrigger>
            <TabsTrigger value="workflow">Workflow</TabsTrigger>
            <TabsTrigger value="registry">Registry</TabsTrigger>
            <TabsTrigger value="reports">Reports</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            <div className="grid gap-4 lg:grid-cols-3">
              <Card className="border-border/60 bg-background/95">
                <CardHeader>
                  <CardTitle className="text-base">Strategy Profile</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm text-muted-foreground">
                  <div className="text-foreground font-medium">{profile?.profile_name ?? "Loading..."}</div>
                  <p>{profile?.preferred_approach}</p>
                  <div>Success rate: {(profile?.success_rate ?? 0) * 100}%</div>
                  <div>Average confidence: {profile?.average_confidence ?? 0}%</div>
                  <div className="flex flex-wrap gap-2">
                    {(profile?.recent_domains || []).map((domain: string) => (
                      <Badge key={domain} variant="secondary">{domain}</Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card className="border-border/60 bg-background/95">
                <CardHeader>
                  <CardTitle className="text-base">Drift Monitoring</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm text-muted-foreground">
                  <div className="text-foreground font-medium">{drift?.retraining_recommended ? "Retraining recommended" : "Stable"}</div>
                  <div>Baseline confidence: {drift?.baseline_confidence ?? 0}%</div>
                  <div>Recent confidence: {drift?.recent_confidence ?? 0}%</div>
                  <div>Baseline success rate: {(drift?.baseline_success_rate ?? 0) * 100}%</div>
                  <div>Recent success rate: {(drift?.recent_success_rate ?? 0) * 100}%</div>
                </CardContent>
              </Card>

              <Card className="border-border/60 bg-background/95">
                <CardHeader>
                  <CardTitle className="text-base">Reflection Reports</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm text-muted-foreground">
                  <div className="text-foreground font-medium">Latest calibration notes</div>
                  <p className="whitespace-pre-wrap">{reflection?.confidence_calibration_note || reflection?.pattern_summary || "No report yet."}</p>
                </CardContent>
              </Card>
            </div>

            <Card className="border-border/60 bg-background/95">
              <CardHeader>
                <CardTitle className="text-base">Human-in-the-loop override queue</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm text-muted-foreground">
                <div>Queued review count: {overview?.human_review_queue_size ?? 0}</div>
                <div>Scheduled reflection status: {overview?.scheduled_reflection_status ?? "idle"}</div>
                <div>Active model: {overview?.active_model ?? "none"}</div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="graph" className="space-y-6">
            <Card className="border-border/60 bg-background/95">
              <CardHeader>
                <CardTitle className="text-base">Execution Memory Graph</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-col gap-3 md:flex-row">
                  <Input value={taskId} onChange={(event) => setTaskId(event.target.value)} placeholder="Enter task ID" />
                  <Button onClick={() => loadGraph()} className="gap-2">
                    <Workflow size={16} />
                    Load Graph
                  </Button>
                </div>
                {graphError ? (
                  <div className="rounded-xl border border-amber-400/30 bg-amber-400/10 p-4 text-sm text-amber-100">
                    {graphError}
                  </div>
                ) : null}
                {graph && (
                  <div className="grid gap-4 lg:grid-cols-2">
                    <div>
                      <h3 className="text-sm font-semibold text-foreground mb-3">Pictorial Graph</h3>
                      <div ref={graphContainerRef} className="min-h-72 rounded-lg border border-border/60 bg-background p-4 overflow-auto" />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-foreground mb-3">Graph Details</h3>
                      <ScrollArea className="h-72 rounded-lg border border-border/60 p-3">
                        <div className="space-y-2">
                          {graph.nodes.map((node: any) => (
                            <div key={node.id} className="rounded-md border border-border/60 bg-secondary/40 p-3">
                              <div className="flex items-center justify-between gap-2">
                                <span className="font-medium text-foreground">{node.label}</span>
                                <Badge variant="outline">{node.type}</Badge>
                              </div>
                              <p className="text-xs text-muted-foreground mt-1">{node.status}</p>
                            </div>
                          ))}
                        </div>
                      </ScrollArea>
                    </div>
                  </div>
                )}
                {similar.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-foreground mb-3">Similar Tasks</h3>
                    <div className="grid gap-3 md:grid-cols-2">
                      {similar.map((item) => (
                        <div key={item.task_id} className="rounded-lg border border-border/60 bg-secondary/40 p-4 text-sm">
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-medium text-foreground">{item.goal}</span>
                            <Badge>{Math.round(item.similarity * 100)}%</Badge>
                          </div>
                          <div className="mt-2 text-muted-foreground">Confidence {item.confidence}% · {item.risk_level} · {item.status}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="predict" className="space-y-6">
            <Card className="border-border/60 bg-background/95">
              <CardHeader>
                <CardTitle className="text-base">Outcome Prediction</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Textarea value={goal} onChange={(event) => setGoal(event.target.value)} placeholder="Enter a goal to predict success probability" className="min-h-32" />
                <div className="flex gap-3">
                  <Button onClick={() => predictGoal()} className="gap-2">
                    <Wand2 size={16} />
                    Predict and Simulate
                  </Button>
                </div>
                {prediction && (
                  <div className="grid gap-4 lg:grid-cols-2">
                    <div className="rounded-lg border border-border/60 bg-secondary/40 p-4">
                      <div className="text-sm text-muted-foreground">Predicted success</div>
                      <div className="mt-1 text-3xl font-bold text-foreground">{Math.round(prediction.predicted_success_probability * 100)}%</div>
                      <div className="mt-2 text-sm">Risk: {prediction.predicted_risk_level}</div>
                      <div className="mt-2 text-sm">Band: {prediction.confidence_band}</div>
                      <div className="mt-2 text-sm">Human review: {prediction.human_review_required ? "Required" : "Optional"}</div>
                    </div>
                    <div className="rounded-lg border border-border/60 bg-secondary/40 p-4 text-sm text-muted-foreground">
                      <div className="font-medium text-foreground mb-2">Safeguards</div>
                      <ul className="space-y-2">
                        {(prediction.recommended_safeguards || []).map((item: string) => <li key={item}>• {item}</li>)}
                      </ul>
                      <Separator className="my-4" />
                      <div className="font-medium text-foreground mb-2">Failure modes</div>
                      <ul className="space-y-2">
                        {(prediction.likely_failure_modes || []).map((item: string) => <li key={item}>• {item}</li>)}
                      </ul>
                    </div>
                  </div>
                )}
                {simulation && (
                  <div className="rounded-lg border border-border/60 bg-muted/30 p-4 text-sm text-muted-foreground">
                    <div className="font-medium text-foreground">Simulation result</div>
                    <div>Scenario: {simulation.scenario}</div>
                    <div>Predicted confidence: {simulation.predicted_confidence}%</div>
                    <div>Risk: {simulation.predicted_risk_level}</div>
                    <div className="mt-2 font-medium text-foreground">Mitigation steps</div>
                    <ul className="mt-2 space-y-1">
                      {(simulation.mitigation_steps || []).map((item: string) => <li key={item}>• {item}</li>)}
                    </ul>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="workflow" className="space-y-6">
            <Card className="border-border/60 bg-background/95">
              <CardHeader>
                <CardTitle className="text-base">Workflow DSL Editor</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Input value={workflowTitle} onChange={(event) => setWorkflowTitle(event.target.value)} placeholder="Workflow title" />
                <Textarea value={workflow} onChange={(event) => setWorkflow(event.target.value)} className="min-h-40" placeholder="Use arrows or task chains, for example: Research -> Build -> Review" />
                <div className="flex gap-3">
                  <Button onClick={parseWorkflow}>Parse Workflow</Button>
                </div>
                {workflowError ? (
                  <div className="rounded-xl border border-rose-400/30 bg-rose-400/10 p-4 text-sm text-rose-100">
                    {workflowError}
                  </div>
                ) : null}
                {parsedWorkflow && (
                  <div className="grid gap-4 lg:grid-cols-2">
                    <div>
                      <h3 className="text-sm font-semibold text-foreground mb-2">Pictorial Workflow</h3>
                      <div ref={workflowContainerRef} className="min-h-72 rounded-lg border border-border/60 bg-background p-4 overflow-auto" />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-foreground mb-2">Workflow Steps</h3>
                      <div className="space-y-2">
                        {parsedWorkflow.nodes.map((node: any) => (
                          <div key={node.id} className="rounded-md border border-border/60 bg-secondary/40 p-3 text-sm">
                            <div className="font-medium text-foreground">{node.label}</div>
                            <div className="text-xs text-muted-foreground">{node.id}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="registry" className="space-y-6">
            <Card className="border-border/60 bg-background/95">
              <CardHeader>
                <CardTitle className="text-base">Model Registry</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-3 md:grid-cols-3">
                  <Input value={modelName} onChange={(event) => setModelName(event.target.value)} placeholder="Model name" />
                  <Input value={modelVersion} onChange={(event) => setModelVersion(event.target.value)} placeholder="Version" />
                  <Button onClick={saveModel} className="gap-2"><Save size={16} /> Save model</Button>
                </div>
                <Textarea value={modelDescription} onChange={(event) => setModelDescription(event.target.value)} className="min-h-24" placeholder="Model description" />
                <div className="grid gap-4 md:grid-cols-2">
                  {models.map((model) => (
                    <div key={model.model_id} className="rounded-lg border border-border/60 bg-secondary/40 p-4 text-sm">
                      <div className="flex items-center justify-between gap-2">
                        <div>
                          <div className="font-medium text-foreground">{model.name}</div>
                          <div className="text-xs text-muted-foreground">{model.version}</div>
                        </div>
                        <Badge variant={model.active ? "default" : "secondary"}>{model.active ? "active" : model.status}</Badge>
                      </div>
                      <p className="mt-2 text-muted-foreground">{model.description}</p>
                      <div className="mt-3 flex items-center gap-2">
                        <Button size="sm" variant="secondary" onClick={() => rollbackModel(model.model_id)}>Rollback</Button>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="reports" className="space-y-6">
            <Card className="border-border/60 bg-background/95">
              <CardHeader>
                <CardTitle className="text-base">Reflection Report</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm text-muted-foreground">
                <div className="font-medium text-foreground">Pattern Summary</div>
                <p className="whitespace-pre-wrap">{reflection?.pattern_summary || "No reflection report yet."}</p>
                <div className="font-medium text-foreground">Lessons</div>
                <ul className="space-y-2">
                  {(reflection?.lessons || []).map((lesson: string) => <li key={lesson}>• {lesson}</li>)}
                </ul>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        <Card className="border-border/60 bg-background/95">
          <CardHeader>
            <CardTitle className="text-base">Status</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            <div>Signed in as {user?.name}</div>
            <div className="mt-2">This page combines the current agent system with the future intelligence layer you asked for.</div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default withAuth(Intelligence);
