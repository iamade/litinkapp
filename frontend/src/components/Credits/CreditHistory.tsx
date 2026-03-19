import React from "react";
import { apiClient } from "../../lib/api";

interface CreditHistoryItem {
  id?: string;
  created_at?: string;
  operation_type?: string;
  operation?: string;
  credits_used?: number;
  credits?: number;
  amount?: number;
  reference?: string;
  reference_id?: string;
}

interface CreditHistoryResponse {
  items?: CreditHistoryItem[];
  history?: CreditHistoryItem[];
  transactions?: CreditHistoryItem[];
}

const formatDate = (value?: string) => {
  if (!value) return "N/A";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
};

export default function CreditHistory() {
  const [items, setItems] = React.useState<CreditHistoryItem[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let active = true;

    const loadHistory = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await apiClient.get<CreditHistoryResponse>("/credits/history?page=1&limit=20");
        if (!active) return;
        const rows = response.items ?? response.history ?? response.transactions ?? [];
        setItems(rows);
      } catch (err) {
        if (!active) return;
        setError("Failed to load credit history.");
      } finally {
        if (active) setLoading(false);
      }
    };

    loadHistory();
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg border border-gray-100 dark:border-gray-700 p-6">
      <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">Credit History</h2>

      {loading && <p className="text-sm text-gray-500 dark:text-gray-400">Loading credit history...</p>}
      {error && <p className="text-sm text-red-500">{error}</p>}

      {!loading && !error && items.length === 0 && (
        <p className="text-sm text-gray-500 dark:text-gray-400">No credit transactions yet.</p>
      )}

      {!loading && !error && items.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
                <th className="py-2 pr-4">Date</th>
                <th className="py-2 pr-4">Operation</th>
                <th className="py-2 pr-4">Credits Used</th>
                <th className="py-2">Reference</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, index) => {
                const used = item.credits_used ?? item.credits ?? item.amount ?? 0;
                return (
                  <tr
                    key={item.id || `${item.created_at || "row"}-${index}`}
                    className="border-b border-gray-100 dark:border-gray-700 last:border-0"
                  >
                    <td className="py-2 pr-4 text-gray-700 dark:text-gray-300">{formatDate(item.created_at)}</td>
                    <td className="py-2 pr-4 text-gray-900 dark:text-gray-100">
                      {item.operation_type || item.operation || "Unknown"}
                    </td>
                    <td className="py-2 pr-4 text-gray-900 dark:text-gray-100">{used}</td>
                    <td className="py-2 text-gray-700 dark:text-gray-300">
                      {item.reference || item.reference_id || "N/A"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
