import { useState } from "react";
import clsx from "clsx";
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
}

type SortKey = keyof Pick<ExperimentSummary, "timestamp" | "domain" | "duration_ms" | "proved">;

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function formatTimestamp(iso: string): string {
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
    if (key === sortKey) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const sorted = [...experiments]
    .filter((e) => {
      if (!filter) return true;
      const q = filter.toLowerCase();
      return e.domain.toLowerCase().includes(q) || e.conjecture.toLowerCase().includes(q);
    })
    .sort((a, b) => {
      const mul = sortDir === "asc" ? 1 : -1;
      if (sortKey === "timestamp") return mul * a.timestamp.localeCompare(b.timestamp);
      if (sortKey === "domain") return mul * a.domain.localeCompare(b.domain);
      if (sortKey === "duration_ms") return mul * (a.duration_ms - b.duration_ms);
      if (sortKey === "proved") return mul * (Number(a.proved) - Number(b.proved));
      return 0;
    });

  const SortTh = ({ label, k }: { label: string; k: SortKey }) => (
    <th
      className="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide cursor-pointer select-none hover:text-brand-500 whitespace-nowrap"
      onClick={() => handleSort(k)}
    >
      {label}
      {sortKey === k && (
        <span className="ml-1 text-brand-500">{sortDir === "asc" ? "↑" : "↓"}</span>
      )}
    </th>
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200">
          Experiments
          <span className="ml-2 text-sm font-normal text-slate-400 dark:text-slate-500">
            ({experiments.length})
          </span>
        </h2>
        <input
          type="search"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter by domain or conjecture…"
          className="px-3 py-1.5 text-sm rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500 w-72"
        />
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : sorted.length === 0 ? (
        <div className="text-center py-12 text-slate-400 dark:text-slate-500">
          {filter ? "No experiments match your filter." : "No experiments yet. Run the pipeline above."}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
              <tr>
                <SortTh label="Time" k="timestamp" />
                <SortTh label="Domain" k="domain" />
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                  Conjecture
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                  Lean
                </th>
                <SortTh label="Proved" k="proved" />
                <SortTh label="Duration" k="duration_ms" />
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
              {sorted.map((exp) => (
                <tr
                  key={exp.id}
                  className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
                >
                  <td className="px-4 py-3 text-xs font-mono text-slate-500 dark:text-slate-400 whitespace-nowrap">
                    {formatTimestamp(exp.timestamp)}
                  </td>
                  <td className="px-4 py-3 text-xs font-medium text-slate-700 dark:text-slate-300 whitespace-nowrap">
                    {exp.domain}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400 max-w-xs truncate">
                    {exp.conjecture}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={clsx(
                        "px-1.5 py-0.5 rounded text-xs font-mono",
                        exp.is_valid
                          ? "bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-300"
                          : "bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-300"
                      )}
                    >
                      {exp.is_valid ? "✓" : "✗"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={clsx(
                        "px-1.5 py-0.5 rounded text-xs font-mono",
                        exp.proved
                          ? "bg-green-50 dark:bg-green-900/30 text-green-600 dark:text-green-300"
                          : "bg-yellow-50 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-300"
                      )}
                    >
                      {exp.proved ? "proved" : "open"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs font-mono text-slate-400 dark:text-slate-500 whitespace-nowrap">
                    {formatDuration(exp.duration_ms)}
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/experiments/${exp.id}`}
                      className="text-xs text-brand-500 hover:text-brand-600 dark:hover:text-brand-400 font-medium"
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
