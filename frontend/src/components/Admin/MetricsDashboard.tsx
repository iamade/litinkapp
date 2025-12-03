import React, { useState, useEffect } from "react";
import { Activity, CheckCircle, XCircle, Loader2 } from "lucide-react";
import { apiClient } from "../../lib/api";

interface FallbackData {
  script_generation: ServiceMetrics;
  image_generation: ServiceMetrics;
  video_generation: ServiceMetrics;
  audio_generation: ServiceMetrics;
  overall_summary: {
    total_operations: number;
    total_fallbacks: number;
    overall_fallback_rate: number;
  };
}

interface ServiceMetrics {
  service: string;
  total_operations: number;
  fallback_count: number;
  fallback_rate: number;
}

interface ModelPerformance {
  model: string;
  total_attempts: number;
  successful: number;
  failed: number;
  success_rate: number;
  average_generation_time: number;
}

export default function MetricsDashboard() {
  const [fallbackData, setFallbackData] = useState<FallbackData | null>(null);
  const [modelPerformance, setModelPerformance] = useState<ModelPerformance[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMetrics();
  }, []);

  const fetchMetrics = async () => {
    try {
      setLoading(true);
      const [fallback, performance] = await Promise.all([
        apiClient.get<FallbackData>("/admin/metrics/fallback-rates"),
        apiClient.get<{ models: ModelPerformance[] }>("/admin/metrics/model-performance"),
      ]);
      setFallbackData(fallback);
      setModelPerformance(performance.models);
    } catch (err: any) {
      setError(err.message || "Failed to fetch metrics");
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

  if (!fallbackData) {
    return (
      <div className="text-center py-12 text-gray-500 dark:text-gray-400">
        No metrics data available
      </div>
    );
  }

  const services = [
    fallbackData.script_generation,
    fallbackData.image_generation,
    fallbackData.video_generation,
    fallbackData.audio_generation,
  ];

  const getStatusColor = (rate: number) => {
    if (rate < 20) return "text-green-600 dark:text-green-400";
    if (rate < 40) return "text-yellow-600 dark:text-yellow-400";
    return "text-red-600 dark:text-red-400";
  };

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900 dark:to-blue-800 rounded-lg p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-blue-600 dark:text-blue-300 font-medium">
              Overall Fallback Rate (7 days)
            </p>
            <p className={`text-4xl font-bold mt-2 ${getStatusColor(fallbackData.overall_summary.overall_fallback_rate)}`}>
              {fallbackData.overall_summary.overall_fallback_rate.toFixed(1)}%
            </p>
            <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
              {fallbackData.overall_summary.total_fallbacks} of {fallbackData.overall_summary.total_operations} operations
            </p>
          </div>
          <div className="p-4 bg-blue-200 dark:bg-blue-700 rounded-full">
            <Activity className="w-8 h-8 text-blue-700 dark:text-blue-200" />
          </div>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-700 rounded-lg p-6 shadow">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Fallback Rates by Service
        </h3>
        <div className="space-y-4">
          {services.map((service) => (
            <div key={service.service} className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300 capitalize">
                  {service.service.replace(/_/g, " ")}
                </span>
                <span className={`text-sm font-bold ${getStatusColor(service.fallback_rate)}`}>
                  {service.fallback_rate.toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${
                    service.fallback_rate < 20
                      ? "bg-green-500"
                      : service.fallback_rate < 40
                      ? "bg-yellow-500"
                      : "bg-red-500"
                  }`}
                  style={{ width: `${Math.min(service.fallback_rate, 100)}%` }}
                />
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {service.fallback_count} fallbacks / {service.total_operations} operations
              </p>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white dark:bg-gray-700 rounded-lg p-6 shadow">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Top Model Performance
        </h3>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-600">
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-700 dark:text-gray-300">
                  Model
                </th>
                <th className="text-center py-3 px-4 text-sm font-medium text-gray-700 dark:text-gray-300">
                  Attempts
                </th>
                <th className="text-center py-3 px-4 text-sm font-medium text-gray-700 dark:text-gray-300">
                  Success Rate
                </th>
                <th className="text-center py-3 px-4 text-sm font-medium text-gray-700 dark:text-gray-300">
                  Avg Time
                </th>
              </tr>
            </thead>
            <tbody>
              {modelPerformance.slice(0, 10).map((model) => (
                <tr key={model.model} className="border-b border-gray-100 dark:border-gray-600">
                  <td className="py-3 px-4 text-sm text-gray-900 dark:text-white font-mono">
                    {model.model}
                  </td>
                  <td className="py-3 px-4 text-sm text-center text-gray-700 dark:text-gray-300">
                    {model.total_attempts}
                  </td>
                  <td className="py-3 px-4 text-center">
                    <div className="flex items-center justify-center gap-2">
                      {model.success_rate >= 90 ? (
                        <CheckCircle className="w-4 h-4 text-green-500" />
                      ) : model.success_rate >= 70 ? (
                        <Activity className="w-4 h-4 text-yellow-500" />
                      ) : (
                        <XCircle className="w-4 h-4 text-red-500" />
                      )}
                      <span className={`text-sm font-medium ${getStatusColor(100 - model.success_rate)}`}>
                        {model.success_rate.toFixed(1)}%
                      </span>
                    </div>
                  </td>
                  <td className="py-3 px-4 text-sm text-center text-gray-700 dark:text-gray-300">
                    {model.average_generation_time.toFixed(1)}s
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="bg-yellow-50 dark:bg-yellow-900 rounded-lg p-4">
        <p className="text-sm text-yellow-800 dark:text-yellow-200">
          <strong>Alert Threshold:</strong> Fallback rates above 30% trigger warnings.
          Rates above 50% trigger critical alerts.
        </p>
      </div>
    </div>
  );
}
