import { ShieldAlert } from "lucide-react";
import type { ReactNode } from "react";
import type { Access } from "@/components/navigation/nav";
import { useI18n } from "@/i18n";
import type { Role } from "@/services/api/schemas";
import { isStaff, useSession } from "./providers/SessionProvider";

export function canAccess(role: Role, access: Access = "all"): boolean {
  switch (access) {
    case "admin":
      return role === "administrator";
    case "planner":
      return role === "administrator" || role === "district_planner";
    case "staff":
      return isStaff(role);
    case "analyst":
      return isStaff(role) || role === "citizen_science_monitor";
    case "field":
      return isStaff(role) || role === "citizen_science_monitor" || role === "cooperative_leader";
    default:
      return true;
  }
}

/**
 * Show a page only to roles allowed to use it. The backend refuses the same requests;
 * this keeps people from landing on a page full of "forbidden" errors.
 */
export function RequireAccess({ access, children }: { access: Access; children: ReactNode }) {
  const { t } = useI18n();
  const { role } = useSession();
  if (canAccess(role, access)) return <>{children}</>;
  return (
    <div role="alert" className="mx-auto mt-16 flex max-w-md flex-col items-center gap-3 rounded-card border border-line bg-surface p-8 text-center shadow-card">
      <ShieldAlert aria-hidden className="h-8 w-8 text-amber" />
      <p className="text-sm text-ink">{t(`access.${access}` as const)}</p>
    </div>
  );
}
