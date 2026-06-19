import { test, expect } from '@playwright/test';

test.describe('Login Flow', () => {
  test('navigate to login page', async ({ page }) => {
    await page.goto('/login');
    await expect(page).toHaveTitle(/Fleet/);
  });

  test('login with valid credentials', async ({ page }) => {
    await page.goto('/login');
    
    await page.fill('input[type="email"]', 'admin@test.com');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button[type="submit"]');
    
    // Should redirect to dashboard
    await expect(page).toHaveURL('/dashboard');
  });

  test('show error with invalid credentials', async ({ page }) => {
    await page.goto('/login');
    
    await page.fill('input[type="email"]', 'admin@test.com');
    await page.fill('input[type="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');
    
    // Should show error message
    await expect(page.locator('.ant-alert')).toBeVisible();
  });
});

test.describe('Dashboard', () => {
  test('dashboard loads with stats cards', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Stats cards should be visible
    await expect(page.locator('.ant-statistic')).toHaveCount(4);
  });

  test('dashboard charts render', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Charts should render
    await expect(page.locator('.recharts-wrapper')).toBeVisible();
  });
});

test.describe('Alerts', () => {
  test('alerts page loads', async ({ page }) => {
    await page.goto('/dashboard/alerts');
    
    // Should load alerts table
    await expect(page.locator('.ant-table')).toBeVisible();
  });

  test('filter by severity', async ({ page }) => {
    await page.goto('/dashboard/alerts');
    
    // Select critical severity
    await page.selectOption('select', 'critical');
    
    // Should filter results
    await expect(page.locator('.ant-tag.ant-tag-red')).toBeVisible();
  });
});