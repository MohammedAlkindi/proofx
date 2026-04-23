import { useState } from "react";
import clsx from "clsx";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Stage = "idle" | "generating" | "formalizing" | "verifying" | "done" | "error";

interface PipelineResult {
  experiment_id: string;
  conjecture: string;
  is_valid: boolean;
  proved: boolean;
  duration_ms: number;
  git_sha: string | null;
  snapshot_error?: string;
}

interface PipelineResponse {
  domain: string;
  total_duration_ms: number;
  results: PipelineResult[];
}

const SUGGESTED_DOMAINS = [
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

const STAGE_LABELS: Record<Stage, string> = {
  idle: "Ready",
  generating: "Generating conjectures…",
  formalizing: "Formalizing in Lean 4…",
  verifying: "Attempting proofs…",
  done: "Pipeline complete",
  error: "Pipeline failed",
};

function StageBar({ stage }: { stage: Stage }) {
  const stages: Stage[] = ["generating", "formalizing", "verifying", "done"];
  const activeIdx = stages.indexOf(stage);

  return (
    <div className="flex items-center gap-2 my-4">
      {stages.map((s, i) => (
        <div key={s} className="flex items-center gap-2">
          <div
            className={clsx(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all",
              i < activeIdx && "bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300",
              i === activeIdx && "bg-brand-100 dark:bg-brand-900/40 text-brand-700 dark:text-brand-300 animate-pulse",
              i > activeIdx && "bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-500"
            )}
          >
            {i < activeIdx && <span>✓</span>}
            {i === activeIdx && <span className="w-2 h-2 rounded-full bg-brand-500 inline-block animate-ping" />}
            {STAGE_LABELS[s]}
          </div>
          {i < stages.length - 1 && (
            <div className={clsx("h-px w-6", i < activeIdx ? "bg-green-400" : "bg-slate-200 dark:bg-slate-700")} />
          )}
        </div>
      ))}
    </div>
  );
}

function ResultCard({ result }: { result: PipelineResult }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-slate-200 dark:border-slate-700 rounded-lg p-4 space-y-2">
      <div className="flex items-start justify-between gap-4">
        <p className="text-sm font-medium text-slate-800 dark:text-slate-200 flex-1">
          {result.conjecture}
        </p>
        <div className="flex gap-2 shrink-0">
          <span
            className={clsx(
              "px-2 py-0.5 rounded text-xs font-mono",
              result.is_valid
                ? "bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300"
                : "bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300"
            )}
          >
            {result.is_valid ? "Lean ✓" : "Lean ✗"}
          </span>
          <span
            className={clsx(
              "px-2 py-0.5 rounded text-xs font-mono",
              result.proved
                ? "bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300"
                : "bg-yellow-100 dark:bg-yellow-900/40 text-yellow-700 dark:text-yellow-300"
            )}
          >
            {result.proved ? "Proved ✓" : "Unproved"}
          </span>
        </div>
      </div>
      <div className="text-xs text-slate-400 dark:text-slate-500 font-mono">
        {result.duration_ms}ms
        {result.git_sha && (
          <span className="ml-3">
            sha: <span className="text-brand-500">{result.git_sha.slice(0, 8)}</span>
          </span>
        )}
      </div>
      <button
        onClick={() => setExpanded(!expanded)}
        className="text-xs text-brand-500 hover:text-brand-600 dark:hover:text-brand-400"
      >
        {expanded ? "▲ Hide ID" : "▼ Show experiment ID"}
      </button>
      {expanded && (
        <p className="font-mono text-xs text-slate-500 dark:text-slate-400 break-all">
          {result.experiment_id}
        </p>
      )}
    </div>
  );
}

export default function Pipeline({ onRunComplete }: { onRunComplete?: () => void }) {
  const [domain, setDomain] = useState("");
  const [n, setN] = useState(1);
  const [stage, setStage] = useState<Stage>("idle");
  const [response, setResponse] = useState<PipelineResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState("");

  const handleRun = async () => {
    if (!domain.trim()) return;
    setStage("generating");
    setResponse(null);
    setErrorMsg("");

    try {
      setStage("generating");
      await new Promise((r) => setTimeout(r, 200));
      setStage("formalizing");
      await new Promise((r) => setTimeout(r, 200));
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
      onRunComplete?.();
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : String(err));
      setStage("error");
    }
  };

  const running = stage === "generating" || stage === "formalizing" || stage === "verifying";

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1 text-slate-700 dark:text-slate-300">
            Mathematical domain
          </label>
          <input
            type="text"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            placeholder="e.g. number theory"
            disabled={running}
            className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-50"
          />
          <div className="flex flex-wrap gap-2 mt-2">
            {SUGGESTED_DOMAINS.map((d) => (
              <button
                key={d}
                onClick={() => setDomain(d)}
                disabled={running}
                className="px-2.5 py-1 text-xs rounded-full border border-slate-300 dark:border-slate-600 hover:border-brand-400 hover:text-brand-600 dark:hover:text-brand-400 transition-colors disabled:opacity-40"
              >
                {d}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-4">
          <label className="text-sm font-medium text-slate-700 dark:text-slate-300">Conjectures:</label>
          {[1, 2, 3].map((v) => (
            <button
              key={v}
              onClick={() => setN(v)}
              disabled={running}
              className={clsx(
                "w-8 h-8 rounded-full text-sm font-mono font-bold transition-colors disabled:opacity-40",
                n === v
                  ? "bg-brand-500 text-white"
                  : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700"
              )}
            >
              {v}
            </button>
          ))}
        </div>

        <button
          onClick={handleRun}
          disabled={running || !domain.trim()}
          className="px-6 py-2.5 bg-brand-500 hover:bg-brand-600 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {running ? "Running…" : "Run Pipeline"}
        </button>
      </div>

      {stage !== "idle" && <StageBar stage={stage} />}

      {stage === "error" && (
        <div className="p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm">
          {errorMsg}
        </div>
      )}

      {response && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-slate-700 dark:text-slate-300">Results</h3>
            <span className="text-xs text-slate-400 dark:text-slate-500 font-mono">
              total: {response.total_duration_ms}ms
            </span>
          </div>
          {response.results.map((r) => (
            <ResultCard key={r.experiment_id} result={r} />
          ))}
        </div>
      )}
    </div>
  );
}
