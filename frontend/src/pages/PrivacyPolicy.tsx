import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

export default function PrivacyPolicy() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-16 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        {/* Back Link */}
        <Link
          to="/legal"
          className="inline-flex items-center gap-2 text-purple-600 dark:text-purple-400 hover:underline mb-8 text-sm"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Legal Documents
        </Link>

        <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">
          Privacy Policy
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-500 mb-10">
          Last updated: March 23, 2026
        </p>

        <div className="prose prose-gray dark:prose-invert max-w-none space-y-8 text-gray-700 dark:text-gray-300">
          {/* 1. Introduction */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              1. Introduction
            </h2>
            <p>
              People Protocol Inc. ("Company," "we," "us," or "our") is
              committed to protecting your privacy. This Privacy Policy explains
              how we collect, use, disclose, and safeguard your personal
              information when you use the LitInkAI platform and services
              (collectively, the "Service"), accessible at litink.ai.
            </p>
            <p>
              We comply with the Personal Information Protection and Electronic
              Documents Act (PIPEDA), Canada's federal privacy law, and strive
              to meet the standards of the European Union's General Data
              Protection Regulation (GDPR) for our international users. Where
              applicable, we also comply with the California Consumer Privacy Act
              (CCPA/CPRA).
            </p>
          </section>

          {/* 2. Application of this Policy */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              2. Application of this Policy
            </h2>
            <p>
              This Privacy Policy applies to all users of the Service, including
              visitors to our website, registered users, and subscribers. It
              covers information collected through the Service, email
              communications, and interactions with our support team.
            </p>
            <p>
              This Policy does not apply to third-party websites, services, or
              applications that may be linked from or integrated with the
              Service. We encourage you to review the privacy policies of any
              third-party services you interact with.
            </p>
          </section>

          {/* 3. What Information We Collect & Why */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              3. What Information We Collect &amp; Why
            </h2>

            <h3 className="text-lg font-medium text-gray-800 dark:text-gray-200 mt-4">
              3.1 Information You Provide
            </h3>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>
                <strong>Account Information:</strong> Name, email address,
                password (encrypted), and profile details when you create an
                account.
              </li>
              <li>
                <strong>Payment Information:</strong> Billing address, payment
                method details. Payment processing is handled by Stripe — we do
                not directly store your full credit card numbers.
              </li>
              <li>
                <strong>User Content:</strong> Scripts, stories, prompts,
                uploaded documents, voice recordings, images, and other materials
                you submit to the Service ("Input Content").
              </li>
              <li>
                <strong>Generated Content:</strong> AI-generated images, videos,
                voiceovers, music, and other outputs produced by the Service
                based on your Input Content.
              </li>
              <li>
                <strong>Communications:</strong> Emails, support requests,
                feedback, and other communications you send to us.
              </li>
            </ul>

            <h3 className="text-lg font-medium text-gray-800 dark:text-gray-200 mt-4">
              3.2 Information Collected Automatically
            </h3>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>
                <strong>Usage Data:</strong> Pages visited, features used,
                generation history, credit consumption, time spent on the
                platform, click patterns, and interaction data.
              </li>
              <li>
                <strong>Device Information:</strong> IP address, browser type and
                version, operating system, device identifiers, and screen
                resolution.
              </li>
              <li>
                <strong>Cookies &amp; Tracking Technologies:</strong> We use
                cookies, local storage, and similar technologies to maintain your
                session, remember preferences, and analyze usage patterns. See
                Section 10 for details.
              </li>
              <li>
                <strong>Log Data:</strong> Server logs that record requests,
                errors, timestamps, and referral URLs.
              </li>
            </ul>
          </section>

          {/* 4. How We Use Your Information */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              4. How We Use Your Information
            </h2>
            <p>We use the information we collect for the following purposes:</p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>
                <strong>Service Delivery:</strong> To process your Input Content,
                generate outputs, manage your account, and provide the core
                functionality of the platform.
              </li>
              <li>
                <strong>Billing &amp; Payments:</strong> To process
                subscriptions, credit purchases, and manage your billing history
                through Stripe.
              </li>
              <li>
                <strong>Communication:</strong> To send transactional emails
                (account confirmations, password resets, billing receipts),
                respond to support requests, and send service updates.
              </li>
              <li>
                <strong>Analytics &amp; Improvement:</strong> To understand how
                users interact with the Service, identify trends, diagnose
                issues, and improve features.
              </li>
              <li>
                <strong>Security:</strong> To detect, prevent, and respond to
                fraud, abuse, security incidents, and technical issues.
              </li>
              <li>
                <strong>Legal Compliance:</strong> To comply with legal
                obligations, enforce our Terms of Service, and protect our
                rights.
              </li>
              <li>
                <strong>Marketing (with consent):</strong> To send promotional
                communications about new features, offers, and updates — only
                with your explicit opt-in consent per CASL requirements.
              </li>
            </ul>
          </section>

          {/* 5. How We Share Your Information */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              5. How We Share Your Information
            </h2>
            <p>
              <strong>We do not sell your personal information.</strong> We share
              information only in the following circumstances:
            </p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>
                <strong>Service Providers:</strong> With trusted third-party
                providers who assist us in operating the Service, including
                Stripe (payments), cloud hosting providers (data storage and
                processing), AI model providers (content generation), email
                delivery services, and analytics platforms. These providers are
                contractually bound to protect your information.
              </li>
              <li>
                <strong>Legal Requirements:</strong> When required by law, legal
                process, or government request, or when we believe disclosure is
                necessary to protect our rights, your safety, or the safety of
                others.
              </li>
              <li>
                <strong>Business Transfers:</strong> In connection with a merger,
                acquisition, reorganization, or sale of assets, your information
                may be transferred to the acquiring entity.
              </li>
              <li>
                <strong>With Your Consent:</strong> In any other circumstance
                where we have your explicit consent to share.
              </li>
            </ul>
          </section>

          {/* 6. Data Storage & International Transfers */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              6. Data Storage &amp; International Transfers
            </h2>
            <p>
              Your information is primarily stored on servers located in Canada
              and the United States. By using the Service, you acknowledge that
              your information may be transferred to, stored, and processed in
              countries other than your country of residence, including countries
              that may have different data protection laws.
            </p>
            <p>
              Where we transfer personal data internationally, we implement
              appropriate safeguards, including standard contractual clauses
              approved by relevant data protection authorities, to ensure your
              information receives an adequate level of protection.
            </p>
          </section>

          {/* 7. User Rights (PIPEDA & GDPR) */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              7. Your Rights
            </h2>
            <p>
              Depending on your location, you may have the following rights
              regarding your personal information:
            </p>

            <h3 className="text-lg font-medium text-gray-800 dark:text-gray-200 mt-4">
              Under PIPEDA (Canadian Users)
            </h3>
            <ul className="list-disc list-inside space-y-1 ml-4">
              <li>Right to access your personal information</li>
              <li>Right to request correction of inaccurate information</li>
              <li>Right to withdraw consent for data collection and use</li>
              <li>Right to file a complaint with the Privacy Commissioner of Canada</li>
            </ul>

            <h3 className="text-lg font-medium text-gray-800 dark:text-gray-200 mt-4">
              Under GDPR (EU/EEA Users)
            </h3>
            <ul className="list-disc list-inside space-y-1 ml-4">
              <li>Right of access (Article 15)</li>
              <li>Right to rectification (Article 16)</li>
              <li>Right to erasure / "right to be forgotten" (Article 17)</li>
              <li>Right to restriction of processing (Article 18)</li>
              <li>Right to data portability (Article 20)</li>
              <li>Right to object to processing (Article 21)</li>
              <li>Right not to be subject to automated decision-making (Article 22)</li>
            </ul>

            <h3 className="text-lg font-medium text-gray-800 dark:text-gray-200 mt-4">
              Under CCPA/CPRA (California Users)
            </h3>
            <ul className="list-disc list-inside space-y-1 ml-4">
              <li>Right to know what information we collect</li>
              <li>Right to delete personal information</li>
              <li>Right to opt-out of sale of personal information (we do not sell your data)</li>
              <li>Right to non-discrimination for exercising your rights</li>
            </ul>

            <h3 className="text-lg font-medium text-gray-800 dark:text-gray-200 mt-4">
              Model Training Opt-Out
            </h3>
            <p>
              You have the right to opt out of having your content used for AI
              model training at any time. You can manage this in your account
              settings or by emailing{" "}
              <a href="mailto:privacy@litink.ai" className="text-purple-600 dark:text-purple-400 hover:underline">
                privacy@litink.ai
              </a>
              .
            </p>

            <p className="mt-4">
              To exercise any of these rights, contact us at{" "}
              <a href="mailto:privacy@litink.ai" className="text-purple-600 dark:text-purple-400 hover:underline">
                privacy@litink.ai
              </a>
              . We will respond to all requests within 30 days (or as required
              by applicable law).
            </p>
          </section>

          {/* 8. Data Security */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              8. Data Security
            </h2>
            <p>
              We implement industry-standard technical and organizational
              measures to protect your personal information, including:
            </p>
            <ul className="list-disc list-inside space-y-1 ml-4">
              <li>Encryption of data in transit (TLS/SSL) and at rest</li>
              <li>Secure password hashing (bcrypt)</li>
              <li>Regular security audits and vulnerability assessments</li>
              <li>Access controls and role-based permissions for employees</li>
              <li>Monitoring for unauthorized access attempts</li>
            </ul>
            <p className="mt-2">
              While we strive to protect your information, no method of
              electronic transmission or storage is 100% secure. We cannot
              guarantee absolute security but will notify you of any data breach
              as required by applicable law.
            </p>
          </section>

          {/* 9. Data Retention */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              9. Data Retention
            </h2>
            <p>
              We retain your personal information for as long as necessary to
              provide the Service and fulfill the purposes described in this
              Policy:
            </p>
            <ul className="list-disc list-inside space-y-1 ml-4">
              <li>
                <strong>Active Accounts:</strong> Data is retained for the
                duration of your account.
              </li>
              <li>
                <strong>Deleted Accounts:</strong> Account data is deleted within
                30 days of account termination, except where retention is
                required by law (e.g., billing records for tax purposes).
              </li>
              <li>
                <strong>Generated Content:</strong> Stored for the duration of
                your account and deleted within 30 days of termination.
              </li>
              <li>
                <strong>Log Data:</strong> Retained for up to 12 months for
                security and analytics purposes.
              </li>
              <li>
                <strong>Billing Records:</strong> Retained for 7 years as
                required by Canadian tax law.
              </li>
            </ul>
          </section>

          {/* 10. Cookie Policy */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              10. Cookies &amp; Tracking Technologies
            </h2>
            <p>We use the following types of cookies and similar technologies:</p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>
                <strong>Essential Cookies:</strong> Required for the Service to
                function (authentication, session management, security). Cannot
                be disabled.
              </li>
              <li>
                <strong>Preference Cookies:</strong> Remember your settings,
                such as theme (dark/light mode) and language preferences.
              </li>
              <li>
                <strong>Analytics Cookies:</strong> Help us understand how users
                interact with the Service (page views, feature usage, error
                tracking). We use privacy-respecting analytics tools.
              </li>
            </ul>
            <p className="mt-2">
              You can manage cookie preferences through your browser settings.
              Disabling essential cookies may impair the functionality of the
              Service.
            </p>
          </section>

          {/* 11. Children's Policy */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              11. Children's Privacy
            </h2>
            <p>
              The Service is not intended for use by anyone under 18 years of
              age. We do not knowingly collect personal information from children
              under 18. If we become aware that we have collected personal
              information from a child under 18, we will take steps to delete
              that information promptly. If you believe a child under 18 has
              provided us with personal information, please contact us at{" "}
              <a href="mailto:privacy@litink.ai" className="text-purple-600 dark:text-purple-400 hover:underline">
                privacy@litink.ai
              </a>
              .
            </p>
          </section>

          {/* 12. Changes to this Policy */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              12. Changes to this Policy
            </h2>
            <p>
              We may update this Privacy Policy from time to time to reflect
              changes in our practices, technologies, legal requirements, or
              other factors. When we make material changes, we will notify you by
              email and/or by posting a notice on the Service at least 30 days
              before the changes take effect.
            </p>
            <p>
              We encourage you to review this Policy periodically. Your
              continued use of the Service after any changes constitutes your
              acceptance of the updated Policy.
            </p>
          </section>

          {/* 13. Contact / Data Protection Officer */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              13. Contact &amp; Data Protection
            </h2>
            <p>
              If you have questions, concerns, or requests regarding this Privacy
              Policy or our data practices, please contact us:
            </p>
            <div className="mt-2 bg-gray-100 dark:bg-gray-800 rounded-lg p-4">
              <p className="font-medium text-gray-900 dark:text-white">
                People Protocol Inc. — Privacy Team
              </p>
              <p>Alberta, Canada</p>
              <p>
                Privacy inquiries:{" "}
                <a href="mailto:privacy@litink.ai" className="text-purple-600 dark:text-purple-400 hover:underline">
                  privacy@litink.ai
                </a>
              </p>
              <p>
                General:{" "}
                <a href="mailto:contact@peopleprotocol.ca" className="text-purple-600 dark:text-purple-400 hover:underline">
                  contact@peopleprotocol.ca
                </a>
              </p>
            </div>
            <p className="mt-4">
              <strong>For Canadian residents:</strong> If you are not satisfied
              with our response, you have the right to file a complaint with the{" "}
              <a
                href="https://www.priv.gc.ca"
                target="_blank"
                rel="noopener noreferrer"
                className="text-purple-600 dark:text-purple-400 hover:underline"
              >
                Office of the Privacy Commissioner of Canada
              </a>
              .
            </p>
            <p>
              <strong>For EU residents:</strong> You may file a complaint with
              your local supervisory authority under GDPR.
            </p>
          </section>
        </div>

        {/* Back to Legal Hub */}
        <div className="mt-12 text-center">
          <Link
            to="/legal"
            className="inline-flex items-center gap-2 text-purple-600 dark:text-purple-400 hover:underline text-sm"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Legal Documents
          </Link>
        </div>
      </div>
    </div>
  );
}
