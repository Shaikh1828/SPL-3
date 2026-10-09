# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: frontend\e2e\app.spec.ts >> Archery Scoring System - Comprehensive E2E Test Suite >> 3. Match Scoring Page: Camera Streams, Single Lane AI Scan, Score Now, and Confirm Batch
- Location: frontend\e2e\app.spec.ts:36:3

# Error details

```
Error: page.goto: Protocol error (Page.navigate): Cannot navigate to invalid URL
Call log:
  - navigating to "/login", waiting until "load"

```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test'
  2   | 
  3   | test.describe('Archery Scoring System - Comprehensive E2E Test Suite', () => {
  4   |   test.beforeEach(async ({ page }) => {
  5   |     // Navigate to Login page and log in as Admin
> 6   |     await page.goto('/login')
      |                ^ Error: page.goto: Protocol error (Page.navigate): Cannot navigate to invalid URL
  7   |     await page.waitForLoadState('networkidle')
  8   | 
  9   |     // If on login page, fill credentials and sign in
  10  |     if (await page.locator('#username').count() > 0) {
  11  |       await page.locator('#username').fill('admin')
  12  |       await page.locator('#password').fill('admin123!')
  13  |       await page.locator('#login-submit').click()
  14  |       await page.waitForURL('**/dashboard', { timeout: 10000 })
  15  |     }
  16  |   })
  17  | 
  18  |   test('1. Dashboard KPIs and navigation', async ({ page }) => {
  19  |     await page.goto('/dashboard')
  20  |     await page.waitForLoadState('networkidle')
  21  | 
  22  |     // Check dashboard elements
  23  |     await expect(page.getByRole('heading', { name: 'Tournament Live Dashboard' })).toBeVisible()
  24  |     await expect(page.locator('text=Active Sessions').first()).toBeVisible()
  25  |     await expect(page.locator('text=Total Archers').first()).toBeVisible()
  26  |   })
  27  | 
  28  |   test('2. Tournament selection & sessions list', async ({ page }) => {
  29  |     await page.goto('/tournaments')
  30  |     await page.waitForLoadState('networkidle')
  31  | 
  32  |     // Check tournament list loaded
  33  |     await expect(page.locator('h3:has-text("Summer Regional Qualifier")').first()).toBeVisible()
  34  |   })
  35  | 
  36  |   test('3. Match Scoring Page: Camera Streams, Single Lane AI Scan, Score Now, and Confirm Batch', async ({ page }) => {
  37  |     await page.goto('/scoring')
  38  |     await page.waitForLoadState('networkidle')
  39  | 
  40  |     // Verify main components on scoring page
  41  |     await expect(page.locator('text=Match Scoring & Target Vision').first()).toBeVisible()
  42  |     await expect(page.locator('text=AI Target Cameras').first()).toBeVisible()
  43  | 
  44  |     // Verify OBS / Camera Stream Bridge controls
  45  |     await expect(page.locator('text=OBS & Camera Stream Bridge').first()).toBeVisible()
  46  | 
  47  |     // Test AI Auto-Detect (Score Now)
  48  |     const scoreNowBtn = page.locator('button:has-text("Score Now")').first()
  49  |     if (await scoreNowBtn.isVisible()) {
  50  |       await scoreNowBtn.click()
  51  | 
  52  |       // Should transition to Scorer Verification & Staging Matrix
  53  |       await expect(page.locator('text=Scorer Verification & Staging Matrix').first()).toBeVisible({ timeout: 15000 })
  54  |       await expect(page.locator('text=Lanes Ready for Confirmation').first()).toBeVisible()
  55  | 
  56  |       // Test Override single arrow
  57  |       const firstArrowBtn = page.locator('button[title*="Click to override"]').first()
  58  |       if (await firstArrowBtn.isVisible()) {
  59  |         await firstArrowBtn.click()
  60  |         await expect(page.locator('text=Manual Score Override').first()).toBeVisible()
  61  | 
  62  |         // Select 10 pts override inside the modal
  63  |         const modal10Btn = page.locator('.fixed.inset-0 button:has-text("10")').first()
  64  |         if (await modal10Btn.isVisible()) {
  65  |           await modal10Btn.click({ force: true })
  66  |         }
  67  |       }
  68  | 
  69  |       // Confirm & Submit End
  70  |       const confirmSubmitBtn = page.locator('button:has-text("Confirm & Submit")').first()
  71  |       if (await confirmSubmitBtn.isVisible()) {
  72  |         await confirmSubmitBtn.click()
  73  |       }
  74  | 
  75  |       // Should complete submission cleanly
  76  |       await page.waitForTimeout(1500)
  77  |     }
  78  | 
  79  |     // Test Manual Rapid Scorepad Tab
  80  |     const rapidTab = page.locator('button:has-text("Manual Override Scorepad")').first()
  81  |     if (await rapidTab.isVisible()) {
  82  |       await rapidTab.click()
  83  |       await expect(page.locator('text=Rapid Keypad Score Entry').or(page.locator('button:has-text("10")')).first()).toBeVisible()
  84  |     }
  85  |   })
  86  | 
  87  |   test('4. Target Gallery: Filters, Scanned Images, and Score Inspection Modal', async ({ page }) => {
  88  |     await page.goto('/reports')
  89  |     await page.waitForLoadState('networkidle')
  90  | 
  91  |     // Switch to Target Gallery tab
  92  |     const galleryTab = page.locator('button:has-text("Target Gallery")').first()
  93  |     await galleryTab.click()
  94  |     await page.waitForTimeout(1500)
  95  | 
  96  |     // Check gallery controls
  97  |     await expect(page.locator('text=Target Camera Scans & AI Vision Gallery').first()).toBeVisible()
  98  | 
  99  |     // Verify scans found badge
  100 |     const scansFoundBadge = page.locator('text=/\\d+ Scans Found/').first()
  101 |     await expect(scansFoundBadge).toBeVisible({ timeout: 10000 })
  102 | 
  103 |     // Check if gallery cards with images are rendered
  104 |     const galleryCards = page.locator('div[class*="glass-card"]:has(img), img[src*="image"]')
  105 |     const count = await galleryCards.count()
  106 |     expect(count).toBeGreaterThan(0)
```