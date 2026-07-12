/**
 * ProofX frontend error monitoring via Sentry.
 *
 * Setup:
 *   1. Create a free project at https://sentry.io
 *   2. Replace SENTRY_DSN below with your project DSN
 *   3. Optionally set SENTRY_ENV via your CI/CD environment
 *
 * This file is loaded before other scripts so it captures all errors.
 */

(function initMonitoring() {
  const SENTRY_DSN = window.__SENTRY_DSN__ || "";
  const SENTRY_ENV = window.__SENTRY_ENV__ || "production";
  const SENTRY_RELEASE = window.__SENTRY_RELEASE__ || "proofx@unknown";

  if (!SENTRY_DSN) {
    // No DSN configured — fail silently in production, warn in dev
    if (location.hostname === "localhost" || location.hostname === "127.0.0.1") {
      console.info("[ProofX monitoring] Sentry DSN not set. Set window.__SENTRY_DSN__ to enable.");
    }
    return;
  }

  // Dynamically load the Sentry SDK only when DSN is present
  const script = document.createElement("script");
  script.src = "https://browser.sentry-cdn.com/7.119.0/bundle.tracing.min.js";
  script.crossOrigin = "anonymous";
  script.integrity = "sha384-placeholder"; // replace with the actual SRI hash from Sentry docs

  script.onload = function () {
    if (typeof Sentry === "undefined") return;

    Sentry.init({
      dsn: SENTRY_DSN,
      environment: SENTRY_ENV,
      release: SENTRY_RELEASE,

      // Capture 10% of transactions for performance monitoring
      tracesSampleRate: 0.1,

      // Ignore known noisy errors
      ignoreErrors: [
        "ResizeObserver loop limit exceeded",
        "Non-Error promise rejection captured",
        /^Script error\.?$/,
      ],

      beforeSend(event) {
        // Strip PII from breadcrumbs before sending
        if (event.breadcrumbs) {
          event.breadcrumbs.values = (event.breadcrumbs.values || []).map((b) => {
            if (b.data && b.data.url) {
              try {
                const u = new URL(b.data.url);
                u.search = "";
                b.data.url = u.toString();
              } catch (_) {}
            }
            return b;
          });
        }
        return event;
      },
    });
  };

  // Insert before first script tag
  const firstScript = document.getElementsByTagName("script")[0];
  firstScript.parentNode.insertBefore(script, firstScript);
})();
