# HexTract Pitch Deck — Build & Edit Prompt

Use this prompt with Claude (or paste it into any LLM with file access) to modify the HexTract pitch deck.

---

## Prompt

```
I have a PowerPoint pitch deck for "HexTract AI Agent" — a pharma BMR digitization and validation pipeline. The deck is built programmatically using a Node.js script with PptxGenJS.

**Files:**
- `slides.js` — the main build script (PptxGenJS + react-icons + sharp)
- `package.json` — dependencies: pptxgenjs, react, react-dom, react-icons, sharp

**How to build:**
1. `npm install` (in the directory containing package.json and slides.js)
2. `node slides.js`
3. Output: `HexTract_Pitch_Deck.pptx` in the same directory

**Color palette ("Midnight Executive"):**
- Navy background: #0F1B2D (main), #162338 (mid), #1E2D45 (light/cards)
- Teal accent: #0EA5E9 (primary), #0284C7 (dark), #7DD3FC (light)
- Status colors: red #EF4444, orange #F97316, green #22C55E
- Text: white #FFFFFF, off-white #F1F5F9, gray #94A3B8

**Fonts:**
- Headers: Arial Black
- Body: Calibri
- Code/monospace: Consolas

**Icons:** Rendered as PNG via react-icons (FontAwesome set) → React server-side render → sharp SVG-to-PNG → base64 inline. To add a new icon, import it from `react-icons/fa` and call `iconToBase64Png(IconComponent, colorHex, size)`.

**Current 10-slide structure:**
1. Title — "HexTract AI Agent" / "BMR Digitization & Validation with AI-Powered Extraction"
2. The Problem — $4-8B annual cost, 60-70% paper-based, 800+ FDA warnings
3. Our Solution — 4 pillars: Interchangeable LLM, LLM-as-Judge Scoring, Streamlit Review UI, Active Feedback Loop
4. How It Works — 7-stage pipeline: Input Capture → Extraction & Schema Learning → LLM-as-Judge → Human Review (Streamlit) → Re-Extraction Loop → Validated Persistence → Active Feedback Loop
5. System Architecture — 4 pipeline boxes + re-extraction loop + BMR Repository end state + Active Feedback Loop bar
6. Validation Gate — Pass/fail two-panel layout with "High-Quality Human-Curated BMR Repository" as end state
7. What We Catch — 6 error types in 2×3 grid (OOS, Missing Fields, Date Inconsistencies, Cross-Field Mismatches, Impossible Values, Status Contradictions)
8. Demo: Live Results — Batch record + COA side-by-side with deviation counts and confidence scores
9. Business Impact — 90% error reduction, 70% faster review, $50K+ saved per deviation + ALCOA+ compliance row
10. Closing — Tech stack, call to action

**Key design patterns:**
- Every slide has a navy background with a colored accent bar at top (teal for most, red for slide 2, orange for slide 7, green for slides 6 and 9)
- Cards use `navyLight` (#1E2D45) fill with rounded corners (rectRound) and outer shadow
- Slide numbers appear bottom-right as "N / 10"
- Each slide function is wrapped in a block scope `{ const s = pres.addSlide(); ... }`

**Product context:**
HexTract is a GMP (Good Manufacturing Practice) compliance tool for pharmaceutical manufacturing. It extracts structured data from handwritten batch manufacturing records (BMRs) and Certificates of Analysis (COAs) using vision LLMs, validates for deviations (OOS results, missing data, date errors, etc.), and routes flagged records through a human review loop in Streamlit. The end goal is building a high-quality, human-curated BMR repository. It follows ALCOA+ data integrity principles and 21 CFR Part 11 compliance.

---

**My change request:** [DESCRIBE WHAT YOU WANT TO CHANGE HERE]

Please read slides.js, make the edits, and rebuild with `node slides.js`. Show me the affected slides after rendering.
```

---

## Setup from scratch

If starting fresh (no `node_modules`):

```bash
mkdir pptx-build && cd pptx-build
npm init -y
npm install pptxgenjs react react-dom react-icons sharp
# Copy slides.js into this directory
node slides.js
```

## Tips

- **To preview slides as images**, install LibreOffice and run:
  ```bash
  soffice --headless --convert-to jpg --outdir ./renders HexTract_Pitch_Deck.pptx
  ```
- **To add a slide**, add a new block after the last slide in the `build()` function, increment `TOTAL`, and update slide numbers.
- **To change the product name**, find-and-replace "HexTract" in slides.js.
- **To swap the color scheme**, update the `C` object at the top of slides.js.
