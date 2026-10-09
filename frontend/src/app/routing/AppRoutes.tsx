import { Link, Route, Routes } from "react-router-dom";
import { AppLayout } from "@/app/layouts/AppLayout";
import { OverviewPage } from "@/features/overview/OverviewPage";
import { useI18n } from "@/i18n";

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

/** Pages rebuilt in React. Everything else is still a classic page linked from the sidebar. */
export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<OverviewPage />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
