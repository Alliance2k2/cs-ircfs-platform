import { lazy, type ComponentType, type ReactNode } from "react";
import { Link, Navigate, Route, Routes } from "react-router-dom";
import { canAccess, RequireAccess } from "@/app/access";
import { useSession } from "@/app/providers/SessionProvider";
import { AppLayout } from "@/app/layouts/AppLayout";
import { ROUTES, type Access } from "@/components/navigation/nav";
import { OverviewPage } from "@/features/overview/OverviewPage";
import { useI18n } from "@/i18n";

/** Each workspace is its own chunk, loaded when first opened. */
function page<K extends string>(load: () => Promise<Record<K, ComponentType>>, name: K) {
  return lazy(() => load().then((module) => ({ default: module[name] })));
}

const ActionsPage = page(() => import("@/features/actions/ActionsPage"), "ActionsPage");
const FieldReportsPage = page(() => import("@/features/field-reports/FieldReportsPage"), "FieldReportsPage");
const CropsPage = page(() => import("@/features/crops/CropsPage"), "CropsPage");
const NutritionPage = page(() => import("@/features/nutrition/NutritionPage"), "NutritionPage");
const IrrigationPage = page(() => import("@/features/irrigation/IrrigationPage"), "IrrigationPage");
const ClimatePage = page(() => import("@/features/climate/ClimatePage"), "ClimatePage");
const MapPage = page(() => import("@/features/map/MapPage"), "MapPage");
const EvaluationPage = page(() => import("@/features/evaluation/EvaluationPage"), "EvaluationPage");
const GrievancesPage = page(() => import("@/features/grievances/GrievancesPage"), "GrievancesPage");
const CooperativesPage = page(() => import("@/features/cooperatives/CooperativesPage"), "CooperativesPage");
const ChannelsPage = page(() => import("@/features/channels/ChannelsPage"), "ChannelsPage");
const SimulatorPage = page(() => import("@/features/simulator/SimulatorPage"), "SimulatorPage");
const TrendsPage = page(() => import("@/features/trends/TrendsPage"), "TrendsPage");
const MonthlyReportPage = page(() => import("@/features/monthly/MonthlyReportPage"), "MonthlyReportPage");
const AdminPage = page(() => import("@/features/admin/AdminPage"), "AdminPage");

const WORKSPACES: { path: string; element: ReactNode }[] = [
  { path: "actions", element: <ActionsPage /> },
  { path: "field-reports", element: <FieldReportsPage /> },
  { path: "crops", element: <CropsPage /> },
  { path: "nutrition", element: <NutritionPage /> },
  { path: "irrigation", element: <IrrigationPage /> },
  { path: "climate", element: <ClimatePage /> },
  { path: "map", element: <MapPage /> },
  { path: "evaluation", element: <EvaluationPage /> },
  { path: "grievances", element: <GrievancesPage /> },
  { path: "cooperatives", element: <CooperativesPage /> },
  { path: "channels", element: <ChannelsPage /> },
  { path: "simulator", element: <SimulatorPage /> },
  { path: "trends", element: <TrendsPage /> },
  { path: "monthly-report", element: <MonthlyReportPage /> },
  { path: "admin", element: <AdminPage /> },
];

/** The access level of a route, from the menu, so the two never disagree. */
const accessOf = (path: string): Access => ROUTES.find((route) => route.to === `/${path}`)?.access ?? "all";

/** The overview, or the first page this role may use (a cooperative leader starts on field reports). */
function Home() {
  const { role } = useSession();
  if (canAccess(role, accessOf(""))) return <OverviewPage />;
  const first = ROUTES.find((route) => route.to !== "/" && canAccess(role, route.access));
  return first?.to ? <Navigate to={first.to} replace /> : <RequireAccess access={accessOf("")}><OverviewPage /></RequireAccess>;
}

function NotFound() {
  const { t } = useI18n();
  return (
    <div className="mx-auto max-w-md py-20 text-center">
      <h1 className="text-2xl font-extrabold">{t("notFound.title")}</h1>
      <p className="mt-2 text-sm text-muted">{t("notFound.body")}</p>
      <Link to="/" className="mt-6 inline-block rounded-control bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary-strong">
        {t("notFound.back")}
      </Link>
    </div>
  );
}

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Home />} />
        {WORKSPACES.map(({ path, element }) => (
          <Route key={path} path={path} element={<RequireAccess access={accessOf(path)}>{element}</RequireAccess>} />
        ))}
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
