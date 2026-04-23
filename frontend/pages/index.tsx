import { useState, useCallback } from "react";
import useSWR from "swr";
import Pipeline from "../components/Pipeline";
import ExperimentTable, { ExperimentSummary } from "../components/ExperimentTable";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export default function Home() {
  const [refreshKey, setRefreshKey] = useState(0);

  const { data, isLoading } = useSWR<ExperimentSummary[]>(
    `${API}/api/v1/experiments?_r=${refreshKey}`,
    fetcher,
    { refreshInterval: 0, revalidateOnFocus: false }
  );

  const handleRunComplete = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  return (
    <div className="space-y-12">
      <section>
        <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100 mb-1">
          Germinal
        </h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm mb-8">
          AI-powered mathematical conjecture explorer — generate, formalize in Lean 4, and attempt automated proofs.
        </p>
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-4">
            New Experiment
          </h2>
          <Pipeline onRunComplete={handleRunComplete} />
        </div>
      </section>

      <section>
        <ExperimentTable experiments={data ?? []} loading={isLoading} />
      </section>
    </div>
  );
}
