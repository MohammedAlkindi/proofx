import { ReactNode, CSSProperties, createContext, useContext } from "react";
import Link from "next/link";
import Sidebar from "./Sidebar";

/* ─── Context for bumping the sidebar refresh ─── */
export const SidebarBumpContext = createContext<() => void>(() => {});
export const useSidebarBump = () => useContext(SidebarBumpContext);

interface LayoutProps {
  children: ReactNode;
  dark: boolean;
  toggleDark: () => void;
  sidebarRefreshKey: number;
  onSidebarBump: () => void;
  onOpenPalette: () => void;
}

const S: Record<string, CSSProperties> = {
  shell: {
    minHeight: "100vh",
  },
  header: {
    height: 48,
    borderBottom: "1px solid var(--border-s)",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "0 20px 0 16px",
    position: "fixed",
    top: 0,
    left: 0,
    right: 0,
    zIndex: 100,
    background: "var(--bg-page)",
  },
  headerLeft: {
    display: "flex",
    alignItems: "center",
    gap: 10,
  },
  wordmark: {
    fontWeight: 600,
    fontSize: 15,
    color: "var(--t-primary)",
    textDecoration: "none",
    letterSpacing: "-0.02em",
  },
  subtitle: {
    fontFamily: "JetBrains Mono, Fira Code, monospace",
    fontSize: 11,
    color: "var(--t-tertiary)",
  },
  headerRight: {
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  body: {
    display: "flex",
    paddingTop: 48,
  },
  main: {
    flex: 1,
    marginLeft: 240,
    padding: "40px 48px",
    minHeight: "calc(100vh - 48px)",
  },
  inner: {
    maxWidth: 860,
    margin: "0 auto",
  },
};

const kbBtnBase: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 6,
  padding: "4px 10px",
  borderRadius: 6,
  border: "1px solid var(--border-s)",
  background: "var(--bg-input)",
  cursor: "pointer",
  fontSize: 11,
  color: "var(--t-tertiary)",
  fontFamily: "JetBrains Mono, Fira Code, monospace",
  transition: "border-color 150ms, color 150ms",
};

const iconBtnBase: CSSProperties = {
  width: 30,
  height: 30,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  borderRadius: 6,
  border: "1px solid var(--border-s)",
  background: "var(--bg-input)",
  cursor: "pointer",
  fontSize: 13,
  color: "var(--t-secondary)",
  transition: "border-color 150ms",
};

export default function Layout({
  children,
  dark,
  toggleDark,
  sidebarRefreshKey,
  onSidebarBump,
  onOpenPalette,
}: LayoutProps) {
  return (
    <SidebarBumpContext.Provider value={onSidebarBump}>
      <div style={S.shell}>
        {/* ── Header ── */}
        <header style={S.header}>
          <div style={S.headerLeft}>
            <Link href="/" style={S.wordmark}>
              Germinal
            </Link>
            <span style={S.subtitle}>conjecture engine</span>
          </div>

          <div style={S.headerRight}>
            {/* ⌘K search trigger */}
            <button
              onClick={onOpenPalette}
              aria-label="Open command palette"
              style={kbBtnBase}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "var(--accent)";
                e.currentTarget.style.color = "var(--accent)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "var(--border-s)";
                e.currentTarget.style.color = "var(--t-tertiary)";
              }}
            >
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <circle cx="5.5" cy="5.5" r="4" stroke="currentColor" strokeWidth="1.4" />
                <path d="M9 9l2.5 2.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
              </svg>
              <span>⌘K</span>
            </button>

            {/* Theme toggle */}
            <button
              onClick={toggleDark}
              aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
              style={iconBtnBase}
              onMouseEnter={(e) =>
                (e.currentTarget.style.borderColor = "var(--border-a)")
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.borderColor = "var(--border-s)")
              }
            >
              {dark ? "☀" : "☽"}
            </button>
          </div>
        </header>

        {/* ── Sidebar + Main ── */}
        <div style={S.body}>
          <Sidebar refreshKey={sidebarRefreshKey} />
          <main style={S.main}>
            <div style={S.inner}>{children}</div>
          </main>
        </div>
      </div>
    </SidebarBumpContext.Provider>
  );
}
