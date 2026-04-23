import { useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";

type RoutePerfSnapshot = {
  totalSamples: number;
  triggerCounts: Record<string, number>;
  routeCounts: Record<string, number>;
  familyCounts: Record<string, number>;
};

type RoutePerfHistoryEntry = {
  windowIndex: number;
  generatedAt: string;
  totalSamples: number;
  overall: {
    p95: number;
  } | null;
  byFamily: Record<string, { p95: number }>;
};

type RoutePerfConsole = {
  snapshot: () => RoutePerfSnapshot;
  history: () => RoutePerfHistoryEntry[];
  clearHistory: () => void;
  exportCsv: () => string;
  exportHistoryCsv: () => string;
  exportHistoryJson: () => string;
  exportLatestWindowCsv: () => string;
  exportLatestWindowJson: () => string;
  exportSnapshotJson: () => string;
  exportBundleJson: () => string;
  downloadCsv: () => boolean;
  downloadHistoryCsv: () => boolean;
  downloadHistoryJson: () => boolean;
  downloadLatestWindowCsv: () => boolean;
  downloadLatestWindowJson: () => boolean;
  downloadSnapshotJson: () => boolean;
  downloadBundleJson: () => boolean;
  copyCsv: () => Promise<boolean>;
  copyHistoryCsv: () => Promise<boolean>;
  copyHistoryJson: () => Promise<boolean>;
  copyLatestWindowCsv: () => Promise<boolean>;
  copyLatestWindowJson: () => Promise<boolean>;
  copySnapshotJson: () => Promise<boolean>;
  copyBundleJson: () => Promise<boolean>;
};

const readRoutePerfConsole = () => (window as Window & { __routePerf?: RoutePerfConsole }).__routePerf;

const formatCountMap = (counts: Record<string, number>) =>
  Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 4)
    .map(([key, value]) => `${key}:${value}`)
    .join("  ");

const formatP95 = (value?: number) => (typeof value === "number" ? `${value.toFixed(1)}ms` : "n/a");

type RoutePerfStatus =
  | "idle"
  | "csv"
  | "history-csv"
  | "history-json"
  | "latest-window-csv"
  | "latest-window-json"
  | "snapshot-json"
  | "bundle-json"
  | "download-csv"
  | "download-history-csv"
  | "download-history-json"
  | "download-latest-window-csv"
  | "download-latest-window-json"
  | "download-snapshot-json"
  | "download-bundle-json"
  | "error";

const formatStatus = (status: RoutePerfStatus) => {
  switch (status) {
    case "csv":
      return "copied CSV";
    case "history-csv":
      return "copied history CSV";
    case "history-json":
      return "copied history JSON";
    case "latest-window-csv":
      return "copied latest window CSV";
    case "latest-window-json":
      return "copied latest window JSON";
    case "snapshot-json":
      return "copied snapshot JSON";
    case "bundle-json":
      return "copied bundle JSON";
    case "download-csv":
      return "downloaded CSV";
    case "download-history-csv":
      return "downloaded history CSV";
    case "download-history-json":
      return "downloaded history JSON";
    case "download-latest-window-csv":
      return "downloaded latest window CSV";
    case "download-latest-window-json":
      return "downloaded latest window JSON";
    case "download-snapshot-json":
      return "downloaded snapshot JSON";
    case "download-bundle-json":
      return "downloaded bundle JSON";
    case "error":
      return "action failed";
    default:
      return "";
  }
};

const getLatestFamilyP95 = (entry?: RoutePerfHistoryEntry) => {
  if (!entry) {
    return "n/a";
  }

  const familyEntries = Object.entries(entry.byFamily);
  if (familyEntries.length === 0) {
    return "n/a";
  }

  const [family, metrics] = familyEntries.sort((a, b) => b[1].p95 - a[1].p95)[0];
  return `${family}:${metrics.p95.toFixed(1)}ms`;
};

const DevRoutePerfOverlay = () => {
  const [visible, setVisible] = useState(true);
  const [snapshot, setSnapshot] = useState<RoutePerfSnapshot | null>(null);
  const [history, setHistory] = useState<RoutePerfHistoryEntry[]>([]);
  const [historyCount, setHistoryCount] = useState(0);
  const [copyState, setCopyState] = useState<RoutePerfStatus>("idle");

  useEffect(() => {
    if (!import.meta.env.DEV) {
      return;
    }

    const refresh = () => {
      const devConsole = readRoutePerfConsole();
      if (!devConsole) {
        return;
      }

      setSnapshot(devConsole.snapshot());
      const allHistory = devConsole.history();
      setHistoryCount(allHistory.length);
      setHistory(allHistory.slice(-5));
    };

    refresh();
    const intervalId = window.setInterval(refresh, 1000);
    const keydownHandler = (event: KeyboardEvent) => {
      if (!event.ctrlKey || !event.altKey || event.shiftKey || event.metaKey) {
        return;
      }

      const key = event.key.toLowerCase();

      if (key !== "r" && key !== "j" && key !== "k" && key !== "l" && key !== "s" && key !== "a" && key !== "o" && key !== "w" && key !== "d" && key !== "h" && key !== "i" && key !== "y" && key !== "u") {
        return;
      }

      const target = event.target as HTMLElement | null;
      if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable)) {
        return;
      }

      event.preventDefault();

      if (key === "r") {
        setVisible((current) => !current);
        return;
      }

      const devConsole = readRoutePerfConsole();
      if (!devConsole) {
        return;
      }

      if (key === "o") {
        setCopyState(devConsole.downloadSnapshotJson() ? "download-snapshot-json" : "error");
        return;
      }

      if (key === "w") {
        setCopyState(devConsole.downloadBundleJson() ? "download-bundle-json" : "error");
        return;
      }

      if (key === "d") {
        setCopyState(devConsole.downloadCsv() ? "download-csv" : "error");
        return;
      }

      if (key === "h") {
        setCopyState(devConsole.downloadHistoryCsv() ? "download-history-csv" : "error");
        return;
      }

      if (key === "i") {
        setCopyState(devConsole.downloadHistoryJson() ? "download-history-json" : "error");
        return;
      }

      if (key === "y") {
        setCopyState(devConsole.downloadLatestWindowCsv() ? "download-latest-window-csv" : "error");
        return;
      }

      if (key === "u") {
        setCopyState(devConsole.downloadLatestWindowJson() ? "download-latest-window-json" : "error");
        return;
      }

      const copyAction =
        key === "j"
          ? devConsole.copyHistoryJson
          : key === "k"
            ? devConsole.copyLatestWindowCsv
            : key === "l"
              ? devConsole.copyLatestWindowJson
              : key === "s"
                ? devConsole.copySnapshotJson
                : devConsole.copyBundleJson;

      void Promise.resolve(copyAction()).then((success) => {
        if (!success) {
          setCopyState("error");
          return;
        }

        setCopyState(
          key === "k"
            ? "latest-window-csv"
            : key === "l"
              ? "latest-window-json"
              : key === "s"
                ? "snapshot-json"
                : key === "a"
                  ? "bundle-json"
                  : key === "j"
                    ? "history-json"
                    : "csv",
        );
      });
    };

    window.addEventListener("keydown", keydownHandler);

    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener("keydown", keydownHandler);
    };
  }, []);

  const latestWindow = history.at(-1);
  const latestFamilyLabel = useMemo(() => {
    if (!snapshot?.familyCounts) {
      return "n/a";
    }

    const entries = Object.entries(snapshot.familyCounts).filter(([, count]) => count > 0);
    if (entries.length === 0) {
      return "n/a";
    }

    return entries.sort((a, b) => b[1] - a[1]).map(([family, count]) => `${family}:${count}`).join("  ");
  }, [snapshot]);

  useEffect(() => {
    if (!import.meta.env.DEV || copyState === "idle" || copyState === "error") {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setCopyState("idle");
    }, 2500);

    return () => window.clearTimeout(timeoutId);
  }, [copyState]);

  if (!import.meta.env.DEV) {
    return null;
  }

  if (!visible) {
    return (
      <div className="fixed bottom-4 right-4 z-[60]">
        <Button type="button" size="sm" variant="secondary" className="rounded-full shadow-lg" onClick={() => setVisible(true)}>
          Route Perf
        </Button>
      </div>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 z-[60] w-[340px] max-w-[calc(100vw-2rem)]">
      <Card className="border-border/70 bg-background/95 shadow-2xl backdrop-blur supports-[backdrop-filter]:bg-background/85">
        <CardHeader className="space-y-2 pb-3">
          <div className="flex items-center justify-between gap-2">
            <CardTitle className="text-sm font-semibold tracking-wide">Route Perf</CardTitle>
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="text-[10px] uppercase tracking-[0.22em]">
                dev
              </Badge>
              <Badge variant="outline" className="text-[10px] uppercase tracking-[0.22em]">
                {`${historyCount}/20`}
              </Badge>
            </div>
          </div>
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>live samples</span>
            <span>{snapshot?.totalSamples ?? 0}</span>
          </div>
          <div className="h-1 rounded-full bg-muted">
            <div
              className="h-1 rounded-full bg-primary transition-all"
              style={{ width: `${Math.min(100, (snapshot?.totalSamples ?? 0) * 10)}%` }}
            />
          </div>
        </CardHeader>
        <CardContent className="space-y-3 pt-0">
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-md border border-border/60 bg-muted/40 p-2">
              <div className="text-muted-foreground">latest p95</div>
              <div className="mt-1 font-medium">{formatP95(latestWindow?.overall?.p95)}</div>
            </div>
            <div className="rounded-md border border-border/60 bg-muted/40 p-2">
              <div className="text-muted-foreground">latest family p95</div>
              <div className="mt-1 font-medium">{getLatestFamilyP95(latestWindow)}</div>
            </div>
          </div>

          <div className="space-y-1 text-xs">
            <div className="text-muted-foreground">routes</div>
            <div className="min-h-8 rounded-md border border-border/60 bg-muted/30 p-2 font-mono text-[11px] text-foreground/90">
              {snapshot ? formatCountMap(snapshot.routeCounts) || "no route samples yet" : "loading..."}
            </div>
          </div>

          <div className="space-y-1 text-xs">
            <div className="text-muted-foreground">families</div>
            <div className="min-h-8 rounded-md border border-border/60 bg-muted/30 p-2 font-mono text-[11px] text-foreground/90">
              {latestFamilyLabel}
            </div>
          </div>

          <ScrollArea className="h-28 rounded-md border border-border/60 bg-muted/20 p-2">
            <div className="space-y-2 text-[11px] text-muted-foreground">
              {history.length === 0 ? (
                <div>no completed summary windows yet</div>
              ) : (
                history
                  .slice()
                  .reverse()
                  .map((entry) => (
                    <div key={entry.windowIndex} className="rounded-md border border-border/50 bg-background/80 p-2 text-foreground/90">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-medium">window {entry.windowIndex}</span>
                        <span>{new Date(entry.generatedAt).toLocaleTimeString()}</span>
                      </div>
                      <div className="mt-1 text-muted-foreground">
                        samples {entry.totalSamples} · p95 {formatP95(entry.overall?.p95)}
                      </div>
                    </div>
                  ))
              )}
            </div>
          </ScrollArea>

          <div className="grid grid-cols-2 gap-2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => {
                const devConsole = readRoutePerfConsole();
                devConsole?.clearHistory();
                setCopyState("idle");
              }}
            >
              Clear History
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={async () => {
                const devConsole = readRoutePerfConsole();
                if (!devConsole) {
                  return;
                }

                setCopyState((await devConsole.copyHistoryJson()) ? "history-json" : "error");
              }}
            >
              Copy History JSON
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={async () => {
                const devConsole = readRoutePerfConsole();
                if (!devConsole) {
                  return;
                }

                setCopyState((await devConsole.copyLatestWindowJson()) ? "latest-window-json" : "error");
              }}
            >
              Copy Latest Window JSON
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={async () => {
                const devConsole = readRoutePerfConsole();
                if (!devConsole) {
                  return;
                }

                setCopyState((await devConsole.copySnapshotJson()) ? "snapshot-json" : "error");
              }}
            >
              Copy Snapshot JSON
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={async () => {
                const devConsole = readRoutePerfConsole();
                if (!devConsole) {
                  return;
                }

                setCopyState((await devConsole.copyBundleJson()) ? "bundle-json" : "error");
              }}
            >
              Copy Bundle JSON
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => {
                const devConsole = readRoutePerfConsole();
                if (!devConsole) {
                  return;
                }

                setCopyState(devConsole.downloadSnapshotJson() ? "download-snapshot-json" : "error");
              }}
            >
              Download Snapshot JSON
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => {
                const devConsole = readRoutePerfConsole();
                if (!devConsole) {
                  return;
                }

                setCopyState(devConsole.downloadHistoryCsv() ? "download-history-csv" : "error");
              }}
            >
              Download History CSV
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => {
                const devConsole = readRoutePerfConsole();
                if (!devConsole) {
                  return;
                }

                setCopyState(devConsole.downloadHistoryJson() ? "download-history-json" : "error");
              }}
            >
              Download History JSON
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => {
                const devConsole = readRoutePerfConsole();
                if (!devConsole) {
                  return;
                }

                setCopyState(devConsole.downloadLatestWindowCsv() ? "download-latest-window-csv" : "error");
              }}
            >
              Download Latest Window CSV
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => {
                const devConsole = readRoutePerfConsole();
                if (!devConsole) {
                  return;
                }

                setCopyState(devConsole.downloadLatestWindowJson() ? "download-latest-window-json" : "error");
              }}
            >
              Download Latest Window JSON
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => {
                const devConsole = readRoutePerfConsole();
                if (!devConsole) {
                  return;
                }

                setCopyState(devConsole.downloadBundleJson() ? "download-bundle-json" : "error");
              }}
            >
              Download Bundle JSON
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => {
                const devConsole = readRoutePerfConsole();
                if (!devConsole) {
                  return;
                }

                setCopyState(devConsole.downloadCsv() ? "download-csv" : "error");
              }}
            >
              Download CSV
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={async () => {
                const devConsole = readRoutePerfConsole();
                if (!devConsole) {
                  return;
                }

                setCopyState((await devConsole.copyLatestWindowCsv()) ? "latest-window-csv" : "error");
              }}
            >
              Copy Latest Window CSV
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={async () => {
                const devConsole = readRoutePerfConsole();
                if (!devConsole) {
                  return;
                }

                setCopyState((await devConsole.copyCsv()) ? "csv" : "error");
              }}
            >
              Copy CSV
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={async () => {
                const devConsole = readRoutePerfConsole();
                if (!devConsole) {
                  return;
                }

                setCopyState((await devConsole.copyHistoryCsv()) ? "history-csv" : "error");
              }}
            >
              Copy History
            </Button>
          </div>

          <div className="flex items-center justify-between gap-2 text-[11px] text-muted-foreground">
            <span>
              {copyState === "idle" ? `history ${history.length} windows` : formatStatus(copyState)} · Ctrl+Alt+R toggles · Ctrl+Alt+J copies history JSON · Ctrl+Alt+L copies latest window JSON · Ctrl+Alt+K copies latest window CSV · Ctrl+Alt+S copies snapshot JSON · Ctrl+Alt+A copies bundle JSON · Ctrl+Alt+O downloads snapshot JSON · Ctrl+Alt+W downloads bundle JSON · Ctrl+Alt+D downloads CSV · Ctrl+Alt+H downloads history CSV · Ctrl+Alt+I downloads history JSON · Ctrl+Alt+Y downloads latest window CSV · Ctrl+Alt+U downloads latest window JSON
            </span>
            <div className="flex items-center gap-2">
              <Button type="button" variant="ghost" size="sm" className="h-7 px-2 text-[11px]" onClick={() => setCopyState("idle")}>Reset Copy State</Button>
              <Button type="button" variant="ghost" size="sm" className="h-7 px-2 text-[11px]" onClick={() => setVisible(false)}>
                Hide
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default DevRoutePerfOverlay;