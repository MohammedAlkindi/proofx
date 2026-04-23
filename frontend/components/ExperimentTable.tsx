import { useState, CSSProperties } from "react";
import Link from "next/link";

export interface ExperimentSummary {
  id: string;
  timestamp: string;
  domain: string;
  conjecture: string;
  is_valid: boolean;
  proved: boolean;
  model_used: string;
  duration_ms: number;
  novelty_score?: number;
  proof_strategy?: string;
}

type SortKey = keyof Pick<ExperimentSummary, "timestamp" | "domain" | "duration_ms" | "proved">;

function fmtDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function fmtTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function StatusBadge({ proved, isValid }: { proved: boolean; isValid: boolean }) {
  const label  = proved ? "proved" : isValid ? "sorry" : "error";
  const colors: Record<string, CSSProperties> = {
    proved: { background: "rgba(16,185,129,0.1)",  color: "var(--success)", border: "1px solid rgba(16,185,129,0.2)" },
    sorry:  { background: "rgba(245,158,11,0.1)",  color: "var(--warning)", border: "1px solid rgba(245,158,11,0.2)" },
    error:  { background: "rgba(239,68,68,0.1)",   color: "var(--danger)",  border: "1px solid rgba(239,68,68,0.2)" },
  };
  return (
    <span
      style={{
        ...colors[label],
        fontFamily: "JetBrains Mono, monospace",
        fontSize: 10,
        fontWeight: 600,
        padding: "2px 7px",
        borderRadius: 4,
        letterSpacing: "0.05em",
        textTransform: "uppercase",
        display: "inline-block",
      }}
    >
      {label}
    </span>
  );
}

function SortArrow({ active, dir }: { active: boolean; dir: "asc" | "desc" }) {
  if (!active) return <span style={{ color: "var(--t-tertiary)", marginLeft: 4, opacity: 0.4 }}>↕</span>;
  return (
    <span style={{ color: "var(--accent)", marginLeft: 4 }}>
      {dir === "asc" ? "↑" : "↓"}
    </span>
  );
}

const thStyle: CSSProperties = {
  padding: "8px 12px",
  textAlign: "left",
  fontSize: 10,
  fontWeight: 600,
  letterSpacing: "0.07em",
  textTransform: "uppercase",
  color: "var(--t-tertiary)",
  whiteSpace: "nowrap",
  userSelect: "none",
  cursor: "pointer",
  borderBottom: "1px solid var(--border-s)",
  background: "var(--bg-input)",
};

const thStaticStyle: CSSProperties = {
  ...thStyle,
  cursor: "default",
};

export default function ExperimentTable({
  experiments,
  loading,
}: {
  experiments: ExperimentSummary[];
  loading: boolean;
}) {
  const [sortKey, setSortKey] = useState<SortKey>("timestamp");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [filter, setFilter] = useState("");

  const handleSort = (key: SortKey) => {
    if (key === sortKey) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(key); setSortDir("desc"); }
  };

  const sorted = [...experiments]
    .filter((e) => {
      if (!filter) return true;
      const q = filter.toLowerCase();
      return e.domain.toLowerCase().includes(q) || e.conjecture.toLowerCase().includes(q);
    })
    .sort((a, b) => {
      const m = sortDir === "asc" ? 1 : -1;
      if (sortKey === "timestamp")   return m * a.timestamp.localeCompare(b.timestamp);
      if (sortKey === "domain")      return m * a.domain.localeCompare(b.domain);
      if (sortKey === "duration_ms") return m * (a.duration_ms - b.duration_ms);
      if (sortKey === "proved")      return m * (Number(a.proved) - Number(b.proved));
      return 0;
    });

  return (
    <div>
      {/* Header row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 16,
        }}
      >
        <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
          <span
            style={{
              fontSize: 15,
              fontWeight: 600,
              color: "var(--t-primary)",
              letterSpacing: "-0.01em",
            }}
          >
            Experiments
          </span>
          <span
            style={{
              fontSize: 12,
              color: "var(--t-tertiary)",
              fontFamily: "JetBrains Mono, monospace",
            }}
          >
            {experiments.length}
          </span>
        </div>
        <input
          type="search"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter…"
          style={{
            padding: "5px 10px",
            fontSize: 12,
            borderRadius: 6,
            border: "1px solid var(--border-s)",
            background: "var(--bg-input)",
            color: "var(--t-primary)",
            outline: "none",
            width: 200,
            transition: "border-color 150ms",
          }}
          onFocus={(e) => (e.currentTarget.style.borderColor = "var(--accent)")}
          onBlur={(e)  => (e.currentTarget.style.borderColor = "var(--border-s)")}
        />
      </div>

      {/* Table */}
      {loading ? (
        <div style={{ display: "flex", justifyContent: "center", padding: "48px 0" }}>
          <div
            style={{
              width: 24,
              height: 24,
              borderRadius: "50%",
              border: "2px solid var(--accent)",
              borderTopColor: "transparent",
              animation: "spin 0.8s linear infinite",
            }}
          />
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      ) : sorted.length === 0 ? (
        <div
          style={{
            textAlign: "center",
            padding: "64px 0",
            display: "flex",
            flexDirection: "column",
            gap: 6,
          }}
        >
          <span style={{ fontSize: 13, color: "var(--t-tertiary)" }}>
            {filter ? "No experiments match your filter." : "No experiments yet."}
          </span>
          {!filter && (
            <span style={{ fontSize: 12, color: "var(--border-a)" }}>
              Run your first pipeline above.
            </span>
          )}
        </div>
      ) : (
        <div
          style={{
            border: "1px solid var(--border-s)",
            borderRadius: 8,
            overflow: "hidden",
          }}
        >
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={thStyle} onClick={() => handleSort("timestamp")}>
                  Time <SortArrow active={sortKey === "timestamp"} dir={sortDir} />
                </th>
                <th style={thStyle} onClick={() => handleSort("domain")}>
                  Domain <SortArrow active={sortKey === "domain"} dir={sortDir} />
                </th>
                <th style={thStaticStyle}>Conjecture</th>
                <th style={thStyle} onClick={() => handleSort("proved")}>
                  Status <SortArrow active={sortKey === "proved"} dir={sortDir} />
                </th>
                <th style={thStyle} onClick={() => handleSort("duration_ms")}>
                  Duration <SortArrow active={sortKey === "duration_ms"} dir={sortDir} />
                </th>
                <th style={{ ...thStaticStyle, width: 60 }} />
              </tr>
            </thead>
            <tbody>
              {sorted.map((exp, rowIdx) => (
                <tr
                  key={exp.id}
                  style={{
                    borderTop: rowIdx === 0 ? "none" : "1px solid var(--border-s)",
                    transition: "background 100ms",
                  }}
                  onMouseEnter={(e) =>
                    ((e.currentTarget as HTMLElement).style.background = "var(--bg-input)")
                  }
                  onMouseLeave={(e) =>
                    ((e.currentTarget as HTMLElement).style.background = "transparent")
                  }
                >
                  <td
                    style={{
                      padding: "9px 12px",
                      fontFamily: "JetBrains Mono, monospace",
                      fontSize: 11,
                      color: "var(--t-tertiary)",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {fmtTime(exp.timestamp)}
                  </td>
                  <td
                    style={{
                      padding: "9px 12px",
                      fontSize: 12,
                      fontWeight: 500,
                      color: "var(--t-primary)",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {exp.domain}
                  </td>
                  <td
                    style={{
                      padding: "9px 12px",
                      fontSize: 12,
                      color: "var(--t-secondary)",
                      maxWidth: 260,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {exp.conjecture}
                  </td>
                  <td style={{ padding: "9px 12px" }}>
                    <StatusBadge proved={exp.proved} isValid={exp.is_valid} />
                  </td>
                  <td
                    style={{
                      padding: "9px 12px",
                      fontFamily: "JetBrains Mono, monospace",
                      fontSize: 11,
                      color: "var(--t-tertiary)",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {fmtDuration(exp.duration_ms)}
                  </td>
                  <td style={{ padding: "9px 12px" }}>
                    <Link
                      href={`/experiments/${exp.id}`}
                      style={{
                        fontSize: 11,
                        color: "var(--accent)",
                        textDecoration: "none",
                        fontWeight: 500,
                      }}
                    >
                      View →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
