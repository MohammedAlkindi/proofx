import { useRouter } from "next/router";
import useSWR from "swr";
import Link from "next/link";
import clsx from "clsx";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface ExperimentDetail {
  id: string;
  timestamp: string;
  domain: string;
  conjecture: string;
  lean_code: string;
  is_valid: boolean;
  proved: boolean;
  final_proof: string | null;
  model_used: string;
  duration_ms: number;
  extra: Record<string, unknown>;
}

const fetcher = (url: string) => fetch(url).then((r) => r.json());

function CodeBlock({ code, label }: { code: string; label: string }) {
  return (
    <div className="space-y-1">
      <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
        {label}
      </div>
      <pre className="overflow-x-auto bg-slate-950 dark:bg-slate-900 text-green-300 text-xs p-4 rounded-lg border border-slate-700 font-mono leading-relaxed whitespace-pre-wrap">
        {code}
      </pre>
    </div>
  );
}

function Badge({ ok, trueLabel, falseLabel }: { ok: boolean; trueLabel: string; falseLabel: string }) {
  return (
    <span
      className={clsx(
        "px-2 py-0.5 rounded text-xs font-semibold",
        ok
          ? "bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300"
          : "bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300"
      )}
    >
      {ok ? trueLabel : falseLabel}
    </span>
  );
}

function MetaRow({ label, value }: { label: string; value: string | number | boolean }) {
  return (
    <div className="flex items-start gap-3 py-2 border-b border-slate-100 dark:border-slate-800 last:border-0">
      <span className="text-xs font-medium text-slate-500 dark:text-slate-400 w-36 shrink-0">{label}</span>
      <span className="text-xs font-mono text-slate-700 dark:text-slate-300 break-all">
        {String(value)}
      </span>
    </div>
  );
}

export default function ExperimentDetailPage() {
  const router = useRouter();
  const { id } = router.query;

  const { data, isLoading, error } = useSWR<ExperimentDetail>(
    id ? `${API}/api/v1/experiments/${id}` : null,
    fetcher
  );

  if (isLoading) {
    return (
      <div className="flex justify-center py-24">
        <div className="w-10 h-10 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="text-center py-24 space-y-3">
        <p className="text-slate-400 dark:text-slate-500">Experiment not found.</p>
        <Link href="/" className="text-brand-500 text-sm hover:underline">
          ← Back to explorer
        </Link>
      </div>
    );
  }

  const { extra, ...core } = data;

  return (
    <div className="space-y-8 max-w-4xl">
      <div className="flex items-center gap-3">
        <Link href="/" className="text-sm text-brand-500 hover:text-brand-600 dark:hover:text-brand-400">
          ← Experiments
        </Link>
        <span className="text-slate-300 dark:text-slate-600">/</span>
        <span className="text-xs font-mono text-slate-400 dark:text-slate-500 truncate">{data.id}</span>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold text-brand-500 uppercase tracking-wide mb-1">{data.domain}</p>
            <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              {data.conjecture}
            </h1>
          </div>
          <div className="flex gap-2 shrink-0">
            <Badge ok={data.is_valid} trueLabel="Lean ✓" falseLabel="Lean ✗" />
            <Badge ok={data.proved} trueLabel="Proved" falseLabel="Open" />
          </div>
        </div>

        <div className="bg-slate-50 dark:bg-slate-900 rounded-lg p-4">
          <MetaRow label="Experiment ID" value={core.id} />
          <MetaRow label="Timestamp" value={core.timestamp} />
          <MetaRow label="Model" value={core.model_used} />
          <MetaRow label="Duration" value={`${core.duration_ms}ms`} />
          {typeof extra.confidence_estimate === "number" && (
            <MetaRow label="Confidence" value={`${(extra.confidence_estimate as number * 100).toFixed(0)}%`} />
          )}
          {typeof extra.subfield === "string" && extra.subfield && (
            <MetaRow label="Subfield" value={extra.subfield as string} />
          )}
          {typeof extra.motivation === "string" && extra.motivation && (
            <MetaRow label="Motivation" value={extra.motivation as string} />
          )}
          {Array.isArray(extra.tags) && extra.tags.length > 0 && (
            <div className="flex items-start gap-3 py-2">
              <span className="text-xs font-medium text-slate-500 dark:text-slate-400 w-36 shrink-0">Tags</span>
              <div className="flex flex-wrap gap-1.5">
                {(extra.tags as string[]).map((tag) => (
                  <span
                    key={tag}
                    className="px-2 py-0.5 bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 rounded text-xs font-mono"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {data.lean_code && <CodeBlock code={data.lean_code} label="Lean 4 Formalization" />}

        {data.proved && data.final_proof && (
          <CodeBlock code={data.final_proof} label="Automated Proof" />
        )}

        {!data.proved && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800">
            <span className="text-yellow-600 dark:text-yellow-400 text-sm">
              This conjecture remains open — no automated proof was found.
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
