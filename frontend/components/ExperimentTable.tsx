import { useState, CSSProperties, ReactNode } from "react";
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
  // Present only when the ensemble counterexample search has been run (new records).
  // null/undefined means "never checked" (proved conjectures or pre-dual records).
  counterexample_checked?: boolean | null;
  counterexample_found?: boolean | null;
}

type SortKey = keyof Pick<ExperimentSummary, "timestamp" | "domain" | "duration_ms" | "proved">;
type StatusFilter = "all" | "proved" | "open" | "invalid";

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

function Highlight({ text, query }: { text: string; query: string }): ReactNode {
  if (!query) return <>{text}</>;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return <>{text}</>;
  return (
    <>
      {text.slice(0, idx)}
      <mark
        style={{
          background: "rgba(124,58,237,0.2)",
          color: "var(--accent)",
          borderRadius: 2,
          padding: "0 1px",
        }}
      >
        {text.slice(idx, idx + query.length)}
      </mark>
      {text.slice(idx + query.length)}
    </>
  );
}

function NoveltyBar({ score }: { score: number }) {
  const pct = Math.max(0, Math.min(1, score)) * 100;
  const color =
    score >= 0.7 ? "var(--success)" : score >= 0.4 ? "var(--warning)" : "var(--danger)";
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 5,
      }}
    >
      <div
        style={{
          width: 40,
          height: 3,
          borderRadius: 2,
          background: "var(--border-s)",
          overflow: "hidden",
          flexShrink: 0,
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${pct}%`,
            background: color,
            borderRadius: 2,
            transition: "width 300ms ease",
          }}
        />
      </div>
      <span
        style={{
          fontFamily: "JetBrains Mono, monospace",
          fontSize: 10,
          color,
        }}
      >
        {pct.toFixed(0)}%
      </span>
    </div>
  );
}

type StatusLabel = "proved" | "unrefuted" | "sorry" | "error";

function StatusBadge({
  proved,
  isValid,
  counterexampleChecked,
  counterexampleFound,
}: {
  proved: boolean;
  isValid: boolean;
  counterexampleChecked?: boolean | null;
  counterexampleFound?: boolean | null;
}) {
  // "unrefuted": ensemble search ran, is lean-valid, but no method found a counterexample.
  // Distinct from "sorry" (not yet checked) — absence of disproof ≠ evidence of truth.
  const label: StatusLabel = proved
    ? "proved"
    : isValid && counterexampleChecked && !counterexampleFound
    ? "unrefuted"
    : isValid
    ? "sorry"
    : "error";

  const colors: Record<StatusLabel, CSSProperties> = {
    proved:    { background: "rgba(16,185,129,0.1)", color: "var(--success)", border: "1px solid rgba(16,185,129,0.2)" },
    unrefuted: { background: "rgba(59,130,246,0.1)", color: "#3b82f6",        border: "1px solid rgba(59,130,246,0.2)" },
    sorry:     { background: "rgba(245,158,11,0.1)", color: "var(--warning)", border: "1px solid rgba(245,158,11,0.2)" },
    error:     { background: "rgba(239,68,68,0.1)",  color: "var(--danger)",  border: "1px solid rgba(239,68,68,0.2)" },
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
  if (!active)
    return <span style={{ color: "var(--t-tertiary)", marginLeft: 4, opacity: 0.4 }}>↕</span>;
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

const thStaticStyle: CSSProperties = { ...thStyle, cursor: "default" };

const STATUS_TABS: { key: StatusFilter; label: string }[] = [
  { key: "all",     label: "All" },
  { key: "proved",  label: "Proved" },
  { key: "open",    label: "Open" },
  { key: "invalid", label: "Invalid" },
];

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
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");

  const handleSort = (key: SortKey) => {
    if (key === sortKey) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(key); setSortDir("desc"); }
  };

  // Counts for tabs
  const counts: Record<StatusFilter, number> = {
    all:     experiments.length,
    proved:  experiments.filter((e) => e.proved).length,
    open:    experiments.filter((e) => !e.proved && e.is_valid).length,
    invalid: experiments.filter((e) => !e.is_valid).length,
  };

  const sorted = [...experiments]
    .filter((e) => {
      // Status filter
      if (statusFilter === "proved")  return e.proved;
      if (statusFilter === "open")    return !e.proved && e.is_valid;
      if (statusFilter === "invalid") return !e.is_valid;
      return true;
    })
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
          marginBottom: 12,
          flexWrap: "wrap",
          gap: 10,
        }}
      >
        <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
          <span style={{ fontSize: 15, fontWeight: 600, color: "var(--t-primary)", letterSpacing: "-0.01em" }}>
            Experiments
          </span>
          <span style={{ fontSize: 12, color: "var(--t-tertiary)", fontFamily: "JetBrains Mono, monospace" }}>
            {sorted.length}
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

      {/* Status filter tabs */}
      <div
        style={{
          display: "flex",
          gap: 2,
          marginBottom: 14,
          background: "var(--bg-input)",
          borderRadius: 7,
          padding: 3,
          width: "fit-content",
        }}
      >
        {STATUS_TABS.map(({ key, label }) => {
          const active = statusFilter === key;
          return (
            <button
              key={key}
              onClick={() => setStatusFilter(key)}
              style={{
                padding: "4px 12px",
                fontSize: 11,
                fontWeight: active ? 600 : 400,
                borderRadius: 5,
                border: "none",
                background: active ? "var(--bg-card)" : "transparent",
                color: active ? "var(--t-primary)" : "var(--t-tertiary)",
                cursor: "pointer",
                fontFamily: "inherit",
                display: "flex",
                alignItems: "center",
                gap: 5,
                boxShadow: active ? "0 1px 3px rgba(0,0,0,0.12)" : "none",
                transition: "background 150ms, color 150ms",
              }}
            >
              {label}
              <span
                style={{
                  fontFamily: "JetBrains Mono, monospace",
                  fontSize: 10,
                  color: active ? "var(--accent)" : "var(--t-tertiary)",
                  opacity: 0.8,
                }}
              >
                {counts[key]}
              </span>
            </button>
          );
        })}
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
            {filter || statusFilter !== "all"
              ? "No experiments match your filter."
              : "No experiments yet."}
          </span>
          {!filter && statusFilter === "all" && (
            <span style={{ fontSize: 12, color: "var(--border-a)" }}>
              Run your first pipeline above.
            </span>
          )}
        </div>
      ) : (
        <div style={{ border: "1px solid var(--border-s)", borderRadius: 8, overflow: "hidden" }}>
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
                <th style={thStaticStyle}>Novelty</th>
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
                  className="anim-row-in"
                  style={{
                    borderTop: rowIdx === 0 ? "none" : "1px solid var(--border-s)",
                    transition: "background 100ms",
                    animationDelay: `${Math.min(rowIdx * 30, 200)}ms`,
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
                    <Highlight text={exp.domain} query={filter} />
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
                    <Highlight text={exp.conjecture} query={filter} />
                  </td>
                  <td style={{ padding: "9px 12px" }}>
                    <StatusBadge
                      proved={exp.proved}
                      isValid={exp.is_valid}
                      counterexampleChecked={exp.counterexample_checked}
                      counterexampleFound={exp.counterexample_found}
                    />
                  </td>
                  <td style={{ padding: "9px 12px" }}>
                    {typeof exp.novelty_score === "number" ? (
                      <NoveltyBar score={exp.novelty_score} />
                    ) : (
                      <span style={{ fontSize: 10, color: "var(--border-a)" }}>—</span>
                    )}
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
