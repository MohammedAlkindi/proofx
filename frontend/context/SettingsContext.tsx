import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

export type ThemePreference = "system" | "light" | "dark";
export type DensityPreference = "comfortable" | "compact";
export type AccentPreference = "indigo" | "teal" | "amber" | "rose" | "slate";
export type DefaultExperimentView = "table" | "cards";

export interface GerminalSettings {
  theme: ThemePreference;
  density: DensityPreference;
  accent: AccentPreference;
  showTechnicalDetail: boolean;
  defaultExperimentView: DefaultExperimentView;
  animationsEnabled: boolean;
}

interface SettingsContextValue {
  settings: GerminalSettings;
  resolvedTheme: "light" | "dark";
  updateSettings: (patch: Partial<GerminalSettings>) => void;
  resetSettings: () => void;
}

const STORAGE_KEY = "germinal.settings.v1";

export const defaultSettings: GerminalSettings = {
  theme: "system",
  density: "comfortable",
  accent: "indigo",
  showTechnicalDetail: true,
  defaultExperimentView: "table",
  animationsEnabled: true,
};

const accents: Record<AccentPreference, { accent: string; hover: string; bg: string }> = {
  indigo: { accent: "#4f46e5", hover: "#4338ca", bg: "rgba(79, 70, 229, 0.1)" },
  teal: { accent: "#0f766e", hover: "#115e59", bg: "rgba(15, 118, 110, 0.1)" },
  amber: { accent: "#b45309", hover: "#92400e", bg: "rgba(180, 83, 9, 0.11)" },
  rose: { accent: "#be123c", hover: "#9f1239", bg: "rgba(190, 18, 60, 0.1)" },
  slate: { accent: "#475569", hover: "#334155", bg: "rgba(71, 85, 105, 0.12)" },
};

const SettingsContext = createContext<SettingsContextValue | undefined>(undefined);

function sameSettings(a: GerminalSettings, b: GerminalSettings): boolean {
  return (
    a.theme === b.theme &&
    a.density === b.density &&
    a.accent === b.accent &&
    a.showTechnicalDetail === b.showTechnicalDetail &&
    a.defaultExperimentView === b.defaultExperimentView &&
    a.animationsEnabled === b.animationsEnabled
  );
}

function parseStoredSettings(raw: string | null): GerminalSettings {
  if (!raw) return defaultSettings;

  try {
    const parsed = JSON.parse(raw) as Partial<GerminalSettings>;
    return {
      ...defaultSettings,
      ...parsed,
      theme: ["system", "light", "dark"].includes(String(parsed.theme))
        ? (parsed.theme as ThemePreference)
        : defaultSettings.theme,
      density: ["comfortable", "compact"].includes(String(parsed.density))
        ? (parsed.density as DensityPreference)
        : defaultSettings.density,
      accent: ["indigo", "teal", "amber", "rose", "slate"].includes(String(parsed.accent))
        ? (parsed.accent as AccentPreference)
        : defaultSettings.accent,
      defaultExperimentView: ["table", "cards"].includes(String(parsed.defaultExperimentView))
        ? (parsed.defaultExperimentView as DefaultExperimentView)
        : defaultSettings.defaultExperimentView,
      showTechnicalDetail:
        typeof parsed.showTechnicalDetail === "boolean"
          ? parsed.showTechnicalDetail
          : defaultSettings.showTechnicalDetail,
      animationsEnabled:
        typeof parsed.animationsEnabled === "boolean"
          ? parsed.animationsEnabled
          : defaultSettings.animationsEnabled,
    };
  } catch {
    return defaultSettings;
  }
}

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<GerminalSettings>(defaultSettings);
  const [systemTheme, setSystemTheme] = useState<"light" | "dark">("light");
  const [hydrated, setHydrated] = useState(false);
  const lastStoredSettings = useRef<string | null>(null);

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const syncSystemTheme = () => setSystemTheme(media.matches ? "dark" : "light");
    const storedSettings = localStorage.getItem(STORAGE_KEY);
    const parsedSettings = parseStoredSettings(storedSettings);

    lastStoredSettings.current = storedSettings ?? JSON.stringify(defaultSettings);
    setSettings((current) => (sameSettings(current, parsedSettings) ? current : parsedSettings));
    syncSystemTheme();
    setHydrated(true);

    media.addEventListener("change", syncSystemTheme);
    return () => media.removeEventListener("change", syncSystemTheme);
  }, []);

  const resolvedTheme = settings.theme === "system" ? systemTheme : settings.theme;

  useEffect(() => {
    const root = document.documentElement;
    const accent = accents[settings.accent];

    root.classList.toggle("dark", resolvedTheme === "dark");
    root.dataset.theme = settings.theme;
    root.dataset.density = settings.density;
    root.dataset.accent = settings.accent;
    root.dataset.detail = settings.showTechnicalDetail ? "technical" : "essential";
    root.dataset.motion = settings.animationsEnabled ? "on" : "off";
    root.style.setProperty("--accent", accent.accent);
    root.style.setProperty("--accent-h", accent.hover);
    root.style.setProperty("--accent-bg", accent.bg);
  }, [
    resolvedTheme,
    settings.accent,
    settings.animationsEnabled,
    settings.density,
    settings.showTechnicalDetail,
    settings.theme,
  ]);

  useEffect(() => {
    if (!hydrated) return;
    const serialized = JSON.stringify(settings);
    if (serialized === lastStoredSettings.current) return;

    localStorage.setItem(STORAGE_KEY, serialized);
    lastStoredSettings.current = serialized;
  }, [hydrated, settings]);

  const updateSettings = useCallback((patch: Partial<GerminalSettings>) => {
    setSettings((current) => {
      const next = { ...current, ...patch };
      return sameSettings(current, next) ? current : next;
    });
  }, []);

  const resetSettings = useCallback(() => {
    setSettings((current) => (sameSettings(current, defaultSettings) ? current : defaultSettings));
  }, []);

  const value = useMemo(
    () => ({ settings, resolvedTheme, updateSettings, resetSettings }),
    [settings, resolvedTheme, updateSettings, resetSettings]
  );

  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}

export function useSettings() {
  const context = useContext(SettingsContext);
  if (!context) {
    throw new Error("useSettings must be used inside SettingsProvider");
  }
  return context;
}
