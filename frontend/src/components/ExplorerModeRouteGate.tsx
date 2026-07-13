import React from "react";
import { Navigate } from "react-router-dom";
import { CREATOR_HOME_PATH, isExplorerModeEnabled } from "../lib/explorerMode";

export function ExplorerModeRouteGate({ children }: { children: React.ReactNode }) {
  if (!isExplorerModeEnabled()) {
    return <Navigate to={CREATOR_HOME_PATH} replace />;
  }

  return <>{children}</>;
}
