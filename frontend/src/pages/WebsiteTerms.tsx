import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

export default function WebsiteTerms() {
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
          Website Terms of Use
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
              These Website Terms of Use ("Website Terms") govern your access to
              and use of the LitInkAI marketing website at litink.ai and any
              associated public-facing web pages (the "Website"), operated by
              People Protocol Inc. ("Company," "we," "us," or "our").
            </p>
            <p>
              By accessing or browsing the Website, you agree to be bound by
              these Website Terms. If you do not agree, please do not use the
              Website. Use of the LitInkAI platform and services is governed by
              our separate{" "}
              <Link to="/terms" className="text-purple-600 dark:text-purple-400 hover:underline">
                Terms of Service
              </Link>
              .
            </p>
          </section>

          {/* 2. Intellectual Property */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              2. Intellectual Property
            </h2>
            <p>
              All content on the Website — including text, graphics, logos,
              icons, images, audio clips, video clips, data compilations,
              software, and the overall design and layout — is the property of
              People Protocol Inc. or its content suppliers and is protected by
              Canadian and international copyright, trademark, and other
              intellectual property laws.
            </p>
            <p>
              The LitInkAI name, logo, and all related names, logos, product and
              service names, designs, and slogans are trademarks of People
              Protocol Inc. You may not use these marks without our prior written
              permission.
            </p>
          </section>

          {/* 3. Permitted Use */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              3. Permitted Use
            </h2>
            <p>You may access and use the Website for:</p>
            <ul className="list-disc list-inside space-y-1 ml-4">
              <li>Personal, non-commercial informational purposes</li>
              <li>Learning about LitInkAI's products and services</li>
              <li>Accessing public documentation and resources</li>
              <li>Navigating to the LitInkAI platform to create an account or sign in</li>
            </ul>
            <p className="mt-2">
              You may temporarily download one copy of materials on the Website
              for personal, non-commercial viewing only. This is a license, not a
              transfer of title.
            </p>
          </section>

          {/* 4. Prohibited Use */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              4. Prohibited Use
            </h2>
            <p>You agree not to:</p>
            <ul className="list-disc list-inside space-y-1 ml-4">
              <li>
                Copy, reproduce, distribute, republish, download, display, post,
                or transmit any Website content in any form without prior written
                consent
              </li>
              <li>
                Use any automated system (including robots, spiders, scrapers, or
                data mining tools) to access, monitor, or copy Website content
              </li>
              <li>
                Modify, adapt, translate, reverse-engineer, decompile, or
                disassemble any portion of the Website
              </li>
              <li>
                Use the Website in any way that could damage, disable,
                overburden, or impair its functionality
              </li>
              <li>
                Frame or mirror any part of the Website on any other server or
                Internet-based device
              </li>
              <li>
                Remove any copyright, trademark, or other proprietary notices
                from Website content
              </li>
              <li>
                Use the Website for any unlawful purpose or to solicit the
                performance of any illegal activity
              </li>
            </ul>
          </section>

          {/* 5. Disclaimers */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              5. Disclaimers
            </h2>
            <p>
              The information on the Website is provided for general
              informational purposes only. While we strive to keep the
              information accurate and up-to-date, we make no representations or
              warranties of any kind, express or implied, about the
              completeness, accuracy, reliability, suitability, or availability
              of the Website or the information, products, services, or related
              graphics contained on the Website.
            </p>
            <p>
              Any reliance you place on such information is strictly at your own
              risk. Product descriptions, pricing, and feature availability are
              subject to change without notice.
            </p>
            <p className="uppercase font-semibold text-sm mt-4">
              THE WEBSITE AND ITS CONTENT ARE PROVIDED "AS IS" AND "AS
              AVAILABLE" WITHOUT ANY WARRANTIES OF ANY KIND, WHETHER EXPRESS OR
              IMPLIED, INCLUDING BUT NOT LIMITED TO WARRANTIES OF
              MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, OR
              NON-INFRINGEMENT.
            </p>
          </section>

          {/* 6. Third-Party Links */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              6. Links to Third-Party Sites
            </h2>
            <p>
              The Website may contain links to third-party websites or services
              that are not owned or controlled by People Protocol Inc. We have no
              control over, and assume no responsibility for, the content,
              privacy policies, or practices of any third-party websites or
              services.
            </p>
            <p>
              The inclusion of any link does not imply endorsement,
              recommendation, or approval by People Protocol Inc. You access
              third-party websites entirely at your own risk and subject to the
              terms and conditions of those websites.
            </p>
          </section>

          {/* 7. Governing Law */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              7. Governing Law
            </h2>
            <p>
              These Website Terms are governed by and construed in accordance
              with the laws of the Province of Alberta and the federal laws of
              Canada applicable therein. Any disputes arising from or relating to
              these Website Terms or your use of the Website shall be subject to
              the exclusive jurisdiction of the courts of Alberta, Canada.
            </p>
            <p>
              If any provision of these Website Terms is found to be invalid or
              unenforceable by a court of competent jurisdiction, the remaining
              provisions shall continue in full force and effect.
            </p>
          </section>

          {/* 8. Contact */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              8. Contact
            </h2>
            <p>
              If you have questions about these Website Terms, please contact us:
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
