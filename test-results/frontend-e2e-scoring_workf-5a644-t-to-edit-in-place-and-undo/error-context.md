# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: frontend\e2e\scoring_workflow.spec.ts >> Archery Match Scoring & Manual Slot Override E2E Suite >> 1. Manual ScorePad: record arrows, click any slot to edit in-place, and undo
- Location: frontend\e2e\scoring_workflow.spec.ts:17:3

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
  3   | test.describe('Archery Match Scoring & Manual Slot Override E2E Suite', () => {
  4   |   test.beforeEach(async ({ page }) => {
> 5   |     await page.goto('/login')
      |                ^ Error: page.goto: Protocol error (Page.navigate): Cannot navigate to invalid URL
  6   |     await page.waitForLoadState('networkidle')
  7   | 
  8   |     // If on login page, fill credentials and sign in
  9   |     if (await page.locator('#username').count() > 0) {
  10  |       await page.locator('#username').fill('admin')
  11  |       await page.locator('#password').fill('admin123!')
  12  |       await page.locator('#login-submit').click()
  13  |       await page.waitForURL('**/dashboard', { timeout: 10000 })
  14  |     }
  15  |   })
  16  | 
  17  |   test('1. Manual ScorePad: record arrows, click any slot to edit in-place, and undo', async ({ page }) => {
  18  |     await page.goto('/scoring')
  19  |     await page.waitForLoadState('networkidle')
  20  | 
  21  |     // Switch to Rapid Scorepad
  22  |     const rapidTab = page.locator('button:has-text("Manual Override Scorepad")').first()
  23  |     await expect(rapidTab).toBeVisible()
  24  |     await rapidTab.click()
  25  | 
  26  |     // Ensure scorepad is visible
  27  |     await expect(page.locator('text=Current End Arrows').first()).toBeVisible()
  28  | 
  29  |     // Record Arrow 1: 10 pts
  30  |     const btn10 = page.locator('button:has-text("10")').first()
  31  |     await btn10.click()
  32  |     await page.waitForTimeout(600)
  33  | 
  34  |     // Record Arrow 2: 9 pts
  35  |     const btn9 = page.locator('button:has-text("9")').first()
  36  |     await btn9.click()
  37  |     await page.waitForTimeout(600)
  38  | 
  39  |     // Record Arrow 3: 8 pts
  40  |     const btn8 = page.locator('button:has-text("8")').first()
  41  |     await btn8.click()
  42  |     await page.waitForTimeout(600)
  43  | 
  44  |     // Verify Slot #3 shows '8'
  45  |     const slot3 = page.locator('button:has-text("#3")').first()
  46  |     await expect(slot3).toContainText('8')
  47  | 
  48  |     // Click directly on Slot #3 to select it for editing
  49  |     await slot3.click()
  50  |     await page.waitForTimeout(300)
  51  | 
  52  |     // Now tap 'X' button to override Slot #3
  53  |     const btnX = page.locator('button:has-text("X")').first()
  54  |     await btnX.click()
  55  |     await page.waitForTimeout(800)
  56  | 
  57  |     // Verify Slot #3 has been updated in-place to 'X' without breaking Slot #1 (10) or Slot #2 (9)
  58  |     await expect(slot3).toContainText('X')
  59  |     const slot1 = page.locator('button:has-text("#1")').first()
  60  |     const slot2 = page.locator('button:has-text("#2")').first()
  61  |     await expect(slot1).toContainText('10')
  62  |     await expect(slot2).toContainText('9')
  63  | 
  64  |     // Test Undo Arrow
  65  |     const undoBtn = page.locator('button:has-text("Undo Arrow")').first()
  66  |     if (await undoBtn.isVisible() && await undoBtn.isEnabled()) {
  67  |       await undoBtn.click()
  68  |       await page.waitForTimeout(800)
  69  |     }
  70  |   })
  71  | 
  72  |   test('2. Score Details Modal: Multi-Arrow Breakdown & In-Modal Override', async ({ page }) => {
  73  |     await page.goto('/reports')
  74  |     await page.waitForLoadState('networkidle')
  75  | 
  76  |     // Switch to Target Gallery tab
  77  |     const galleryTab = page.locator('button:has-text("Target Gallery")').first()
  78  |     await galleryTab.click()
  79  |     await page.waitForTimeout(1000)
  80  | 
  81  |     // If any scan cards exist, open inspect modal
  82  |     const inspectBtn = page.locator('button:has-text("Inspect")').first()
  83  |     if (await inspectBtn.isVisible()) {
  84  |       await inspectBtn.click()
  85  |       await page.waitForTimeout(600)
  86  | 
  87  |       // Verify Shot Analysis modal is open
  88  |       await expect(page.locator('text=Shot Analysis').first()).toBeVisible()
  89  |       await expect(page.locator('text=Annotated Target Detection').first()).toBeVisible()
  90  | 
  91  |       // Close modal
  92  |       const closeBtn = page.locator('button:has-text("Close Preview")').first()
  93  |       if (await closeBtn.isVisible()) {
  94  |         await closeBtn.click()
  95  |       }
  96  |     }
  97  |   })
  98  | 
  99  |   test('3. End Session & Auto-Advance all active archers to next session', async ({ page }) => {
  100 |     await page.goto('/scoring')
  101 |     await page.waitForLoadState('networkidle')
  102 | 
  103 |     // Check if End Session button is present
  104 |     const endSessionBtn = page.locator('button:has-text("End Session")').first()
  105 |     if (await endSessionBtn.isVisible()) {
```