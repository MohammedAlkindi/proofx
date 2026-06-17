import { useState, useRef } from "react";
import { useRouter } from "next/router";
import useSWR from "swr";
import Link from "next/link";
import { CodeBlock } from "../../components/Pipeline";
import MathDisplay from "../../components/MathDisplay";

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

interface LineageNode {
  id: string;
  conjecture: string;
  domain: string;
  proved: boolean;
  is_valid: boolean;
}

interface LineageData {
  experiment_id: string;
  parent: LineageNode | null;
  children: LineageNode[];
}

interface MethodResult {
  method: string;          // "llm" | "symbolic" | "wolfram"
  applicable: boolean;
  found: boolean;
  counterexample: string | null;
  reasoning: string;
}

interface CounterexampleData {
  experiment_id: string;
  found: boolean;
  counterexample: string | null;
  reasoning: string;
  // Present only in dual-search records (new format)
  llm_result?: MethodResult;
  symbolic_result?: MethodResult;
  wolfram_result?: MethodResult;
}

const fetcher = (url: string) => fetch(url).then((r) => r.json());

// ── Utility components ─────────────────────────────────────────────────────

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

      <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
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

// ── Interactive Lean editor ────────────────────────────────────────────────

interface VerifyResult {
  proved: boolean;
  final_proof: string | null;
  failure_reason: string | null;
  attempts: Array<{ attempt: string | number; success: boolean; error: string }>;
}

function LeanEditor({ initialCode }: { initialCode: string }) {
  const [code, setCode]         = useState(initialCode);
  const [verifying, setVerifying] = useState(false);
  const [result, setResult]     = useState<VerifyResult | null>(null);
  const [error, setError]       = useState("");
  const textareaRef             = useRef<HTMLTextAreaElement>(null);

  const handleVerify = async () => {
    if (!code.trim() || verifying) return;
    setVerifying(true);
    setResult(null);
    setError("");
    try {
      const res = await fetch(`${API}/api/v1/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lean_code: code, strategy: "claude_standard" }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail ?? res.statusText);
      }
      const data: VerifyResult = await res.json();
      setResult(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setVerifying(false);
    }
  };

  const handleTabKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key !== "Tab") return;
    e.preventDefault();
    const ta = textareaRef.current;
    if (!ta) return;
    const start = ta.selectionStart;
    const end   = ta.selectionEnd;
    const newCode = code.slice(0, start) + "  " + code.slice(end);
    setCode(newCode);
    requestAnimationFrame(() => {
      ta.selectionStart = ta.selectionEnd = start + 2;
    });
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
      {/* Editor header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "7px 12px",
          background: "#111",
          border: "1px solid #222",
          borderBottom: "none",
          borderRadius: "8px 8px 0 0",
        }}
      >
        <span
          style={{
            fontSize: 10,
            fontWeight: 500,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "var(--t-tertiary)",
          }}
        >
          Interactive Editor
        </span>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          {result && (
            <span
              style={{
                fontSize: 10,
                fontFamily: "JetBrains Mono, monospace",
                fontWeight: 600,
                padding: "2px 8px",
                borderRadius: 4,
                textTransform: "uppercase",
                letterSpacing: "0.06em",
                background: result.proved ? "rgba(16,185,129,0.12)" : "rgba(239,68,68,0.12)",
                color: result.proved ? "var(--success)" : "var(--danger)",
                border: `1px solid ${result.proved ? "rgba(16,185,129,0.25)" : "rgba(239,68,68,0.25)"}`,
              }}
            >
              {result.proved ? "proved ✓" : "failed ✗"}
            </span>
          )}
          <button
            onClick={handleVerify}
            disabled={verifying || !code.trim()}
            style={{
              padding: "4px 12px",
              fontSize: 11,
              fontWeight: 500,
              borderRadius: 4,
              border: "none",
              background: verifying ? "var(--bg-hover)" : "var(--accent)",
              color: verifying ? "var(--t-tertiary)" : "#fff",
              cursor: verifying || !code.trim() ? "default" : "pointer",
              fontFamily: "inherit",
              display: "flex",
              alignItems: "center",
              gap: 5,
              transition: "background 150ms",
            }}
          >
            {verifying && (
              <span
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  border: "1.5px solid rgba(255,255,255,0.3)",
                  borderTopColor: "#fff",
                  display: "inline-block",
                  animation: "spin 0.8s linear infinite",
                }}
              />
            )}
            {verifying ? "Verifying…" : "Re-verify"}
          </button>
        </div>
      </div>

      {/* Code textarea */}
      <textarea
        ref={textareaRef}
        value={code}
        onChange={(e) => setCode(e.target.value)}
        onKeyDown={handleTabKey}
        spellCheck={false}
        style={{
          width: "100%",
          minHeight: 240,
          padding: "12px 16px",
          fontSize: 12,
          lineHeight: 1.65,
          fontFamily: "JetBrains Mono, Fira Code, monospace",
          background: "#0d0d0d",
          color: "#d4d4d4",
          border: "1px solid #222",
          borderRadius: 0,
          resize: "vertical",
          outline: "none",
          boxSizing: "border-box",
          tabSize: 2,
        }}
      />

      {/* Result / error area */}
      {(result || error) && (
        <div
          style={{
            padding: "10px 14px",
            background: "#0d0d0d",
            border: "1px solid #222",
            borderTop: "none",
            borderRadius: "0 0 8px 8px",
            fontSize: 12,
            fontFamily: "JetBrains Mono, monospace",
          }}
        >
          {error && (
            <span style={{ color: "var(--danger)" }}>{error}</span>
          )}
          {result && !result.proved && result.failure_reason && (
            <span style={{ color: "var(--warning)" }}>{result.failure_reason}</span>
          )}
          {result?.proved && result.final_proof && (
            <div style={{ marginTop: 8 }}>
              <span style={{ color: "var(--success)", display: "block", marginBottom: 6 }}>Proof found:</span>
              <pre
                style={{
                  margin: 0,
                  color: "#d4d4d4",
                  fontSize: 11,
                  lineHeight: 1.6,
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-all",
                }}
              >
                {result.final_proof}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Counterexample panel ───────────────────────────────────────────────────

/** Single-method result card used inside CounterexamplePanel. */
function MethodResultCard({ result }: { result: MethodResult }) {
  const label =
    result.method === "symbolic"
      ? "Symbolic (brute-force)"
      : result.method === "wolfram"
      ? "Wolfram Alpha"
      : "LLM (Claude)";

  if (!result.applicable) {
    return (
      <div
        style={{
          padding: "8px 12px",
          borderRadius: 6,
          border: "1px solid var(--border-s)",
          background: "var(--bg-input)",
        }}
      >
        <span style={{ fontSize: 11, fontWeight: 600, color: "var(--t-tertiary)" }}>
          {label}
        </span>
        <span style={{ fontSize: 11, color: "var(--t-tertiary)", marginLeft: 8 }}>
          — not applicable
        </span>
        <p style={{ fontSize: 11, color: "var(--t-tertiary)", margin: "4px 0 0", lineHeight: 1.5 }}>
          {result.reasoning}
        </p>
      </div>
    );
  }

  return (
    <div
      style={{
        padding: "8px 12px",
        borderRadius: 6,
        border: `1px solid ${result.found ? "rgba(239,68,68,0.25)" : "rgba(100,116,139,0.25)"}`,
        background: result.found ? "rgba(239,68,68,0.05)" : "var(--bg-input)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: "var(--t-secondary)" }}>{label}</span>
        <span
          style={{
            fontSize: 10,
            fontWeight: 600,
            fontFamily: "JetBrains Mono, monospace",
            padding: "1px 6px",
            borderRadius: 3,
            textTransform: "uppercase",
            letterSpacing: "0.05em",
            background: result.found ? "rgba(239,68,68,0.1)" : "rgba(100,116,139,0.1)",
            color: result.found ? "var(--danger)" : "var(--t-tertiary)",
            border: `1px solid ${result.found ? "rgba(239,68,68,0.2)" : "rgba(100,116,139,0.2)"}`,
          }}
        >
          {result.found ? "found" : "none found"}
        </span>
      </div>

      {result.found && result.counterexample && (
        <p style={{ fontSize: 12, color: "var(--t-primary)", margin: "4px 0 4px", lineHeight: 1.6 }}>
          <MathDisplay text={result.counterexample} />
        </p>
      )}

      <p style={{ fontSize: 11, color: "var(--t-tertiary)", margin: "4px 0 0", lineHeight: 1.5 }}>
        {result.reasoning}
      </p>
    </div>
  );
}

function CounterexamplePanel({ experimentId, isProved }: { experimentId: string; isProved: boolean }) {
  const [searching, setSearching] = useState(false);
  const [result, setResult]       = useState<CounterexampleData | null>(null);
  const [error, setError]         = useState("");

  // Load existing result on mount
  const { data: existing } = useSWR<CounterexampleData>(
    `${API}/api/v1/experiments/${experimentId}/counterexample`,
    fetcher,
    { revalidateOnFocus: false }
  );

  const displayResult = result ?? (existing?.reasoning ? existing : null);

  if (isProved) return null;

  const handleSearch = async () => {
    setSearching(true);
    setError("");
    try {
      const res = await fetch(`${API}/api/v1/experiments/${experimentId}/counterexample`, {
        method: "POST",
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail ?? res.statusText);
      }
      const data: CounterexampleData = await res.json();
      setResult(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSearching(false);
    }
  };

  const methodResults = [
    displayResult?.llm_result,
    displayResult?.symbolic_result,
    displayResult?.wolfram_result,
  ].filter((item): item is MethodResult => item != null);
  const hasMethodResults = methodResults.length >= 2;
  const applicableResults = methodResults.filter((item) => item.applicable);
  const disagreement =
    applicableResults.some((item) => item.found)
    && applicableResults.some((item) => !item.found);

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
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span
          style={{
            fontSize: 10,
            fontWeight: 500,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            color: "var(--t-tertiary)",
          }}
        >
          Counterexample Search
        </span>
        <button
          onClick={handleSearch}
          disabled={searching}
          style={{
            padding: "4px 12px",
            fontSize: 11,
            borderRadius: 4,
            border: "1px solid var(--border-s)",
            background: "var(--bg-input)",
            color: "var(--t-secondary)",
            cursor: searching ? "default" : "pointer",
            fontFamily: "inherit",
            display: "flex",
            alignItems: "center",
            gap: 5,
            opacity: searching ? 0.6 : 1,
            transition: "border-color 150ms",
          }}
          onMouseEnter={(e) => !searching && (e.currentTarget.style.borderColor = "var(--accent)")}
          onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border-s)")}
        >
          {searching ? "Searching…" : "Search"}
        </button>
      </div>

      {error && (
        <span style={{ fontSize: 12, color: "var(--danger)", fontFamily: "JetBrains Mono, monospace" }}>
          {error}
        </span>
      )}

      {displayResult && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {/* Aggregate verdict */}
          <div
            style={{
              padding: "8px 12px",
              borderRadius: 6,
              background: displayResult.found ? "rgba(239,68,68,0.07)" : "rgba(59,130,246,0.05)",
              border: `1px solid ${displayResult.found ? "rgba(239,68,68,0.2)" : "rgba(59,130,246,0.2)"}`,
            }}
          >
            <span
              style={{
                fontSize: 12,
                fontWeight: 600,
                color: displayResult.found ? "var(--danger)" : "#3b82f6",
              }}
            >
              {displayResult.found
                ? "Counterexample found — conjecture appears false"
                : hasMethodResults
                ? "Unrefuted — no applicable method found a counterexample (absence of disproof ≠ truth)"
                : "No counterexample found"}
            </span>
          </div>

          {/* Disagreement warning */}
          {disagreement && (
            <div
              style={{
                padding: "8px 12px",
                borderRadius: 6,
                background: "rgba(245,158,11,0.08)",
                border: "1px solid rgba(245,158,11,0.3)",
              }}
            >
              <span style={{ fontSize: 12, fontWeight: 600, color: "var(--warning)" }}>
                ⚠ Methods disagree — inspect both results carefully before drawing conclusions
              </span>
            </div>
          )}

          {/* Per-method results (new format) */}
          {hasMethodResults ? (
            <>
              <span style={{ fontSize: 10, color: "var(--t-tertiary)", fontWeight: 500, letterSpacing: "0.05em", textTransform: "uppercase" }}>
                Per-method results
              </span>
              {methodResults.map((methodResult) => (
                <MethodResultCard key={methodResult.method} result={methodResult} />
              ))}
            </>
          ) : (
            /* Legacy single-method display */
            <>
              {displayResult.found && displayResult.counterexample && (
                <div>
                  <span style={{ fontSize: 11, color: "var(--t-tertiary)", display: "block", marginBottom: 4 }}>
                    Counterexample
                  </span>
                  <p style={{ fontSize: 13, lineHeight: 1.6, color: "var(--t-primary)", margin: 0 }}>
                    <MathDisplay text={displayResult.counterexample} />
                  </p>
                </div>
              )}
              {displayResult.reasoning && (
                <div>
                  <span style={{ fontSize: 11, color: "var(--t-tertiary)", display: "block", marginBottom: 4 }}>
                    Reasoning
                  </span>
                  <p style={{ fontSize: 12, lineHeight: 1.6, color: "var(--t-secondary)", margin: 0 }}>
                    {displayResult.reasoning}
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {!displayResult && !searching && !error && (
        <p style={{ fontSize: 12, color: "var(--t-tertiary)", margin: 0 }}>
          Run counterexample search (LLM + symbolic brute-force + Wolfram when configured) to attempt
          to disprove this conjecture.
          Independent methods with different failure modes run together.
        </p>
      )}
    </div>
  );
}

// ── Lineage panel ──────────────────────────────────────────────────────────

function LineagePanel({ experimentId }: { experimentId: string }) {
  const { data, isLoading } = useSWR<LineageData>(
    `${API}/api/v1/experiments/${experimentId}/lineage`,
    fetcher,
    { revalidateOnFocus: false }
  );

  const [deriving, setDeriving]   = useState(false);
  const [deriveRelation, setDeriveRelation] = useState<"generalization" | "special_case" | "analogue">("generalization");
  const [deriveN, setDeriveN]     = useState(2);
  const [deriveMsg, setDeriveMsg] = useState("");

  const hasContent = data && (data.parent !== null || data.children.length > 0);

  const handleDerive = async () => {
    setDeriving(true);
    setDeriveMsg("");
    try {
      const res = await fetch(`${API}/api/v1/experiments/${experimentId}/derive`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ n: deriveN, relation: deriveRelation }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail ?? res.statusText);
      }
      const data = await res.json();
      setDeriveMsg(`Pipeline started — job ${data.job_id.slice(0, 8)}…`);
    } catch (e: unknown) {
      setDeriveMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setDeriving(false);
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
        gap: 16,
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
        Lineage
      </span>

      {isLoading && (
        <span style={{ fontSize: 12, color: "var(--t-tertiary)" }}>Loading…</span>
      )}

      {/* Parent */}
      {data?.parent && (
        <div>
          <span style={{ fontSize: 11, color: "var(--t-tertiary)", display: "block", marginBottom: 6 }}>
            Derived from
          </span>
          <LineageCard node={data.parent} />
        </div>
      )}

      {/* Children */}
      {data && data.children.length > 0 && (
        <div>
          <span style={{ fontSize: 11, color: "var(--t-tertiary)", display: "block", marginBottom: 6 }}>
            {data.children.length} derived conjecture{data.children.length > 1 ? "s" : ""}
          </span>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {data.children.map((c) => (
              <LineageCard key={c.id} node={c} />
            ))}
          </div>
        </div>
      )}

      {!isLoading && !hasContent && (
        <p style={{ fontSize: 12, color: "var(--t-tertiary)", margin: 0 }}>
          No lineage yet. Use Derive to generate related conjectures.
        </p>
      )}

      {/* Derive controls */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 10,
          paddingTop: 10,
          borderTop: "1px solid var(--border-s)",
        }}
      >
        <span style={{ fontSize: 11, color: "var(--t-tertiary)" }}>Generate derived conjectures</span>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <select
            value={deriveRelation}
            onChange={(e) => setDeriveRelation(e.target.value as typeof deriveRelation)}
            style={{
              padding: "4px 8px",
              fontSize: 11,
              background: "var(--bg-input)",
              border: "1px solid var(--border-s)",
              borderRadius: 4,
              color: "var(--t-secondary)",
              fontFamily: "inherit",
              outline: "none",
            }}
          >
            <option value="generalization">Generalization</option>
            <option value="special_case">Special case</option>
            <option value="analogue">Analogue</option>
          </select>

          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            {[1, 2, 3].map((v) => (
              <button
                key={v}
                onClick={() => setDeriveN(v)}
                style={{
                  width: 24,
                  height: 24,
                  borderRadius: 4,
                  border: `1px solid ${deriveN === v ? "var(--accent)" : "var(--border-s)"}`,
                  background: deriveN === v ? "rgba(124,58,237,0.1)" : "var(--bg-input)",
                  color: deriveN === v ? "var(--accent)" : "var(--t-tertiary)",
                  cursor: "pointer",
                  fontSize: 11,
                  fontFamily: "JetBrains Mono, monospace",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  transition: "border-color 150ms",
                }}
              >
                {v}
              </button>
            ))}
          </div>

          <button
            onClick={handleDerive}
            disabled={deriving}
            style={{
              padding: "4px 12px",
              fontSize: 11,
              borderRadius: 4,
              border: "none",
              background: deriving ? "var(--bg-hover)" : "var(--accent)",
              color: deriving ? "var(--t-tertiary)" : "#fff",
              cursor: deriving ? "default" : "pointer",
              fontFamily: "inherit",
              opacity: deriving ? 0.7 : 1,
              transition: "background 150ms",
            }}
          >
            {deriving ? "Deriving…" : "Derive"}
          </button>
        </div>

        {deriveMsg && (
          <span
            style={{
              fontSize: 11,
              fontFamily: "JetBrains Mono, monospace",
              color: deriveMsg.startsWith("Pipeline") ? "var(--success)" : "var(--danger)",
            }}
          >
            {deriveMsg}
          </span>
        )}
      </div>
    </div>
  );
}

function LineageCard({ node }: { node: LineageNode }) {
  return (
    <Link
      href={`/experiments/${node.id}`}
      style={{ textDecoration: "none" }}
    >
      <div
        style={{
          padding: "8px 12px",
          borderRadius: 6,
          border: "1px solid var(--border-s)",
          background: "var(--bg-input)",
          display: "flex",
          alignItems: "flex-start",
          gap: 10,
          cursor: "pointer",
          transition: "border-color 150ms",
        }}
        onMouseEnter={(e) => ((e.currentTarget as HTMLDivElement).style.borderColor = "var(--accent)")}
        onMouseLeave={(e) => ((e.currentTarget as HTMLDivElement).style.borderColor = "var(--border-s)")}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <span
            style={{
              fontSize: 12,
              color: "var(--t-primary)",
              lineHeight: 1.5,
              display: "block",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {node.conjecture}
          </span>
          <span style={{ fontSize: 10, fontFamily: "JetBrains Mono, monospace", color: "var(--t-tertiary)" }}>
            {node.domain} · {node.id.slice(0, 8)}
          </span>
        </div>
        <div style={{ display: "flex", gap: 4, flexShrink: 0 }}>
          {node.proved && (
            <span style={{ fontSize: 10, color: "var(--success)", fontFamily: "JetBrains Mono, monospace" }}>proved</span>
          )}
          {!node.proved && node.is_valid && (
            <span style={{ fontSize: 10, color: "var(--warning)", fontFamily: "JetBrains Mono, monospace" }}>open</span>
          )}
          {!node.is_valid && (
            <span style={{ fontSize: 10, color: "var(--danger)", fontFamily: "JetBrains Mono, monospace" }}>invalid</span>
          )}
        </div>
      </div>
    </Link>
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

  // Determine if dual CX search has run and found nothing — "unrefuted" state.
  const cxResult = extra.counterexample_result as Record<string, unknown> | null | undefined;
  const cxChecked =
    cxResult != null
    && ("llm_result" in cxResult || "symbolic_result" in cxResult || "wolfram_result" in cxResult);
  const cxFound = Boolean(cxResult?.found);
  const isUnrefuted = !data.proved && cxChecked && !cxFound;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>

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
          <Badge ok={data.proved} trueLabel="proved" falseLabel={isUnrefuted ? "unrefuted" : "open"} />
        </div>
      </div>

      {/* Split panel */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1.5fr", gap: 16 }}>
        {/* Left: conjecture + metadata + counterexample + lineage + annotation */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Conjecture with KaTeX rendering */}
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
            <p style={{ fontSize: 14, lineHeight: 1.7, color: "var(--t-primary)", letterSpacing: "-0.01em", margin: 0 }}>
              <MathDisplay text={data.conjecture} />
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

          {/* Counterexample search (only for unproved) */}
          <CounterexamplePanel experimentId={data.id} isProved={data.proved} />

          {/* Lineage */}
          <LineagePanel experimentId={data.id} />

          {/* Annotation form */}
          <AnnotationForm experimentId={data.id} />
        </div>

        {/* Right: Lean 4 code + interactive editor + proof */}
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

          {/* Interactive Lean editor */}
          {data.lean_code && (
            <LeanEditor initialCode={data.lean_code} />
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
                background: isUnrefuted ? "rgba(59,130,246,0.05)" : "rgba(245,158,11,0.06)",
                border: isUnrefuted ? "1px solid rgba(59,130,246,0.2)" : "1px solid rgba(245,158,11,0.2)",
              }}
            >
              {isUnrefuted ? (
                <span style={{ fontSize: 13, color: "#3b82f6" }}>
                  This conjecture is <strong>unrefuted</strong> — no configured/applicable
                  counterexample search found a counterexample, but absence of disproof is not
                  evidence of truth. It has not been proved.
                </span>
              ) : (
                <span style={{ fontSize: 13, color: "var(--warning)" }}>
                  This conjecture remains open — no automated proof was found.
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
