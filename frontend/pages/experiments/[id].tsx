import { useState } from "react";
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
          minWidth: 110,
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

function Badge({ ok, trueLabel, falseLabel }: { ok: boolean; trueLabel: string; falseLabel: string }) {
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

// ── Export button ──────────────────────────────────────────────────────────

function ExportButton({ id, fmt, label }: { id: string; fmt: string; label: string }) {
  const [loading, setLoading] = useState(false);

  const handleExport = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/experiments/${id}/export?fmt=${fmt}`);
      const text = await res.text();
      const ext = fmt === "latex" ? "tex" : "lean";
      const blob = new Blob([text], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `experiment_${id.slice(0, 8)}.${ext}`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleExport}
      disabled={loading}
      style={{
        padding: "5px 12px",
        fontSize: 11,
        borderRadius: 5,
        border: "1px solid var(--border-s)",
        background: "var(--bg-input)",
        color: "var(--t-secondary)",
        cursor: loading ? "default" : "pointer",
        fontFamily: "JetBrains Mono, monospace",
        opacity: loading ? 0.6 : 1,
        transition: "border-color 150ms",
      }}
      onMouseEnter={(e) => !loading && (e.currentTarget.style.borderColor = "var(--accent)")}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border-s)")}
    >
      {loading ? "…" : label}
    </button>
  );
}

// ── Annotation form ────────────────────────────────────────────────────────

function AnnotationForm({ experimentId }: { experimentId: string }) {
  const [interesting, setInteresting] = useState(false);
  const [notes, setNotes]             = useState("");
  const [proof, setProof]             = useState("");
  const [saved, setSaved]             = useState(false);
  const [saving, setSaving]           = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await fetch(`${API}/api/v1/experiments/${experimentId}/annotate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          interesting,
          notes,
          correct_proof: proof.trim() || null,
          annotator: "human",
        }),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border-s)",
        borderRadius: 8,
        padding: 20,
        display: "flex",
        flexDirection: "column",
        gap: 14,
      }}
    >
      <span
        style={{
          fontSize: 10,
          fontWeight: 500,
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          color: "var(--t-tertiary)",
        }}
      >
        Annotate
      </span>

      <label
        style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}
      >
        <input
          type="checkbox"
          checked={interesting}
          onChange={(e) => setInteresting(e.target.checked)}
          style={{ accentColor: "var(--accent)", width: 14, height: 14 }}
        />
        <span style={{ fontSize: 13, color: "var(--t-secondary)" }}>Mark as interesting</span>
      </label>

      <div>
        <span style={{ fontSize: 11, color: "var(--t-tertiary)", display: "block", marginBottom: 5 }}>Notes</span>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Any observations, references, or ideas…"
          rows={3}
          style={{
            width: "100%",
            padding: "8px 10px",
            fontSize: 12,
            background: "var(--bg-input)",
            border: "1px solid var(--border-s)",
            borderRadius: 5,
            color: "var(--t-primary)",
            fontFamily: "inherit",
            resize: "vertical",
            outline: "none",
          }}
        />
      </div>

      <div>
        <span style={{ fontSize: 11, color: "var(--t-tertiary)", display: "block", marginBottom: 5 }}>
          Correct proof (Lean 4, optional)
        </span>
        <textarea
          value={proof}
          onChange={(e) => setProof(e.target.value)}
          placeholder="Paste a correct Lean 4 proof if you have one…"
          rows={4}
          style={{
            width: "100%",
            padding: "8px 10px",
            fontSize: 12,
            background: "#0d0d0d",
            border: "1px solid var(--border-s)",
            borderRadius: 5,
            color: "#d4d4d4",
            fontFamily: "JetBrains Mono, monospace",
            resize: "vertical",
            outline: "none",
          }}
        />
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <button
          onClick={handleSave}
          disabled={saving}
          style={{
            padding: "7px 16px",
            background: saving ? "var(--bg-hover)" : "var(--accent)",
            color: saving ? "var(--t-tertiary)" : "#fff",
            border: "none",
            borderRadius: 5,
            fontSize: 12,
            fontWeight: 500,
            cursor: saving ? "default" : "pointer",
            fontFamily: "inherit",
            transition: "background 150ms",
          }}
        >
          {saving ? "Saving…" : "Save annotation"}
        </button>
        {saved && (
          <span style={{ fontSize: 12, color: "var(--success)", fontFamily: "JetBrains Mono, monospace" }}>
            Saved ✓
          </span>
        )}
      </div>
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────

export default function ExperimentDetailPage() {
  const router = useRouter();
  const { id } = router.query;

  const { data, isLoading, error } = useSWR<ExperimentDetail>(
    id ? `${API}/api/v1/experiments/${id}` : null,
    fetcher
  );

  if (isLoading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: 320 }}>
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
      <div style={{ textAlign: "center", padding: "64px 0", display: "flex", flexDirection: "column", gap: 12, alignItems: "center" }}>
        <span style={{ fontSize: 13, color: "var(--t-tertiary)" }}>Experiment not found.</span>
        <Link href="/" style={{ fontSize: 12, color: "var(--accent)", textDecoration: "none" }}>
          ← Back to explorer
        </Link>
      </div>
    );
  }

  const { extra } = data;
  const badge: "proved" | "sorry" | "error" = data.proved ? "proved" : data.is_valid ? "sorry" : "error";
  const complexity = extra.complexity as Record<string, number> | undefined;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Breadcrumb */}
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <Link href="/" style={{ fontSize: 12, color: "var(--accent)", textDecoration: "none" }}>
          ← Experiments
        </Link>
        <span style={{ color: "var(--t-tertiary)", fontSize: 12 }}>/</span>
        <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 11, color: "var(--t-tertiary)" }}>
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
        <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--accent)" }}>
          {data.domain}
        </span>
        <span style={{ color: "var(--border-a)", fontSize: 12 }}>·</span>
        <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 11, color: "var(--t-tertiary)" }}>
          {data.model_used}
        </span>
        <span style={{ color: "var(--border-a)", fontSize: 12 }}>·</span>
        <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 11, color: "var(--t-tertiary)" }}>
          {data.duration_ms.toLocaleString()}ms
        </span>
        <span style={{ color: "var(--border-a)", fontSize: 12 }}>·</span>
        <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 11, color: "var(--t-tertiary)" }}>
          {new Date(data.timestamp).toLocaleString()}
        </span>

        {/* Export buttons */}
        <div style={{ marginLeft: "auto", display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
          <ExportButton id={data.id} fmt="lean" label="↓ .lean" />
          <ExportButton id={data.id} fmt="latex" label="↓ .tex" />
          <Badge ok={data.is_valid} trueLabel="lean ✓" falseLabel="lean ✗" />
          <Badge ok={data.proved} trueLabel="proved" falseLabel="open" />
        </div>
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
            <p style={{ fontSize: 14, lineHeight: 1.6, color: "var(--t-primary)", letterSpacing: "-0.01em" }}>
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
              <MetaItem label="Confidence" value={`${((extra.confidence_estimate as number) * 100).toFixed(0)}%`} />
            )}
            {typeof extra.novelty_score === "number" && (
              <MetaItem label="Novelty" value={`${((extra.novelty_score as number) * 100).toFixed(0)}%`} />
            )}
            {typeof extra.proof_strategy === "string" && (
              <MetaItem label="Strategy" value={extra.proof_strategy as string} />
            )}
            {complexity && (
              <>
                <MetaItem label="Formalizability" value={`${complexity.formalizability ?? "?"} / 5`} />
                <MetaItem label="Proof difficulty" value={`${complexity.proof_difficulty ?? "?"} / 5`} />
              </>
            )}
            {typeof extra.subfield === "string" && extra.subfield && (
              <MetaItem label="Subfield" value={extra.subfield as string} />
            )}
            {typeof extra.motivation === "string" && extra.motivation && (
              <MetaItem label="Motivation" value={extra.motivation as string} />
            )}
            {Array.isArray(extra.tags) && extra.tags.length > 0 && (
              <div style={{ display: "flex", alignItems: "flex-start", gap: 8, padding: "7px 0" }}>
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 500,
                    letterSpacing: "0.05em",
                    textTransform: "uppercase",
                    color: "var(--t-tertiary)",
                    minWidth: 110,
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

          {/* Annotation form */}
          <AnnotationForm experimentId={data.id} />
        </div>

        {/* Right: Lean 4 code + proof */}
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
