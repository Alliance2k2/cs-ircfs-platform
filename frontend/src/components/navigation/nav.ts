import {
  AlertTriangle,
  BookOpenCheck,
  ClipboardList,
  CloudRain,
  FileBarChart,
  Globe,
  HeartPulse,
  LayoutDashboard,
  type LucideIcon,
  Map,
  MessageSquareText,
  Radio,
  Settings,
  Smartphone,
  Sprout,
  TrendingUp,
  Users,
  Wrench,
} from "lucide-react";
import type { MessageKey } from "@/i18n/en";

/**
 * The whole application menu. ``to`` is a React route; ``href`` a page outside the app.
 * ``access`` hides links a role cannot use; it mirrors the backend's role checks:
 * - all: every signed-in role
 * - field: Citizen Science Monitors, cooperative leaders and district staff
 * - analyst: Citizen Science Monitors and district staff (the analytics endpoints)
 * - staff: district officers, planners and administrators
 * - planner: district planners and administrators (sending advice, editing cooperatives)
 * - admin: administrators
 */
export type Access = "all" | "field" | "analyst" | "staff" | "planner" | "admin";

export interface NavItem {
  label: MessageKey;
  icon: LucideIcon;
  to?: string;
  href?: string;
  access?: Access;
}

export interface NavGroup {
  label: MessageKey;
  items: NavItem[];
}

export const NAV: NavGroup[] = [
  {
    label: "nav.group.dashboard",
    items: [
      { label: "nav.overview", icon: LayoutDashboard, to: "/", access: "analyst" },
      { label: "nav.actions", icon: AlertTriangle, to: "/actions", access: "staff" },
    ],
  },
  {
    label: "nav.group.field2",
    items: [
      { label: "nav.fieldReports", icon: ClipboardList, to: "/field-reports", access: "field" },
      { label: "nav.crops", icon: Sprout, to: "/crops", access: "analyst" },
      { label: "nav.nutrition", icon: HeartPulse, to: "/nutrition", access: "analyst" },
    ],
  },
  {
    label: "nav.group.water",
    items: [
      { label: "nav.irrigation", icon: Wrench, to: "/irrigation", access: "field" },
      { label: "nav.climate", icon: CloudRain, to: "/climate", access: "analyst" },
      { label: "nav.districtMap", icon: Map, to: "/map" },
    ],
  },
  {
    label: "nav.group.evaluation",
    items: [{ label: "nav.evaluation", icon: BookOpenCheck, to: "/evaluation", access: "analyst" }],
  },
  {
    label: "nav.group.community",
    items: [
      { label: "nav.grievances", icon: MessageSquareText, to: "/grievances", access: "staff" },
      { label: "nav.cooperatives", icon: Users, to: "/cooperatives", access: "staff" },
    ],
  },
  {
    label: "nav.group.comms",
    items: [
      { label: "nav.channels2", icon: Radio, to: "/channels", access: "field" },
      { label: "nav.simulator", icon: Smartphone, to: "/simulator", access: "field" },
    ],
  },
  {
    label: "nav.group.reports",
    items: [
      { label: "nav.trends", icon: TrendingUp, to: "/trends", access: "analyst" },
      { label: "nav.monthly", icon: FileBarChart, to: "/monthly-report", access: "analyst" },
    ],
  },
  {
    label: "nav.group.admin",
    items: [
      { label: "nav.admin", icon: Settings, to: "/admin", access: "admin" },
      { label: "nav.home", icon: Globe, href: "/" },
    ],
  },
];

/** Every route with its group, for breadcrumbs and the search palette. */
export const ROUTES = NAV.flatMap((group) => group.items.filter((item) => item.to).map((item) => ({ ...item, group: group.label })));
