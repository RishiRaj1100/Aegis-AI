import { beforeEach, describe, expect, it, vi } from "vitest";
import { installDevRouteTimingHooks, reportDevRouteCommit } from "@/utils/routeTiming";

describe("routeTiming", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-04-17T23:59:59.000Z"));

    vi.spyOn(window, "requestAnimationFrame").mockImplementation((callback: FrameRequestCallback) => {
      callback(0);
      return 1;
    });

    vi.spyOn(window, "cancelAnimationFrame").mockImplementation(() => undefined);
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn().mockReturnValue("blob:route-perf-test"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });

    installDevRouteTimingHooks({ enabled: true });
    (window as Window & { __routePerf?: { reset: () => void } }).__routePerf?.reset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("installs dev console controls", () => {
    const controls = (window as Window & {
      __routePerf?: {
        reset: () => void;
        snapshot: () => { totalSamples: number; routeCounts: Record<string, number>; familyCounts: Record<string, number> };
        dump: () => void;
        export: () => {
          totalSamples: number;
          byFamily: Record<string, { count: number }>;
          byRoute: Record<string, { count: number }>;
        };
        history: () => Array<{ windowIndex: number; totalSamples: number; generatedAt: string }>;
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
    }).__routePerf;

    expect(controls).toBeDefined();
    expect(typeof controls?.reset).toBe("function");
    expect(typeof controls?.snapshot).toBe("function");
    expect(typeof controls?.dump).toBe("function");
    expect(typeof controls?.export).toBe("function");
    expect(typeof controls?.history).toBe("function");
    expect(typeof controls?.clearHistory).toBe("function");
    expect(typeof controls?.exportCsv).toBe("function");
    expect(typeof controls?.exportHistoryCsv).toBe("function");
    expect(typeof controls?.exportHistoryJson).toBe("function");
    expect(typeof controls?.exportLatestWindowCsv).toBe("function");
    expect(typeof controls?.exportLatestWindowJson).toBe("function");
    expect(typeof controls?.exportSnapshotJson).toBe("function");
    expect(typeof controls?.exportBundleJson).toBe("function");
    expect(typeof controls?.downloadCsv).toBe("function");
    expect(typeof controls?.downloadHistoryCsv).toBe("function");
    expect(typeof controls?.downloadHistoryJson).toBe("function");
    expect(typeof controls?.downloadLatestWindowCsv).toBe("function");
    expect(typeof controls?.downloadLatestWindowJson).toBe("function");
    expect(typeof controls?.downloadSnapshotJson).toBe("function");
    expect(typeof controls?.downloadBundleJson).toBe("function");
    expect(typeof controls?.copyCsv).toBe("function");
    expect(typeof controls?.copyHistoryCsv).toBe("function");
    expect(typeof controls?.copyHistoryJson).toBe("function");
    expect(typeof controls?.copyLatestWindowCsv).toBe("function");
    expect(typeof controls?.copyLatestWindowJson).toBe("function");
    expect(typeof controls?.copySnapshotJson).toBe("function");
    expect(typeof controls?.copyBundleJson).toBe("function");
    expect(controls?.snapshot().totalSamples).toBe(0);
    expect(controls?.snapshot().routeCounts).toEqual({});
    expect(controls?.snapshot().familyCounts).toEqual({});
  });

  it("emits per-route and summary logs with canonical trigger labels", async () => {
    const infoSpy = vi.spyOn(console, "info").mockImplementation(() => undefined);

    for (let i = 0; i < 10; i += 1) {
      reportDevRouteCommit(`/to-${i}`, "PUSH", `/from-${i}`, { enabled: true });
    }

    const controls = (window as Window & {
      __routePerf?: {
        snapshot: () => { totalSamples: number; routeCounts: Record<string, number>; familyCounts: Record<string, number> };
        export: () => {
          totalSamples: number;
          byFamily: Record<string, { count: number }>;
          byRoute: Record<string, { count: number }>;
        };
        history: () => Array<{ windowIndex: number; totalSamples: number; generatedAt: string }>;
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
    }).__routePerf;

    const logLines = infoSpy.mock.calls.map((entry) => String(entry[0]));

    expect(logLines.some((line) => line.includes("[route-perf] pushstate"))).toBe(true);
    expect(logLines.some((line) => line.includes("[route-perf-summary]"))).toBe(true);
    expect(logLines.some((line) => line.includes("pushstate:p95="))).toBe(true);
    expect(logLines.some((line) => line.includes("routes=/to-"))).toBe(true);
    expect(logLines.some((line) => line.includes("families=other:p95="))).toBe(true);
    expect(controls?.snapshot().totalSamples).toBe(0);
    expect(controls?.history().length).toBe(1);
    expect(controls?.history()[0].windowIndex).toBe(1);
    expect(controls?.history()[0].totalSamples).toBe(10);

    reportDevRouteCommit("/dashboard", "PUSH", "/", { enabled: true });
    expect(controls?.snapshot().routeCounts["/dashboard"]).toBe(1);
    expect(controls?.snapshot().familyCounts.app).toBe(1);

    const exported = controls?.export();
    expect(exported?.totalSamples).toBe(1);
    expect(exported?.byRoute["/dashboard"].count).toBe(1);
    expect(exported?.byFamily.app.count).toBe(1);

    const csv = controls?.exportCsv() ?? "";
    expect(csv).toContain("generatedAt,sampleWindowSize,totalSamples,group,key,count,p50,p95,min,max");
    expect(csv).toContain(",route,/dashboard,");
    expect(csv).toContain(",family,app,");

    const historyCsv = controls?.exportHistoryCsv() ?? "";
    expect(historyCsv).toContain("windowIndex,generatedAt,sampleWindowSize,totalSamples,overallP50,overallP95,overallMin,overallMax");
    expect(historyCsv).toContain("1,");

    const historyJson = controls?.exportHistoryJson() ?? "";
    expect(historyJson).toContain('"entryCount": 1');
    expect(historyJson).toContain('"windowIndex": 1');

    const latestWindowCsv = controls?.exportLatestWindowCsv() ?? "";
    expect(latestWindowCsv).toContain("windowIndex,generatedAt,sampleWindowSize,totalSamples,overallP50,overallP95,overallMin,overallMax,topFamily,topFamilyP95");
    expect(latestWindowCsv).toContain("\n1,");

    const latestWindowJson = controls?.exportLatestWindowJson() ?? "";
    expect(latestWindowJson).toContain('"windowIndex": 1');
    expect(latestWindowJson).toContain('"byFamily"');

    const snapshotJson = controls?.exportSnapshotJson() ?? "";
    expect(snapshotJson).toContain('"sampleWindowSize"');
    expect(snapshotJson).toContain('"byRoute"');

    const bundleJson = controls?.exportBundleJson() ?? "";
    expect(bundleJson).toContain('"generatedAt"');
    expect(bundleJson).toContain('"latestWindow"');
    expect(bundleJson).toContain('"history"');

    const originalCreateElement = document.createElement.bind(document);
    const clickSpy = vi.fn();
    let capturedDownloadName = "";
    vi.spyOn(document, "createElement").mockImplementation((tagName: string) => {
      if (tagName === "a") {
        const anchor = originalCreateElement(tagName) as HTMLAnchorElement;
        Object.defineProperty(anchor, "click", { configurable: true, value: clickSpy });
        Object.defineProperty(anchor, "download", {
          configurable: true,
          get: () => capturedDownloadName,
          set: (value: string) => {
            capturedDownloadName = value;
          },
        });
        return anchor;
      }

      return originalCreateElement(tagName);
    });

    expect(controls?.downloadCsv()).toBe(true);
    expect(controls?.downloadHistoryCsv()).toBe(true);
    expect(controls?.downloadHistoryJson()).toBe(true);
    expect(controls?.downloadLatestWindowCsv()).toBe(true);
    expect(controls?.downloadLatestWindowJson()).toBe(true);
    expect(controls?.downloadSnapshotJson()).toBe(true);
    expect(controls?.downloadBundleJson()).toBe(true);
    expect(clickSpy).toHaveBeenCalled();
    expect(capturedDownloadName).toMatch(/^route-perf-bundle-2026-04-17T23-59-59-000Z\.json$/);

    await expect(controls?.copyCsv()).resolves.toBe(true);
    await expect(controls?.copyHistoryCsv()).resolves.toBe(true);
    await expect(controls?.copyHistoryJson()).resolves.toBe(true);
    await expect(controls?.copyLatestWindowCsv()).resolves.toBe(true);
    await expect(controls?.copyLatestWindowJson()).resolves.toBe(true);
    await expect(controls?.copySnapshotJson()).resolves.toBe(true);
    await expect(controls?.copyBundleJson()).resolves.toBe(true);

    controls?.clearHistory();
    expect(controls?.history()).toEqual([]);
  });

  it("returns false when blob downloads are unavailable", () => {
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: undefined,
    });

    const controls = (window as Window & {
      __routePerf?: {
        downloadCsv: () => boolean;
      };
    }).__routePerf;

    expect(controls?.downloadCsv()).toBe(false);
  });
});
