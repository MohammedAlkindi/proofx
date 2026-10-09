interface ProofXBenchmarkRun {
  policy: string;
  seed: number;
  ledger: string;
  rare_hits: number;
  rare_recall: number;
  min_ratio: number;
  median_candidate: number;
  elapsed_s: number;
}

interface ProofXBenchmarkManifest {
  schema_version: string;
  config: { max_n: number; budget: number; seeds: number[] };
  reference_size: number;
  rare_set_size: number;
  runs: ProofXBenchmarkRun[];
  provenance: Record<string, unknown>;
}

interface ProofXBenchmarkRow {
  candidate: number;
  actual_partitions: number;
  expected_partitions: number;
  ratio: number;
  witness: [number, number] | null;
}
