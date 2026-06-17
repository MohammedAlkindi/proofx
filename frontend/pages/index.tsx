import { useCallback, useEffect, useRef, useState } from "react";
import useSWR from "swr";
import Pipeline, { PipelineResponse, Stage } from "../components/Pipeline";
import ExperimentTable, { ExperimentSummary } from "../components/ExperimentTable";
import StatsBar from "../components/StatsBar";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const fetcher = (url: string) => fetch(url).then((r) => r.json());

const domains = [
  "number theory",
  "graph theory",
  "combinatorics",
  "group theory",
  "Ramsey theory",
  "elliptic curves",
  "additive combinatorics",
  "algebraic topology",
];

interface HomeProps {
  onSidebarBump?: () => void;
}

function formatElapsed(seconds: number) {
  if (seconds < 60) return `${seconds}s`;
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

export default function Home({ onSidebarBump }: HomeProps) {
  const [domain, setDomain] = useState("");
  const [n, setN] = useState(1);
  const [stage, setStage] = useState<Stage>("idle");
  const [response, setResponse] = useState<PipelineResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTime = useRef<number>(0);

  const { data: experiments, isLoading } = useSWR<ExperimentSummary[]>(
    `${API}/api/v1/experiments?_r=${refreshKey}`,
    fetcher,
    { refreshInterval: 0, revalidateOnFocus: false }
  );

  const running = stage === "generating" || stage === "formalizing" || stage === "verifying";

  useEffect(() => {
    if (!running) {
      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = null;
      setElapsed(0);
      return;
    }

    timerRef.current = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTime.current) / 1000));
    }, 1000);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [running]);

  useEffect(() => {
    if (!jobId) return;

    const poll = async () => {
      try {
        const res = await fetch(`${API}/api/v1/jobs/${jobId}`);
        const data = await res.json();

        if (data.status === "running") {
          setStage("verifying");
        } else if (data.status === "done") {
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null;
          setResponse(data.result);
          setStage("done");
          setRefreshKey((key) => key + 1);
          onSidebarBump?.();
        } else if (data.status === "error") {
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null;
          setErrorMsg(data.error ?? "Pipeline failed");
          setStage("error");
        }
      } catch {
        // Keep polling through transient API/network failures.
      }
    };

    pollRef.current = setInterval(poll, 2000);
    void poll();

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [jobId, onSidebarBump]);

  const handleRun = useCallback(async () => {
    if (!domain.trim() || running) return;

    startTime.current = Date.now();
    setStage("generating");
    setResponse(null);
    setErrorMsg("");
    setJobId(null);

    try {
      setTimeout(() => setStage("formalizing"), 1200);

      const res = await fetch(`${API}/api/v1/pipeline`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ domain: domain.trim(), n }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail ?? res.statusText);
      }

      const data = await res.json();
      setJobId(data.job_id);
      setStage("verifying");
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : String(err));
      setStage("error");
    }
  }, [domain, n, running]);

  const handleReset = () => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = null;
    setStage("idle");
    setResponse(null);
    setErrorMsg("");
    setJobId(null);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "calc(var(--density-gap) * 1.4)" }}>
      <section style={{ display: "grid", gap: "var(--density-gap)", gridTemplateColumns: "minmax(0, 1.25fr) minmax(260px, 0.75fr)" }}>
        <div>
          <span className="label">Research pipeline</span>
          <h1
            style={{
              color: "var(--t-primary)",
              fontSize: 30,
              fontWeight: 700,
              letterSpacing: 0,
              lineHeight: 1.15,
              margin: "8px 0 0",
            }}
          >
            Generate, formalize, verify, and snapshot mathematical conjectures.
          </h1>
          <p style={{ color: "var(--t-secondary)", fontSize: 14, lineHeight: 1.7, margin: "12px 0 0", maxWidth: 690 }}>
            Germinal treats unproved and unrefuted claims as unknowns. Lean typechecking,
            automated proof attempts, and counterexample searches remain visible as separate signals.
          </p>
        </div>
        <StatsBar />
      </section>

      <section className="panel" style={{ padding: "var(--density-pad)" }}>
        <div style={{ display: "grid", gap: "var(--density-gap)", gridTemplateColumns: "minmax(0, 1fr) auto" }}>
          <div>
            <label className="label" htmlFor="domain">
              Domain
            </label>
            <input
              className="control"
              disabled={running}
              id="domain"
              onChange={(event) => setDomain(event.target.value)}
              onKeyDown={(event) => event.key === "Enter" && handleRun()}
              placeholder="number theory, graph theory, elliptic curves"
              style={{
                display: "block",
                fontSize: 14,
                height: 42,
                marginTop: 8,
                opacity: running ? 0.65 : 1,
                padding: "0 13px",
                width: "100%",
              }}
              type="text"
              value={domain}
            />
          </div>

          <div style={{ minWidth: 180 }}>
            <span className="label">Conjectures</span>
            <div style={{ display: "flex", gap: 4, marginTop: 8 }}>
              {[1, 2, 3].map((value) => (
                <button
                  className={n === value ? "primary-button" : "secondary-button"}
                  disabled={running}
                  key={value}
                  onClick={() => setN(value)}
                  style={{ height: 42, width: 48 }}
                >
                  {value}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 14 }}>
          {domains.map((item) => {
            const selected = domain === item;
            return (
              <button
                key={item}
                disabled={running}
                onClick={() => setDomain(item)}
                style={{
                  background: selected ? "var(--accent-bg)" : "var(--bg-input)",
                  border: `1px solid ${selected ? "var(--accent)" : "var(--border-s)"}`,
                  borderRadius: 999,
                  color: selected ? "var(--accent)" : "var(--t-secondary)",
                  cursor: running ? "default" : "pointer",
                  fontSize: 12,
                  fontWeight: 600,
                  opacity: running ? 0.55 : 1,
                  padding: "5px 10px",
                }}
              >
                {item}
              </button>
            );
          })}
        </div>

        <div style={{ alignItems: "center", display: "flex", gap: 10, marginTop: 18, flexWrap: "wrap" }}>
          <button
            className="primary-button"
            disabled={running || !domain.trim()}
            onClick={handleRun}
            style={{ height: 38, minWidth: 154, padding: "0 16px" }}
          >
            {running && (
              <span
                className="anim-spin"
                style={{
                  border: "2px solid rgba(255,255,255,0.35)",
                  borderRadius: "50%",
                  borderTopColor: "#fff",
                  height: 14,
                  marginRight: 8,
                  width: 14,
                }}
              />
            )}
            {running ? "Running" : "Run pipeline"}
          </button>

          {(stage === "done" || stage === "error") && (
            <button className="secondary-button" onClick={handleReset} style={{ height: 38, padding: "0 14px" }}>
              Reset
            </button>
          )}

          <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
            {jobId && (
              <span className="mono muted" style={{ fontSize: 11 }}>
                job {jobId.slice(0, 12)}
              </span>
            )}
            {running && elapsed > 0 && (
              <span className="mono" style={{ color: elapsed > 60 ? "var(--warning)" : "var(--accent)", fontSize: 11 }}>
                elapsed {formatElapsed(elapsed)}
              </span>
            )}
          </div>
        </div>

        {stage !== "idle" && (
          <div style={{ marginTop: "var(--density-gap)" }}>
            <Pipeline stage={stage} response={response} errorMsg={errorMsg} />
          </div>
        )}
      </section>

      <ExperimentTable experiments={experiments ?? []} loading={isLoading} />
    </div>
  );
}
