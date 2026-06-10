import { Link } from "react-router-dom";

export default function Terms() {
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
              <Link to="/privacy" className="transition hover:text-foreground">
                Privacy Policy
              </Link>
              <Link
                to="/login"
                className="rounded-lg px-3 py-1.5 text-sm font-medium transition"
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
            Terms of Service
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Effective date: <strong className="text-foreground">[EFFECTIVE_DATE]</strong> · Last
            updated: <strong className="text-foreground">[LAST_UPDATED_DATE]</strong>
          </p>

          <div className="mt-10 space-y-10 text-sm leading-relaxed text-muted-foreground">
            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                1. Acceptance of Terms
              </h2>
              <p>
                By creating an account or using the Draftly Service, you agree to be bound by these
                Terms of Service (“Terms”) and our{" "}
                <Link
                  to="/privacy"
                  className="text-foreground underline underline-offset-2 transition hover:opacity-70"
                >
                  Privacy Policy
                </Link>
                . If you do not agree, do not use the Service.
              </p>
              <p className="mt-3">
                You must be at least <strong className="text-foreground">18 years old</strong> to
                create an account. By registering, you represent that you meet this requirement.
              </p>
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                2. Description of Service
              </h2>
              <p>
                Draftly is a proposal generation platform operated by{" "}
                <strong className="text-foreground">[COMPANY_NAME]</strong>. The Service allows
                organisations to upload reference documents, submit RFP (Request for Proposal) text,
                and receive AI-generated proposal drafts using retrieval-augmented generation (RAG).
              </p>
              <p className="mt-3">
                The Service is provided on a subscription basis. Features and limits vary by plan
                tier.
              </p>
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                3. Account Registration
              </h2>
              <ul className="list-disc space-y-1.5 pl-4">
                <li>
                  You must provide accurate, complete information during registration and keep it up
                  to date.
                </li>
                <li>One account per person. You may not share login credentials.</li>
                <li>
                  You are responsible for maintaining the security of your password and all activity
                  under your account.
                </li>
                <li>
                  Notify us immediately at{" "}
                  <a
                    href="mailto:[COMPANY_EMAIL]"
                    className="text-foreground underline underline-offset-2 transition hover:opacity-70"
                  >
                    [COMPANY_EMAIL]
                  </a>{" "}
                  if you suspect unauthorised access.
                </li>
                <li>Email verification is required before your account is activated.</li>
              </ul>
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                4. Acceptable Use
              </h2>
              <p>You agree not to use the Service to:</p>
              <ul className="mt-3 list-disc space-y-1.5 pl-4">
                <li>
                  Upload, generate, or distribute content that is illegal, defamatory, fraudulent,
                  or infringes third-party intellectual property.
                </li>
                <li>
                  Attempt to reverse-engineer, decompile, or extract the underlying AI models or
                  system prompts.
                </li>
                <li>
                  Use automated means (scrapers, bots) to access the Service in ways that exceed
                  normal usage or harm performance for other users.
                </li>
                <li>
                  Resell, sublicense, or redistribute access to the Service without prior written
                  consent.
                </li>
                <li>Circumvent quota limits, billing, or authentication mechanisms.</li>
              </ul>
              <p className="mt-3">
                We reserve the right to suspend or terminate accounts that violate these rules
                without prior notice.
              </p>
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                5. Subscription and Billing
              </h2>
              <p>
                Paid plans are billed on a monthly or annual basis through{" "}
                <a
                  href="https://stripe.com"
                  className="text-foreground underline underline-offset-2 transition hover:opacity-70"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Stripe
                </a>
                . By subscribing, you authorise us to charge your payment method on a recurring
                basis.
              </p>
              <ul className="mt-3 list-disc space-y-1.5 pl-4">
                <li>
                  <strong className="text-foreground">Refunds:</strong> [REFUND_POLICY_DETAIL].
                </li>
                <li>
                  <strong className="text-foreground">Cancellation:</strong> You may cancel at any
                  time via the Customer Portal. Access continues until the end of the current
                  billing period.
                </li>
                <li>
                  <strong className="text-foreground">Price changes:</strong> We will notify you at
                  least <strong className="text-foreground">[X] days</strong> before any price
                  increase. Continued use after the effective date constitutes acceptance.
                </li>
                <li>
                  <strong className="text-foreground">Failed payments:</strong> If payment fails,
                  your account may be downgraded to the free tier after a grace period.
                </li>
                <li>
                  All fees are exclusive of applicable taxes. We may collect VAT or sales tax as
                  required by law.
                </li>
              </ul>
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                6. Intellectual Property
              </h2>
              <div className="space-y-3">
                <div>
                  <strong className="text-foreground">Your content</strong> — documents, RFP text,
                  and generated proposals belong to you. You grant Draftly a limited, non-exclusive
                  licence to process this content solely to provide the Service. We do not use your
                  content to train AI models or share it with other customers.
                </div>
                <div>
                  <strong className="text-foreground">Our IP</strong> — the Draftly platform, UI,
                  brand, system prompts, and underlying technology remain the exclusive property of
                  [COMPANY_NAME]. No rights are transferred to you except the licence to use the
                  Service.
                </div>
              </div>
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                7. Data Processing
              </h2>
              <p>
                Our collection and use of personal data is described in our{" "}
                <Link
                  to="/privacy"
                  className="text-foreground underline underline-offset-2 transition hover:opacity-70"
                >
                  Privacy Policy
                </Link>
                . By using the Service, you agree to that policy. For enterprise customers requiring
                a Data Processing Agreement (DPA), contact{" "}
                <a
                  href="mailto:[LEGAL_EMAIL]"
                  className="text-foreground underline underline-offset-2 transition hover:opacity-70"
                >
                  [LEGAL_EMAIL]
                </a>
                .
              </p>
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                8. Disclaimer of Warranties
              </h2>
              <p>
                THE SERVICE IS PROVIDED “AS IS” AND “AS AVAILABLE” WITHOUT WARRANTY OF ANY KIND,
                EXPRESS OR IMPLIED, INCLUDING WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
                PARTICULAR PURPOSE, OR NON-INFRINGEMENT. We do not warrant that the Service will be
                uninterrupted, error-free, or that AI-generated proposals will be accurate,
                complete, or suitable for any particular use.
              </p>
              <p className="mt-3">
                Generated proposals are AI-assisted drafts. You are responsible for reviewing,
                editing, and verifying any content before submission to third parties.
              </p>
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                9. Limitation of Liability
              </h2>
              <p>
                TO THE MAXIMUM EXTENT PERMITTED BY LAW, [COMPANY_NAME] SHALL NOT BE LIABLE FOR ANY
                INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, OR ANY LOSS OF
                PROFITS, REVENUE, DATA, OR BUSINESS OPPORTUNITIES, ARISING FROM YOUR USE OF THE
                SERVICE, EVEN IF WE HAVE BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.
              </p>
              <p className="mt-3">
                OUR TOTAL LIABILITY FOR ANY CLAIM ARISING UNDER THESE TERMS SHALL NOT EXCEED THE
                AMOUNT YOU PAID TO US IN THE <strong className="text-foreground">12 MONTHS</strong>{" "}
                PRECEDING THE CLAIM.
              </p>
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                10. Governing Law and Disputes
              </h2>
              <p>
                These Terms are governed by the laws of{" "}
                <strong className="text-foreground">[JURISDICTION]</strong>,{" "}
                <strong className="text-foreground">[COUNTRY]</strong>, without regard to
                conflict-of-law principles. Any disputes shall be resolved in the courts of{" "}
                <strong className="text-foreground">[JURISDICTION]</strong>.
              </p>
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                11. Changes to These Terms
              </h2>
              <p>
                We may update these Terms. We will notify you by email and/or in-app notice at least{" "}
                <strong className="text-foreground">[X] days</strong> before material changes take
                effect. Continued use of the Service after the effective date constitutes acceptance
                of the updated Terms.
              </p>
              <p className="mt-3">
                If you do not agree to the updated Terms, you must stop using the Service and may
                cancel your subscription for a pro-rated refund at our discretion.
              </p>
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                12. Contact
              </h2>
              <p>
                For legal enquiries:
                <br />
                <strong className="text-foreground">[COMPANY_NAME]</strong>
                <br />
                <strong className="text-foreground">[COMPANY_ADDRESS]</strong>
                <br />
                Email:{" "}
                <a
                  href="mailto:[LEGAL_EMAIL]"
                  className="text-foreground underline underline-offset-2 transition hover:opacity-70"
                >
                  [LEGAL_EMAIL]
                </a>
              </p>
            </section>
          </div>
        </main>

        {/* Footer */}
        <footer className="border-t border-hairline py-8 text-center text-xs text-muted-foreground">
          <span>© [YEAR] [COMPANY_NAME]. All rights reserved.</span>
          <span className="mx-3">·</span>
          <Link to="/terms" className="text-foreground">
            Terms of Service
          </Link>
          <span className="mx-3">·</span>
          <Link to="/privacy" className="transition hover:text-foreground">
            Privacy Policy
          </Link>
        </footer>
      </div>
    </div>
  );
}
