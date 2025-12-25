import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { Shield, DollarSign, Activity, AlertTriangle, TrendingUp, Database, Users } from "lucide-react";
import CostTrackingDashboard from "../components/Admin/CostTrackingDashboard";
import MetricsDashboard from "../components/Admin/MetricsDashboard";
import AlertsPanel from "../components/Admin/AlertsPanel";
import UserManagementDashboard from "../components/Admin/UserManagementDashboard";

type TabType = "cost" | "metrics" | "alerts" | "users";

export default function AdminDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabType>("cost");
  const [isAuthorized, setIsAuthorized] = useState(false);

  useEffect(() => {
    if (!user) {
      navigate("/auth");
      return;
    }

    const isSuperadmin =
      user.roles?.includes("superadmin") || user.email === "support@litinkai.com";

    if (!isSuperadmin) {
      navigate("/dashboard");
      return;
    }

    setIsAuthorized(true);
  }, [user, navigate]);

  if (!isAuthorized) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-blue-600"></div>
      </div>
    );
  }

  const tabs = [
    {
      id: "cost" as TabType,
      name: "Cost Tracking",
      icon: DollarSign,
      description: "Monitor AI model costs and savings",
    },
    {
      id: "metrics" as TabType,
      name: "Performance Metrics",
      icon: Activity,
      description: "Track fallback rates and model performance",
    },
    {
      id: "alerts" as TabType,
      name: "Alerts & Monitoring",
      icon: AlertTriangle,
      description: "View system alerts and health status",
    },
    {
      id: "users" as TabType,
      name: "User Management",
      icon: Users,
      description: "Manage users and permissions",
    },
  ];

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-3 bg-blue-100 dark:bg-blue-900 rounded-lg">
            <Shield className="w-8 h-8 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              Admin Dashboard
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Cost optimization and system monitoring
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">System Status</p>
                <p className="text-2xl font-bold text-green-600 dark:text-green-400 mt-1">
                  Operational
                </p>
              </div>
              <div className="p-3 bg-green-100 dark:bg-green-900 rounded-lg">
                <Database className="w-6 h-6 text-green-600 dark:text-green-400" />
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">AI Services</p>
                <p className="text-2xl font-bold text-blue-600 dark:text-blue-400 mt-1">
                  4 Active
                </p>
              </div>
              <div className="p-3 bg-blue-100 dark:bg-blue-900 rounded-lg">
                <Activity className="w-6 h-6 text-blue-600 dark:text-blue-400" />
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Cost Efficiency</p>
                <p className="text-2xl font-bold text-purple-600 dark:text-purple-400 mt-1">
                  Optimized
                </p>
              </div>
              <div className="p-3 bg-purple-100 dark:bg-purple-900 rounded-lg">
                <TrendingUp className="w-6 h-6 text-purple-600 dark:text-purple-400" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
        <div className="border-b border-gray-200 dark:border-gray-700">
          <nav className="flex -mb-px">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex-1 px-6 py-4 text-center border-b-2 font-medium text-sm transition-colors ${
                    activeTab === tab.id
                      ? "border-blue-500 text-blue-600 dark:text-blue-400"
                      : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300"
                  }`}
                >
                  <div className="flex items-center justify-center gap-2">
                    <Icon className="w-5 h-5" />
                    <span className="hidden sm:inline">{tab.name}</span>
                    <span className="sm:hidden">{tab.name.split(" ")[0]}</span>
                  </div>
                </button>
              );
            })}
          </nav>
        </div>

        <div className="p-6">
          {activeTab === "cost" && <CostTrackingDashboard />}
          {activeTab === "metrics" && <MetricsDashboard />}
          {activeTab === "alerts" && <AlertsPanel />}
          {activeTab === "users" && <UserManagementDashboard />}
        </div>
      </div>
    </div>
  );
}
