import { expect, test } from "@playwright/test";

const FE = "http://127.0.0.1:10912";

test.describe("GTFS Domain Pages", () => {
  test("Dashboard hero explains GTFS", async ({ page }) => {
    await page.goto(FE);
    await expect(page.locator("[data-testid='hero']")).toBeVisible();
    await expect(page.locator("[data-testid='hero']")).toContainText(
      "General Transit Feed Specification",
    );
    await expect(
      page.locator("[data-testid='hero-stat']").first(),
    ).toBeVisible();
  });

  test("Feeds page loads and renders", async ({ page }) => {
    await page.goto(`${FE}/feeds`);
    await expect(page.locator("[data-testid='feeds-page']")).toBeVisible();
    await expect(page.locator("[data-testid='feed-id-input']")).toBeVisible();
    await expect(page.locator("[data-testid='feed-add-button']")).toBeVisible();
  });

  test("Sources page shows curated presets", async ({ page }) => {
    await page.goto(`${FE}/sources`);
    await expect(page.locator("[data-testid='sources-page']")).toBeVisible();
    await expect(
      page.locator("[data-testid='preset-card-vienna']"),
    ).toBeVisible({ timeout: 10000 });
    await expect(
      page.locator("[data-testid='preset-add-vienna']"),
    ).toBeVisible();
  });

  test("Lines page shows filterable line list", async ({ page }) => {
    await page.goto(`${FE}/lines`);
    await expect(page.locator("[data-testid='lines-page']")).toBeVisible();
    await expect(page.locator("[data-testid='line-search']")).toBeVisible();
    await expect(page.locator("[data-testid='line-filter-1']")).toBeVisible();
  });

  test("Tools page shows dynamic tool list", async ({ page }) => {
    await page.goto(`${FE}/tools`);
    await expect(page.locator("[data-testid='tools-page']")).toBeVisible();
    await expect(
      page.locator("[data-testid='tool-card-add_feed']"),
    ).toBeVisible({ timeout: 10000 });
    await expect(
      page.locator("[data-testid='tool-card-shutdown']"),
    ).toBeVisible();
  });

  test("Skills page renders skill content", async ({ page }) => {
    await page.goto(`${FE}/skills`);
    await expect(page.locator("[data-testid='skills-page']")).toBeVisible();
    await page.locator("[data-testid='skill-gtfs-transit-expert']").click();
    await expect(page.locator("[data-testid='skill-content']")).toContainText(
      "GTFS",
      { timeout: 10000 },
    );
  });

  test("Settings page shows live backend info", async ({ page }) => {
    await page.goto(`${FE}/settings`);
    await expect(page.locator("[data-testid='settings-page']")).toBeVisible();
    await expect(
      page.locator("[data-testid='settings-tool-count']"),
    ).toHaveText("14", { timeout: 10000 });
    await expect(
      page.locator("[data-testid='llm-provider-select']"),
    ).toBeVisible();
  });

  test("Help page renders", async ({ page }) => {
    await page.goto(`${FE}/help`);
    await expect(page.locator("[data-testid='help-page']")).toBeVisible();
  });

  test("Sidebar navigates to all pages", async ({ page }) => {
    await page.goto(FE);
    const links = [
      "Sources",
      "Feeds",
      "Stops",
      "Lines",
      "Chat",
      "Tools",
      "Skills",
      "Settings",
      "Logging",
      "Help",
    ];
    for (const label of links) {
      await page.getByRole("link", { name: label }).click();
      await page.waitForLoadState("networkidle");
    }
    await page.goto(FE);
    await expect(page.locator("[data-testid='dashboard']")).toBeVisible();
  });
});
