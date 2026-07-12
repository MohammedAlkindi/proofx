import { ReactNode, useMemo, useState } from "react";
import Link from "next/link";
import { useSettings } from "../context/SettingsContext";

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
  counterexample_checked?: boolean | null;
  counterexample_found?: boolean | null;
}

type SortKey = keyof Pick<ExperimentSummary, "timestamp" | "domain" | "duration_ms" | "proved">;
type StatusFilter = "all" | "proved" | "open" | "invalid";
type StatusLabel = "proved" | "unrefuted" | "sorry" | "error";

const tabs: { key: StatusFilter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "proved", label: "Proved" },
  { key: "open", label: "Open" },
  { key: "invalid", label: "Invalid" },
];

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

function statusLabel(exp: ExperimentSummary): StatusLabel {
  return exp.proved
    ? "proved"
    : exp.is_valid && exp.counterexample_checked && !exp.counterexample_found
    ? "unrefuted"
    : exp.is_valid
    ? "sorry"
    : "error";
}

function Highlight({ text, query }: { text: string; query: string }): ReactNode {
  if (!query) return <>{text}</>;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return <>{text}</>;
  return (
    <>
      {text.slice(0, idx)}
      <mark>{text.slice(idx, idx + query.length)}</mark>
      {text.slice(idx + query.length)}
    </>
  );
}

function StatusBadge({ status }: { status: StatusLabel }) {
  const styles: Record<StatusLabel, { bg: string; color: string; border: string }> = {
    proved: { bg: "rgba(15,143,103,0.1)", color: "var(--success)", border: "rgba(15,143,103,0.24)" },
    unrefuted: { bg: "rgba(37,99,235,0.1)", color: "var(--info)", border: "rgba(37,99,235,0.24)" },
    sorry: { bg: "rgba(183,121,31,0.1)", color: "var(--warning)", border: "rgba(183,121,31,0.24)" },
    error: { bg: "rgba(194,65,61,0.1)", color: "var(--danger)", border: "rgba(194,65,61,0.24)" },
  };
  const style = styles[status];
  return (
    <span
      className="mono"
      style={{
        background: style.bg,
        border: `1px solid ${style.border}`,
        borderRadius: 4,
        color: style.color,
        display: "inline-flex",
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: "0.05em",
        padding: "2px 7px",
        textTransform: "uppercase",
      }}
    >
      {status}
    </span>
  );
}

function NoveltyBar({ score }: { score: number }) {
  const pct = Math.max(0, Math.min(1, score)) * 100;
  const color = score >= 0.7 ? "var(--success)" : score >= 0.4 ? "var(--warning)" : "var(--danger)";
  return (
    <div style={{ alignItems: "center", display: "flex", gap: 6 }}>
      <div
        style={{
          background: "var(--border-s)",
          borderRadius: 999,
          flex: 1,
          height: 4,
          minWidth: 46,
          overflow: "hidden",
        }}
      >
        <div style={{ background: color, height: "100%", width: `${pct}%` }} />
      </div>
      <span className="mono" style={{ color, fontSize: 10 }}>
        {pct.toFixed(0)}%
      </span>
    </div>
  );
}

function SortArrow({ active, dir }: { active: boolean; dir: "asc" | "desc" }) {
  return (
    <span style={{ color: active ? "var(--accent)" : "var(--t-tertiary)", marginLeft: 5 }}>
      {active ? (dir === "asc" ? "up" : "down") : ""}
    </span>
  );
}

const thStyle = {
  background: "var(--bg-input)",
  borderBottom: "1px solid var(--border-s)",
  color: "var(--t-tertiary)",
  cursor: "pointer",
  fontSize: 10,
  fontWeight: 700,
  letterSpacing: "0.08em",
  padding: "9px 12px",
  textAlign: "left" as const,
  textTransform: "uppercase" as const,
  whiteSpace: "nowrap" as const,
};

export default function ExperimentTable({
  experiments,
  loading,
}: {
  experiments: ExperimentSummary[];
  loading: boolean;
}) {
  const { settings } = useSettings();
  const [sortKey, setSortKey] = useState<SortKey>("timestamp");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [filter, setFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");

  const counts = useMemo<Record<StatusFilter, number>>(
    () => ({
      all: experiments.length,
      proved: experiments.filter((exp) => exp.proved).length,
      open: experiments.filter((exp) => !exp.proved && exp.is_valid).length,
      invalid: experiments.filter((exp) => !exp.is_valid).length,
    }),
    [experiments]
  );

  const sorted = useMemo(() => {
    return [...experiments]
      .filter((exp) => {
        if (statusFilter === "proved") return exp.proved;
        if (statusFilter === "open") return !exp.proved && exp.is_valid;
        if (statusFilter === "invalid") return !exp.is_valid;
        return true;
      })
      .filter((exp) => {
        if (!filter) return true;
        const q = filter.toLowerCase();
        return exp.domain.toLowerCase().includes(q) || exp.conjecture.toLowerCase().includes(q);
      })
      .sort((a, b) => {
        const multiplier = sortDir === "asc" ? 1 : -1;
        if (sortKey === "timestamp") return multiplier * a.timestamp.localeCompare(b.timestamp);
        if (sortKey === "domain") return multiplier * a.domain.localeCompare(b.domain);
        if (sortKey === "duration_ms") return multiplier * (a.duration_ms - b.duration_ms);
        return multiplier * (Number(a.proved) - Number(b.proved));
      });
  }, [experiments, filter, sortDir, sortKey, statusFilter]);

  const handleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDir((dir) => (dir === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const showCards = settings.defaultExperimentView === "cards";

  return (
    <section style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{ alignItems: "center", display: "flex", flexWrap: "wrap", gap: 12, justifyContent: "space-between" }}>
        <div>
          <span className="label">Archive</span>
          <div className="mono muted" style={{ fontSize: 11, marginTop: 3 }}>
            {sorted.length} visible / {experiments.length} total
          </div>
        </div>
        <input
          className="control"
          onChange={(event) => setFilter(event.target.value)}
          placeholder="Filter domain or conjecture"
          style={{ fontSize: 12, height: 34, padding: "0 11px", width: 240 }}
          type="search"
          value={filter}
        />
      </div>

      <div
        style={{
          background: "var(--bg-input)",
          border: "1px solid var(--border-s)",
          borderRadius: 7,
          display: "flex",
          flexWrap: "wrap",
          gap: 3,
          padding: 3,
          width: "fit-content",
        }}
      >
        {tabs.map((tab) => {
          const active = statusFilter === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setStatusFilter(tab.key)}
              style={{
                alignItems: "center",
                background: active ? "var(--bg-card)" : "transparent",
                border: "none",
                borderRadius: 5,
                color: active ? "var(--t-primary)" : "var(--t-tertiary)",
                cursor: "pointer",
                display: "flex",
                fontSize: 11,
                fontWeight: active ? 700 : 500,
                gap: 6,
                height: 28,
                padding: "0 11px",
              }}
            >
              {tab.label}
              <span className="mono" style={{ color: active ? "var(--accent)" : "var(--t-tertiary)", fontSize: 10 }}>
                {counts[tab.key]}
              </span>
            </button>
          );
        })}
      </div>

      {loading ? (
        <div className="panel" style={{ alignItems: "center", display: "flex", justifyContent: "center", minHeight: 220 }}>
          <span
            className="anim-spin"
            style={{
              border: "2px solid var(--accent)",
              borderRadius: "50%",
              borderTopColor: "transparent",
              height: 24,
              width: 24,
            }}
          />
        </div>
      ) : sorted.length === 0 ? (
        <div className="panel" style={{ padding: "56px 24px", textAlign: "center" }}>
          <p style={{ color: "var(--t-primary)", fontSize: 14, fontWeight: 700, margin: 0 }}>
            {filter || statusFilter !== "all" ? "No matching experiments" : "No experiments yet"}
          </p>
          <p style={{ color: "var(--t-tertiary)", fontSize: 13, margin: "6px 0 0" }}>
            {filter || statusFilter !== "all"
              ? "Adjust the filter or status tabs."
              : "Run a pipeline to create the first reproducible snapshot."}
          </p>
        </div>
      ) : showCards ? (
        <div style={{ display: "grid", gap: "var(--density-gap)", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))" }}>
          {sorted.map((exp, rowIdx) => {
            const status = statusLabel(exp);
            return (
              <Link
                className="panel anim-row-in"
                href={`/experiments/${exp.id}`}
                key={exp.id}
                style={{
                  animationDelay: `${Math.min(rowIdx * 25, 160)}ms`,
                  color: "inherit",
                  display: "flex",
                  flexDirection: "column",
                  gap: 12,
                  minHeight: 184,
                  padding: "var(--density-pad)",
                  textDecoration: "none",
                }}
              >
                <div style={{ alignItems: "center", display: "flex", gap: 10, justifyContent: "space-between" }}>
                  <span className="label" style={{ color: "var(--accent)" }}>
                    <Highlight query={filter} text={exp.domain} />
                  </span>
                  <StatusBadge status={status} />
                </div>
                <p style={{ color: "var(--t-primary)", fontSize: 13, lineHeight: 1.65, margin: 0 }}>
                  <Highlight query={filter} text={exp.conjecture} />
                </p>
                <div style={{ display: "flex", flexDirection: "column", gap: 9, marginTop: "auto" }}>
                  {settings.showTechnicalDetail && (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
                      <span className="mono muted" style={{ fontSize: 10 }}>
                        {fmtTime(exp.timestamp)}
                      </span>
                      <span className="mono muted" style={{ fontSize: 10 }}>
                        {fmtDuration(exp.duration_ms)}
                      </span>
                      <span className="mono muted" style={{ fontSize: 10 }}>
                        {exp.id.slice(0, 8)}
                      </span>
                    </div>
                  )}
                  <div style={{ alignItems: "center", display: "flex", justifyContent: "space-between", gap: 12 }}>
                    {typeof exp.novelty_score === "number" && settings.showTechnicalDetail ? (
                      <div style={{ minWidth: 100 }}>
                        <NoveltyBar score={exp.novelty_score} />
                      </div>
                    ) : (
                      <span className="mono muted" style={{ fontSize: 10 }}>
                        {status}
                      </span>
                    )}
                    <span style={{ color: "var(--accent)", fontSize: 12, fontWeight: 700 }}>View</span>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      ) : (
        <div className="panel" style={{ overflow: "auto" }}>
          <table style={{ borderCollapse: "collapse", minWidth: 760, width: "100%" }}>
            <thead>
              <tr>
                <th onClick={() => handleSort("timestamp")} style={thStyle}>
                  Time <SortArrow active={sortKey === "timestamp"} dir={sortDir} />
                </th>
                <th onClick={() => handleSort("domain")} style={thStyle}>
                  Domain <SortArrow active={sortKey === "domain"} dir={sortDir} />
                </th>
                <th style={{ ...thStyle, cursor: "default" }}>Conjecture</th>
                <th onClick={() => handleSort("proved")} style={thStyle}>
                  Status <SortArrow active={sortKey === "proved"} dir={sortDir} />
                </th>
                {settings.showTechnicalDetail && <th style={{ ...thStyle, cursor: "default" }}>Novelty</th>}
                {settings.showTechnicalDetail && (
                  <th onClick={() => handleSort("duration_ms")} style={thStyle}>
                    Duration <SortArrow active={sortKey === "duration_ms"} dir={sortDir} />
                  </th>
                )}
                <th style={{ ...thStyle, cursor: "default", width: 64 }} />
              </tr>
            </thead>
            <tbody>
              {sorted.map((exp, rowIdx) => {
                const status = statusLabel(exp);
                return (
                  <tr
                    className="anim-row-in"
                    key={exp.id}
                    style={{
                      animationDelay: `${Math.min(rowIdx * 20, 140)}ms`,
                      borderTop: rowIdx === 0 ? "none" : "1px solid var(--border-s)",
                    }}
                  >
                    <td className="mono muted" style={{ fontSize: 11, padding: "var(--density-row) 12px", whiteSpace: "nowrap" }}>
                      {fmtTime(exp.timestamp)}
                    </td>
                    <td style={{ color: "var(--t-primary)", fontSize: 12, fontWeight: 700, padding: "var(--density-row) 12px", whiteSpace: "nowrap" }}>
                      <Highlight query={filter} text={exp.domain} />
                    </td>
                    <td style={{ color: "var(--t-secondary)", fontSize: 12, maxWidth: 360, overflow: "hidden", padding: "var(--density-row) 12px", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      <Highlight query={filter} text={exp.conjecture} />
                    </td>
                    <td style={{ padding: "var(--density-row) 12px" }}>
                      <StatusBadge status={status} />
                    </td>
                    {settings.showTechnicalDetail && (
                      <td style={{ padding: "var(--density-row) 12px" }}>
                        {typeof exp.novelty_score === "number" ? (
                          <NoveltyBar score={exp.novelty_score} />
                        ) : (
                          <span className="mono muted" style={{ fontSize: 10 }}>
                            -
                          </span>
                        )}
                      </td>
                    )}
                    {settings.showTechnicalDetail && (
                      <td className="mono muted" style={{ fontSize: 11, padding: "var(--density-row) 12px", whiteSpace: "nowrap" }}>
                        {fmtDuration(exp.duration_ms)}
                      </td>
                    )}
                    <td style={{ padding: "var(--density-row) 12px" }}>
                      <Link href={`/experiments/${exp.id}`} style={{ color: "var(--accent)", fontSize: 12, fontWeight: 700, textDecoration: "none" }}>
                        View
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
