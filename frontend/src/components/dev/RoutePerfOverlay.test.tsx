import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";
import DevRoutePerfOverlay from "@/components/dev/RoutePerfOverlay";

describe("RoutePerfOverlay", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.useFakeTimers();
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });

    Object.defineProperty(window, "__routePerf", {
      configurable: true,
      value: {
        snapshot: () => ({
          totalSamples: 12,
          triggerCounts: { pushstate: 8 },
          routeCounts: { "/dashboard": 5 },
          familyCounts: { app: 5 },
        }),
        history: () => [
          {
            windowIndex: 1,
            generatedAt: new Date().toISOString(),
            sampleWindowSize: 10,
            totalSamples: 10,
            overall: { count: 10, p50: 11, p95: 22, min: 5, max: 30 },
            byTrigger: {},
            byRoute: {},
            byFamily: { app: { count: 10, p50: 9, p95: 18, min: 5, max: 30 } },
          },
        ],
        exportCsv: vi.fn(),
        exportHistoryCsv: vi.fn(),
        exportHistoryJson: vi.fn(),
        exportLatestWindowCsv: vi.fn(),
        exportLatestWindowJson: vi.fn(),
        exportSnapshotJson: vi.fn(),
        exportBundleJson: vi.fn(),
        downloadCsv: vi.fn().mockReturnValue(true),
        downloadHistoryCsv: vi.fn().mockReturnValue(true),
        downloadHistoryJson: vi.fn().mockReturnValue(true),
        downloadLatestWindowCsv: vi.fn().mockReturnValue(true),
        downloadLatestWindowJson: vi.fn().mockReturnValue(true),
        downloadSnapshotJson: vi.fn().mockReturnValue(true),
        downloadBundleJson: vi.fn().mockReturnValue(true),
        clearHistory: vi.fn(),
        copyLatestWindowJson: vi.fn().mockResolvedValue(true),
        copyLatestWindowCsv: vi.fn().mockResolvedValue(true),
        copySnapshotJson: vi.fn().mockResolvedValue(true),
        copyBundleJson: vi.fn().mockResolvedValue(true),
        copyCsv: vi.fn().mockResolvedValue(true),
        copyHistoryCsv: vi.fn().mockResolvedValue(true),
        copyHistoryJson: vi.fn().mockResolvedValue(true),
      },
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders the live overlay and supports hiding", async () => {
    render(<DevRoutePerfOverlay />);

    expect(screen.getByText("Route Perf")).toBeInTheDocument();
    expect(screen.getByText("live samples")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText(/1\/20/)).toBeInTheDocument();
    expect(screen.getByText("latest family p95")).toBeInTheDocument();
    expect(screen.getByText(/history 1 windows/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Copy History JSON" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Copy Latest Window JSON" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Copy Latest Window CSV" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Copy Snapshot JSON" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Copy Bundle JSON" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download Snapshot JSON" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download Bundle JSON" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download CSV" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download History CSV" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download History JSON" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download Latest Window CSV" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download Latest Window JSON" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Hide" }));
    expect(screen.getByRole("button", { name: "Route Perf" })).toBeInTheDocument();

    fireEvent.keyDown(window, { key: "r", ctrlKey: true, altKey: true });
    expect(screen.getByRole("button", { name: "Hide" })).toBeInTheDocument();

    await act(async () => {
      fireEvent.keyDown(window, { key: "j", ctrlKey: true, altKey: true });
      await Promise.resolve();
    });
    expect((window as Window & { __routePerf: { copyHistoryJson: ReturnType<typeof vi.fn> } }).__routePerf.copyHistoryJson).toHaveBeenCalled();

    expect(screen.getByText(/copied history json/i)).toBeInTheDocument();
    act(() => {
      vi.advanceTimersByTime(2600);
    });
    expect(screen.queryByText(/copied history json/i)).not.toBeInTheDocument();
    expect(screen.getByText(/history 1 windows/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Reset Copy State" }));
    expect(screen.getByText(/history 1 windows/i)).toBeInTheDocument();

    await act(async () => {
      fireEvent.keyDown(window, { key: "l", ctrlKey: true, altKey: true });
      await Promise.resolve();
    });
    expect((window as Window & { __routePerf: { copyLatestWindowJson: ReturnType<typeof vi.fn> } }).__routePerf.copyLatestWindowJson).toHaveBeenCalled();
    expect(screen.getByText(/copied latest window json/i)).toBeInTheDocument();
    act(() => {
      vi.advanceTimersByTime(2600);
    });
    expect(screen.queryByText(/copied latest window json/i)).not.toBeInTheDocument();

    await act(async () => {
      fireEvent.keyDown(window, { key: "a", ctrlKey: true, altKey: true });
      await Promise.resolve();
    });
    expect((window as Window & { __routePerf: { copyBundleJson: ReturnType<typeof vi.fn> } }).__routePerf.copyBundleJson).toHaveBeenCalled();
    expect(screen.getByText(/copied bundle json/i)).toBeInTheDocument();
    act(() => {
      vi.advanceTimersByTime(2600);
    });
    expect(screen.queryByText(/copied bundle json/i)).not.toBeInTheDocument();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Copy Latest Window CSV" }));
      await Promise.resolve();
    });
    expect(screen.getByText(/copied latest window csv/i)).toBeInTheDocument();
    act(() => {
      vi.advanceTimersByTime(2600);
    });
    expect(screen.queryByText(/copied latest window csv/i)).not.toBeInTheDocument();

    await act(async () => {
      fireEvent.keyDown(window, { key: "k", ctrlKey: true, altKey: true });
      await Promise.resolve();
    });
    expect((window as Window & { __routePerf: { copyLatestWindowCsv: ReturnType<typeof vi.fn> } }).__routePerf.copyLatestWindowCsv).toHaveBeenCalled();
    expect(screen.getByText(/copied latest window csv/i)).toBeInTheDocument();
    act(() => {
      vi.advanceTimersByTime(2600);
    });
    expect(screen.queryByText(/copied latest window csv/i)).not.toBeInTheDocument();

    await act(async () => {
      fireEvent.keyDown(window, { key: "s", ctrlKey: true, altKey: true });
      await Promise.resolve();
    });
    expect((window as Window & { __routePerf: { copySnapshotJson: ReturnType<typeof vi.fn> } }).__routePerf.copySnapshotJson).toHaveBeenCalled();
    expect(screen.getByText(/copied snapshot json/i)).toBeInTheDocument();
    act(() => {
      vi.advanceTimersByTime(2600);
    });
    expect(screen.queryByText(/copied snapshot json/i)).not.toBeInTheDocument();

    fireEvent.keyDown(window, { key: "o", ctrlKey: true, altKey: true });
    expect((window as Window & { __routePerf: { downloadSnapshotJson: ReturnType<typeof vi.fn> } }).__routePerf.downloadSnapshotJson).toHaveBeenCalled();
    expect(screen.getByText(/downloaded snapshot json/i)).toBeInTheDocument();

    fireEvent.keyDown(window, { key: "w", ctrlKey: true, altKey: true });
    expect((window as Window & { __routePerf: { downloadBundleJson: ReturnType<typeof vi.fn> } }).__routePerf.downloadBundleJson).toHaveBeenCalled();
    expect(screen.getByText(/downloaded bundle json/i)).toBeInTheDocument();

    fireEvent.keyDown(window, { key: "d", ctrlKey: true, altKey: true });
    expect((window as Window & { __routePerf: { downloadCsv: ReturnType<typeof vi.fn> } }).__routePerf.downloadCsv).toHaveBeenCalled();
    expect(screen.getByText(/downloaded csv/i)).toBeInTheDocument();

    fireEvent.keyDown(window, { key: "h", ctrlKey: true, altKey: true });
    expect((window as Window & { __routePerf: { downloadHistoryCsv: ReturnType<typeof vi.fn> } }).__routePerf.downloadHistoryCsv).toHaveBeenCalled();
    expect(screen.getByText(/downloaded history csv/i)).toBeInTheDocument();

    fireEvent.keyDown(window, { key: "i", ctrlKey: true, altKey: true });
    expect((window as Window & { __routePerf: { downloadHistoryJson: ReturnType<typeof vi.fn> } }).__routePerf.downloadHistoryJson).toHaveBeenCalled();
    expect(screen.getByText(/downloaded history json/i)).toBeInTheDocument();

    fireEvent.keyDown(window, { key: "y", ctrlKey: true, altKey: true });
    expect((window as Window & { __routePerf: { downloadLatestWindowCsv: ReturnType<typeof vi.fn> } }).__routePerf.downloadLatestWindowCsv).toHaveBeenCalled();
    expect(screen.getByText(/downloaded latest window csv/i)).toBeInTheDocument();

    fireEvent.keyDown(window, { key: "u", ctrlKey: true, altKey: true });
    expect((window as Window & { __routePerf: { downloadLatestWindowJson: ReturnType<typeof vi.fn> } }).__routePerf.downloadLatestWindowJson).toHaveBeenCalled();
    expect(screen.getByText(/downloaded latest window json/i)).toBeInTheDocument();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Copy Latest Window JSON" }));
      await Promise.resolve();
    });
    expect(screen.getByText(/copied latest window json/i)).toBeInTheDocument();
    act(() => {
      vi.advanceTimersByTime(2600);
    });
    expect(screen.queryByText(/copied latest window json/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Clear History" }));
    expect((window as Window & { __routePerf: { clearHistory: ReturnType<typeof vi.fn> } }).__routePerf.clearHistory).toHaveBeenCalled();
  });
});
