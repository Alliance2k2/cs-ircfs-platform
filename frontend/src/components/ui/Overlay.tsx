import { X } from "lucide-react";
import { useEffect, useId, useMemo, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { useI18n } from "@/i18n";
import { cx } from "@/lib/cx";

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Open overlays with the order they opened in. Order comes from render, not effects:
 * a dialog rendered inside a drawer opens after it even when both mount together
 * (child effects run before their parent's). Only the top overlay answers Escape and Tab.
 */
const stack: { panel: HTMLElement; order: number }[] = [];
let sequence = 0;
const isTop = (panel: HTMLElement) => stack.reduce<(typeof stack)[number] | null>((top, item) => (!top || item.order > top.order ? item : top), null)?.panel === panel;

/** Escape closes, Tab stays inside, focus returns to where it was when the overlay closes. */
function useModalFocus(open: boolean, onClose: () => void) {
  const panel = useRef<HTMLDivElement>(null);
  const close = useRef(onClose);
  close.current = onClose;
  const order = useMemo(() => (open ? ++sequence : 0), [open]);
  useEffect(() => {
    if (!open || !panel.current) return;
    const self = panel.current;
    stack.push({ panel: self, order });
    const previous = document.activeElement as HTMLElement | null;
    if (isTop(self)) (self.querySelector<HTMLElement>(FOCUSABLE) ?? self).focus();
    const onKey = (event: KeyboardEvent) => {
      if (!isTop(self)) return;
      if (event.key === "Escape") {
        event.stopPropagation();
        close.current();
      }
      if (event.key !== "Tab" || !panel.current) return;
      const items = [...panel.current.querySelectorAll<HTMLElement>(FOCUSABLE)];
      if (!items.length) return;
      const [head, tail] = [items[0]!, items[items.length - 1]!];
      if (event.shiftKey && document.activeElement === head) {
        event.preventDefault();
        tail.focus();
      } else if (!event.shiftKey && document.activeElement === tail) {
        event.preventDefault();
        head.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      stack.splice(stack.findIndex((item) => item.panel === self), 1);
      document.body.style.overflow = overflow;
      previous?.focus?.();
    };
  }, [open, order]);
  return panel;
}

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  wide?: boolean;
}

/** A side panel for details and actions on one record. */
export function Drawer({ open, onClose, title, subtitle, children, footer, wide }: DrawerProps) {
  const { t } = useI18n();
  const titleId = useId();
  const panel = useModalFocus(open, onClose);
  if (!open) return null;
  return createPortal(
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-forest-deep/40" onClick={onClose} aria-hidden />
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className={cx("relative flex h-full w-full flex-col bg-surface shadow-raised outline-none", wide ? "max-w-2xl" : "max-w-lg")}
      >
        <header className="flex items-start gap-3 border-b border-line px-5 py-4">
          <div className="min-w-0 flex-1">
            <h2 id={titleId} className="text-lg font-extrabold">
              {title}
            </h2>
            {subtitle && <div className="mt-0.5 text-sm text-muted">{subtitle}</div>}
          </div>
          <button type="button" onClick={onClose} className="rounded-control p-2 text-muted hover:bg-canvas hover:text-forest">
            <X aria-hidden className="h-5 w-5" />
            <span className="sr-only">{t("action.close")}</span>
          </button>
        </header>
        <div className="flex-1 overflow-y-auto px-5 py-4">{children}</div>
        {footer && <footer className="flex flex-wrap justify-end gap-2 border-t border-line px-5 py-3">{footer}</footer>}
      </div>
    </div>,
    document.body,
  );
}

interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  actions: ReactNode;
}

/** A small centred dialog, used for confirmations before an action that changes data. */
export function Dialog({ open, onClose, title, children, actions }: DialogProps) {
  const titleId = useId();
  const panel = useModalFocus(open, onClose);
  if (!open) return null;
  return createPortal(
    <div className="fixed inset-0 z-[60] grid place-items-center p-4">
      <div className="absolute inset-0 bg-forest-deep/40" onClick={onClose} aria-hidden />
      <div ref={panel} role="alertdialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1} className="relative w-full max-w-md rounded-card bg-surface p-5 shadow-raised outline-none">
        <h2 id={titleId} className="text-lg font-extrabold">
          {title}
        </h2>
        <div className="mt-2 text-sm text-ink">{children}</div>
        <div className="mt-5 flex flex-wrap justify-end gap-2">{actions}</div>
      </div>
    </div>,
    document.body,
  );
}
