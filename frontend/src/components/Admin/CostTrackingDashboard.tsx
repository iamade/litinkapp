import React, { useState, useEffect } from "react";
import { DollarSign, TrendingUp, TrendingDown, Loader2 } from "lucide-react";
import { apiClient } from "../../lib/api";

interface CostSummary {
  total_cost: number;
  total_savings: number;
  cost_by_service: {
    script_generation: number;
    image_generation: number;
    video_generation: number;
    audio_generation: number;
  };
  savings_by_service: {
    script_generation: number;
    image_generation: number;
    video_generation: number;
    audio_generation: number;
  };
}

export default function CostTrackingDashboard() {
  const [costSummary, setCostSummary] = useState<CostSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCostSummary();
  }, []);

  const fetchCostSummary = async () => {
    try {
      setLoading(true);
      const data = await apiClient.get<CostSummary>("/admin/cost-tracking/summary");
      setCostSummary(data);
    } catch (err: any) {
      setError(err.message || "Failed to fetch cost data");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900 p-4 rounded-lg">
        <p className="text-red-600 dark:text-red-300">{error}</p>
      </div>
    );
  }

  if (!costSummary) {
    return (
      <div className="text-center py-12 text-gray-500 dark:text-gray-400">
        No cost data available
      </div>
    );
  }

  const totalCost = costSummary.total_cost;
  const totalSavings = costSummary.total_savings;
  const savingsPercentage = totalCost > 0 ? ((totalSavings / (totalCost + totalSavings)) * 100) : 0;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900 dark:to-blue-800 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-blue-600 dark:text-blue-300 font-medium">Total Cost (30 days)</p>
              <p className="text-3xl font-bold text-blue-900 dark:text-white mt-2">
                ${totalCost.toFixed(2)}
              </p>
            </div>
            <div className="p-3 bg-blue-200 dark:bg-blue-700 rounded-full">
              <DollarSign className="w-6 h-6 text-blue-700 dark:text-blue-200" />
            </div>
          </div>
        </div>

        <div className="bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900 dark:to-green-800 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-green-600 dark:text-green-300 font-medium">Total Savings</p>
              <p className="text-3xl font-bold text-green-900 dark:text-white mt-2">
                ${totalSavings.toFixed(2)}
              </p>
            </div>
            <div className="p-3 bg-green-200 dark:bg-green-700 rounded-full">
              <TrendingDown className="w-6 h-6 text-green-700 dark:text-green-200" />
            </div>
          </div>
        </div>

        <div className="bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900 dark:to-purple-800 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-purple-600 dark:text-purple-300 font-medium">Savings Rate</p>
              <p className="text-3xl font-bold text-purple-900 dark:text-white mt-2">
                {savingsPercentage.toFixed(1)}%
              </p>
            </div>
            <div className="p-3 bg-purple-200 dark:bg-purple-700 rounded-full">
              <TrendingUp className="w-6 h-6 text-purple-700 dark:text-purple-200" />
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-700 rounded-lg p-6 shadow">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Cost by Service
          </h3>
          <div className="space-y-3">
            {Object.entries(costSummary.cost_by_service).map(([service, cost]) => (
              <div key={service} className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-300 capitalize">
                  {service.replace(/_/g, " ")}
                </span>
                <span className="font-medium text-gray-900 dark:text-white">
                  ${cost.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white dark:bg-gray-700 rounded-lg p-6 shadow">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Savings by Service
          </h3>
          <div className="space-y-3">
            {Object.entries(costSummary.savings_by_service).map(([service, savings]) => (
              <div key={service} className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-300 capitalize">
                  {service.replace(/_/g, " ")}
                </span>
                <span className="font-medium text-green-600 dark:text-green-400">
                  ${savings.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-blue-50 dark:bg-blue-900 rounded-lg p-4">
        <p className="text-sm text-blue-800 dark:text-blue-200">
          <strong>Note:</strong> Cost tracking shows AI model usage for the last 30 days.
          Savings represent cost reductions from automatic fallback to more affordable models
          when primary models are unavailable.
        </p>
      </div>
    </div>
  );
}
