import {
  Activity,
  AlertTriangle,
  BarChart3,
  CloudRain,
  FileBarChart,
  Globe,
  HeartPulse,
  LayoutDashboard,
  type LucideIcon,
  MapPin,
  MessageSquareText,
  Settings,
  Smartphone,
  TrendingUp,
  Users,
} from "lucide-react";
import type { MessageKey } from "@/i18n/en";

/**
 * The sidebar, mirroring the legacy shell (dashboard/assets/js/app-shell.js GROUPS).
 * ``to`` is a page already rebuilt in React; ``href`` is a classic page that keeps
 * working until it is migrated. ``staffOnly`` hides links a monitor cannot use.
 */
export interface NavItem {
  label: MessageKey;
  icon: LucideIcon;
  to?: string;
  href?: string;
  staffOnly?: boolean;
}

export interface NavGroup {
  label: MessageKey;
  items: NavItem[];
}

export const NAV: NavGroup[] = [
  {
    label: "nav.group.dashboard",
    items: [
      { label: "nav.overview", icon: LayoutDashboard, to: "/" },
      { label: "nav.actnow", icon: AlertTriangle, href: "/act-now.html", staffOnly: true },
      { label: "nav.channels", icon: Activity, href: "/channels.html" },
      { label: "nav.schemes", icon: BarChart3, href: "/schemes.html" },
      { label: "nav.trends", icon: TrendingUp, href: "/trends.html" },
    ],
  },
  {
    label: "nav.group.field",
    items: [
      { label: "nav.advice", icon: CloudRain, href: "/advice.html" },
      { label: "nav.food", icon: HeartPulse, href: "/nutrition.html" },
      { label: "nav.map", icon: MapPin, href: "/map.html" },
      { label: "nav.feedback", icon: MessageSquareText, href: "/feedback.html" },
      { label: "nav.cooperatives", icon: Users, href: "/cooperatives.html" },
    ],
  },
  {
    label: "nav.group.platform",
    items: [
      { label: "nav.management", icon: Settings, href: "/management.html", staffOnly: true },
      { label: "nav.report", icon: FileBarChart, href: "/report.html" },
      { label: "nav.simulator", icon: Smartphone, href: "/simulator.html" },
      { label: "nav.home", icon: Globe, href: "/" },
    ],
  },
];
