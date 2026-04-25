/**
 * MathDisplay — renders a string that may contain LaTeX math delimiters.
 *
 * Inline math:  $...$
 * Display math: $$...$$
 *
 * Non-math text is rendered as plain text. KaTeX handles the LaTeX portions.
 * Falls back to plain text if KaTeX throws (malformed LaTeX, unknown commands).
 */

import { useEffect, useRef } from "react";
import type { CSSProperties } from "react";

// Segment types produced by the parser
type Segment =
  | { kind: "text";    value: string }
  | { kind: "inline"; value: string }
  | { kind: "display"; value: string };

/**
 * Split a string into alternating text / LaTeX segments.
 * Display math ($$...$$) is checked before inline ($...$).
 */
function parse(input: string): Segment[] {
  const segments: Segment[] = [];
  // Matches $$...$$ or $...$  (non-greedy, single-line)
  const re = /(\$\$[\s\S]*?\$\$|\$[^$\n]*?\$)/g;
  let last = 0;
  let match: RegExpExecArray | null;

  while ((match = re.exec(input)) !== null) {
    if (match.index > last) {
      segments.push({ kind: "text", value: input.slice(last, match.index) });
    }
    const raw = match[1];
    if (raw.startsWith("$$")) {
      segments.push({ kind: "display", value: raw.slice(2, -2) });
    } else {
      segments.push({ kind: "inline", value: raw.slice(1, -1) });
    }
    last = match.index + raw.length;
  }

  if (last < input.length) {
    segments.push({ kind: "text", value: input.slice(last) });
  }

  return segments;
}

interface KatexSpanProps {
  latex: string;
  display: boolean;
  style?: CSSProperties;
}

function KatexSpan({ latex, display, style }: KatexSpanProps) {
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    import("katex").then(({ default: katex }) => {
      try {
        katex.render(latex, ref.current!, {
          displayMode: display,
          throwOnError: false,
          strict: false,
        });
      } catch {
        // If rendering fails, show raw LaTeX so the user can see what was intended
        ref.current!.textContent = display ? `$$${latex}$$` : `$${latex}$`;
      }
    });
  }, [latex, display]);

  return (
    <span
      ref={ref}
      style={{
        display: display ? "block" : "inline",
        textAlign: display ? "center" : undefined,
        margin: display ? "8px 0" : undefined,
        ...style,
      }}
    />
  );
}

interface MathDisplayProps {
  text: string;
  style?: CSSProperties;
  className?: string;
}

/**
 * Render `text` with embedded LaTeX ($...$ or $$...$$) using KaTeX.
 * Wraps the entire content in a `<span>` (inline container).
 */
export default function MathDisplay({ text, style, className }: MathDisplayProps) {
  const segments = parse(text);

  return (
    <span style={style} className={className}>
      {segments.map((seg, i) => {
        if (seg.kind === "text") {
          return <span key={i}>{seg.value}</span>;
        }
        return (
          <KatexSpan
            key={i}
            latex={seg.value}
            display={seg.kind === "display"}
          />
        );
      })}
      {/* Load KaTeX CSS once via a hidden style tag injected into the document head */}
      <KatexCSS />
    </span>
  );
}

let cssInjected = false;
function KatexCSS() {
  useEffect(() => {
    if (cssInjected || typeof document === "undefined") return;
    cssInjected = true;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css";
    document.head.appendChild(link);
  }, []);
  return null;
}
