# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: scoring_workflow.spec.ts >> Archery Match Scoring & Manual Slot Override E2E Suite >> 1. Manual ScorePad: record arrows, click any slot to edit in-place, and undo
- Location: frontend\e2e\scoring_workflow.spec.ts:17:3

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: locator.click: Test timeout of 30000ms exceeded.
Call log:
  - waiting for locator('button:has-text("10")').first()
    - locator resolved to <button disabled class="h-14 rounded-xl border flex flex-col items-center justify-center transition-all active:scale-95 bg-amber-500 hover:bg-amber-400 text-navy-950 font-black border-amber-300 shadow-amber-500/30 opacity-40 cursor-not-allowed transform-none shadow-none">…</button>
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - element is not enabled
    - retrying click action
    - waiting 20ms
    2 × waiting for element to be visible, enabled and stable
      - element is not enabled
    - retrying click action
      - waiting 100ms
    44 × waiting for element to be visible, enabled and stable
       - element is not enabled
     - retrying click action
       - waiting 500ms

```

# Page snapshot

```yaml
- generic [ref=f1e3]:
  - complementary [ref=f1e4]:
    - generic [ref=f1e9]:
      - paragraph [ref=f1e10]: ArcheryScore
      - paragraph [ref=f1e11]: Pro System
    - navigation [ref=f1e12]:
      - link "Dashboard" [ref=f1e13] [cursor=pointer]:
        - /url: /dashboard
      - link "Scoring" [ref=f1e20] [cursor=pointer]:
        - /url: /scoring
      - link "Model Training" [ref=f1e26] [cursor=pointer]:
        - /url: /training
      - link "Pose Biomechanics" [ref=f1e40] [cursor=pointer]:
        - /url: /pose-analysis
      - link "Reports" [ref=f1e44] [cursor=pointer]:
        - /url: /reports
      - link "Cameras" [ref=f1e48] [cursor=pointer]:
        - /url: /cameras
      - link "Tournaments" [ref=f1e53] [cursor=pointer]:
        - /url: /tournaments
      - link "Users" [ref=f1e61] [cursor=pointer]:
        - /url: /users
      - link "System Status" [ref=f1e68] [cursor=pointer]:
        - /url: /system
      - link "Settings" [ref=f1e72] [cursor=pointer]:
        - /url: /settings
    - generic "Click to expand Auto-Train AI" [ref=f1e79] [cursor=pointer]:
      - generic [ref=f1e80]: Auto-Train AI
      - generic [ref=f1e95]:
        - generic [ref=f1e96]: Ready
        - button [ref=f1e98]
    - button [ref=f1e102]
  - generic [ref=f1e105]:
    - banner [ref=f1e106]:
      - generic [ref=f1e107]: "Live: Collegiate Qualification"
      - generic [ref=f1e111]:
        - button [ref=f1e112]
        - button "admin" [ref=f1e117]
    - main [ref=f1e125]:
      - generic [ref=f1e126]:
        - generic [ref=f1e127]:
          - generic [ref=f1e128]:
            - generic [ref=f1e129]:
              - generic [ref=f1e130]:
                - generic [ref=f1e131]: AI Camera Target Vision
                - generic [ref=f1e135]: completed
              - heading "Match Scoring & Target Vision" [level=1] [ref=f1e136]
              - paragraph [ref=f1e137]:
                - text: "Primary camera vision pipeline: Click"
                - strong [ref=f1e138]: Score Now
                - text: to auto-score all lanes with YOLO11, review and confirm to advance rounds.
            - generic [ref=f1e139]:
              - generic [ref=f1e140]:
                - generic [ref=f1e147]: "Tournament:"
                - combobox [ref=f1e148] [cursor=pointer]:
                  - option "Inter-University Archery Meet 2026" [selected]
                  - option "Asian Archery Grand Prix 2026"
                  - option "Winter Invitational Grand Prix 2025"
                  - option "Teer 14th National Archery Championship"
                  - option "Bangladesh Independence Cup 2026"
                  - option "Asia Cup Archery Stage 2 - 2026"
                  - option "Summer Regional Qualifier 2026"
                  - option "Olympic Qualification Trials 2026"
                  - option "Spring Grand Prix 2026"
                  - option "National Outdoor Archery Championship 2026"
                  - option "Summer Qualifier 2026"
                  - option "Spring Championship 2026"
              - generic [ref=f1e149]:
                - generic [ref=f1e154]: "Session:"
                - combobox [ref=f1e155] [cursor=pointer]:
                  - option "Collegiate Qualification (completed)" [selected]
              - generic [ref=f1e156]:
                - button "◀" [disabled] [ref=f1e157]
                - generic [ref=f1e158]:
                  - generic [ref=f1e159]: "End #1"
                  - generic [ref=f1e160]: (6 arr/end)
                - button "▶" [ref=f1e161]
              - button "⚡ Score Now (All Lanes)" [ref=f1e162]
              - button "Refresh data" [ref=f1e166]
          - generic [ref=f1e172]:
            - generic [ref=f1e173]: "Active Lanes:"
            - 'button "1 Brady Ellison 322 pts · End 1: 7/6" [ref=f1e174]':
              - generic [ref=f1e175]: "1"
              - generic [ref=f1e176]:
                - paragraph [ref=f1e177]: Brady Ellison
                - generic [ref=f1e178]: "322 pts · End 1: 7/6"
            - 'button "2 Mete Gazoz 246 pts · End 1: 6/6" [ref=f1e179]':
              - generic [ref=f1e180]: "2"
              - generic [ref=f1e181]:
                - paragraph [ref=f1e182]: Mete Gazoz
                - generic [ref=f1e183]: "246 pts · End 1: 6/6"
            - 'button "3 Kim Woo-jin 251 pts · End 1: 6/6" [ref=f1e184]':
              - generic [ref=f1e185]: "3"
              - generic [ref=f1e186]:
                - paragraph [ref=f1e187]: Kim Woo-jin
                - generic [ref=f1e188]: "251 pts · End 1: 6/6"
            - 'button "4 Marcus D''Almeida 246 pts · End 1: 6/6" [ref=f1e189]':
              - generic [ref=f1e190]: "4"
              - generic [ref=f1e191]:
                - paragraph [ref=f1e192]: Marcus D'Almeida
                - generic [ref=f1e193]: "246 pts · End 1: 6/6"
            - 'button "5 Deepika Kumari 243 pts · End 1: 6/6" [ref=f1e194]':
              - generic [ref=f1e195]: "5"
              - generic [ref=f1e196]:
                - paragraph [ref=f1e197]: Deepika Kumari
                - generic [ref=f1e198]: "243 pts · End 1: 6/6"
            - 'button "6 An San 245 pts · End 1: 6/6" [ref=f1e199]':
              - generic [ref=f1e200]: "6"
              - generic [ref=f1e201]:
                - paragraph [ref=f1e202]: An San
                - generic [ref=f1e203]: "245 pts · End 1: 6/6"
        - generic [ref=f1e204]:
          - generic [ref=f1e205]:
            - button "🤖 AI Target Cameras (Primary)" [ref=f1e206]
            - button "📋 Multi-Lane Scorecard Matrix" [ref=f1e210]
            - button "⚡ Manual Override Scorepad" [active] [ref=f1e215]
          - generic [ref=f1e219]:
            - button "Add Archer" [ref=f1e220]
            - button "End Session" [ref=f1e224]
        - generic [ref=f1e227]:
          - generic [ref=f1e228]:
            - generic [ref=f1e229]:
              - generic [ref=f1e230]:
                - generic [ref=f1e231]:
                  - generic [ref=f1e232]:
                    - generic [ref=f1e233]: End 1
                    - heading "Brady Ellison" [level=3] [ref=f1e234]
                    - generic [ref=f1e235]: Lane 1
                  - paragraph [ref=f1e236]: Arrow 6 of 6 in End 1
                - generic [ref=f1e237]:
                  - generic [ref=f1e238]:
                    - generic [ref=f1e239]: End Subtotal
                    - generic [ref=f1e240]: 32 pts
                  - generic [ref=f1e242]:
                    - generic [ref=f1e243]: Total Score
                    - generic [ref=f1e244]: 322 pts
              - generic [ref=f1e245]:
                - generic [ref=f1e246]:
                  - generic [ref=f1e247]: Current End Arrows
                  - generic [ref=f1e248]: 1x 10s this end
                - generic [ref=f1e252]:
                  - generic [ref=f1e253]:
                    - generic [ref=f1e254]: "#1"
                    - generic [ref=f1e255]: X
                  - generic [ref=f1e256]:
                    - generic [ref=f1e257]: "#2"
                    - generic [ref=f1e258]: M
                  - generic [ref=f1e259]:
                    - generic [ref=f1e260]: "#3"
                    - generic [ref=f1e261]: "8"
                  - generic [ref=f1e262]:
                    - generic [ref=f1e263]: "#4"
                    - generic [ref=f1e264]: M
                  - generic [ref=f1e265]:
                    - generic [ref=f1e266]: "#5"
                    - generic [ref=f1e267]: "4"
                  - generic [ref=f1e268]:
                    - generic [ref=f1e269]: "#6"
                    - generic [ref=f1e270]: "4"
              - generic [ref=f1e271]:
                - text: Tap Score to Record Arrow
                - generic [ref=f1e272]:
                  - button "X Bullseye" [disabled] [ref=f1e273]:
                    - generic [ref=f1e274]: X
                    - generic [ref=f1e275]: Bullseye
                  - button "10 10 pts" [disabled] [ref=f1e276]:
                    - generic [ref=f1e277]: "10"
                    - generic [ref=f1e278]: 10 pts
                  - button "9 9 pts" [disabled] [ref=f1e279]:
                    - generic [ref=f1e280]: "9"
                    - generic [ref=f1e281]: 9 pts
                  - button "8 8 pts" [disabled] [ref=f1e282]:
                    - generic [ref=f1e283]: "8"
                    - generic [ref=f1e284]: 8 pts
                  - button "7 7 pts" [disabled] [ref=f1e285]:
                    - generic [ref=f1e286]: "7"
                    - generic [ref=f1e287]: 7 pts
                  - button "6 6 pts" [disabled] [ref=f1e288]:
                    - generic [ref=f1e289]: "6"
                    - generic [ref=f1e290]: 6 pts
                  - button "5 5 pts" [disabled] [ref=f1e291]:
                    - generic [ref=f1e292]: "5"
                    - generic [ref=f1e293]: 5 pts
                  - button "4 4 pts" [disabled] [ref=f1e294]:
                    - generic [ref=f1e295]: "4"
                    - generic [ref=f1e296]: 4 pts
                  - button "3 3 pts" [disabled] [ref=f1e297]:
                    - generic [ref=f1e298]: "3"
                    - generic [ref=f1e299]: 3 pts
                  - button "2 2 pts" [disabled] [ref=f1e300]:
                    - generic [ref=f1e301]: "2"
                    - generic [ref=f1e302]: 2 pts
                  - button "1 1 pts" [disabled] [ref=f1e303]:
                    - generic [ref=f1e304]: "1"
                    - generic [ref=f1e305]: 1 pts
                  - button "M Miss" [disabled] [ref=f1e306]:
                    - generic [ref=f1e307]: M
                    - generic [ref=f1e308]: Miss
              - generic [ref=f1e309]:
                - generic [ref=f1e310]:
                  - button "Prev End" [disabled] [ref=f1e311]
                  - button "Next End" [ref=f1e314]
                - generic [ref=f1e317]:
                  - button "Undo Arrow" [ref=f1e318]
                  - button "End Complete → Next End" [ref=f1e322]
            - generic [ref=f1e325]:
              - heading "Complete Match Scorecard — Brady Ellison (Lane 1)" [level=3] [ref=f1e326]
              - table [ref=f1e332]:
                - rowgroup [ref=f1e333]:
                  - row [ref=f1e334]:
                    - 'columnheader "End #" [ref=f1e335]'
                    - columnheader "Arrow Scores" [ref=f1e336]
                    - columnheader "End Total" [ref=f1e337]
                    - columnheader "Running Total" [ref=f1e338]
                - rowgroup [ref=f1e339]:
                  - row [ref=f1e340]:
                    - cell "End 1" [ref=f1e341]
                    - cell "X 0 8 0 4 4 6" [ref=f1e342]:
                      - generic [ref=f1e343]:
                        - generic "Click to view/override score" [ref=f1e344] [cursor=pointer]: X
                        - generic "Click to view/override score" [ref=f1e345] [cursor=pointer]: "0"
                        - generic "Click to view/override score" [ref=f1e346] [cursor=pointer]: "8"
                        - generic "Click to view/override score" [ref=f1e347] [cursor=pointer]: "0"
                        - generic "Click to view/override score" [ref=f1e348] [cursor=pointer]: "4"
                        - generic "Click to view/override score" [ref=f1e349] [cursor=pointer]: "4"
                        - generic "Click to view/override score" [ref=f1e350] [cursor=pointer]: "6"
                    - cell "32 pts" [ref=f1e351]
                    - cell "32 pts" [ref=f1e352]
                  - row [ref=f1e353]:
                    - cell "End 2" [ref=f1e354]
                    - cell "9 X X 9 9 9" [ref=f1e355]:
                      - generic [ref=f1e356]:
                        - generic "Click to view/override score" [ref=f1e357] [cursor=pointer]: "9"
                        - generic "Click to view/override score" [ref=f1e358] [cursor=pointer]: X
                        - generic "Click to view/override score" [ref=f1e359] [cursor=pointer]: X
                        - generic "Click to view/override score" [ref=f1e360] [cursor=pointer]: "9"
                        - generic "Click to view/override score" [ref=f1e361] [cursor=pointer]: "9"
                        - generic "Click to view/override score" [ref=f1e362] [cursor=pointer]: "9"
                    - cell "56 pts" [ref=f1e363]
                    - cell "88 pts" [ref=f1e364]
          - generic [ref=f1e366]:
            - heading "Session Competitors (6)" [level=3] [ref=f1e368]
            - generic [ref=f1e375]:
              - generic [ref=f1e376] [cursor=pointer]:
                - generic [ref=f1e377]:
                  - generic [ref=f1e378]: "1"
                  - generic [ref=f1e379]:
                    - paragraph [ref=f1e380]: Brady Ellison
                    - paragraph [ref=f1e381]: Lane 1 · Round 7
                - generic [ref=f1e382]:
                  - generic [ref=f1e383]:
                    - text: "322"
                    - generic [ref=f1e384]: pts
                  - button "Remove archer from session" [ref=f1e385]
              - generic [ref=f1e389] [cursor=pointer]:
                - generic [ref=f1e390]:
                  - generic [ref=f1e391]: "2"
                  - generic [ref=f1e392]:
                    - paragraph [ref=f1e393]: Mete Gazoz
                    - paragraph [ref=f1e394]: Lane 2 · Round 7
                - generic [ref=f1e395]:
                  - generic [ref=f1e396]:
                    - text: "246"
                    - generic [ref=f1e397]: pts
                  - button "Remove archer from session" [ref=f1e398]
              - generic [ref=f1e402] [cursor=pointer]:
                - generic [ref=f1e403]:
                  - generic [ref=f1e404]: "3"
                  - generic [ref=f1e405]:
                    - paragraph [ref=f1e406]: Kim Woo-jin
                    - paragraph [ref=f1e407]: Lane 3 · Round 7
                - generic [ref=f1e408]:
                  - generic [ref=f1e409]:
                    - text: "251"
                    - generic [ref=f1e410]: pts
                  - button "Remove archer from session" [ref=f1e411]
              - generic [ref=f1e415] [cursor=pointer]:
                - generic [ref=f1e416]:
                  - generic [ref=f1e417]: "4"
                  - generic [ref=f1e418]:
                    - paragraph [ref=f1e419]: Marcus D'Almeida
                    - paragraph [ref=f1e420]: Lane 4 · Round 5
                - generic [ref=f1e421]:
                  - generic [ref=f1e422]:
                    - text: "246"
                    - generic [ref=f1e423]: pts
                  - button "Remove archer from session" [ref=f1e424]
              - generic [ref=f1e428] [cursor=pointer]:
                - generic [ref=f1e429]:
                  - generic [ref=f1e430]: "5"
                  - generic [ref=f1e431]:
                    - paragraph [ref=f1e432]: Deepika Kumari
                    - paragraph [ref=f1e433]: Lane 5 · Round 5
                - generic [ref=f1e434]:
                  - generic [ref=f1e435]:
                    - text: "243"
                    - generic [ref=f1e436]: pts
                  - button "Remove archer from session" [ref=f1e437]
              - generic [ref=f1e441] [cursor=pointer]:
                - generic [ref=f1e442]:
                  - generic [ref=f1e443]: "6"
                  - generic [ref=f1e444]:
                    - paragraph [ref=f1e445]: An San
                    - paragraph [ref=f1e446]: Lane 6 · Round 5
                - generic [ref=f1e447]:
                  - generic [ref=f1e448]:
                    - text: "245"
                    - generic [ref=f1e449]: pts
                  - button "Remove archer from session" [ref=f1e450]
        - generic [ref=f1e455]:
          - generic [ref=f1e456]:
            - generic [ref=f1e461]:
              - heading "Batch Folder & Target Image Scorer" [level=3] [ref=f1e462]
              - paragraph [ref=f1e463]: Upload a folder of target photos or specify a server directory to auto-score multiple shots at once
            - button "Minimize Batch Scorer" [ref=f1e465]
          - generic [ref=f1e468]:
            - generic [ref=f1e469]:
              - button "Browse Local Folder (Upload)" [ref=f1e470]
              - button "Local Server Directory Path" [ref=f1e474]
            - generic [ref=f1e479]:
              - generic [ref=f1e480]:
                - generic [ref=f1e481]:
                  - generic [ref=f1e482]: Select Target Image Folder *
                  - generic [ref=f1e487] [cursor=pointer]:
                    - paragraph [ref=f1e488]: Click to select an entire folder of target photos
                    - paragraph [ref=f1e489]: Automatically loads and scores all .JPG and .PNG files
                - generic [ref=f1e490]:
                  - checkbox "Save scored points & arrows directly to active session database" [checked] [ref=f1e491]
                  - generic [ref=f1e492] [cursor=pointer]: Save scored points & arrows directly to active session database
              - generic [ref=f1e493]:
                - generic [ref=f1e494]:
                  - heading "Score Attribution" [level=4] [ref=f1e495]
                  - generic [ref=f1e496]:
                    - generic [ref=f1e497]:
                      - generic [ref=f1e498]: Assign to Archer
                      - combobox [ref=f1e499]:
                        - 'option "Lane 1: Brady Ellison" [selected]'
                        - 'option "Lane 2: Mete Gazoz"'
                        - 'option "Lane 3: Kim Woo-jin"'
                        - 'option "Lane 4: Marcus D''Almeida"'
                        - 'option "Lane 5: Deepika Kumari"'
                        - 'option "Lane 6: An San"'
                    - generic [ref=f1e500]:
                      - generic [ref=f1e501]: End / Round Number
                      - spinbutton [ref=f1e502]: "1"
                - button "Start Batch Processing" [ref=f1e504]
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test'
  2   | 
  3   | test.describe('Archery Match Scoring & Manual Slot Override E2E Suite', () => {
  4   |   test.beforeEach(async ({ page }) => {
  5   |     await page.goto('/login')
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
> 31  |     await btn10.click()
      |                 ^ Error: locator.click: Test timeout of 30000ms exceeded.
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
  106 |       // Setup dialog handler to accept confirm dialog
  107 |       page.once('dialog', async (dialog) => {
  108 |         await dialog.accept()
  109 |       })
  110 | 
  111 |       await endSessionBtn.click()
  112 |       await page.waitForTimeout(2000)
  113 | 
  114 |       // Verify active session switched or toast displayed
  115 |       await expect(page.locator('text=Match Scoring & Target Vision').first()).toBeVisible()
  116 |     }
  117 |   })
  118 | })
  119 | 
```