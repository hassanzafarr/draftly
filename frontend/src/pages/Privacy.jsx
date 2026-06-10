import { Link } from "react-router-dom";

export default function Privacy() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-background text-foreground">
      <div className="app-backdrop" />

      <div className="relative z-10">
        {/* Header */}
        <header className="border-b border-hairline bg-surface/60 backdrop-blur-xl">
          <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-4">
            <Link to="/" className="flex items-center gap-2.5">
              <span className="relative flex h-8 w-8 items-center justify-center rounded-lg">
                <span
                  className="absolute inset-0 rounded-lg opacity-60 blur-[8px]"
                  style={{ background: "linear-gradient(135deg, #7c3aed, #2563eb, #06b6d4)" }}
                  aria-hidden
                />
                <img
                  src="/logo.png"
                  alt="Draftly"
                  className="relative h-7 w-7 object-contain drop-shadow-lg"
                />
              </span>
              <span className="font-display text-lg font-semibold tracking-tight text-foreground">
                Draftly
              </span>
            </Link>
            <nav className="flex items-center gap-4 text-sm text-muted-foreground">
              <Link to="/terms" className="transition hover:text-foreground">
                Terms of Service
              </Link>
              <Link
                to="/login"
                className="rounded-lg px-3 py-1.5 text-sm font-medium text-foreground transition"
                style={{
                  background: "linear-gradient(135deg, var(--violet), var(--magenta))",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                }}
              >
                Sign in →
              </Link>
            </nav>
          </div>
        </header>

        {/* Content */}
        <main className="mx-auto max-w-3xl px-6 py-14">
          <h1 className="font-display text-3xl font-semibold tracking-tight text-foreground">
            Privacy Policy
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Effective date: <strong className="text-foreground">[EFFECTIVE_DATE]</strong> · Last
            updated: <strong className="text-foreground">[LAST_UPDATED_DATE]</strong>
          </p>

          <div className="mt-10 space-y-10 text-sm leading-relaxed text-muted-foreground">
            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                1. Introduction and Data Controller
              </h2>
              <p>
                <strong className="text-foreground">[COMPANY_NAME]</strong> (“
                <strong className="text-foreground">Draftly</strong>”, “we”, “us”, or “our”),
                registered at <strong className="text-foreground">[COMPANY_ADDRESS]</strong>,
                operates the Draftly proposal generation platform at{" "}
                <strong className="text-foreground">draftly.software</strong> (the “Service”).
              </p>
              <p className="mt-3">
                This Privacy Policy explains what personal data we collect, why we collect it, how
                we use and protect it, and your rights. Questions? Contact us at{" "}
                <a
                  href="mailto:[PRIVACY_EMAIL]"
                  className="text-foreground underline underline-offset-2 transition hover:opacity-70"
                >
                  [PRIVACY_EMAIL]
                </a>
                .
              </p>
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                2. What Data We Collect
              </h2>
              <div className="space-y-3">
                <div>
                  <strong className="text-foreground">Account data</strong> — your email address and
                  organisation name, collected when you register.
                </div>
                <div>
                  <strong className="text-foreground">Profile data</strong> — avatar URL and Google
                  account ID, only if you sign in with Google.
                </div>
                <div>
                  <strong className="text-foreground">Content data</strong> — documents you upload,
                  RFP text you submit, and proposals generated on your behalf. This data is stored
                  to provide the core Service and is scoped to your organisation.
                </div>
                <div>
                  <strong className="text-foreground">Usage data</strong> — proposal creation
                  counts, document upload counts, and plan tier usage — collected in aggregate to
                  enforce quotas and produce your analytics dashboard.
                </div>
                <div>
                  <strong className="text-foreground">Technical data</strong> — IP address, browser
                  type, and error traces, collected <em>only</em> if you consent to analytics
                  cookies (Sentry error tracking). If you choose “Essential Only”, no technical data
                  is collected by us.
                </div>
                <div>
                  <strong className="text-foreground">Payment data</strong> — billing is handled
                  directly by{" "}
                  <a
                    href="https://stripe.com"
                    className="text-foreground underline underline-offset-2 transition hover:opacity-70"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Stripe
                  </a>
                  . We never see or store your card number, CVC, or bank details. We store only
                  Stripe customer and subscription IDs to manage your plan.
                </div>
              </div>
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                3. How We Use Your Data
              </h2>
              <ul className="list-disc space-y-1.5 pl-4">
                <li>To create and manage your account and organisation.</li>
                <li>
                  To provide the proposal generation Service (RAG retrieval, AI generation, document
                  storage).
                </li>
                <li>
                  To send transactional emails — email verification, password reset, billing
                  receipts.
                </li>
                <li>To process subscription payments through Stripe.</li>
                <li>To enforce plan quotas (document and proposal limits).</li>
                <li>
                  To monitor errors and performance via Sentry —{" "}
                  <em>only with your explicit consent</em>.
                </li>
                <li>
                  To produce the analytics dashboard shown to your organisation (no data shared
                  externally).
                </li>
              </ul>
              <p className="mt-3">
                We do <strong className="text-foreground">not</strong> sell your data to third
                parties, use it for advertising, or train AI models on your documents.
              </p>
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                4. Cookie Policy
              </h2>
              <div className="space-y-3">
                <div>
                  <strong className="text-foreground">Essential storage (always active)</strong> —
                  JWT authentication tokens stored in your browser’s{" "}
                  <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">localStorage</code>.
                  These are necessary for you to stay logged in. They are not advertising cookies
                  and do not track you across websites.
                </div>
                <div>
                  <strong className="text-foreground">Analytics cookies (opt-in only)</strong> — if
                  you click “Accept All” on the consent banner, we load Sentry, which may use
                  browser storage to correlate error sessions. Sentry is configured with text
                  masking and media blocking to minimise exposure of personal data. You can change
                  your preference at any time by clearing your browser’s{" "}
                  <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">localStorage</code> key{" "}
                  <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">
                    draftly-cookie-consent
                  </code>{" "}
                  and reloading.
                </div>
                <div>
                  We use{" "}
                  <strong className="text-foreground">
                    no advertising, social-media, or third-party tracking cookies
                  </strong>
                  .
                </div>
              </div>
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                5. Data Sharing
              </h2>
              <p>We share data only with the following sub-processors:</p>
              <ul className="mt-3 list-disc space-y-1.5 pl-4">
                <li>
                  <strong className="text-foreground">Stripe</strong> — payment processing.{" "}
                  <a
                    href="https://stripe.com/privacy"
                    className="text-foreground underline underline-offset-2 transition hover:opacity-70"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Stripe Privacy Policy
                  </a>
                  .
                </li>
                <li>
                  <strong className="text-foreground">Sentry</strong> — error monitoring (opt-in
                  only).{" "}
                  <a
                    href="https://sentry.io/privacy/"
                    className="text-foreground underline underline-offset-2 transition hover:opacity-70"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Sentry Privacy Policy
                  </a>
                  .
                </li>
                <li>
                  <strong className="text-foreground">Google AI</strong> — document embeddings and
                  proposal generation via API. Input text is sent to Google’s API; it is not used to
                  train Google’s models per their API terms.
                </li>
                <li>
                  <strong className="text-foreground">[HOSTING_PROVIDER]</strong> — infrastructure
                  and database hosting.
                </li>
                <li>
                  <strong className="text-foreground">Resend</strong> — transactional email
                  delivery.
                </li>
              </ul>
              <p className="mt-3">No data is sold to third parties.</p>
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                6. Data Retention
              </h2>
              <p>
                We retain your account and content data for as long as your account is active. If
                you close your account, we will delete your personal data within{" "}
                <strong className="text-foreground">[X] days</strong>, except where retention is
                required by law (e.g., billing records retained for [X] years for tax purposes).
              </p>
              <p className="mt-3">
                To request account deletion, contact{" "}
                <a
                  href="mailto:[PRIVACY_EMAIL]"
                  className="text-foreground underline underline-offset-2 transition hover:opacity-70"
                >
                  [PRIVACY_EMAIL]
                </a>
                .
              </p>
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                7. Your Rights
              </h2>
              <p>Depending on your location, you may have the following rights:</p>
              <ul className="mt-3 list-disc space-y-1.5 pl-4">
                <li>
                  <strong className="text-foreground">Access</strong> — request a copy of the
                  personal data we hold about you.
                </li>
                <li>
                  <strong className="text-foreground">Rectification</strong> — correct inaccurate or
                  incomplete data.
                </li>
                <li>
                  <strong className="text-foreground">Erasure</strong> — request deletion of your
                  data (“right to be forgotten”).
                </li>
                <li>
                  <strong className="text-foreground">Restriction</strong> — ask us to pause
                  processing your data.
                </li>
                <li>
                  <strong className="text-foreground">Portability</strong> — receive your data in a
                  machine-readable format.
                </li>
                <li>
                  <strong className="text-foreground">Objection</strong> — object to processing
                  based on legitimate interests.
                </li>
                <li>
                  <strong className="text-foreground">Withdraw consent</strong> — opt out of
                  analytics cookies at any time (see Cookie Policy above).
                </li>
              </ul>
              <p className="mt-3">
                To exercise any right, contact{" "}
                <a
                  href="mailto:[PRIVACY_EMAIL]"
                  className="text-foreground underline underline-offset-2 transition hover:opacity-70"
                >
                  [PRIVACY_EMAIL]
                </a>
                . We will respond within 30 days.
              </p>
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                8. Security
              </h2>
              <p>
                We use HTTPS, JWT authentication, database-level row isolation per organisation, and
                access controls to protect your data. Passwords are hashed with Django’s default
                PBKDF2 algorithm. No system is perfectly secure — if you discover a vulnerability,
                please report it to{" "}
                <a
                  href="mailto:[PRIVACY_EMAIL]"
                  className="text-foreground underline underline-offset-2 transition hover:opacity-70"
                >
                  [PRIVACY_EMAIL]
                </a>
                .
              </p>
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                9. Changes to This Policy
              </h2>
              <p>
                We may update this policy. Material changes will be communicated by email at least{" "}
                <strong className="text-foreground">[X] days</strong> before they take effect.
                Continued use of the Service after that date constitutes acceptance of the updated
                policy.
              </p>
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                10. Contact
              </h2>
              <p>
                <strong className="text-foreground">[COMPANY_NAME]</strong>
                <br />
                <strong className="text-foreground">[COMPANY_ADDRESS]</strong>
                <br />
                Email:{" "}
                <a
                  href="mailto:[PRIVACY_EMAIL]"
                  className="text-foreground underline underline-offset-2 transition hover:opacity-70"
                >
                  [PRIVACY_EMAIL]
                </a>
              </p>
            </section>
          </div>
        </main>

        {/* Footer */}
        <footer className="border-t border-hairline py-8 text-center text-xs text-muted-foreground">
          <span>© [YEAR] [COMPANY_NAME]. All rights reserved.</span>
          <span className="mx-3">·</span>
          <Link to="/terms" className="transition hover:text-foreground">
            Terms of Service
          </Link>
          <span className="mx-3">·</span>
          <Link to="/privacy" className="text-foreground">
            Privacy Policy
          </Link>
        </footer>
      </div>
    </div>
  );
}
