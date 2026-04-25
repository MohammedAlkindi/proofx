import type { AppProps } from "next/app";
import { useEffect, useState, useCallback } from "react";
import Layout from "../components/Layout";
import CommandPalette from "../components/CommandPalette";
import "../styles/globals.css";

export default function App({ Component, pageProps }: AppProps) {
  const [dark, setDark] = useState(true);
  const [sidebarRefreshKey, setSidebarRefreshKey] = useState(0);
  const [paletteOpen, setPaletteOpen] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("theme");
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const isDark = stored === "light" ? false : stored === "dark" ? true : prefersDark ?? true;
    setDark(isDark);
    document.documentElement.classList.toggle("dark", isDark);
  }, []);

  // Global ⌘K / Ctrl+K listener
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setPaletteOpen((o) => !o);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const toggleDark = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
  };

  const bumpSidebar = useCallback(() => {
    setSidebarRefreshKey((k) => k + 1);
  }, []);

  return (
    <>
      <Layout
        dark={dark}
        toggleDark={toggleDark}
        sidebarRefreshKey={sidebarRefreshKey}
        onSidebarBump={bumpSidebar}
        onOpenPalette={() => setPaletteOpen(true)}
      >
        <Component {...pageProps} onSidebarBump={bumpSidebar} />
      </Layout>
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </>
  );
}
