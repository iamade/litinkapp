import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

export default function TermsOfService() {
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
          Terms of Service
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-500 mb-10">
          Last updated: March 23, 2026
        </p>

        <div className="prose prose-gray dark:prose-invert max-w-none space-y-8 text-gray-700 dark:text-gray-300">
          {/* 1. Introduction & Acceptance */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              1. Introduction &amp; Acceptance
            </h2>
            <p>
              Welcome to LitInkAI. These Terms of Service ("Terms") constitute a
              legally binding agreement between you ("User," "you," or "your")
              and People Protocol Inc., an Alberta, Canada corporation
              ("Company," "we," "us," or "our"), governing your access to and
              use of the LitInkAI platform, available at litink.ai and through
              our applications (collectively, the "Service").
            </p>
            <p>
              By creating an account, accessing, or using the Service, you
              acknowledge that you have read, understood, and agree to be bound
              by these Terms, our{" "}
              <Link to="/privacy" className="text-purple-600 dark:text-purple-400 hover:underline">
                Privacy Policy
              </Link>
              , and our Acceptable Use Policy (Section 7). If you do not agree
              to these Terms, you must not use the Service.
            </p>
            <p>
              These Terms apply to all visitors, users, and others who access or
              use the Service, whether on a free or paid plan.
            </p>
          </section>

          {/* 2. Service Description */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              2. Service Description
            </h2>
            <p>
              LitInkAI is an AI-powered story-to-screen video generation
              platform. The Service enables users to transform written content —
              including scripts, stories, books, screenplays, and text prompts —
              into complete videos using artificial intelligence technologies
              including, but not limited to, text analysis, AI image generation,
              AI video generation, AI voiceover synthesis, AI music composition,
              and automated post-production.
            </p>
            <p>
              The Service operates through a multi-agent AI architecture in which
              specialized AI systems collaborate to produce creative outputs. The
              specific AI models, technologies, and features available may change
              over time as we improve and update the Service.
            </p>
          </section>

          {/* 3. Eligibility & Age Restrictions */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              3. Eligibility &amp; Age Restrictions
            </h2>
            <p>
              You must be at least 18 years of age (or the age of majority in
              your jurisdiction, whichever is greater) to create an account and
              use the Service. By using the Service, you represent and warrant
              that you meet this age requirement.
            </p>
            <p>
              If you are using the Service on behalf of a business, organization,
              or other entity, you represent and warrant that you have the
              authority to bind that entity to these Terms, and "you" refers to
              both you individually and that entity.
            </p>
          </section>

          {/* 4. Account Registration & Security */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              4. Account Registration &amp; Security
            </h2>
            <p>
              To access certain features of the Service, you must create an
              account. You agree to provide accurate, current, and complete
              information during registration and to keep your account
              information updated. You are responsible for safeguarding your
              account credentials (including passwords and API keys) and for all
              activities that occur under your account.
            </p>
            <p>
              You must notify us immediately at{" "}
              <a href="mailto:contact@peopleprotocol.ca" className="text-purple-600 dark:text-purple-400 hover:underline">
                contact@peopleprotocol.ca
              </a>{" "}
              if you suspect unauthorized access to your account. We are not
              liable for any loss arising from unauthorized use of your account
              where you have failed to maintain the security of your credentials.
            </p>
          </section>

          {/* 5. Subscriptions, Fees, Credits & Payment */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              5. Subscriptions, Fees, Credits &amp; Payment
            </h2>

            <h3 className="text-lg font-medium text-gray-800 dark:text-gray-200 mt-4">
              5.1 Subscription Plans
            </h3>
            <p>The Service is offered through the following plans:</p>
            <ul className="list-disc list-inside space-y-1 ml-4">
              <li>
                <strong>Free:</strong> Limited access with 100 credits, watermarked outputs, and restricted features.
              </li>
              <li>
                <strong>Basic ($29/month):</strong> 1,500 credits/month, 720p resolution, watermark removal at download.
              </li>
              <li>
                <strong>Standard ($79/month):</strong> 5,000 credits/month, 1080p resolution, AI model selection, voice cloning, priority processing.
              </li>
              <li>
                <strong>Premium ($199/month):</strong> 15,000 credits/month, 4K resolution, API access, priority processing.
              </li>
              <li>
                <strong>Professional ($499/month):</strong> 50,000 credits/month, 4K resolution, unlimited uploads, dedicated support.
              </li>
              <li>
                <strong>Enterprise (custom pricing):</strong> Tailored solutions with unlimited credits, 8K resolution, dedicated support, and SLA agreements.
              </li>
            </ul>
            <p>
              Plan details, features, and credit allocations are described on our
              pricing page and may be updated from time to time.
            </p>

            <h3 className="text-lg font-medium text-gray-800 dark:text-gray-200 mt-4">
              5.2 Billing &amp; Auto-Renewal
            </h3>
            <p>
              Paid subscriptions are billed on a recurring monthly or annual
              basis, depending on the billing cycle you select. Subscriptions
              automatically renew at the end of each billing period unless you
              cancel before the renewal date. Payment is processed through
              Stripe, our third-party payment processor, and is subject to
              Stripe's terms of service.
            </p>

            <h3 className="text-lg font-medium text-gray-800 dark:text-gray-200 mt-4">
              5.3 Credit System
            </h3>
            <p>
              The Service operates on a credit-based consumption model. Credits
              are consumed when you use AI generation features including, but not
              limited to, image generation, video generation, voiceover
              synthesis, and music composition. Credit costs vary by feature and
              are displayed before each generation.
            </p>
            <p>
              Credits have no monetary value outside the Service, are
              non-transferable, and are non-refundable. Unused credits on monthly
              plans do not roll over unless explicitly stated in your plan terms.
              Credits purchased as add-ons may have different expiry terms as
              specified at the time of purchase.
            </p>

            <h3 className="text-lg font-medium text-gray-800 dark:text-gray-200 mt-4">
              5.4 Refund Policy
            </h3>
            <p>
              All payments are non-refundable except where required by applicable
              law (including Alberta consumer protection law). If you believe you
              are entitled to a refund, contact{" "}
              <a href="mailto:contact@peopleprotocol.ca" className="text-purple-600 dark:text-purple-400 hover:underline">
                contact@peopleprotocol.ca
              </a>
              .
            </p>

            <h3 className="text-lg font-medium text-gray-800 dark:text-gray-200 mt-4">
              5.5 Taxes
            </h3>
            <p>
              All fees are exclusive of applicable taxes. Canadian users are
              subject to GST/HST as required by law. You are responsible for any
              taxes applicable in your jurisdiction.
            </p>

            <h3 className="text-lg font-medium text-gray-800 dark:text-gray-200 mt-4">
              5.6 Fee Changes
            </h3>
            <p>
              We reserve the right to change subscription fees upon 30 days'
              written notice (via email or in-app notification) to existing
              subscribers. Continued use after the effective date constitutes
              acceptance of the new fees.
            </p>
          </section>

          {/* 6. Content & Ownership */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              6. Content &amp; Ownership
            </h2>

            <h3 className="text-lg font-medium text-gray-800 dark:text-gray-200 mt-4">
              6.1 Your Input Content
            </h3>
            <p>
              You retain all ownership rights in the content you provide to the
              Service ("Input Content"), including scripts, stories, prompts,
              uploaded documents, voice recordings, images, and other materials.
              You represent and warrant that you have all necessary rights,
              licenses, and permissions to use and submit your Input Content, and
              that your Input Content does not infringe upon any third party's
              intellectual property rights.
            </p>

            <h3 className="text-lg font-medium text-gray-800 dark:text-gray-200 mt-4">
              6.2 AI-Generated Content (Output)
            </h3>
            <p>
              Subject to these Terms and your compliance with the Acceptable Use
              Policy, we assign to you all rights, title, and interest in the
              AI-generated content produced by the Service based on your Input
              Content ("Generated Content"), to the fullest extent permitted by
              applicable law. This includes images, videos, voiceovers, music,
              and other media generated by the platform.
            </p>
            <p>
              <strong>Free Plan Users:</strong> Generated Content on the Free
              plan is licensed to you under a non-exclusive, non-commercial
              license. You may not use Free-tier Generated Content for commercial
              purposes without upgrading to a paid plan.
            </p>
            <p>
              <strong>Paid Plan Users:</strong> Generated Content on paid plans
              (Creator, Studio, Enterprise) is assigned to you for both personal
              and commercial use, to the fullest extent permitted by law.
            </p>
            <p>
              <strong>Important Notice:</strong> The legal status of copyright in
              AI-generated works is evolving and may vary by jurisdiction. We
              make no representation or warranty that Generated Content will
              receive copyright protection in any particular jurisdiction.
            </p>

            <h3 className="text-lg font-medium text-gray-800 dark:text-gray-200 mt-4">
              6.3 License to LitInkAI
            </h3>
            <p>
              By using the Service, you grant People Protocol Inc. a
              non-exclusive, worldwide, royalty-free, sublicensable license to
              use, reproduce, store, modify, and display your Input Content and
              Generated Content solely for the purposes of: (a) providing,
              operating, and maintaining the Service; (b) improving and
              developing the Service; and (c) as otherwise described in our
              Privacy Policy. This license survives termination of your account
              to the extent necessary for operational purposes (e.g., cached
              data, backups).
            </p>

            <h3 className="text-lg font-medium text-gray-800 dark:text-gray-200 mt-4">
              6.4 Platform Intellectual Property
            </h3>
            <p>
              All rights, title, and interest in the Service — including the
              platform, AI models, algorithms, software, design, branding,
              trademarks, documentation, and all other intellectual property —
              are and remain the exclusive property of People Protocol Inc. and
              its licensors. Nothing in these Terms grants you any rights in our
              intellectual property except the limited right to use the Service
              as described herein.
            </p>
          </section>

          {/* 7. Acceptable Use Policy */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              7. Acceptable Use Policy
            </h2>
            <p>
              You agree not to use the Service to create, upload, store, or
              distribute content that:
            </p>
            <ul className="list-disc list-inside space-y-1 ml-4">
              <li>
                Constitutes, depicts, or promotes child sexual abuse material
                (CSAM) in any form
              </li>
              <li>
                Contains non-consensual intimate imagery or deepfakes of real
                persons without their explicit consent
              </li>
              <li>
                Promotes or incites hatred, violence, or discrimination based on
                race, ethnicity, gender, religion, sexual orientation,
                disability, or other protected characteristics
              </li>
              <li>Contains extreme or gratuitous violence</li>
              <li>Promotes self-harm, suicide, or eating disorders</li>
              <li>
                Infringes upon any third party's intellectual property rights,
                including copyright, trademark, or trade secrets
              </li>
              <li>
                Constitutes fraud, impersonation, or misrepresentation of
                identity
              </li>
              <li>Contains malware, viruses, or other harmful code</li>
              <li>
                Violates any applicable local, national, or international law or
                regulation
              </li>
            </ul>
            <p className="mt-4">You also agree not to:</p>
            <ul className="list-disc list-inside space-y-1 ml-4">
              <li>
                Reverse-engineer, decompile, disassemble, or attempt to discover
                the source code or underlying algorithms of the Service
              </li>
              <li>
                Use automated means (bots, scrapers, crawlers) to access the
                Service without our written permission
              </li>
              <li>
                Attempt to access other users' accounts, content, or data
              </li>
              <li>
                Circumvent or attempt to circumvent any usage limits, rate
                limits, or security measures
              </li>
              <li>
                Resell, sublicense, or provide the Service to third parties as a
                competing service
              </li>
            </ul>
          </section>

          {/* 8. Content Moderation & Enforcement */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              8. Content Moderation &amp; Enforcement
            </h2>
            <p>
              We reserve the right (but assume no obligation) to review,
              monitor, and moderate content created through the Service. We may,
              at our sole discretion and without prior notice:
            </p>
            <ul className="list-disc list-inside space-y-1 ml-4">
              <li>
                Remove or disable access to content that violates these Terms or
                the Acceptable Use Policy
              </li>
              <li>
                Suspend or terminate your account for violations
              </li>
              <li>
                Report illegal content to relevant law enforcement authorities
              </li>
              <li>
                Cooperate with law enforcement investigations as required by law
              </li>
            </ul>
            <p className="mt-2">
              We employ automated content safety systems and reserve the right to
              implement additional moderation measures as necessary to protect
              the platform and its users.
            </p>
          </section>

          {/* 9. Model Training Policy & User Opt-Out */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              9. Model Training Policy &amp; User Opt-Out
            </h2>
            <p>
              We may use anonymized and aggregated usage data to improve the
              Service and our AI models. We will not use your identifiable Input
              Content or Generated Content to train our AI models without your
              explicit consent.
            </p>
            <p>
              You may opt out of any data usage for model training at any time
              through your account settings or by contacting us at{" "}
              <a href="mailto:contact@peopleprotocol.ca" className="text-purple-600 dark:text-purple-400 hover:underline">
                contact@peopleprotocol.ca
              </a>
              . Opting out will not affect your ability to use the Service. For
              full details on data handling, see our{" "}
              <Link to="/privacy" className="text-purple-600 dark:text-purple-400 hover:underline">
                Privacy Policy
              </Link>
              .
            </p>
          </section>

          {/* 10. Disclaimers */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              10. Disclaimers
            </h2>
            <p className="uppercase font-semibold text-sm">
              THE SERVICE IS PROVIDED ON AN "AS-IS" AND "AS-AVAILABLE" BASIS
              WITHOUT WARRANTIES OF ANY KIND, WHETHER EXPRESS, IMPLIED, OR
              STATUTORY. TO THE FULLEST EXTENT PERMITTED BY LAW, WE DISCLAIM ALL
              WARRANTIES, INCLUDING BUT NOT LIMITED TO IMPLIED WARRANTIES OF
              MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE,
              NON-INFRINGEMENT, AND ACCURACY.
            </p>
            <p className="mt-2">
              Without limiting the foregoing, we do not warrant that: (a) the
              Service will be uninterrupted, timely, secure, or error-free; (b)
              the results or Generated Content obtained from the Service will be
              accurate, reliable, or meet your expectations; (c) any AI-generated
              content will receive copyright protection in any jurisdiction; or
              (d) any defects in the Service will be corrected.
            </p>
          </section>

          {/* 11. Limitation of Liability */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              11. Limitation of Liability
            </h2>
            <p className="uppercase font-semibold text-sm">
              TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, IN NO EVENT
              SHALL PEOPLE PROTOCOL INC., ITS OFFICERS, DIRECTORS, EMPLOYEES,
              AGENTS, OR AFFILIATES BE LIABLE FOR ANY INDIRECT, INCIDENTAL,
              SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, INCLUDING BUT NOT
              LIMITED TO LOSS OF PROFITS, DATA, USE, GOODWILL, OR OTHER
              INTANGIBLE LOSSES, ARISING OUT OF OR IN CONNECTION WITH YOUR USE OF
              OR INABILITY TO USE THE SERVICE.
            </p>
            <p className="mt-2">
              Our total aggregate liability to you for all claims arising out of
              or relating to these Terms or the Service shall not exceed the
              greater of: (a) the amounts you have paid to us in the twelve (12)
              months preceding the claim; or (b) one hundred Canadian dollars
              (CAD $100).
            </p>
          </section>

          {/* 12. Indemnification */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              12. Indemnification
            </h2>
            <p>
              You agree to indemnify, defend, and hold harmless People Protocol
              Inc. and its officers, directors, employees, agents, and affiliates
              from and against any and all claims, damages, losses, liabilities,
              costs, and expenses (including reasonable attorneys' fees) arising
              out of or relating to: (a) your use of the Service; (b) your Input
              Content; (c) your Generated Content; (d) your violation of these
              Terms; or (e) your violation of any rights of a third party.
            </p>
          </section>

          {/* 13. Term & Termination */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              13. Term &amp; Termination
            </h2>
            <p>
              These Terms remain in effect for as long as you use the Service.
              You may terminate your account at any time by contacting us or
              through your account settings. We may suspend or terminate your
              account at any time, with or without cause, with or without notice.
            </p>
            <p>
              Upon termination: (a) your right to use the Service ceases
              immediately; (b) any unused credits are forfeited; (c) we may
              delete your account data after a reasonable retention period
              (typically 30 days); and (d) provisions that by their nature should
              survive termination shall survive, including ownership, warranty
              disclaimers, indemnification, and limitation of liability.
            </p>
          </section>

          {/* 14. Governing Law & Dispute Resolution */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              14. Governing Law &amp; Dispute Resolution
            </h2>
            <p>
              These Terms are governed by and construed in accordance with the
              laws of the Province of Alberta and the federal laws of Canada
              applicable therein, without regard to conflict of law principles.
            </p>
            <p>
              Any dispute arising out of or in connection with these Terms shall
              first be attempted to be resolved through good-faith negotiation.
              If the dispute cannot be resolved within 30 days, either party may
              submit the dispute to binding arbitration administered under the
              rules of the ADR Institute of Canada, with proceedings held in
              Calgary, Alberta. Notwithstanding the foregoing, either party may
              seek injunctive or equitable relief in a court of competent
              jurisdiction.
            </p>
          </section>

          {/* 15. Changes to Terms */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              15. Changes to Terms
            </h2>
            <p>
              We reserve the right to modify these Terms at any time. When we
              make material changes, we will notify you by email (to the address
              associated with your account) and/or by posting a prominent notice
              on the Service at least 30 days prior to the changes taking effect.
            </p>
            <p>
              Your continued use of the Service after the effective date of any
              changes constitutes acceptance of the revised Terms. If you do not
              agree with the revised Terms, you must stop using the Service and
              terminate your account.
            </p>
          </section>

          {/* 16. Contact Information */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              16. Contact Information
            </h2>
            <p>
              If you have questions about these Terms, please contact us:
            </p>
            <div className="mt-2 bg-gray-100 dark:bg-gray-800 rounded-lg p-4">
              <p className="font-medium text-gray-900 dark:text-white">
                People Protocol Inc.
              </p>
              <p>Alberta, Canada</p>
              <p>
                Email:{" "}
                <a href="mailto:contact@peopleprotocol.ca" className="text-purple-600 dark:text-purple-400 hover:underline">
                  contact@peopleprotocol.ca
                </a>
              </p>
              <p>
                General:{" "}
                <a href="mailto:contact@peopleprotocol.ca" className="text-purple-600 dark:text-purple-400 hover:underline">
                  contact@peopleprotocol.ca
                </a>
              </p>
            </div>
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
