import { useRouter } from "next/router";
import useSWR from "swr";
import Link from "next/link";
import { CodeBlock } from "../../components/Pipeline";

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

function MetaItem({ label, value }: { label: string; value: string | number }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: 12,
        padding: "7px 0",
        borderBottom: "1px solid var(--border-s)",
      }}
    >
      <span
        style={{
          fontSize: 10,
          fontWeight: 500,
          letterSpacing: "0.05em",
          textTransform: "uppercase",
          color: "var(--t-tertiary)",
          minWidth: 96,
          paddingTop: 1,
          flexShrink: 0,
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontSize: 12,
          fontFamily: "JetBrains Mono, monospace",
          color: "var(--t-secondary)",
          wordBreak: "break-all",
        }}
      >
        {String(value)}
      </span>
    </div>
  );
}

function Badge({
  ok,
  trueLabel,
  falseLabel,
}: {
  ok: boolean;
  trueLabel: string;
  falseLabel: string;
}) {
  return (
    <span
      style={{
        fontFamily: "JetBrains Mono, monospace",
        fontSize: 10,
        fontWeight: 600,
        padding: "2px 8px",
        borderRadius: 4,
        textTransform: "uppercase",
        letterSpacing: "0.06em",
        background: ok ? "rgba(16,185,129,0.1)" : "rgba(239,68,68,0.1)",
        color: ok ? "var(--success)" : "var(--danger)",
        border: `1px solid ${ok ? "rgba(16,185,129,0.2)" : "rgba(239,68,68,0.2)"}`,
      }}
    >
      {ok ? trueLabel : falseLabel}
    </span>
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
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          minHeight: 320,
        }}
      >
        <div
          style={{
            width: 22,
            height: 22,
            borderRadius: "50%",
            border: "2px solid var(--accent)",
            borderTopColor: "transparent",
            animation: "spin 0.8s linear infinite",
          }}
        />
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div
        style={{
          textAlign: "center",
          padding: "64px 0",
          display: "flex",
          flexDirection: "column",
          gap: 12,
          alignItems: "center",
        }}
      >
        <span style={{ fontSize: 13, color: "var(--t-tertiary)" }}>
          Experiment not found.
        </span>
        <Link
          href="/"
          style={{ fontSize: 12, color: "var(--accent)", textDecoration: "none" }}
        >
          ← Back to explorer
        </Link>
      </div>
    );
  }

  const { extra } = data;
  const badge: "proved" | "sorry" | "error" = data.proved
    ? "proved"
    : data.is_valid
    ? "sorry"
    : "error";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Breadcrumb */}
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <Link
          href="/"
          style={{ fontSize: 12, color: "var(--accent)", textDecoration: "none" }}
        >
          ← Experiments
        </Link>
        <span style={{ color: "var(--t-tertiary)", fontSize: 12 }}>/</span>
        <span
          style={{
            fontFamily: "JetBrains Mono, monospace",
            fontSize: 11,
            color: "var(--t-tertiary)",
          }}
        >
          {data.id.slice(0, 20)}…
        </span>
      </div>

      {/* Top metadata bar */}
      <div
        style={{
          background: "var(--bg-card)",
          border: "1px solid var(--border-s)",
          borderRadius: 8,
          padding: "12px 16px",
          display: "flex",
          alignItems: "center",
          gap: 16,
          flexWrap: "wrap",
        }}
      >
        <span
          style={{
            fontSize: 10,
            fontWeight: 600,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "var(--accent)",
          }}
        >
          {data.domain}
        </span>
        <span style={{ color: "var(--border-a)", fontSize: 12 }}>·</span>
        <span
          style={{
            fontFamily: "JetBrains Mono, monospace",
            fontSize: 11,
            color: "var(--t-tertiary)",
          }}
        >
          {data.model_used}
        </span>
        <span style={{ color: "var(--border-a)", fontSize: 12 }}>·</span>
        <span
          style={{
            fontFamily: "JetBrains Mono, monospace",
            fontSize: 11,
            color: "var(--t-tertiary)",
          }}
        >
          {data.duration_ms.toLocaleString()}ms
        </span>
        <span style={{ color: "var(--border-a)", fontSize: 12 }}>·</span>
        <span
          style={{
            fontFamily: "JetBrains Mono, monospace",
            fontSize: 11,
            color: "var(--t-tertiary)",
          }}
        >
          {new Date(data.timestamp).toLocaleString()}
        </span>
        <span style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
          <Badge ok={data.is_valid} trueLabel="lean ✓" falseLabel="lean ✗" />
          <Badge ok={data.proved} trueLabel="proved" falseLabel="open" />
        </span>
      </div>

      {/* Split panel */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1.5fr", gap: 16 }}>
        {/* Left: conjecture + metadata */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Conjecture */}
          <div
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border-s)",
              borderRadius: 8,
              padding: 20,
            }}
          >
            <span
              style={{
                fontSize: 10,
                fontWeight: 500,
                letterSpacing: "0.1em",
                textTransform: "uppercase",
                color: "var(--t-tertiary)",
                display: "block",
                marginBottom: 10,
              }}
            >
              Conjecture
            </span>
            <p
              style={{
                fontSize: 14,
                lineHeight: 1.6,
                color: "var(--t-primary)",
                letterSpacing: "-0.01em",
              }}
            >
              {data.conjecture}
            </p>
          </div>

          {/* Metadata */}
          <div
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border-s)",
              borderRadius: 8,
              padding: "4px 16px 8px",
            }}
          >
            <MetaItem label="ID" value={data.id} />
            <MetaItem label="Timestamp" value={data.timestamp} />
            <MetaItem label="Model" value={data.model_used} />
            <MetaItem label="Duration" value={`${data.duration_ms}ms`} />
            {typeof extra.confidence_estimate === "number" && (
              <MetaItem
                label="Confidence"
                value={`${((extra.confidence_estimate as number) * 100).toFixed(0)}%`}
              />
            )}
            {typeof extra.subfield === "string" && extra.subfield && (
              <MetaItem label="Subfield" value={extra.subfield as string} />
            )}
            {typeof extra.motivation === "string" && extra.motivation && (
              <MetaItem label="Motivation" value={extra.motivation as string} />
            )}
            {Array.isArray(extra.tags) && extra.tags.length > 0 && (
              <div
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 8,
                  padding: "7px 0",
                }}
              >
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 500,
                    letterSpacing: "0.05em",
                    textTransform: "uppercase",
                    color: "var(--t-tertiary)",
                    minWidth: 96,
                    paddingTop: 1,
                    flexShrink: 0,
                  }}
                >
                  Tags
                </span>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                  {(extra.tags as string[]).map((tag) => (
                    <span
                      key={tag}
                      style={{
                        padding: "1px 7px",
                        background: "var(--accent-bg)",
                        color: "var(--accent)",
                        borderRadius: 4,
                        fontSize: 11,
                        fontFamily: "JetBrains Mono, monospace",
                        border: "1px solid rgba(124,58,237,0.2)",
                      }}
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right: Lean 4 code */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {data.lean_code ? (
            <CodeBlock code={data.lean_code} badge={badge} />
          ) : (
            <div
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border-s)",
                borderRadius: 8,
                padding: 24,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--t-tertiary)",
                fontSize: 12,
              }}
            >
              No Lean 4 formalization available.
            </div>
          )}

          {data.proved && data.final_proof && (
            <div>
              <span
                style={{
                  fontSize: 10,
                  fontWeight: 500,
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                  color: "var(--t-tertiary)",
                  display: "block",
                  marginBottom: 8,
                }}
              >
                Automated Proof
              </span>
              <CodeBlock code={data.final_proof} badge="proved" />
            </div>
          )}

          {!data.proved && (
            <div
              style={{
                padding: "12px 16px",
                borderRadius: 8,
                background: "rgba(245,158,11,0.06)",
                border: "1px solid rgba(245,158,11,0.2)",
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <span style={{ fontSize: 13, color: "var(--warning)" }}>
                This conjecture remains open — no automated proof was found.
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
