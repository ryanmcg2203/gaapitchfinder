const { expect, test } = require('./fixtures');

test('mobile navigation and filter disclosures open and close', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('#loading')).toHaveCount(0);

  const drawer = page.locator('#nav-drawer');
  await expect(drawer).not.toBeVisible();
  await page.getByRole('button', { name: 'Open menu' }).click();
  await expect(drawer).toBeVisible();
  await expect(drawer).toHaveClass(/open/);
  await expect(page.locator('#hamburger')).toHaveAttribute('aria-expanded', 'true');
  await expect(drawer).toHaveAttribute('aria-hidden', 'false');
  await expect(page.locator('#drawer-close')).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(drawer).not.toBeVisible();
  await expect(drawer).toHaveAttribute('inert', '');
  await expect(page.locator('#hamburger')).toHaveAttribute('aria-expanded', 'false');
  await expect(page.locator('#hamburger')).toBeFocused();

  await page.keyboard.press('Tab');
  await expect(page.locator('#drawer-close')).not.toBeFocused();

  const filterToggle = page.locator('#mobile-filter-toggle');
  await expect(page.locator('#sel-region')).not.toBeVisible();
  await expect(filterToggle).toHaveAttribute('aria-expanded', 'false');
  await expect(filterToggle).toHaveAttribute('aria-label', 'Show filters');
  await expect(page.locator('#sel-region')).toHaveAttribute('inert', '');
  await filterToggle.click();
  await expect(filterToggle).toHaveAttribute('aria-expanded', 'true');
  await expect(filterToggle).toHaveAttribute('aria-label', 'Hide filters');
  await expect(filterToggle).toHaveText('Hide');
  await expect(page.locator('#sel-region')).toBeVisible();
  await expect(page.locator('#sel-pitch')).toBeVisible();
  await page.locator('#sel-region').focus();
  await page.keyboard.press('Escape');
  await expect(filterToggle).toHaveAttribute('aria-expanded', 'false');
  await expect(filterToggle).toBeFocused();
  await expect(page.locator('#sel-region')).toHaveAttribute('inert', '');
  await expect(page.locator('#sel-region')).not.toBeVisible();
});
