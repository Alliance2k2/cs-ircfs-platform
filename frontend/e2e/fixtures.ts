import { test as base, expect, type Page } from "@playwright/test";

/** Accounts created by backend/scripts/run_e2e_server.py in its temporary database. */
export const PASSWORD = "e2e-password-2026";
export const ROLES = {
  admin: "admin@e2e.test",
  planner: "planner@e2e.test",
  officer: "officer@e2e.test",
  monitor: "monitor@e2e.test",
  leader: "leader@e2e.test",
} as const;
export type RoleName = keyof typeof ROLES;

export const storageFor = (role: RoleName) => `e2e/.auth/${role}.json`;

/** A test signed in as one role (sessions are prepared once in auth.setup.ts). */
export const asRole = (role: RoleName) => base.extend({ storageState: storageFor(role) });

/** The toast confirming a change. */
export async function expectToast(page: Page, text: string | RegExp) {
  await expect(page.getByRole("status").filter({ hasText: text }).first()).toBeVisible();
}

export { expect };
