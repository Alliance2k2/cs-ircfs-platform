import { useQuery } from "@tanstack/react-query";
import { createContext, useContext, type ReactNode } from "react";
import { DataState } from "@/components/feedback/DataState";
import { ApiError, apiGet } from "@/services/api/client";
import { accountSchema, authConfigSchema, type Account, type Role } from "@/services/api/schemas";

/** Who is signed in. ``development`` is the local sign-in bypass (no account). */
export interface Session {
  account: Account | null;
  role: Role;
  development: boolean;
}

const STAFF: Role[] = ["district_officer", "district_planner", "administrator"];
export const isStaff = (role: Role) => STAFF.includes(role);

const SessionContext = createContext<Session | null>(null);

/** Send the browser to the legacy sign-in page, which returns here after sign-in. */
export function redirectToSignIn() {
  const next = window.location.pathname + window.location.search;
  window.location.assign(`/login.html?next=${encodeURIComponent(next)}`);
}

async function loadSession(signal: AbortSignal): Promise<Session> {
  try {
    const account = await apiGet("auth/me", accountSchema, signal);
    return { account, role: account.role, development: false };
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) throw error;
    const config = await apiGet("auth/config", authConfigSchema, signal);
    if (config.development_bypass) return { account: null, role: "administrator", development: true };
    redirectToSignIn();
    return new Promise<Session>(() => undefined); // stay on the loading screen while the browser leaves
  }
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const session = useQuery({ queryKey: ["session"], queryFn: ({ signal }) => loadSession(signal), staleTime: 5 * 60_000, retry: false });

  if (session.isPending) return <DataState kind="loading" fullPage />;
  if (session.isError) {
    const unreachable = session.error instanceof ApiError && session.error.unreachable;
    return <DataState kind={unreachable ? "unreachable" : "error"} message={session.error.message} onRetry={() => session.refetch()} fullPage />;
  }
  return <SessionContext.Provider value={session.data}>{children}</SessionContext.Provider>;
}

export function useSession(): Session {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession must be used inside <SessionProvider>");
  return value;
}
