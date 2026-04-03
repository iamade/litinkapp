import React from "react";
import { Link } from "react-router-dom";
import { FileText, Shield, Globe, ArrowRight } from "lucide-react";

const legalDocs = [
  {
    title: "Terms of Service",
    description:
      "The agreement governing your use of the LitInkAI platform, including content ownership, subscriptions, credits, and acceptable use.",
    path: "/terms",
    icon: FileText,
  },
  {
    title: "Privacy Policy",
    description:
      "How we collect, use, store, and protect your personal information, including your rights under PIPEDA and GDPR.",
    path: "/privacy",
    icon: Shield,
  },
  {
    title: "Website Terms of Use",
    description:
      "Terms governing your access to and use of the LitInkAI marketing website and public-facing content.",
    path: "/website-terms",
    icon: Globe,
  },
];

export default function LegalHub() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-16 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
            Legal Documents
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
            Transparency matters. Review our legal documents to understand how
            LitInkAI operates, how we handle your data, and what your rights
            are.
          </p>
        </div>

        {/* Document Cards */}
        <div className="grid gap-6 md:grid-cols-1">
          {legalDocs.map((doc) => (
            <Link
              key={doc.path}
              to={doc.path}
              className="group block bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700 hover:shadow-md hover:border-purple-300 dark:hover:border-purple-600 transition-all"
            >
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0 w-12 h-12 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
                  <doc.icon className="w-6 h-6 text-purple-600 dark:text-purple-400" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <h2 className="text-xl font-semibold text-gray-900 dark:text-white group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors">
                      {doc.title}
                    </h2>
                    <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-purple-600 dark:group-hover:text-purple-400 group-hover:translate-x-1 transition-all" />
                  </div>
                  <p className="mt-2 text-gray-600 dark:text-gray-400">
                    {doc.description}
                  </p>
                </div>
              </div>
            </Link>
          ))}
        </div>

        {/* Summary Box */}
        <div className="mt-12 bg-purple-50 dark:bg-purple-900/20 rounded-xl p-6 border border-purple-200 dark:border-purple-800">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
            Your Content, Your Rights
          </h3>
          <ul className="space-y-2 text-gray-700 dark:text-gray-300 text-sm">
            <li className="flex items-start gap-2">
              <span className="text-purple-600 dark:text-purple-400 mt-0.5">•</span>
              You own the AI-generated content you create on paid plans, to the fullest extent permitted by law.
            </li>
            <li className="flex items-start gap-2">
              <span className="text-purple-600 dark:text-purple-400 mt-0.5">•</span>
              We do not sell your personal data. Your privacy is protected under Canadian and international law.
            </li>
            <li className="flex items-start gap-2">
              <span className="text-purple-600 dark:text-purple-400 mt-0.5">•</span>
              You can opt out of model training at any time from your account settings.
            </li>
            <li className="flex items-start gap-2">
              <span className="text-purple-600 dark:text-purple-400 mt-0.5">•</span>
              You must be 18 or older to use LitInkAI.
            </li>
          </ul>
        </div>

        {/* Contact */}
        <div className="mt-8 text-center text-sm text-gray-500 dark:text-gray-500">
          <p>
            Questions about our legal documents?{" "}
            <a
              href="mailto:contact@peopleprotocol.ca"
              className="text-purple-600 dark:text-purple-400 hover:underline"
            >
              contact@peopleprotocol.ca
            </a>
          </p>
          <p className="mt-2">Last updated: March 23, 2026</p>
        </div>
      </div>
    </div>
  );
}
