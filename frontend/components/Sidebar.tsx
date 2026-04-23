import { CSSProperties } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import useSWR from "swr";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const fetcher = (url: string) => fetch(url).then((r) => r.json());

interface ExperimentItem {
  id: string;
  domain: string;
  timestamp: string;
  is_valid: boolean;
  proved: boolean;
}

function statusColor(item: ExperimentItem): string {
  if (item.proved) return "var(--success)";
  if (item.is_valid) return "var(--warning)";
  return "var(--danger)";
}

function relativeTime(iso: string): string {
  try {
    const diff = (Date.now() - new Date(iso).getTime()) / 1000;
    if (diff < 60) return "just now";
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
  } catch {
    return "";
  }
}

const sidebar: CSSProperties = {
  width: 240,
  position: "fixed",
  top: 48,
  bottom: 0,
  left: 0,
  borderRight: "1px solid var(--border-s)",
  background: "var(--bg-page)",
  display: "flex",
  flexDirection: "column",
  overflowY: "auto",
  zIndex: 90,
};

export default function Sidebar({ refreshKey = 0 }: { refreshKey?: number }) {
  const router = useRouter();
  const activeId = router.query.id as string | undefined;

  const { data: experiments } = useSWR<ExperimentItem[]>(
    `${API}/api/v1/experiments?_r=${refreshKey}`,
    fetcher,
    { refreshInterval: 15000, revalidateOnFocus: false }
  );

  return (
    <aside style={sidebar}>
      {/* New experiment button */}
      <div style={{ padding: "12px 12px 8px" }}>
        <Link
          href="/"
          style={{
            display: "block",
            width: "100%",
            padding: "7px 0",
            background: "var(--accent)",
            color: "#fff",
            borderRadius: 6,
            textDecoration: "none",
            fontSize: 13,
            fontWeight: 500,
            textAlign: "center",
            transition: "background 150ms",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = "var(--accent-h)")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "var(--accent)")}
        >
          + New Experiment
        </Link>
      </div>

      {/* Divider */}
      <div style={{ height: 1, background: "var(--border-s)", margin: "0 12px" }} />

      {/* Section label */}
      <div
        style={{
          padding: "10px 16px 4px",
          fontSize: 10,
          fontWeight: 500,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          color: "var(--t-tertiary)",
        }}
      >
        History
      </div>

      {/* List */}
      <div style={{ flex: 1, overflowY: "auto" }}>
        {!experiments || experiments.length === 0 ? (
          <div style={{ padding: "8px 16px", fontSize: 12, color: "var(--t-tertiary)" }}>
            No experiments yet.
          </div>
        ) : (
          [...experiments].reverse().map((exp) => {
            const active = activeId === exp.id;
            return (
              <Link
                key={exp.id}
                href={`/experiments/${exp.id}`}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 8,
                  padding: "8px 16px 8px 14px",
                  textDecoration: "none",
                  background: active ? "var(--bg-hover)" : "transparent",
                  borderLeft: active
                    ? "2px solid var(--accent)"
                    : "2px solid transparent",
                  transition: "background 100ms",
                }}
                onMouseEnter={(e) => {
                  if (!active) e.currentTarget.style.background = "var(--bg-hover)";
                }}
                onMouseLeave={(e) => {
                  if (!active) e.currentTarget.style.background = "transparent";
                }}
              >
                {/* Status dot */}
                <div
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: "50%",
                    background: statusColor(exp),
                    marginTop: 5,
                    flexShrink: 0,
                  }}
                />
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div
                    style={{
                      fontSize: 12,
                      color: "var(--t-primary)",
                      fontWeight: active ? 500 : 400,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {exp.domain}
                  </div>
                  <div style={{ fontSize: 10, color: "var(--t-tertiary)", marginTop: 1 }}>
                    {relativeTime(exp.timestamp)}
                  </div>
                </div>
              </Link>
            );
          })
        )}
      </div>
    </aside>
  );
}
