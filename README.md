# ProofX Web

**ProofX Web** is the public-facing interface for the ProofX research initiative.  
It provides a clean, structured, and extensible web layer for presenting research context, experiment summaries, and future interactive tooling.

This repository **does not contain the computational engine**. It is intentionally decoupled.

---

## 🧭 Purpose

The goal of ProofX Web is to:
- Communicate the **research vision** behind ProofX
- Present **high-level experiment narratives and results**
- Serve as a foundation for **interactive research tooling**
- Act as the **public gateway** to ongoing computational work

Think of this as the **front office**, not the lab.

---

## 🏗️ Scope (What This Repo Is / Is Not)

### ✅ This Repository Includes
- Web application source code
- UI components and layouts
- Research descriptions and documentation
- Public-facing content and pages
- Deployment configuration (e.g. Vercel)

### ❌ This Repository Does NOT Include
- Computational engines
- Integer dynamics logic
- Experiment execution code
- Heavy numerical workloads

Those live in a **separate, private or research-focused repository** by design.

---

## 🎯 Design Principles

- **Clarity over flash**
- **Research-first storytelling**
- **Separation of concerns**
- **Future extensibility**
- **Minimal but serious UI**

The web layer is built to scale with the research, not distract from it.

---

## 🧠 Current Features

- ProofX overview and mission
- Research direction summaries
- Structured content sections
- Clean, minimal design system
- Static-first performance with room for interactivity

---

## 🛣️ Roadmap

Planned enhancements include:
- Interactive visualizations (read-only)
- Experiment result dashboards
- Research logs and updates
- API hooks to external compute services
- Public documentation and citations

---

## 🚀 Getting Started

### Prerequisites
- Node.js 18+
- npm or yarn

### Installation
```bash
git clone https://github.com/your-username/proofx-web.git
cd proofx-web
npm install
