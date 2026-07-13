export const CREATOR_HOME_PATH = "/creator";
export const EXPLORER_HOME_PATH = "/dashboard";

type RedirectUser = {
  roles?: string[];
  preferred_mode?: "explorer" | "creator" | null;
};

export function isExplorerModeEnabled(): boolean {
  return import.meta.env.VITE_FEATURE_EXPLORER_MODE === "true";
}

export function getPostAuthRedirect(user: RedirectUser): string {
  if (!isExplorerModeEnabled()) {
    return CREATOR_HOME_PATH;
  }

  const hasCreator = user.roles?.includes("creator");
  const hasExplorer = user.roles?.includes("explorer");

  if (hasCreator && !hasExplorer) {
    return CREATOR_HOME_PATH;
  }

  if (!hasCreator && hasExplorer) {
    return EXPLORER_HOME_PATH;
  }

  return user.preferred_mode === "creator" ? CREATOR_HOME_PATH : EXPLORER_HOME_PATH;
}

export function getExplorerHomePath(): string {
  return isExplorerModeEnabled() ? EXPLORER_HOME_PATH : CREATOR_HOME_PATH;
}
