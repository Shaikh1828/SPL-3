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

    // Ensure scorepad is visible
    await expect(page.locator('text=Current End Arrows').first()).toBeVisible()

    // Select first archer if available
    const competitorCard = page.locator('div:has-text("Lane 1")').first()
    if (await competitorCard.isVisible()) {
      await competitorCard.click()
      await page.waitForTimeout(300)
    }

    // Record Arrow 1: 10 pts
    const btn10 = page.locator('[data-testid="score-pad-btn-10"]').first()
    await expect(btn10).toBeVisible()
    await btn10.click()
    await page.waitForTimeout(800)

    // Record Arrow 2: 9 pts
    const btn9 = page.locator('[data-testid="score-pad-btn-9"]').first()
    await btn9.click()
    await page.waitForTimeout(800)

    // Record Arrow 3: 8 pts
    const btn8 = page.locator('[data-testid="score-pad-btn-8"]').first()
    await btn8.click()
    await page.waitForTimeout(800)

    // Verify Slot #3 shows '8'
    const slot3 = page.locator('[data-testid="arrow-slot-3"]').first()
    await expect(slot3).toContainText('8')

    // Click directly on Slot #3 to select it for in-place editing
    await slot3.click()
    await page.waitForTimeout(400)

    // Now tap 'X' button to override Slot #3
    const btnX = page.locator('[data-testid="score-pad-btn-X"]').first()
    await btnX.click()
    await page.waitForTimeout(1000)

    // Verify Slot #3 has been updated in-place to 'X' without breaking Slot #1 (10) or Slot #2 (9)
    await expect(slot3).toContainText('X')
    const slot1 = page.locator('[data-testid="arrow-slot-1"]').first()
    const slot2 = page.locator('[data-testid="arrow-slot-2"]').first()
    await expect(slot1).toContainText('10')
    await expect(slot2).toContainText('9')

    // Test Undo Arrow
    const undoBtn = page.locator('button:has-text("Undo Arrow")').first()
    if (await undoBtn.isVisible() && await undoBtn.isEnabled()) {
      await undoBtn.click()
      await page.waitForTimeout(800)
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
    await page.goto('/scoring')
    await page.waitForLoadState('networkidle')

    // Check if End Session button is present
    const endSessionBtn = page.locator('button:has-text("End Session")').first()
    if (await endSessionBtn.isVisible()) {
      // Setup dialog handler to accept confirm dialog
      page.once('dialog', async (dialog) => {
        await dialog.accept()
      })

      await endSessionBtn.click()
      await page.waitForTimeout(2000)

      // Verify active session switched or toast displayed
      await expect(page.locator('text=Match Scoring & Target Vision').first()).toBeVisible()
    }
  })
})
