import React, { useState } from "react";
import Link from "next/link";

/* ─── Types ─────────────────────────────────────────────────────────────── */
export type Stage = "idle" | "generating" | "formalizing" | "verifying" | "done" | "error";

export interface PipelineResult {
  experiment_id: string;
  conjecture: string;
  is_valid: boolean;
  proved: boolean;
  duration_ms: number;
  git_sha: string | null;
  snapshot_error?: string;
  proof_strategy?: string;
  novelty_score?: number;
  complexity?: { formalizability?: number; proof_difficulty?: number; recommended_strategy?: string };
}

export interface PipelineResponse {
  domain: string;
  total_duration_ms: number;
  results: PipelineResult[];
}

/* ─── Stepped pipeline indicator ────────────────────────────────────────── */
const STEPS = [
  { key: "generating",  label: "generate"  },
  { key: "formalizing", label: "formalize" },
  { key: "verifying",   label: "verify"    },
  { key: "done",        label: "complete"  },
] as const;

const STAGE_IDX: Record<Stage, number> = {
  idle: -1, generating: 0, formalizing: 1, verifying: 2, done: 3, error: -1,
};

function PipelineSteps({ stage }: { stage: Stage }) {
  const activeIdx = STAGE_IDX[stage];

  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        padding: "20px 0 4px",
        gap: 0,
      }}
    >
      {STEPS.map((step, i) => {
        const isDone    = stage === "done" || (activeIdx > i && activeIdx !== -1);
        const isActive  = activeIdx === i && stage !== "done";
        const isPending = !isDone && !isActive;

        return (
          <React.Fragment key={step.key}>
            <div
              className="anim-step-in"
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                animationDelay: `${i * 80}ms`,
              }}
            >
              {/* Circle */}
              <div
                className={isActive ? "anim-pipeline-pulse" : undefined}
                style={{
                  width: 20,
                  height: 20,
                  borderRadius: "50%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  background: isDone
                    ? "var(--success)"
                    : isActive
                    ? "var(--accent)"
                    : "transparent",
                  border: isPending ? "1.5px solid var(--border-a)" : "none",
                  transition: "background 300ms, border-color 300ms",
                }}
              >
                {isDone && (
                  <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                    <path
                      d="M2 5l2.5 2.5L8 3"
                      stroke="#fff"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                )}
                {isActive && (
                  <div
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      background: "#fff",
                    }}
                  />
                )}
              </div>

              {/* Label */}
              <span
                style={{
                  fontFamily: "JetBrains Mono, Fira Code, monospace",
                  fontSize: 10,
                  marginTop: 6,
                  color: isDone
                    ? "var(--success)"
                    : isActive
                    ? "var(--accent)"
                    : "var(--t-tertiary)",
                  transition: "color 300ms",
                }}
              >
                {step.label}
              </span>
            </div>

            {/* Connector */}
            {i < STEPS.length - 1 && (
              <div
                style={{
                  height: 1.5,
                  flex: 1,
                  marginTop: 9,
                  minWidth: 20,
                  maxWidth: 80,
                  background: isDone ? "var(--success)" : "var(--border-s)",
                  transition: "background 400ms ease",
                }}
              />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

/* ─── Lean 4 syntax highlighting ─────────────────────────────────────────── */
const LEAN_KW = new Set([
  "theorem", "lemma", "def", "by", "have", "exact", "omega", "simp", "rw",
  "intro", "apply", "cases", "induction", "where", "fun", "import", "open",
  "namespace", "end", "noncomputable", "variable", "instance", "class",
  "structure", "sorry", "return", "if", "then", "else", "match", "with",
  "let", "in", "do", "example", "calc", "show", "from", "tauto", "ring",
  "linarith", "norm_num", "decide", "constructor", "use", "obtain", "refine",
]);

function HighlightLine({ line }: { line: string }) {
  const commentIdx = line.indexOf("--");

  const renderTokens = (text: string) =>
    text.split(/(\b[A-Za-z_]\w*\b)/).map((tok, i) =>
      LEAN_KW.has(tok) ? (
        <span key={i} style={{ color: "var(--accent)" }}>{tok}</span>
      ) : (
        <span key={i}>{tok}</span>
      )
    );

  if (commentIdx === 0) {
    return <span style={{ color: "#555" }}>{line}</span>;
  }
  if (commentIdx > 0) {
    return (
      <>
        {renderTokens(line.slice(0, commentIdx))}
        <span style={{ color: "#555" }}>{line.slice(commentIdx)}</span>
      </>
    );
  }
  return <>{renderTokens(line)}</>;
}

function CodeBlock({
  code,
  badge,
}: {
  code: string;
  badge: "proved" | "sorry" | "error" | null;
}) {
  const [copied, setCopied] = useState(false);
  const lines = code.split("\n");

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const badgeStyle = (): React.CSSProperties => {
    if (badge === "proved")
      return {
        background: "rgba(16,185,129,0.12)",
        color: "var(--success)",
        border: "1px solid rgba(16,185,129,0.25)",
      };
    if (badge === "sorry")
      return {
        background: "rgba(245,158,11,0.12)",
        color: "var(--warning)",
        border: "1px solid rgba(245,158,11,0.25)",
      };
    if (badge === "error")
      return {
        background: "rgba(239,68,68,0.12)",
        color: "var(--danger)",
        border: "1px solid rgba(239,68,68,0.25)",
      };
    return {};
  };

  return (
    <div
      style={{
        background: "#0d0d0d",
        border: "1px solid #222",
        borderRadius: 8,
        overflow: "hidden",
      }}
    >
      {/* Toolbar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "7px 12px",
          borderBottom: "1px solid #1a1a1a",
        }}
      >
        {badge ? (
          <span
            style={{
              ...badgeStyle(),
              fontFamily: "JetBrains Mono, monospace",
              fontSize: 10,
              fontWeight: 600,
              letterSpacing: "0.06em",
              padding: "2px 8px",
              borderRadius: 4,
              textTransform: "uppercase",
            }}
          >
            {badge}
          </span>
        ) : (
          <span style={{ fontSize: 10, color: "#444", fontFamily: "monospace" }}>
            lean 4
          </span>
        )}
        <button
          onClick={handleCopy}
          style={{
            fontSize: 11,
            color: copied ? "var(--success)" : "#555",
            background: "none",
            border: "none",
            cursor: "pointer",
            fontFamily: "JetBrains Mono, monospace",
            transition: "color 150ms",
          }}
        >
          {copied ? "copied" : "copy"}
        </button>
      </div>

      {/* Code */}
      <pre
        style={{
          margin: 0,
          padding: "12px 0",
          fontSize: 12,
          lineHeight: 1.65,
          fontFamily: "JetBrains Mono, Fira Code, monospace",
          color: "#d4d4d4",
          overflowX: "auto",
        }}
      >
        {lines.map((line, idx) => (
          <div key={idx} style={{ display: "flex" }}>
            <span
              style={{
                color: "#333",
                userSelect: "none",
                minWidth: 40,
                paddingRight: 16,
                paddingLeft: 12,
                textAlign: "right",
                fontSize: 11,
              }}
            >
              {idx + 1}
            </span>
            <span style={{ paddingRight: 16, flex: 1 }}>
              <HighlightLine line={line} />
            </span>
          </div>
        ))}
      </pre>
    </div>
  );
}

/* ─── Result card ────────────────────────────────────────────────────────── */
function ResultCard({ result }: { result: PipelineResult }) {
  const badge: "proved" | "sorry" | "error" = result.proved
    ? "proved"
    : result.is_valid
    ? "sorry"
    : "error";

  const badgeColors = {
    proved: { bg: "rgba(16,185,129,0.1)", color: "var(--success)", border: "rgba(16,185,129,0.2)" },
    sorry:  { bg: "rgba(245,158,11,0.1)",  color: "var(--warning)", border: "rgba(245,158,11,0.2)" },
    error:  { bg: "rgba(239,68,68,0.1)",   color: "var(--danger)",  border: "rgba(239,68,68,0.2)" },
  }[badge];

  return (
    <div
      className="anim-slide-up"
      style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border-s)",
        borderRadius: 8,
        overflow: "hidden",
      }}
    >
      {/* Content row */}
      <div
        style={{
          padding: "12px 16px",
          display: "flex",
          alignItems: "flex-start",
          gap: 12,
        }}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <p
            style={{
              fontSize: 13,
              color: "var(--t-primary)",
              lineHeight: 1.55,
              margin: 0,
            }}
          >
            {result.conjecture}
          </p>
          <div style={{ display: "flex", gap: 12, marginTop: 7, alignItems: "center", flexWrap: "wrap" }}>
            <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 10, color: "var(--t-tertiary)" }}>
              {result.duration_ms.toLocaleString()}ms
            </span>
            {result.git_sha && (
              <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 10, color: "var(--t-tertiary)" }}>
                sha: <span style={{ color: "var(--accent)" }}>{result.git_sha.slice(0, 8)}</span>
              </span>
            )}
            {result.proof_strategy && (
              <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 10, color: "var(--t-tertiary)" }}>
                strategy: <span style={{ color: "var(--accent)" }}>{result.proof_strategy}</span>
              </span>
            )}
            {typeof result.novelty_score === "number" && (
              <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 10, color: "var(--t-tertiary)" }}>
                novelty: <span style={{ color: result.novelty_score > 0.7 ? "var(--success)" : "var(--warning)" }}>
                  {(result.novelty_score * 100).toFixed(0)}%
                </span>
              </span>
            )}
          </div>
        </div>

        {/* Badges */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 4,
            alignItems: "flex-end",
            flexShrink: 0,
          }}
        >
          <span
            style={{
              background: badgeColors.bg,
              color: badgeColors.color,
              border: `1px solid ${badgeColors.border}`,
              fontFamily: "JetBrains Mono, monospace",
              fontSize: 10,
              fontWeight: 600,
              padding: "2px 8px",
              borderRadius: 4,
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            {badge}
          </span>
          <span
            style={{
              fontFamily: "JetBrains Mono, monospace",
              fontSize: 10,
              color: result.is_valid ? "var(--success)" : "var(--danger)",
            }}
          >
            lean {result.is_valid ? "✓" : "✗"}
          </span>
        </div>
      </div>

      {/* Footer */}
      <div
        style={{
          padding: "7px 16px",
          borderTop: "1px solid var(--border-s)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          background: "var(--bg-input)",
        }}
      >
        <span
          style={{
            fontFamily: "JetBrains Mono, monospace",
            fontSize: 10,
            color: "var(--t-tertiary)",
          }}
        >
          {result.experiment_id.slice(0, 16)}…
        </span>
        <Link
          href={`/experiments/${result.experiment_id}`}
          style={{
            fontSize: 11,
            color: "var(--accent)",
            textDecoration: "none",
            fontWeight: 500,
          }}
        >
          View detail →
        </Link>
      </div>
    </div>
  );
}

/* ─── Main Pipeline display component ───────────────────────────────────── */
interface PipelineProps {
  stage: Stage;
  response: PipelineResponse | null;
  errorMsg: string;
}

export default function Pipeline({ stage, response, errorMsg }: PipelineProps) {
  if (stage === "idle") return null;

  return (
    <div>
      <PipelineSteps stage={stage} />

      {/* Error */}
      {stage === "error" && errorMsg && (
        <div
          className="anim-error-in"
          style={{
            marginTop: 16,
            padding: "12px 16px",
            borderRadius: 8,
            background: "rgba(239,68,68,0.08)",
            border: "1px solid rgba(239,68,68,0.2)",
            color: "var(--danger)",
            fontSize: 13,
          }}
        >
          {errorMsg}
        </div>
      )}

      {/* Results */}
      {response && (
        <div style={{ marginTop: 24 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: 12,
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
              Results — {response.domain}
            </span>
            <span
              style={{
                fontFamily: "JetBrains Mono, monospace",
                fontSize: 10,
                color: "var(--t-tertiary)",
              }}
            >
              {response.total_duration_ms.toLocaleString()}ms total
            </span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {response.results.map((r) => (
              <ResultCard key={r.experiment_id} result={r} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* Re-export CodeBlock for use in detail page */
export { CodeBlock };
