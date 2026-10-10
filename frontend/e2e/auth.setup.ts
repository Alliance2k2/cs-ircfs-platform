import { test as setup } from "@playwright/test";
import { PASSWORD, ROLES, storageFor, type RoleName } from "./fixtures";

// One session per role, signed in through the API (login is rate limited per address and email).
for (const role of Object.keys(ROLES) as RoleName[]) {
  setup(`sign in as ${role}`, async ({ request }) => {
    const response = await request.post("/api/v1/auth/login", { data: { email: ROLES[role], password: PASSWORD } });
    if (!response.ok()) throw new Error(`Sign-in for ${role} failed: ${response.status()} ${await response.text()}`);
    await request.storageState({ path: storageFor(role) });
  });
}
