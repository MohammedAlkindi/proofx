import useSWR from "swr";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const fetcher = (url: string) => fetch(url).then((r) => r.json());

interface StatsResponse {
  total_experiments: number;
  proved_count: number;
  valid_count: number;
}

interface StatItem {
  label: string;
  value: string | number;
  accent?: boolean;
}

function Stat({ label, value, accent }: StatItem) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 2,
        padding: "0 20px",
      }}
    >
      <span
        style={{
          fontFamily: "JetBrains Mono, monospace",
          fontSize: 18,
          fontWeight: 600,
          color: accent ? "var(--accent)" : "var(--t-primary)",
          letterSpacing: "-0.02em",
        }}
      >
        {value}
      </span>
      <span
        style={{
          fontSize: 10,
          fontWeight: 500,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          color: "var(--t-tertiary)",
        }}
      >
        {label}
      </span>
    </div>
  );
}

function Divider() {
  return (
    <div
      style={{
        width: 1,
        height: 32,
        background: "var(--border-s)",
        flexShrink: 0,
      }}
    />
  );
}

export default function StatsBar() {
  const { data } = useSWR<StatsResponse>(`${API}/api/v1/stats`, fetcher, {
    refreshInterval: 30000,
    revalidateOnFocus: false,
  });

  if (!data || data.total_experiments === 0) return null;

  const openCount = data.valid_count - data.proved_count;
  const successRate =
    data.total_experiments > 0
      ? Math.round((data.proved_count / data.total_experiments) * 100)
      : 0;

  return (
    <div
      className="anim-slide-up"
      style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border-s)",
        borderRadius: 10,
        padding: "14px 24px",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 0,
        flexWrap: "wrap",
      }}
    >
      <Stat label="Experiments" value={data.total_experiments} />
      <Divider />
      <Stat label="Proved" value={data.proved_count} accent />
      <Divider />
      <Stat label="Open" value={openCount} />
      <Divider />
      <Stat label="Success Rate" value={`${successRate}%`} accent={successRate >= 50} />
    </div>
  );
}
