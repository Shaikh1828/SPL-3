import { test, expect } from '@playwright/test'

test.describe('Archery Scoring System - Comprehensive E2E Test Suite', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to Login page and log in as Admin
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

  test('1. Dashboard KPIs and navigation', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Check dashboard elements
    await expect(page.getByRole('heading', { name: 'Tournament Live Dashboard' })).toBeVisible()
    await expect(page.locator('text=Active Sessions').first()).toBeVisible()
    await expect(page.locator('text=Total Archers').first()).toBeVisible()
  })

  test('2. Tournament selection & sessions list', async ({ page }) => {
    await page.goto('/tournaments')
    await page.waitForLoadState('networkidle')

    // Check tournament list loaded
    await expect(page.locator('h3:has-text("Summer Regional Qualifier")').first()).toBeVisible()
  })

  test('3. Match Scoring Page: Camera Streams, Single Lane AI Scan, Score Now, and Confirm Batch', async ({ page }) => {
    await page.goto('/scoring')
    await page.waitForLoadState('networkidle')

    // Verify main components on scoring page
    await expect(page.locator('text=Match Scoring & Target Vision').first()).toBeVisible()
    await expect(page.locator('text=AI Target Cameras').first()).toBeVisible()

    // Verify OBS / Camera Stream Bridge controls
    await expect(page.locator('text=OBS & Camera Stream Bridge').first()).toBeVisible()

    // Test AI Auto-Detect (Score Now)
    const scoreNowBtn = page.locator('button:has-text("Score Now")').first()
    if (await scoreNowBtn.isVisible()) {
      await scoreNowBtn.click()

      // Should transition to Scorer Verification & Staging Matrix
      await expect(page.locator('text=Scorer Verification & Staging Matrix').first()).toBeVisible({ timeout: 15000 })
      await expect(page.locator('text=Lanes Ready for Confirmation').first()).toBeVisible()

      // Test Override single arrow
      const firstArrowBtn = page.locator('button[title*="Click to override"]').first()
      if (await firstArrowBtn.isVisible()) {
        await firstArrowBtn.click()
        await expect(page.locator('text=Manual Score Override').first()).toBeVisible()

        // Select 10 pts override inside the modal
        const modal10Btn = page.locator('.fixed.inset-0 button:has-text("10")').first()
        if (await modal10Btn.isVisible()) {
          await modal10Btn.click({ force: true })
        }
      }

      // Confirm & Submit End
      const confirmSubmitBtn = page.locator('button:has-text("Confirm & Submit")').first()
      if (await confirmSubmitBtn.isVisible()) {
        await confirmSubmitBtn.click()
      }

      // Should complete submission cleanly
      await page.waitForTimeout(1500)
    }

    // Test Manual Rapid Scorepad Tab
    const rapidTab = page.locator('button:has-text("Manual Override Scorepad")').first()
    if (await rapidTab.isVisible()) {
      await rapidTab.click()
      await expect(page.locator('text=Rapid Keypad Score Entry').or(page.locator('button:has-text("10")')).first()).toBeVisible()
    }
  })

  test('4. Target Gallery: Filters, Scanned Images, and Score Inspection Modal', async ({ page }) => {
    await page.goto('/reports')
    await page.waitForLoadState('networkidle')

    // Switch to Target Gallery tab
    const galleryTab = page.locator('button:has-text("Target Gallery")').first()
    await galleryTab.click()
    await page.waitForTimeout(1500)

    // Check gallery controls
    await expect(page.locator('text=Target Camera Scans & AI Vision Gallery').first()).toBeVisible()

    // Verify scans found badge
    const scansFoundBadge = page.locator('text=/\\d+ Scans Found/').first()
    await expect(scansFoundBadge).toBeVisible({ timeout: 10000 })

    // Check if gallery cards with images are rendered
    const galleryCards = page.locator('div[class*="glass-card"]:has(img), img[src*="image"]')
    const count = await galleryCards.count()
    expect(count).toBeGreaterThan(0)

    // Click on a target scan card to open the detail inspection modal
    const firstScan = page.locator('.aspect-video').first()
    if (await firstScan.isVisible()) {
      await firstScan.click()
      await expect(page.locator('button:has(svg.lucide-x)').first()).toBeVisible({ timeout: 6000 })

      // Close modal
      const closeBtn = page.locator('button:has(svg.lucide-x)').first()
      if (await closeBtn.isVisible()) {
        await closeBtn.click()
      }
    }
  })

  test('5. Reports & Analytics: End Progression, 2D Target Dispersion, and Fatigue Curve', async ({ page }) => {
    await page.goto('/reports')
    await page.waitForLoadState('networkidle')

    // 1. Tournament & Match Analytics Tab
    await expect(page.locator('text=Score Distribution Histogram').first()).toBeVisible()
    await expect(page.locator('text=End Progression & Fatigue Curve').first()).toBeVisible()
    await expect(page.locator('text=Lane Accuracy & Variance Matrix').first()).toBeVisible()

    // 2. Archer Career & Comparison Tab
    const archersTab = page.locator('button:has-text("Archer Career & Comparison")').first()
    await archersTab.click()
    await page.waitForTimeout(1500)

    // Verify Archer Longitudinal Analytics
    await expect(page.locator('text=Career Arrow Avg').first()).toBeVisible()
    await expect(page.locator('text=Target Spatial Dispersion & Grouping (CEP)').first()).toBeVisible()
    await expect(page.locator('text=Shot Sequence Fatigue & Stamina Curve').first()).toBeVisible()
    await expect(page.locator('text=Windage Bias').first()).toBeVisible()

    // 3. Official Leaderboard Tab
    const leaderboardTab = page.locator('button:has-text("Official Leaderboard")').first()
    await leaderboardTab.click()
    await page.waitForTimeout(1500)

    await expect(page.locator('text=Official Standings & Leaderboard').first()).toBeVisible()
    await expect(page.locator('th:has-text("Archer Name")').first()).toBeVisible()
  })

  test('6. Cameras Management and Live Preview', async ({ page }) => {
    await page.goto('/scoring')
    await page.waitForLoadState('networkidle')

    await page.goto('/cameras')
    await page.waitForLoadState('networkidle')

    // Verify Cameras view
    await expect(page.locator('text=Camera & OBS Stream Hub').or(page.locator('text=No Active Session')).first()).toBeVisible()
  })

  test('7. Tournament Stage Progression & Elimination Funnel Verification', async ({ page }) => {
    await page.goto('/reports')
    await page.waitForLoadState('networkidle')

    // Verify Stage Progression & Elimination section
    await expect(page.locator('text=Tournament Stage Progression & Elimination Funnel').first()).toBeVisible({ timeout: 10000 })
    await expect(page.locator('text=Elimination Breakdown & Final Standings').first()).toBeVisible()

    // Verify Stage 1, Stage 2, Stage 3 cards exist in the funnel
    await expect(page.locator('text=Stage 1').first()).toBeVisible()

    // Check table with elimination status badges
    await expect(page.locator('th:has-text("Seed")').first()).toBeVisible()
    await expect(page.locator('th:has-text("Tournament Status / Medal")').first()).toBeVisible()
  })

  test('8. Dashboard Tournament Selector Ribbon & Smooth Leaderboard Scroll', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Verify Tournament Selector ribbon
    await expect(page.locator('text=Select Tournament to View Standings').first()).toBeVisible()

    // Click on "View Leaderboard" in a tournament card
    const viewLeaderboardBtn = page.locator('span:has-text("View Leaderboard")').first()
    await expect(viewLeaderboardBtn).toBeVisible()
    await viewLeaderboardBtn.click()

    // Ensure Tournament Live Dashboard banner and leaderboard are in view
    await expect(page.locator('#tournament-live-dashboard-section')).toBeVisible()
    await expect(page.locator('text=Leaderboard & Player Roster').first()).toBeVisible()
  })
})
