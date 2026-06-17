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

function statusLabel(item: ExperimentItem): string {
  if (item.proved) return "proved";
  if (item.is_valid) return "open";
  return "invalid";
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
  background: "var(--bg-page)",
  borderRight: "1px solid var(--border-s)",
  bottom: 0,
  display: "flex",
  flexDirection: "column",
  left: 0,
  overflowY: "auto",
  position: "fixed",
  top: 56,
  width: 260,
  zIndex: 90,
};

export default function Sidebar({ refreshKey = 0 }: { refreshKey?: number }) {
  const router = useRouter();
  const activeId = router.query.id as string | undefined;

  const { data: experiments, isLoading } = useSWR<ExperimentItem[]>(
    `${API}/api/v1/experiments?_r=${refreshKey}`,
    fetcher,
    { refreshInterval: 15000, revalidateOnFocus: false }
  );

  const recent = [...(experiments ?? [])].reverse().slice(0, 80);

  return (
    <aside className="app-sidebar" style={sidebar}>
      <div style={{ padding: "16px 14px 12px" }}>
        <Link
          href="/"
          className="primary-button"
          style={{ height: 36, textDecoration: "none", width: "100%" }}
        >
          New experiment
        </Link>
      </div>

      <div style={{ borderTop: "1px solid var(--border-s)", padding: "13px 14px 8px" }}>
        <div style={{ alignItems: "center", display: "flex", justifyContent: "space-between" }}>
          <span className="label">Recent</span>
          {experiments && (
            <span className="mono muted" style={{ fontSize: 10 }}>
              {experiments.length}
            </span>
          )}
        </div>
      </div>

      <div style={{ flex: 1, overflowY: "auto", paddingBottom: 16 }}>
        {isLoading ? (
          <div className="muted" style={{ fontSize: 12, padding: "8px 16px" }}>
            Loading experiments...
          </div>
        ) : recent.length === 0 ? (
          <div className="muted" style={{ fontSize: 12, lineHeight: 1.6, padding: "8px 16px" }}>
            No experiments yet.
          </div>
        ) : (
          recent.map((exp) => {
            const active = activeId === exp.id;
            return (
              <Link
                href={`/experiments/${exp.id}`}
                key={exp.id}
                style={{
                  background: active ? "var(--bg-hover)" : "transparent",
                  borderLeft: active ? "2px solid var(--accent)" : "2px solid transparent",
                  display: "flex",
                  gap: 10,
                  padding: "9px 14px 9px 12px",
                  textDecoration: "none",
                }}
              >
                <span
                  aria-label={statusLabel(exp)}
                  style={{
                    background: statusColor(exp),
                    borderRadius: 999,
                    flexShrink: 0,
                    height: 7,
                    marginTop: 6,
                    width: 7,
                  }}
                />
                <span style={{ minWidth: 0 }}>
                  <span
                    style={{
                      color: active ? "var(--t-primary)" : "var(--t-secondary)",
                      display: "block",
                      fontSize: 12,
                      fontWeight: active ? 600 : 500,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {exp.domain}
                  </span>
                  <span className="mono muted" style={{ display: "block", fontSize: 10, marginTop: 2 }}>
                    {relativeTime(exp.timestamp)} / {exp.id.slice(0, 8)}
                  </span>
                </span>
              </Link>
            );
          })
        )}
      </div>
    </aside>
  );
}
