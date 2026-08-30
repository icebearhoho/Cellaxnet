export const WORKSPACE_COOKIE = "area303_workspace";

export function readActiveWorkspaceId(): number | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(
    new RegExp(`(?:^|;\\s*)${WORKSPACE_COOKIE}=([^;]*)`),
  );
  if (!match) return null;
  const value = Number(decodeURIComponent(match[1]));
  return Number.isInteger(value) && value > 0 ? value : null;
}

export function setActiveWorkspaceId(workspaceId: number): void {
  if (typeof document === "undefined") return;
  const secure = location.protocol === "https:";
  document.cookie =
    `${WORKSPACE_COOKIE}=${workspaceId}; path=/; max-age=31536000; samesite=lax` +
    (secure ? "; secure" : "");
}

export function clearActiveWorkspace(): void {
  if (typeof document === "undefined") return;
  document.cookie = `${WORKSPACE_COOKIE}=; path=/; max-age=0; samesite=lax`;
}
