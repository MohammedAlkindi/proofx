import { CSSProperties, ReactNode, createContext, useContext } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import Sidebar from "./Sidebar";
import { ThemePreference, useSettings } from "../context/SettingsContext";

export const SidebarBumpContext = createContext<() => void>(() => {});
export const useSidebarBump = () => useContext(SidebarBumpContext);

interface LayoutProps {
  children: ReactNode;
  sidebarRefreshKey: number;
  onSidebarBump: () => void;
  onOpenPalette: () => void;
}

const header: CSSProperties = {
  alignItems: "center",
  background: "color-mix(in srgb, var(--bg-page) 92%, transparent)",
  backdropFilter: "blur(12px)",
  borderBottom: "1px solid var(--border-s)",
  display: "flex",
  height: 56,
  justifyContent: "space-between",
  left: 0,
  padding: "0 22px",
  position: "fixed",
  right: 0,
  top: 0,
  zIndex: 100,
};

const navLinkBase: CSSProperties = {
  alignItems: "center",
  borderRadius: 6,
  display: "inline-flex",
  fontSize: 12,
  fontWeight: 600,
  gap: 7,
  height: 32,
  padding: "0 10px",
  textDecoration: "none",
};

const iconButton: CSSProperties = {
  alignItems: "center",
  background: "var(--bg-input)",
  border: "1px solid var(--border-s)",
  borderRadius: 6,
  color: "var(--t-secondary)",
  cursor: "pointer",
  display: "inline-flex",
  height: 32,
  justifyContent: "center",
  width: 32,
};

function themeLabel(theme: ThemePreference, resolvedTheme: "light" | "dark") {
  if (theme === "system") return resolvedTheme === "dark" ? "System dark" : "System light";
  return theme === "dark" ? "Dark" : "Light";
}

export default function Layout({
  children,
  sidebarRefreshKey,
  onSidebarBump,
  onOpenPalette,
}: LayoutProps) {
  const router = useRouter();
  const { settings, resolvedTheme, updateSettings } = useSettings();

  const cycleTheme = () => {
    const next: ThemePreference =
      settings.theme === "system" ? "light" : settings.theme === "light" ? "dark" : "system";
    updateSettings({ theme: next });
  };

  const settingsActive = router.pathname === "/settings";

  return (
    <SidebarBumpContext.Provider value={onSidebarBump}>
      <div style={{ minHeight: "100vh" }}>
        <header style={header}>
          <div style={{ alignItems: "center", display: "flex", gap: 18, minWidth: 0 }}>
            <Link
              href="/"
              style={{
                alignItems: "baseline",
                display: "inline-flex",
                gap: 9,
                textDecoration: "none",
                whiteSpace: "nowrap",
              }}
            >
              <span style={{ color: "var(--t-primary)", fontSize: 16, fontWeight: 700 }}>
                Germinal
              </span>
              <span className="mono" style={{ color: "var(--t-tertiary)", fontSize: 11 }}>
                conjecture engine
              </span>
            </Link>
          </div>

          <div style={{ alignItems: "center", display: "flex", gap: 8 }}>
            <button
              aria-label="Open command palette"
              className="secondary-button"
              onClick={onOpenPalette}
              style={{ ...navLinkBase, color: "var(--t-secondary)" }}
            >
              <span aria-hidden="true">Search</span>
              <kbd
                className="mono"
                style={{
                  border: "1px solid var(--border-s)",
                  borderRadius: 4,
                  color: "var(--t-tertiary)",
                  fontSize: 10,
                  padding: "1px 5px",
                }}
              >
                Ctrl K
              </kbd>
            </button>

            <Link
              href="/settings"
              style={{
                ...navLinkBase,
                background: settingsActive ? "var(--accent-bg)" : "transparent",
                color: settingsActive ? "var(--accent)" : "var(--t-secondary)",
              }}
            >
              Settings
            </Link>

            <button
              aria-label={`Theme: ${themeLabel(settings.theme, resolvedTheme)}`}
              onClick={cycleTheme}
              style={iconButton}
              title={`Theme: ${themeLabel(settings.theme, resolvedTheme)}`}
            >
              {resolvedTheme === "dark" ? "D" : "L"}
            </button>
          </div>
        </header>

        <div style={{ display: "flex", paddingTop: 56 }}>
          <Sidebar refreshKey={sidebarRefreshKey} />
          <main
            className="app-main"
            style={{
              flex: 1,
              marginLeft: 260,
              minHeight: "calc(100vh - 56px)",
              padding: "var(--page-pad)",
            }}
          >
            <div style={{ margin: "0 auto", maxWidth: "var(--content-max)" }}>{children}</div>
          </main>
        </div>
      </div>
    </SidebarBumpContext.Provider>
  );
}
