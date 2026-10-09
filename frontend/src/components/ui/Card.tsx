import type { HTMLAttributes, ReactNode } from "react";
import { cx } from "@/lib/cx";

export function Card({ className, children, ...rest }: HTMLAttributes<HTMLElement> & { children: ReactNode }) {
  return (
    <section className={cx("rounded-card border border-line bg-surface shadow-card", className)} {...rest}>
      {children}
    </section>
  );
}

interface CardHeaderProps {
  title: string;
  note?: string;
  id?: string;
  action?: ReactNode;
}

/** A card title with an optional one-line explanation and an action on the right. */
export function CardHeader({ title, note, id, action }: CardHeaderProps) {
  return (
    <header className="flex flex-wrap items-start justify-between gap-3 border-b border-line px-5 py-4">
      <div className="min-w-0">
        <h2 id={id} className="text-base font-bold">
          {title}
        </h2>
        {note && <p className="mt-0.5 text-sm text-muted">{note}</p>}
      </div>
      {action}
    </header>
  );
}
