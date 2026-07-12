import { CSSProperties } from "react";
import {
  AccentPreference,
  DefaultExperimentView,
  DensityPreference,
  ThemePreference,
  useSettings,
} from "../context/SettingsContext";

const row: CSSProperties = {
  alignItems: "flex-start",
  borderTop: "1px solid var(--border-s)",
  display: "grid",
  gap: 24,
  gridTemplateColumns: "minmax(180px, 0.8fr) minmax(0, 1.2fr)",
  padding: "22px 0",
};

const helper: CSSProperties = {
  color: "var(--t-tertiary)",
  fontSize: 12,
  lineHeight: 1.6,
  marginTop: 5,
};

function FieldCopy({ title, body }: { title: string; body: string }) {
  return (
    <div>
      <h2 style={{ color: "var(--t-primary)", fontSize: 14, fontWeight: 700, margin: 0 }}>
        {title}
      </h2>
      <p style={helper}>{body}</p>
    </div>
  );
}

function Segmented<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T;
  options: Array<{ value: T; label: string }>;
  onChange: (value: T) => void;
}) {
  return (
    <div
      style={{
        background: "var(--bg-input)",
        border: "1px solid var(--border-s)",
        borderRadius: 7,
        display: "flex",
        flexWrap: "wrap",
        gap: 3,
        padding: 3,
        width: "fit-content",
      }}
    >
      {options.map((option) => {
        const active = value === option.value;
        return (
          <button
            key={option.value}
            onClick={() => onChange(option.value)}
            style={{
              background: active ? "var(--bg-card)" : "transparent",
              border: "none",
              borderRadius: 5,
              color: active ? "var(--t-primary)" : "var(--t-tertiary)",
              cursor: "pointer",
              fontSize: 12,
              fontWeight: active ? 700 : 500,
              minHeight: 30,
              padding: "0 12px",
            }}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
}) {
  return (
    <label style={{ alignItems: "center", cursor: "pointer", display: "flex", gap: 10 }}>
      <input
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        style={{ accentColor: "var(--accent)", height: 16, width: 16 }}
        type="checkbox"
      />
      <span style={{ color: "var(--t-secondary)", fontSize: 13, fontWeight: 500 }}>{label}</span>
    </label>
  );
}

const accentOptions: Array<{ value: AccentPreference; label: string; color: string }> = [
  { value: "indigo", label: "Indigo", color: "#4f46e5" },
  { value: "teal", label: "Teal", color: "#0f766e" },
  { value: "amber", label: "Amber", color: "#b45309" },
  { value: "rose", label: "Rose", color: "#be123c" },
  { value: "slate", label: "Slate", color: "#475569" },
];

export default function SettingsPage() {
  const { settings, resolvedTheme, updateSettings, resetSettings } = useSettings();

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--density-gap)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 18, flexWrap: "wrap" }}>
        <div>
          <span className="label">Workspace</span>
          <h1
            style={{
              color: "var(--t-primary)",
              fontSize: 28,
              fontWeight: 700,
              letterSpacing: 0,
              margin: "6px 0 0",
            }}
          >
            Settings
          </h1>
          <p style={{ color: "var(--t-secondary)", fontSize: 14, lineHeight: 1.7, margin: "8px 0 0" }}>
            Tune Germinal for reading, comparing, and reviewing experiments. Preferences stay in
            this browser only.
          </p>
        </div>
        <button className="secondary-button" onClick={resetSettings} style={{ height: 34, padding: "0 12px" }}>
          Reset defaults
        </button>
      </div>

      <section className="panel" style={{ padding: "0 var(--density-pad)" }}>
        <div style={{ ...row, borderTop: "none" }}>
          <FieldCopy title="Theme" body={`Current resolved theme: ${resolvedTheme}.`} />
          <Segmented<ThemePreference>
            value={settings.theme}
            onChange={(theme) => updateSettings({ theme })}
            options={[
              { value: "system", label: "System" },
              { value: "light", label: "Light" },
              { value: "dark", label: "Dark" },
            ]}
          />
        </div>

        <div style={row}>
          <FieldCopy title="Density" body="Compact mode tightens tables, cards, and page spacing." />
          <Segmented<DensityPreference>
            value={settings.density}
            onChange={(density) => updateSettings({ density })}
            options={[
              { value: "comfortable", label: "Comfortable" },
              { value: "compact", label: "Compact" },
            ]}
          />
        </div>

        <div style={row}>
          <FieldCopy title="Accent" body="Used for active states, links, focus rings, and selected controls." />
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {accentOptions.map((accent) => {
              const active = settings.accent === accent.value;
              return (
                <button
                  key={accent.value}
                  onClick={() => updateSettings({ accent: accent.value })}
                  style={{
                    alignItems: "center",
                    background: active ? "var(--accent-bg)" : "var(--bg-input)",
                    border: `1px solid ${active ? "var(--accent)" : "var(--border-s)"}`,
                    borderRadius: 7,
                    color: active ? "var(--accent)" : "var(--t-secondary)",
                    cursor: "pointer",
                    display: "inline-flex",
                    fontSize: 12,
                    fontWeight: 700,
                    gap: 8,
                    minHeight: 32,
                    padding: "0 11px",
                  }}
                >
                  <span
                    style={{
                      background: accent.color,
                      borderRadius: 999,
                      display: "inline-block",
                      height: 10,
                      width: 10,
                    }}
                  />
                  {accent.label}
                </button>
              );
            })}
          </div>
        </div>

        <div style={row}>
          <FieldCopy
            title="Technical Detail"
            body="Hide secondary metadata when you want a cleaner review surface."
          />
          <Toggle
            checked={settings.showTechnicalDetail}
            label="Show model, ids, timing, strategy, and supporting metadata"
            onChange={(showTechnicalDetail) => updateSettings({ showTechnicalDetail })}
          />
        </div>

        <div style={row}>
          <FieldCopy title="Default Experiment View" body="Choose how the main experiment archive opens." />
          <Segmented<DefaultExperimentView>
            value={settings.defaultExperimentView}
            onChange={(defaultExperimentView) => updateSettings({ defaultExperimentView })}
            options={[
              { value: "table", label: "Table" },
              { value: "cards", label: "Cards" },
            ]}
          />
        </div>

        <div style={row}>
          <FieldCopy title="Animations" body="Disable motion for a quieter, faster-feeling interface." />
          <Toggle
            checked={settings.animationsEnabled}
            label="Enable interface animations"
            onChange={(animationsEnabled) => updateSettings({ animationsEnabled })}
          />
        </div>
      </section>
    </div>
  );
}
