type NavigationTrigger = "click" | "pushstate" | "replacestate" | "popstate" | "navigation";
type RouteFamily = "auth" | "app" | "other";

type RoutePerfSnapshot = {
  totalSamples: number;
  triggerCounts: Partial<Record<NavigationTrigger, number>>;
  routeCounts: Record<string, number>;
  familyCounts: Partial<Record<RouteFamily, number>>;
};

type RoutePerfDistribution = {
  count: number;
  p50: number;
  p95: number;
  min: number;
  max: number;
};

type RoutePerfExport = {
  generatedAt: string;
  sampleWindowSize: number;
  totalSamples: number;
  overall: RoutePerfDistribution | null;
  byTrigger: Partial<Record<NavigationTrigger, RoutePerfDistribution>>;
  byRoute: Record<string, RoutePerfDistribution>;
  byFamily: Partial<Record<RouteFamily, RoutePerfDistribution>>;
};

type RoutePerfHistoryEntry = RoutePerfExport & {
  windowIndex: number;
};

type RoutePerfHistoryReport = {
  generatedAt: string;
  entryCount: number;
  entries: RoutePerfHistoryEntry[];
};

type RoutePerfBundleReport = {
  generatedAt: string;
  snapshot: RoutePerfExport;
  latestWindow: RoutePerfHistoryEntry | null;
  history: RoutePerfHistoryEntry[];
};

type RoutePerfLatestWindowReport = RoutePerfHistoryEntry | null;

type RoutePerfRow = {
  group: "overall" | "trigger" | "route" | "family";
  key: string;
  count: number;
  p50: number;
  p95: number;
  min: number;
  max: number;
};

type PendingNavigation = {
  startedAt: number;
  from: string;
  to?: string;
  trigger: NavigationTrigger;
};

type RouteTimingOptions = {
  enabled?: boolean;
};

let didInstallHooks = false;
let pendingNavigation: PendingNavigation | null = null;
const SUMMARY_SAMPLE_SIZE = 10;
const HISTORY_BUFFER_SIZE = 20;
const routeDurationSamples: number[] = [];
const routeDurationByTrigger: Partial<Record<NavigationTrigger, number[]>> = {};
const routeDurationByPath: Record<string, number[]> = {};
const routeDurationByFamily: Partial<Record<RouteFamily, number[]>> = {};
const routePerfHistory: RoutePerfHistoryEntry[] = [];
let routePerfWindowIndex = 0;

const isRouteTimingEnabled = (options?: RouteTimingOptions) =>
  options?.enabled ?? import.meta.env.DEV;

const getCurrentPath = () => `${window.location.pathname}${window.location.search}${window.location.hash}`;

const normalizePath = (value?: string) => {
  if (!value) {
    return "";
  }

  try {
    const parsed = new URL(value, window.location.origin);
    return `${parsed.pathname}${parsed.search}${parsed.hash}`;
  } catch {
    return value;
  }
};

function pushRoutePerfHistoryEntry(report: RoutePerfExport) {
  routePerfHistory.push({
    ...report,
    windowIndex: ++routePerfWindowIndex,
  });

  if (routePerfHistory.length > HISTORY_BUFFER_SIZE) {
    routePerfHistory.shift();
  }
}

function getRoutePerfHistory(): RoutePerfHistoryEntry[] {
  return routePerfHistory.map((entry) => ({ ...entry }));
}

function getLatestRoutePerfHistoryEntry(): RoutePerfLatestWindowReport {
  const latest = routePerfHistory.at(-1);
  return latest ? { ...latest } : null;
}

function clearRoutePerfHistory() {
  routePerfHistory.length = 0;
}

const beginNavigation = (to: string | undefined, trigger: NavigationTrigger) => {
  pendingNavigation = {
    startedAt: performance.now(),
    from: getCurrentPath(),
    to: normalizePath(to),
    trigger,
  };
};

const parseHistoryTarget = (target: string | URL | null | undefined) => {
  if (!target) {
    return undefined;
  }

  if (target instanceof URL) {
    return `${target.pathname}${target.search}${target.hash}`;
  }

  return target;
};

const mapNavigationTypeToTrigger = (navigationType: string): NavigationTrigger => {
  if (navigationType === "PUSH") {
    return "pushstate";
  }

  if (navigationType === "REPLACE") {
    return "replacestate";
  }

  if (navigationType === "POP") {
    return "popstate";
  }

  return "navigation";
};

const getRouteFamily = (path: string): RouteFamily => {
  if (
    path === "/login" ||
    path === "/register" ||
    path === "/forgot-password" ||
    path === "/ui/login" ||
    path === "/ui/register" ||
    path === "/ui/forgot-password"
  ) {
    return "auth";
  }

  if (
    path === "/dashboard" ||
    path === "/analytics" ||
    path === "/ui/dashboard" ||
    path === "/ui/analytics"
  ) {
    return "app";
  }

  return "other";
};

const getPercentile = (values: number[], percentile: number) => {
  if (values.length === 0) {
    return 0;
  }

  const sorted = [...values].sort((a, b) => a - b);
  const index = (sorted.length - 1) * percentile;
  const lowerIndex = Math.floor(index);
  const upperIndex = Math.ceil(index);
  const weight = index - lowerIndex;

  if (lowerIndex === upperIndex) {
    return sorted[lowerIndex];
  }

  return sorted[lowerIndex] * (1 - weight) + sorted[upperIndex] * weight;
};

const buildDistribution = (values: number[]): RoutePerfDistribution | null => {
  if (values.length === 0) {
    return null;
  }

  return {
    count: values.length,
    p50: Number(getPercentile(values, 0.5).toFixed(3)),
    p95: Number(getPercentile(values, 0.95).toFixed(3)),
    min: Number(Math.min(...values).toFixed(3)),
    max: Number(Math.max(...values).toFixed(3)),
  };
};

const maybeEmitSummary = () => {
  if (routeDurationSamples.length < SUMMARY_SAMPLE_SIZE) {
    return;
  }

  const p50 = getPercentile(routeDurationSamples, 0.5);
  const p95 = getPercentile(routeDurationSamples, 0.95);
  const min = Math.min(...routeDurationSamples);
  const max = Math.max(...routeDurationSamples);

  const triggerSummaries = Object.entries(routeDurationByTrigger)
    .filter((entry): entry is [NavigationTrigger, number[]] => Array.isArray(entry[1]) && entry[1].length > 0)
    .map(([trigger, values]) => `${trigger}:p95=${getPercentile(values, 0.95).toFixed(1)}ms(n=${values.length})`)
    .join(" ");

  const routeSummaries = Object.entries(routeDurationByPath)
    .filter((entry): entry is [string, number[]] => entry[1].length > 0)
    .sort((a, b) => b[1].length - a[1].length)
    .slice(0, 3)
    .map(([path, values]) => `${path}:p95=${getPercentile(values, 0.95).toFixed(1)}ms(n=${values.length})`)
    .join(" ");

  const routeSuffix = routeSummaries ? ` routes=${routeSummaries}` : "";

  const familySummaries = (Object.entries(routeDurationByFamily) as Array<[RouteFamily, number[]]>)
    .filter((entry) => entry[1].length > 0)
    .map(([family, values]) => `${family}:p95=${getPercentile(values, 0.95).toFixed(1)}ms(n=${values.length})`)
    .join(" ");

  const familySuffix = familySummaries ? ` families=${familySummaries}` : "";

  console.info(
    `[route-perf-summary] last ${routeDurationSamples.length} transitions p50=${p50.toFixed(1)}ms p95=${p95.toFixed(1)}ms min=${min.toFixed(1)}ms max=${max.toFixed(1)}ms ${triggerSummaries}${routeSuffix}${familySuffix}`.trim(),
  );

  pushRoutePerfHistoryEntry(getRoutePerfExport());

  routeDurationSamples.length = 0;
  Object.keys(routeDurationByTrigger).forEach((trigger) => {
    delete routeDurationByTrigger[trigger as NavigationTrigger];
  });
  Object.keys(routeDurationByPath).forEach((path) => {
    delete routeDurationByPath[path];
  });
  Object.keys(routeDurationByFamily).forEach((family) => {
    delete routeDurationByFamily[family as RouteFamily];
  });
};

const recordDurationSample = (trigger: NavigationTrigger, toPath: string, durationMs: number) => {
  routeDurationSamples.push(durationMs);

  const triggerSamples = routeDurationByTrigger[trigger] ?? [];
  triggerSamples.push(durationMs);
  routeDurationByTrigger[trigger] = triggerSamples;

  const routeSamples = routeDurationByPath[toPath] ?? [];
  routeSamples.push(durationMs);
  routeDurationByPath[toPath] = routeSamples;

  const family = getRouteFamily(toPath);
  const familySamples = routeDurationByFamily[family] ?? [];
  familySamples.push(durationMs);
  routeDurationByFamily[family] = familySamples;
};

const resetRoutePerfSamples = () => {
  routeDurationSamples.length = 0;
  Object.keys(routeDurationByTrigger).forEach((trigger) => {
    delete routeDurationByTrigger[trigger as NavigationTrigger];
  });
  Object.keys(routeDurationByPath).forEach((path) => {
    delete routeDurationByPath[path];
  });
  Object.keys(routeDurationByFamily).forEach((family) => {
    delete routeDurationByFamily[family as RouteFamily];
  });
};

const getRoutePerfSnapshot = (): RoutePerfSnapshot => {
  const triggerCounts: Partial<Record<NavigationTrigger, number>> = {};
  const routeCounts: Record<string, number> = {};
  const familyCounts: Partial<Record<RouteFamily, number>> = {};

  (Object.entries(routeDurationByTrigger) as Array<[NavigationTrigger, number[]]>).forEach(([trigger, values]) => {
    triggerCounts[trigger] = values.length;
  });

  Object.entries(routeDurationByPath).forEach(([path, values]) => {
    routeCounts[path] = values.length;
  });

  (Object.entries(routeDurationByFamily) as Array<[RouteFamily, number[]]>).forEach(([family, values]) => {
    familyCounts[family] = values.length;
  });

  return {
    totalSamples: routeDurationSamples.length,
    triggerCounts,
    routeCounts,
    familyCounts,
  };
};

const getRoutePerfExport = (): RoutePerfExport => {
  const byTrigger: Partial<Record<NavigationTrigger, RoutePerfDistribution>> = {};
  const byRoute: Record<string, RoutePerfDistribution> = {};
  const byFamily: Partial<Record<RouteFamily, RoutePerfDistribution>> = {};

  (Object.entries(routeDurationByTrigger) as Array<[NavigationTrigger, number[]]>).forEach(([trigger, values]) => {
    const distribution = buildDistribution(values);
    if (distribution) {
      byTrigger[trigger] = distribution;
    }
  });

  Object.entries(routeDurationByPath).forEach(([path, values]) => {
    const distribution = buildDistribution(values);
    if (distribution) {
      byRoute[path] = distribution;
    }
  });

  (Object.entries(routeDurationByFamily) as Array<[RouteFamily, number[]]>).forEach(([family, values]) => {
    const distribution = buildDistribution(values);
    if (distribution) {
      byFamily[family] = distribution;
    }
  });

  return {
    generatedAt: new Date().toISOString(),
    sampleWindowSize: SUMMARY_SAMPLE_SIZE,
    totalSamples: routeDurationSamples.length,
    overall: buildDistribution(routeDurationSamples),
    byTrigger,
    byRoute,
    byFamily,
  };
};

const toCsvCell = (value: string | number) => {
  const text = String(value);
  if (text.includes(",") || text.includes("\n") || text.includes("\"")) {
    return `"${text.replace(/\"/g, '""')}"`;
  }

  return text;
};

const getRoutePerfRows = (report: RoutePerfExport): RoutePerfRow[] => {
  const rows: RoutePerfRow[] = [];

  if (report.overall) {
    rows.push({
      group: "overall",
      key: "all",
      ...report.overall,
    });
  }

  (Object.entries(report.byTrigger) as Array<[NavigationTrigger, RoutePerfDistribution]>).forEach(([key, value]) => {
    rows.push({ group: "trigger", key, ...value });
  });

  Object.entries(report.byRoute).forEach(([key, value]) => {
    rows.push({ group: "route", key, ...value });
  });

  (Object.entries(report.byFamily) as Array<[RouteFamily, RoutePerfDistribution]>).forEach(([key, value]) => {
    rows.push({ group: "family", key, ...value });
  });

  return rows;
};

const getRoutePerfCsv = (): string => {
  const report = getRoutePerfExport();
  const rows = getRoutePerfRows(report);
  const header = ["generatedAt", "sampleWindowSize", "totalSamples", "group", "key", "count", "p50", "p95", "min", "max"];

  const csvRows = rows.map((row) => [
    report.generatedAt,
    report.sampleWindowSize,
    report.totalSamples,
    row.group,
    row.key,
    row.count,
    row.p50,
    row.p95,
    row.min,
    row.max,
  ]);

  return [header, ...csvRows]
    .map((line) => line.map((cell) => toCsvCell(cell)).join(","))
    .join("\n");
};

const getRoutePerfHistoryCsv = (): string => {
  const history = getRoutePerfHistory();
  const header = ["windowIndex", "generatedAt", "sampleWindowSize", "totalSamples", "overallP50", "overallP95", "overallMin", "overallMax"];

  const rows = history.map((entry) => [
    entry.windowIndex,
    entry.generatedAt,
    entry.sampleWindowSize,
    entry.totalSamples,
    entry.overall?.p50 ?? "",
    entry.overall?.p95 ?? "",
    entry.overall?.min ?? "",
    entry.overall?.max ?? "",
  ]);

  return [header, ...rows]
    .map((line) => line.map((cell) => toCsvCell(cell)).join(","))
    .join("\n");
};

const getRoutePerfHistoryJson = (): string =>
  JSON.stringify(
    {
      generatedAt: new Date().toISOString(),
      entryCount: routePerfHistory.length,
      entries: getRoutePerfHistory(),
    } satisfies RoutePerfHistoryReport,
    null,
    2,
  );

const getRoutePerfLatestWindowJson = (): string => {
  const latest = getLatestRoutePerfHistoryEntry();
  return latest ? JSON.stringify(latest, null, 2) : "";
};

const getRoutePerfLatestWindowCsv = (): string => {
  const latest = getLatestRoutePerfHistoryEntry();

  if (!latest) {
    return "";
  }

  const topFamily = (Object.entries(latest.byFamily) as Array<[RouteFamily, RoutePerfDistribution]>).sort(
    (a, b) => b[1].p95 - a[1].p95,
  )[0];
  const header = ["windowIndex", "generatedAt", "sampleWindowSize", "totalSamples", "overallP50", "overallP95", "overallMin", "overallMax", "topFamily", "topFamilyP95"];
  const row = [
    latest.windowIndex,
    latest.generatedAt,
    latest.sampleWindowSize,
    latest.totalSamples,
    latest.overall?.p50 ?? "",
    latest.overall?.p95 ?? "",
    latest.overall?.min ?? "",
    latest.overall?.max ?? "",
    topFamily?.[0] ?? "",
    topFamily?.[1].p95 ?? "",
  ];

  return [header, row].map((line) => line.map((cell) => toCsvCell(cell)).join(",")).join("\n");
};

const getRoutePerfBundleJson = (): string =>
  JSON.stringify(
    {
      generatedAt: new Date().toISOString(),
      snapshot: getRoutePerfExport(),
      latestWindow: getLatestRoutePerfHistoryEntry(),
      history: getRoutePerfHistory(),
    } satisfies RoutePerfBundleReport,
    null,
    2,
  );

const formatDownloadTimestamp = () => new Date().toISOString().replace(/[:.]/g, "-");

const buildDownloadFilename = (prefix: string, extension: string) => `${prefix}-${formatDownloadTimestamp()}.${extension}`;

const downloadTextFile = (filename: string, contents: string, mimeType: string) => {
  if (typeof document === "undefined") {
    return false;
  }

  if (typeof URL.createObjectURL !== "function") {
    return false;
  }

  const blob = new Blob([contents], { type: `${mimeType};charset=utf-8` });
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.rel = "noopener";
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  if (typeof URL.revokeObjectURL === "function") {
    URL.revokeObjectURL(objectUrl);
  }
  return true;
};

const installDevConsoleControls = () => {
  const devWindow = window as Window & {
    __routePerf?: {
      reset: () => void;
      snapshot: () => RoutePerfSnapshot;
      dump: () => void;
      export: () => RoutePerfExport;
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
  };

  devWindow.__routePerf = {
    reset: () => {
      resetRoutePerfSamples();
      console.info("[route-perf] sample window reset");
    },
    snapshot: () => getRoutePerfSnapshot(),
    dump: () => {
      const snapshot = getRoutePerfSnapshot();
      console.table(snapshot.triggerCounts);
      console.table(snapshot.routeCounts);
      console.table(snapshot.familyCounts);
      console.info(`[route-perf] total queued samples=${snapshot.totalSamples}`);
    },
    export: () => getRoutePerfExport(),
    history: () => getRoutePerfHistory(),
    clearHistory: () => clearRoutePerfHistory(),
    exportCsv: () => getRoutePerfCsv(),
    exportHistoryCsv: () => getRoutePerfHistoryCsv(),
    exportHistoryJson: () => getRoutePerfHistoryJson(),
    exportLatestWindowCsv: () => getRoutePerfLatestWindowCsv(),
    exportLatestWindowJson: () => getRoutePerfLatestWindowJson(),
    exportSnapshotJson: () => JSON.stringify(getRoutePerfExport(), null, 2),
    exportBundleJson: () => getRoutePerfBundleJson(),
    downloadCsv: () => downloadTextFile(buildDownloadFilename("route-perf", "csv"), getRoutePerfCsv(), "text/csv"),
    downloadHistoryCsv: () => downloadTextFile(buildDownloadFilename("route-perf-history", "csv"), getRoutePerfHistoryCsv(), "text/csv"),
    downloadHistoryJson: () => downloadTextFile(buildDownloadFilename("route-perf-history", "json"), getRoutePerfHistoryJson(), "application/json"),
    downloadLatestWindowCsv: () => downloadTextFile(buildDownloadFilename("route-perf-latest-window", "csv"), getRoutePerfLatestWindowCsv(), "text/csv"),
    downloadLatestWindowJson: () => downloadTextFile(buildDownloadFilename("route-perf-latest-window", "json"), getRoutePerfLatestWindowJson(), "application/json"),
    downloadSnapshotJson: () => downloadTextFile(buildDownloadFilename("route-perf-snapshot", "json"), JSON.stringify(getRoutePerfExport(), null, 2), "application/json"),
    downloadBundleJson: () => downloadTextFile(buildDownloadFilename("route-perf-bundle", "json"), getRoutePerfBundleJson(), "application/json"),
    copyCsv: async () => {
      const csv = getRoutePerfCsv();

      if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(csv);
        console.info("[route-perf] csv copied to clipboard");
        return true;
      }

      const textarea = document.createElement("textarea");
      textarea.value = csv;
      textarea.setAttribute("readonly", "true");
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();

      const copied = document.execCommand("copy");
      document.body.removeChild(textarea);

      if (copied) {
        console.info("[route-perf] csv copied to clipboard");
      }

      return copied;
    },
    copyHistoryCsv: async () => {
      const csv = getRoutePerfHistoryCsv();

      if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(csv);
        console.info("[route-perf] history csv copied to clipboard");
        return true;
      }

      const textarea = document.createElement("textarea");
      textarea.value = csv;
      textarea.setAttribute("readonly", "true");
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();

      const copied = document.execCommand("copy");
      document.body.removeChild(textarea);

      if (copied) {
        console.info("[route-perf] history csv copied to clipboard");
      }

      return copied;
    },
    copyHistoryJson: async () => {
      const json = getRoutePerfHistoryJson();

      if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(json);
        console.info("[route-perf] history json copied to clipboard");
        return true;
      }

      const textarea = document.createElement("textarea");
      textarea.value = json;
      textarea.setAttribute("readonly", "true");
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();

      const copied = document.execCommand("copy");
      document.body.removeChild(textarea);

      if (copied) {
        console.info("[route-perf] history json copied to clipboard");
      }

      return copied;
    },
    copyLatestWindowCsv: async () => {
      const csv = getRoutePerfLatestWindowCsv();

      if (!csv) {
        return false;
      }

      if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(csv);
        console.info("[route-perf] latest window csv copied to clipboard");
        return true;
      }

      const textarea = document.createElement("textarea");
      textarea.value = csv;
      textarea.setAttribute("readonly", "true");
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();

      const copied = document.execCommand("copy");
      document.body.removeChild(textarea);

      if (copied) {
        console.info("[route-perf] latest window csv copied to clipboard");
      }

      return copied;
    },
    copyLatestWindowJson: async () => {
      const json = getRoutePerfLatestWindowJson();

      if (!json) {
        return false;
      }

      if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(json);
        console.info("[route-perf] latest window json copied to clipboard");
        return true;
      }

      const textarea = document.createElement("textarea");
      textarea.value = json;
      textarea.setAttribute("readonly", "true");
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();

      const copied = document.execCommand("copy");
      document.body.removeChild(textarea);

      if (copied) {
        console.info("[route-perf] latest window json copied to clipboard");
      }

      return copied;
    },
    copySnapshotJson: async () => {
      const json = JSON.stringify(getRoutePerfExport(), null, 2);

      if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(json);
        console.info("[route-perf] snapshot json copied to clipboard");
        return true;
      }

      const textarea = document.createElement("textarea");
      textarea.value = json;
      textarea.setAttribute("readonly", "true");
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();

      const copied = document.execCommand("copy");
      document.body.removeChild(textarea);

      if (copied) {
        console.info("[route-perf] snapshot json copied to clipboard");
      }

      return copied;
    },
    copyBundleJson: async () => {
      const json = getRoutePerfBundleJson();

      if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(json);
        console.info("[route-perf] bundle json copied to clipboard");
        return true;
      }

      const textarea = document.createElement("textarea");
      textarea.value = json;
      textarea.setAttribute("readonly", "true");
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();

      const copied = document.execCommand("copy");
      document.body.removeChild(textarea);

      if (copied) {
        console.info("[route-perf] bundle json copied to clipboard");
      }

      return copied;
    },
  };
};

const installHistoryHooks = () => {
  const originalPushState = history.pushState.bind(history);
  const originalReplaceState = history.replaceState.bind(history);

  history.pushState = function pushState(data: unknown, unused: string, url?: string | URL | null) {
    beginNavigation(parseHistoryTarget(url), "pushstate");
    return originalPushState(data, unused, url);
  };

  history.replaceState = function replaceState(data: unknown, unused: string, url?: string | URL | null) {
    beginNavigation(parseHistoryTarget(url), "replacestate");
    return originalReplaceState(data, unused, url);
  };
};

const installAnchorClickHook = () => {
  document.addEventListener(
    "click",
    (event) => {
      if (!(event.target instanceof Element)) {
        return;
      }

      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
        return;
      }

      const anchor = event.target.closest("a[href]");
      if (!(anchor instanceof HTMLAnchorElement)) {
        return;
      }

      if (anchor.target && anchor.target !== "_self") {
        return;
      }

      const href = anchor.getAttribute("href");
      if (!href || href.startsWith("#")) {
        return;
      }

      const resolved = new URL(anchor.href, window.location.href);
      if (resolved.origin !== window.location.origin) {
        return;
      }

      beginNavigation(`${resolved.pathname}${resolved.search}${resolved.hash}`, "click");
    },
    true,
  );
};

const installPopstateHook = () => {
  window.addEventListener("popstate", () => {
    beginNavigation(getCurrentPath(), "popstate");
  });
};

export const installDevRouteTimingHooks = (options?: RouteTimingOptions) => {
  if (!isRouteTimingEnabled(options) || didInstallHooks || typeof window === "undefined") {
    return;
  }

  didInstallHooks = true;
  installHistoryHooks();
  installAnchorClickHook();
  installPopstateHook();
  installDevConsoleControls();
};

export const reportDevRouteCommit = (
  nextPath: string,
  navigationType: string,
  previousPath: string,
  options?: RouteTimingOptions,
) => {
  if (!isRouteTimingEnabled(options) || typeof window === "undefined") {
    return () => undefined;
  }

  const pending = pendingNavigation;
  pendingNavigation = null;

  const startedAt = pending?.startedAt ?? performance.now();
  const trigger = pending?.trigger ?? mapNavigationTypeToTrigger(navigationType);
  const fromPath = normalizePath(pending?.from || previousPath || "(unknown)");
  const toPath = normalizePath(nextPath);
  const intendedPath = normalizePath(pending?.to);
  const targetMismatch = intendedPath && intendedPath !== toPath;

  let rafOne = 0;
  let rafTwo = 0;
  let cancelled = false;

  rafOne = window.requestAnimationFrame(() => {
    rafTwo = window.requestAnimationFrame(() => {
      if (cancelled) {
        return;
      }

      const durationMs = performance.now() - startedAt;
      const mismatchSuffix = targetMismatch ? ` (expected ${intendedPath})` : "";

      recordDurationSample(trigger, toPath, durationMs);

      console.info(
        `[route-perf] ${trigger} ${fromPath} -> ${toPath} in ${durationMs.toFixed(1)}ms${mismatchSuffix}`,
      );

      maybeEmitSummary();
    });
  });

  return () => {
    cancelled = true;
    if (rafOne) {
      window.cancelAnimationFrame(rafOne);
    }
    if (rafTwo) {
      window.cancelAnimationFrame(rafTwo);
    }
  };
};
