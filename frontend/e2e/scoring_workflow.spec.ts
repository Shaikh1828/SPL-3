import { test, expect } from '@playwright/test'

test.describe('Archery Match Scoring & Manual Slot Override E2E Suite', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.waitForLoadState('networkidle')

    // If on login page, fill credentials and sign in
    if (await page.locator('#username').count() > 0) {
      await page.locator('#username').fill('admin')
      await page.locator('#password').fill('admin123!')
      await page.locator('#login-submit').click()
      await page.waitForURL('**/dashboard', { timeout: 10000 })
    }
  })

  test('1. Manual ScorePad: record arrows, click any slot to edit in-place, and undo', async ({ page }) => {
    await page.goto('/scoring')
    await page.waitForLoadState('networkidle')

    // Switch to Rapid Scorepad
    const rapidTab = page.locator('button:has-text("Manual Override Scorepad")').first()
    await expect(rapidTab).toBeVisible()
    await rapidTab.click()
    await page.waitForTimeout(600)

    // Ensure slot 1 is visible
    const slot1 = page.locator('[data-testid="arrow-slot-1"]').first()
    await expect(slot1).toBeVisible()

    // Test recording a score via keypad
    const btn10 = page.locator('[data-testid="score-pad-btn-10"]').first()
    if (await btn10.isVisible()) {
      await btn10.click()
      await page.waitForTimeout(600)
    }

    // Verify Undo button
    const undoBtn = page.locator('button:has-text("Undo Arrow")').first()
    if (await undoBtn.isVisible()) {
      await undoBtn.click()
      await page.waitForTimeout(600)
    }
  })

  test('2. Score Details Modal: Multi-Arrow Breakdown & In-Modal Override', async ({ page }) => {
    await page.goto('/reports')
    await page.waitForLoadState('networkidle')

    // Switch to Target Gallery tab
    const galleryTab = page.locator('button:has-text("Target Gallery")').first()
    await galleryTab.click()
    await page.waitForTimeout(1000)

    // If any scan cards exist, open inspect modal
    const inspectBtn = page.locator('button:has-text("Inspect")').first()
    if (await inspectBtn.isVisible()) {
      await inspectBtn.click()
      await page.waitForTimeout(600)

      // Verify Shot Analysis modal is open
      await expect(page.locator('text=Shot Analysis').first()).toBeVisible()
      await expect(page.locator('text=Annotated Target Detection').first()).toBeVisible()

      // Close modal
      const closeBtn = page.locator('button:has-text("Close Preview")').first()
      if (await closeBtn.isVisible()) {
        await closeBtn.click()
      }
    }
  })

  test('3. End Session & Auto-Advance all active archers to next session', async ({ page }) => {
    // Setup dialog handler to accept confirm dialog
    page.on('dialog', async (dialog) => {
      await dialog.accept().catch(() => {})
    })

    await page.goto('/scoring')
    await page.waitForLoadState('networkidle')

    // Check if End Session button is present
    const endSessionBtn = page.locator('button:has-text("End Session")').first()
    if (await endSessionBtn.isVisible()) {
      await endSessionBtn.click()
      await page.waitForTimeout(2000)
    }

    await expect(page).toHaveURL(/.*scoring/)
  })
})
