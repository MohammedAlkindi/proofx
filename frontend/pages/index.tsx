import { useState, useCallback, CSSProperties } from "react";
import useSWR from "swr";
import Pipeline, { Stage, PipelineResponse } from "../components/Pipeline";
import ExperimentTable, { ExperimentSummary } from "../components/ExperimentTable";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const fetcher = (url: string) => fetch(url).then((r) => r.json());

const DOMAINS = [
  "number theory",
  "graph theory",
  "algebraic topology",
  "combinatorics",
  "analytic number theory",
  "group theory",
  "Ramsey theory",
  "additive combinatorics",
  "knot theory",
  "elliptic curves",
];

const sectionLabel: CSSProperties = {
  fontSize: 10,
  fontWeight: 500,
  letterSpacing: "0.1em",
  textTransform: "uppercase",
  color: "var(--t-tertiary)",
  marginBottom: 8,
  display: "block",
};

interface HomeProps {
  onSidebarBump?: () => void;
}

export default function Home({ onSidebarBump }: HomeProps) {
  const [domain, setDomain]   = useState("");
  const [n, setN]             = useState(1);
  const [stage, setStage]     = useState<Stage>("idle");
  const [response, setResponse] = useState<PipelineResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  const { data: experiments, isLoading } = useSWR<ExperimentSummary[]>(
    `${API}/api/v1/experiments?_r=${refreshKey}`,
    fetcher,
    { refreshInterval: 0, revalidateOnFocus: false }
  );

  const running =
    stage === "generating" || stage === "formalizing" || stage === "verifying";

  const handleRun = useCallback(async () => {
    if (!domain.trim() || running) return;
    setStage("generating");
    setResponse(null);
    setErrorMsg("");

    try {
      await new Promise((r) => setTimeout(r, 300));
      setStage("formalizing");
      await new Promise((r) => setTimeout(r, 300));
      setStage("verifying");

      const res = await fetch(`${API}/api/v1/pipeline`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ domain: domain.trim(), n }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail ?? res.statusText);
      }

      const data: PipelineResponse = await res.json();
      setResponse(data);
      setStage("done");
      setRefreshKey((k) => k + 1);
      onSidebarBump?.();
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : String(err));
      setStage("error");
    }
  }, [domain, n, running, onSidebarBump]);

  const handleReset = () => {
    setStage("idle");
    setResponse(null);
    setErrorMsg("");
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 48 }}>
      {/* ── Configuration panel ── */}
      <section>
        <div
          style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border-s)",
            borderRadius: 10,
            padding: 24,
          }}
        >
          <h2
            style={{
              fontSize: 15,
              fontWeight: 600,
              color: "var(--t-primary)",
              letterSpacing: "-0.01em",
              marginBottom: 20,
            }}
          >
            New Experiment
          </h2>

          {/* Domain */}
          <span style={sectionLabel}>Domain</span>
          <input
            type="text"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleRun()}
            placeholder="e.g. number theory, elliptic curves, graph theory…"
            disabled={running}
            style={{
              width: "100%",
              padding: "9px 12px",
              fontSize: 13,
              background: "var(--bg-input)",
              border: "1px solid var(--border-s)",
              borderRadius: 6,
              color: "var(--t-primary)",
              outline: "none",
              transition: "border-color 150ms",
              fontFamily: "inherit",
              opacity: running ? 0.6 : 1,
            }}
            onFocus={(e) => (e.currentTarget.style.borderColor = "var(--accent)")}
            onBlur={(e)  => (e.currentTarget.style.borderColor = "var(--border-s)")}
          />

          {/* Pills */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}>
            {DOMAINS.map((d) => {
              const selected = domain === d;
              return (
                <button
                  key={d}
                  onClick={() => setDomain(d)}
                  disabled={running}
                  style={{
                    padding: "3px 10px",
                    fontSize: 11,
                    borderRadius: 4,
                    border: `1px solid ${selected ? "var(--accent)" : "var(--border-s)"}`,
                    background: selected ? "rgba(124,58,237,0.1)" : "var(--bg-input)",
                    color: selected ? "var(--accent)" : "var(--t-secondary)",
                    cursor: running ? "default" : "pointer",
                    opacity: running ? 0.4 : 1,
                    transition: "border-color 150ms, background 150ms, color 150ms",
                    fontFamily: "inherit",
                  }}
                  onMouseEnter={(e) => {
                    if (!running && !selected) {
                      e.currentTarget.style.borderColor = "var(--accent)";
                      e.currentTarget.style.color = "var(--accent)";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!selected) {
                      e.currentTarget.style.borderColor = "var(--border-s)";
                      e.currentTarget.style.color = "var(--t-secondary)";
                    }
                  }}
                >
                  {d}
                </button>
              );
            })}
          </div>

          {/* Count selector */}
          <div style={{ marginTop: 18, display: "flex", alignItems: "center", gap: 2 }}>
            <span style={{ fontSize: 13, color: "var(--t-secondary)" }}>Generate [</span>
            {[1, 2, 3].map((v, i) => (
              <span key={v} style={{ display: "flex", alignItems: "center" }}>
                {i > 0 && (
                  <span
                    style={{ fontSize: 13, color: "var(--t-tertiary)", margin: "0 1px" }}
                  >
                    |
                  </span>
                )}
                <button
                  onClick={() => setN(v)}
                  disabled={running}
                  style={{
                    fontSize: 13,
                    fontFamily: "JetBrains Mono, monospace",
                    fontWeight: n === v ? 500 : 400,
                    color: n === v ? "var(--accent)" : "var(--t-tertiary)",
                    background: "none",
                    border: "none",
                    cursor: running ? "default" : "pointer",
                    padding: "0 5px",
                    opacity: running ? 0.5 : 1,
                    transition: "color 150ms",
                  }}
                >
                  {v}
                </button>
              </span>
            ))}
            <span style={{ fontSize: 13, color: "var(--t-secondary)" }}>
              ] conjectures
            </span>
          </div>

          {/* Action buttons */}
          <div style={{ marginTop: 18, display: "flex", gap: 8 }}>
            <button
              onClick={handleRun}
              disabled={running || !domain.trim()}
              style={{
                flex: 1,
                height: 36,
                background:
                  running || !domain.trim() ? "var(--bg-hover)" : "var(--accent)",
                color: running || !domain.trim() ? "var(--t-tertiary)" : "#fff",
                border: "none",
                borderRadius: 6,
                fontSize: 13,
                fontWeight: 500,
                cursor: running || !domain.trim() ? "not-allowed" : "pointer",
                transition: "background 150ms, transform 100ms",
                fontFamily: "inherit",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 8,
              }}
              onMouseEnter={(e) => {
                if (!running && domain.trim()) {
                  e.currentTarget.style.background = "var(--accent-h)";
                  e.currentTarget.style.transform = "scale(0.99)";
                }
              }}
              onMouseLeave={(e) => {
                if (!running && domain.trim()) {
                  e.currentTarget.style.background = "var(--accent)";
                  e.currentTarget.style.transform = "scale(1)";
                }
              }}
            >
              {running && (
                <span
                  style={{
                    width: 13,
                    height: 13,
                    borderRadius: "50%",
                    border: "2px solid rgba(255,255,255,0.3)",
                    borderTopColor: "#fff",
                    display: "inline-block",
                    animation: "spin 0.8s linear infinite",
                  }}
                />
              )}
              {running ? "Running pipeline…" : "Run Pipeline"}
            </button>

            {(stage === "done" || stage === "error") && (
              <button
                onClick={handleReset}
                style={{
                  padding: "0 14px",
                  height: 36,
                  background: "var(--bg-input)",
                  border: "1px solid var(--border-s)",
                  borderRadius: 6,
                  fontSize: 12,
                  color: "var(--t-secondary)",
                  cursor: "pointer",
                  fontFamily: "inherit",
                  transition: "border-color 150ms",
                }}
                onMouseEnter={(e) =>
                  (e.currentTarget.style.borderColor = "var(--border-a)")
                }
                onMouseLeave={(e) =>
                  (e.currentTarget.style.borderColor = "var(--border-s)")
                }
              >
                Reset
              </button>
            )}
          </div>

          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>

          {/* Pipeline status + results */}
          {stage !== "idle" && (
            <Pipeline stage={stage} response={response} errorMsg={errorMsg} />
          )}
        </div>
      </section>

      {/* ── Experiments table ── */}
      <section>
        <ExperimentTable experiments={experiments ?? []} loading={isLoading} />
      </section>
    </div>
  );
}
