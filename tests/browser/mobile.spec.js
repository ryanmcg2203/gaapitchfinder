const { expect, test } = require('./fixtures');

test('mobile navigation and filter disclosures open and close', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('#loading')).toHaveCount(0);

  const drawer = page.locator('#nav-drawer');
  await expect(drawer).not.toBeVisible();
  await page.getByRole('button', { name: 'Open menu' }).click();
  await expect(drawer).toBeVisible();
  await expect(drawer).toHaveClass(/open/);
  await page.getByRole('button', { name: 'Close menu' }).click();
  await expect(drawer).not.toBeVisible();

  const filterToggle = page.locator('#mobile-filter-toggle');
  await expect(page.locator('#sel-region')).not.toBeVisible();
  await expect(filterToggle).toHaveAttribute('aria-expanded', 'false');
  await filterToggle.click();
  await expect(filterToggle).toHaveAttribute('aria-expanded', 'true');
  await expect(filterToggle).toHaveText('Hide');
  await expect(page.locator('#sel-region')).toBeVisible();
  await expect(page.locator('#sel-pitch')).toBeVisible();
  await filterToggle.click();
  await expect(filterToggle).toHaveAttribute('aria-expanded', 'false');
  await expect(page.locator('#sel-region')).not.toBeVisible();
});
