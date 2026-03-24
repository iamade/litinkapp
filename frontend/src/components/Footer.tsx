import React from "react";
import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          {/* Company */}
          <div className="text-sm text-gray-500 dark:text-gray-500">
            © {new Date().getFullYear()} People Protocol Inc. All rights
            reserved.
          </div>

          {/* Legal Links */}
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <Link
              to="/legal"
              className="text-gray-500 dark:text-gray-500 hover:text-purple-600 dark:hover:text-purple-400 transition-colors"
            >
              Legal
            </Link>
            <span className="text-gray-300 dark:text-gray-700">|</span>
            <Link
              to="/terms"
              className="text-gray-500 dark:text-gray-500 hover:text-purple-600 dark:hover:text-purple-400 transition-colors"
            >
              Terms of Service
            </Link>
            <span className="text-gray-300 dark:text-gray-700">|</span>
            <Link
              to="/privacy"
              className="text-gray-500 dark:text-gray-500 hover:text-purple-600 dark:hover:text-purple-400 transition-colors"
            >
              Privacy Policy
            </Link>
            <span className="text-gray-300 dark:text-gray-700">|</span>
            <Link
              to="/website-terms"
              className="text-gray-500 dark:text-gray-500 hover:text-purple-600 dark:hover:text-purple-400 transition-colors"
            >
              Website Terms
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
