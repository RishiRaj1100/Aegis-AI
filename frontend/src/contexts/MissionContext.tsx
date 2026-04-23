import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { UserManager } from "@/services/api";
import { useAuth } from "@/contexts/AuthContext";

export interface MissionState {
  goal: string;
  taskId: string;
  language: string;
  status: string;
  confidence: number;
  riskLevel: string;
  subtasks: number;
  updatedAt: string;
  source: "dashboard" | "voice" | "manual";
}

interface MissionContextValue {
  mission: MissionState | null;
  hasMission: boolean;
  setMission: (mission: MissionState) => void;
  clearMission: () => void;
}

const LEGACY_STORAGE_KEY = "aegis_current_mission";
const STORAGE_KEY_PREFIX = "aegis_current_mission:";

const getMissionStorageKey = (): string => {
  const user = UserManager.getUser();
  const userId = user?.id?.trim();
  return userId ? `${STORAGE_KEY_PREFIX}${userId}` : LEGACY_STORAGE_KEY;
};

const MissionContext = createContext<MissionContextValue | undefined>(undefined);

const readMission = (storageKey: string): MissionState | null => {
  try {
    const raw = localStorage.getItem(storageKey);
    if (!raw) {
      return null;
    }

    return JSON.parse(raw) as MissionState;
  } catch {
    return null;
  }
};

export const MissionProvider = ({ children }: { children: React.ReactNode }) => {
  const { user } = useAuth();
  const [storageKey, setStorageKey] = useState<string>(() => getMissionStorageKey());
  const [mission, setMissionState] = useState<MissionState | null>(() => readMission(getMissionStorageKey()));

  useEffect(() => {
    // Remove old shared key once per mount to prevent cross-user leakage from older builds.
    localStorage.removeItem(LEGACY_STORAGE_KEY);
  }, []);

  useEffect(() => {
    setStorageKey(getMissionStorageKey());
  }, [user?.id]);

  useEffect(() => {
    const onStorage = () => {
      setStorageKey(getMissionStorageKey());
    };

    window.addEventListener("storage", onStorage);
    window.addEventListener("focus", onStorage);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("focus", onStorage);
    };
  }, []);

  useEffect(() => {
    setMissionState(readMission(storageKey));
  }, [storageKey]);

  useEffect(() => {
    const handleStorage = (event: StorageEvent) => {
      if (event.key !== storageKey) {
        return;
      }

      setMissionState(readMission(storageKey));
    };

    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, [storageKey]);

  useEffect(() => {
    if (!mission) {
      localStorage.removeItem(storageKey);
      return;
    }

    localStorage.setItem(storageKey, JSON.stringify(mission));
  }, [mission, storageKey]);

  const value = useMemo<MissionContextValue>(
    () => ({
      mission,
      hasMission: !!mission,
      setMission: (nextMission) => setMissionState(nextMission),
      clearMission: () => setMissionState(null),
    }),
    [mission]
  );

  return <MissionContext.Provider value={value}>{children}</MissionContext.Provider>;
};

export const useMission = () => {
  const context = useContext(MissionContext);
  if (!context) {
    throw new Error("useMission must be used within a MissionProvider");
  }
  return context;
};
