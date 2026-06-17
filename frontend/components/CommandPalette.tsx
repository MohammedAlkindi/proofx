import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/router";
import useSWR from "swr";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const fetcher = (url: string) => fetch(url).then((r) => r.json());

interface ExperimentItem {
  id: string;
  domain: string;
  conjecture: string;
  timestamp: string;
  proved: boolean;
  is_valid: boolean;
}

interface Props {
  open: boolean;
  onClose: () => void;
}

function statusDot(item: ExperimentItem) {
  const color = item.proved
    ? "var(--success)"
    : item.is_valid
    ? "var(--warning)"
    : "var(--danger)";
  return (
    <div
      style={{
        width: 6,
        height: 6,
        borderRadius: "50%",
        background: color,
        flexShrink: 0,
        marginTop: 2,
      }}
    />
  );
}

function highlight(text: string, query: string): React.ReactNode {
  if (!query) return text;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return text;
  return (
    <>
      {text.slice(0, idx)}
      <mark
        style={{
          background: "rgba(124,58,237,0.25)",
          color: "var(--accent)",
          borderRadius: 2,
          padding: "0 1px",
        }}
      >
        {text.slice(idx, idx + query.length)}
      </mark>
      {text.slice(idx + query.length)}
    </>
  );
}

export default function CommandPalette({ open, onClose }: Props) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [activeIdx, setActiveIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const { data: experiments } = useSWR<ExperimentItem[]>(
    open ? `${API}/api/v1/experiments?limit=200` : null,
    fetcher,
    { revalidateOnFocus: false }
  );

  const filtered = (experiments ?? []).filter((e) => {
    if (!query) return true;
    const q = query.toLowerCase();
    return (
      e.domain.toLowerCase().includes(q) ||
      e.conjecture.toLowerCase().includes(q) ||
      e.id.toLowerCase().includes(q)
    );
  });

  const navigate = useCallback(
    (id: string) => {
      router.push(`/experiments/${id}`);
      onClose();
    },
    [router, onClose]
  );

  // Focus input when opened
  useEffect(() => {
    if (open) {
      setQuery("");
      setActiveIdx(0);
      setTimeout(() => inputRef.current?.focus(), 30);
    }
  }, [open]);

  // Keyboard navigation
  useEffect(() => {
    if (!open) return;

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIdx((i) => Math.min(i + 1, filtered.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIdx((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter" && filtered[activeIdx]) {
        navigate(filtered[activeIdx].id);
      }
    };

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, filtered, activeIdx, navigate, onClose]);

  // Scroll active item into view
  useEffect(() => {
    const el = listRef.current?.children[activeIdx] as HTMLElement | undefined;
    el?.scrollIntoView({ block: "nearest" });
  }, [activeIdx]);

  // Reset active index when query changes
  useEffect(() => setActiveIdx(0), [query]);

  if (!open) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        className="anim-fade-in"
        style={{
          position: "fixed",
          inset: 0,
          background: "rgba(0,0,0,0.45)",
          zIndex: 200,
          backdropFilter: "blur(2px)",
        }}
      />

      {/* Modal */}
      <div
        className="anim-palette-in"
        style={{
          position: "fixed",
          top: "20vh",
          left: "50%",
          transform: "translateX(-50%)",
          width: "min(640px, calc(100vw - 40px))",
          background: "var(--bg-card)",
          border: "1px solid var(--border-a)",
          borderRadius: 12,
          boxShadow: "0 24px 64px rgba(0,0,0,0.4)",
          zIndex: 201,
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Search input */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "14px 16px",
            borderBottom: "1px solid var(--border-s)",
          }}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            style={{ flexShrink: 0, color: "var(--t-tertiary)" }}
          >
            <circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.5" />
            <path d="M11 11l3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search experiments by domain, conjecture, or ID..."
            style={{
              flex: 1,
              background: "none",
              border: "none",
              outline: "none",
              fontSize: 14,
              color: "var(--t-primary)",
              fontFamily: "inherit",
            }}
          />
          <kbd
            style={{
              fontFamily: "JetBrains Mono, monospace",
              fontSize: 10,
              color: "var(--t-tertiary)",
              background: "var(--bg-input)",
              border: "1px solid var(--border-s)",
              borderRadius: 4,
              padding: "2px 6px",
            }}
          >
            esc
          </kbd>
        </div>

        {/* Results list */}
        <div
          ref={listRef}
          style={{
            overflowY: "auto",
            maxHeight: "50vh",
          }}
        >
          {filtered.length === 0 ? (
            <div
              style={{
                padding: "32px 16px",
                textAlign: "center",
                fontSize: 13,
                color: "var(--t-tertiary)",
              }}
            >
              {query ? `No experiments matching "${query}"` : "No experiments yet"}
            </div>
          ) : (
            filtered.map((exp, i) => {
              const active = i === activeIdx;
              return (
                <div
                  key={exp.id}
                  onClick={() => navigate(exp.id)}
                  onMouseEnter={() => setActiveIdx(i)}
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 10,
                    padding: "10px 16px",
                    cursor: "pointer",
                    background: active ? "var(--bg-hover)" : "transparent",
                    borderLeft: active ? "2px solid var(--accent)" : "2px solid transparent",
                    transition: "background 60ms",
                  }}
                >
                  {statusDot(exp)}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        fontSize: 12,
                        fontWeight: 500,
                        color: "var(--t-primary)",
                        textTransform: "uppercase",
                        letterSpacing: "0.04em",
                        marginBottom: 3,
                      }}
                    >
                      {highlight(exp.domain, query)}
                    </div>
                    <div
                      style={{
                        fontSize: 12,
                        color: "var(--t-secondary)",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {highlight(exp.conjecture, query)}
                    </div>
                  </div>
                  <span
                    style={{
                      fontFamily: "JetBrains Mono, monospace",
                      fontSize: 10,
                      color: "var(--t-tertiary)",
                      flexShrink: 0,
                    }}
                  >
                    {exp.id.slice(0, 8)}
                  </span>
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            padding: "8px 16px",
            borderTop: "1px solid var(--border-s)",
            display: "flex",
            gap: 14,
            alignItems: "center",
          }}
        >
          {(
            [
              ["up/down", "navigate"],
              ["enter", "open"],
              ["esc", "close"],
            ] as [string, string][]
          ).map(([key, label]) => (
            <span
              key={key}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 5,
                fontSize: 11,
                color: "var(--t-tertiary)",
              }}
            >
              <kbd
                style={{
                  fontFamily: "JetBrains Mono, monospace",
                  fontSize: 10,
                  background: "var(--bg-input)",
                  border: "1px solid var(--border-s)",
                  borderRadius: 4,
                  padding: "1px 5px",
                }}
              >
                {key}
              </kbd>
              {label}
            </span>
          ))}
          <span
            style={{
              marginLeft: "auto",
              fontFamily: "JetBrains Mono, monospace",
              fontSize: 10,
              color: "var(--t-tertiary)",
            }}
          >
            {filtered.length} result{filtered.length !== 1 ? "s" : ""}
          </span>
        </div>
      </div>
    </>
  );
}
