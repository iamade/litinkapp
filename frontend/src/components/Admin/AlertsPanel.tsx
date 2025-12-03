import React, { useState, useEffect } from "react";
import { AlertTriangle, CheckCircle, Info, XCircle, Loader2, Clock } from "lucide-react";
import { apiClient } from "../../lib/api";

interface Alert {
  id: string;
  alert_type: string;
  severity: "info" | "warning" | "critical";
  message: string;
  metric_value: number;
  threshold_value: number;
  metadata: any;
  created_at: string;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
}

interface AlertStatistics {
  total_alerts: number;
  by_severity: {
    info: number;
    warning: number;
    critical: number;
  };
  by_type: Record<string, number>;
  acknowledged: number;
  unacknowledged: number;
}

export default function AlertsPanel() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [statistics, setStatistics] = useState<AlertStatistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "unacknowledged">("unacknowledged");

  useEffect(() => {
    fetchAlerts();
    fetchStatistics();
  }, [filter]);

  const fetchAlerts = async () => {
    try {
      setLoading(true);
      const acknowledged = filter === "all" ? undefined : false;
      const data = await apiClient.get<{ alerts: Alert[] }>(
        `/admin/alerts/recent?hours=24${acknowledged !== undefined ? `&acknowledged=${acknowledged}` : ""}`
      );
      setAlerts(data.alerts);
    } catch (err: any) {
      setError(err.message || "Failed to fetch alerts");
    } finally {
      setLoading(false);
    }
  };

  const fetchStatistics = async () => {
    try {
      const data = await apiClient.get<AlertStatistics>("/admin/alerts/statistics?days=7");
      setStatistics(data);
    } catch (err: any) {
      console.error("Failed to fetch statistics:", err);
    }
  };

  const acknowledgeAlert = async (alertId: string) => {
    try {
      await apiClient.post("/admin/alerts/acknowledge", { alert_id: alertId });
      fetchAlerts();
      fetchStatistics();
    } catch (err: any) {
      console.error("Failed to acknowledge alert:", err);
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case "critical":
        return <XCircle className="w-5 h-5 text-red-500" />;
      case "warning":
        return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
      default:
        return <Info className="w-5 h-5 text-blue-500" />;
    }
  };

  const getSeverityBg = (severity: string) => {
    switch (severity) {
      case "critical":
        return "bg-red-50 dark:bg-red-900 border-red-200 dark:border-red-700";
      case "warning":
        return "bg-yellow-50 dark:bg-yellow-900 border-yellow-200 dark:border-yellow-700";
      default:
        return "bg-blue-50 dark:bg-blue-900 border-blue-200 dark:border-blue-700";
    }
  };

  const formatRelativeTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  };

  if (loading && alerts.length === 0) {
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

  return (
    <div className="space-y-6">
      {statistics && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-gray-700 rounded-lg p-4 shadow">
            <p className="text-sm text-gray-600 dark:text-gray-400">Total Alerts (7d)</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
              {statistics.total_alerts}
            </p>
          </div>
          <div className="bg-red-50 dark:bg-red-900 rounded-lg p-4 shadow border border-red-200 dark:border-red-700">
            <p className="text-sm text-red-600 dark:text-red-300">Critical</p>
            <p className="text-2xl font-bold text-red-900 dark:text-red-100 mt-1">
              {statistics.by_severity.critical}
            </p>
          </div>
          <div className="bg-yellow-50 dark:bg-yellow-900 rounded-lg p-4 shadow border border-yellow-200 dark:border-yellow-700">
            <p className="text-sm text-yellow-600 dark:text-yellow-300">Warnings</p>
            <p className="text-2xl font-bold text-yellow-900 dark:text-yellow-100 mt-1">
              {statistics.by_severity.warning}
            </p>
          </div>
          <div className="bg-green-50 dark:bg-green-900 rounded-lg p-4 shadow border border-green-200 dark:border-green-700">
            <p className="text-sm text-green-600 dark:text-green-300">Acknowledged</p>
            <p className="text-2xl font-bold text-green-900 dark:text-green-100 mt-1">
              {statistics.acknowledged}
            </p>
          </div>
        </div>
      )}

      <div className="flex items-center gap-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Recent Alerts (24h)
        </h3>
        <div className="flex gap-2">
          <button
            onClick={() => setFilter("unacknowledged")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
              filter === "unacknowledged"
                ? "bg-blue-600 text-white"
                : "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600"
            }`}
          >
            Unacknowledged
          </button>
          <button
            onClick={() => setFilter("all")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
              filter === "all"
                ? "bg-blue-600 text-white"
                : "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600"
            }`}
          >
            All Alerts
          </button>
        </div>
      </div>

      <div className="space-y-3">
        {alerts.length === 0 ? (
          <div className="bg-green-50 dark:bg-green-900 rounded-lg p-8 text-center border border-green-200 dark:border-green-700">
            <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
            <p className="text-green-800 dark:text-green-200 font-medium">
              No alerts to display
            </p>
            <p className="text-sm text-green-600 dark:text-green-300 mt-1">
              System is operating normally
            </p>
          </div>
        ) : (
          alerts.map((alert) => (
            <div
              key={alert.id}
              className={`rounded-lg p-4 border ${getSeverityBg(alert.severity)} transition`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3 flex-1">
                  <div className="mt-0.5">{getSeverityIcon(alert.severity)}</div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="font-semibold text-gray-900 dark:text-white">
                        {alert.message}
                      </h4>
                      <span className="px-2 py-0.5 text-xs font-medium bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded">
                        {alert.alert_type.replace(/_/g, " ")}
                      </span>
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-300 space-y-1">
                      <p>
                        <strong>Metric:</strong> {alert.metric_value?.toFixed(2)} |
                        <strong> Threshold:</strong> {alert.threshold_value?.toFixed(2)}
                      </p>
                      {alert.metadata?.service && (
                        <p className="capitalize">
                          <strong>Service:</strong> {alert.metadata.service.replace(/_/g, " ")}
                        </p>
                      )}
                      <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 mt-2">
                        <Clock className="w-3 h-3" />
                        {formatRelativeTime(alert.created_at)}
                      </div>
                    </div>
                  </div>
                </div>
                {!alert.acknowledged_at && (
                  <button
                    onClick={() => acknowledgeAlert(alert.id)}
                    className="px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600 transition"
                  >
                    Acknowledge
                  </button>
                )}
                {alert.acknowledged_at && (
                  <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
                    <CheckCircle className="w-4 h-4" />
                    <span>Acknowledged</span>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
