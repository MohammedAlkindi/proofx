import type { AppProps } from "next/app";
import { useCallback, useEffect, useState } from "react";
import Layout from "../components/Layout";
import CommandPalette from "../components/CommandPalette";
import { SettingsProvider } from "../context/SettingsContext";
import "../styles/globals.css";

export default function App({ Component, pageProps }: AppProps) {
  const [sidebarRefreshKey, setSidebarRefreshKey] = useState(0);
  const [paletteOpen, setPaletteOpen] = useState(false);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setPaletteOpen((open) => !open);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const bumpSidebar = useCallback(() => {
    setSidebarRefreshKey((key) => key + 1);
  }, []);

  return (
    <SettingsProvider>
      <Layout
        sidebarRefreshKey={sidebarRefreshKey}
        onSidebarBump={bumpSidebar}
        onOpenPalette={() => setPaletteOpen(true)}
      >
        <Component {...pageProps} onSidebarBump={bumpSidebar} />
      </Layout>
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </SettingsProvider>
  );
}
