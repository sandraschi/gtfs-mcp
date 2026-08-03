import { expect, test } from "@playwright/test";

const BE = "http://127.0.0.1:10913";
const FE = "http://127.0.0.1:10912";

test.describe("Fleet Audit", () => {
  test("Backend health", async ({ request }) => {
    const resp = await request.get(`${BE}/health`);
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.status).toBe("ok");
    expect(body.tool_count).toBeGreaterThanOrEqual(7);
  });

  test("Backend diagnostics", async ({ request }) => {
    const resp = await request.get(`${BE}/api/v1/diagnostics`);
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.tool_count).toBeGreaterThanOrEqual(7);
  });

  test("Capabilities + skills", async ({ request }) => {
    const caps = await (await request.get(`${BE}/api/capabilities`)).json();
    expect(caps.features.feeds).toBe(true);
    const skills = await (await request.get(`${BE}/api/skills`)).json();
    expect(skills.skills.length).toBeGreaterThan(0);
  });

  test("Frontend loads", async ({ page }) => {
    await page.goto(FE, { timeout: 15000 });
    await expect(page.locator("#root")).toBeAttached();
    await expect(page.locator("[data-testid='dashboard']")).toBeVisible();
  });

  test("No console errors on dashboard", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });
    await page.goto(FE);
    await expect(page.locator("[data-testid='backend-dot']")).toBeVisible();
    expect(errors).toEqual([]);
  });

  test("All pages navigate", async ({ page }) => {
    const pages: Array<[string, string]> = [
      ["/", "dashboard"],
      ["/chat", "chat"],
      ["/settings", "settings"],
      ["/logging", "logging"],
    ];
    for (const [route] of pages) {
      await page.goto(`${FE}${route}`);
      await page.waitForLoadState("networkidle");
    }
    await page.goto(`${FE}/`);
    await expect(page.locator("[data-testid='dashboard']")).toBeVisible();
  });
});
