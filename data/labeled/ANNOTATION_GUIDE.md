# DarkShield human validation — labeling guide

Use this guide to fill `label_human1`, `label_human2`, and `label_human3` in `human_validation_set.csv`. Each cell must be **exactly** one of the 11 allowed labels (lowercase, underscores as shown) or left empty until you label.

## Allowed labels

`fake_urgency`, `confirm_shaming`, `hidden_costs`, `visual_interference`, `sneaking`, `forced_continuity`, `misdirection`, `social_proof_manipulation`, `bait_and_switch`, `roach_motel`, `none`

---

## Category definitions and examples

### 1. `fake_urgency`

**Definition:** Language or timers that pressure a user to act quickly (stock scarcity, countdowns, “hurry”).

**Examples:**

1. “Only 2 left — offer ends in 00:04:12.”
2. “Flash sale: 95% claimed in your city.”
3. “High demand: complete payment within 10 minutes to keep this price.”

### 2. `confirm_shaming`

**Definition:** Opt-out wording that embarrasses or guilts the user for declining savings, trials, or “smart” choices.

**Examples:**

1. “No thanks, I prefer paying full price.”
2. “I don’t want free shipping today.”
3. “Decline protection — I like risky orders.”

### 3. `hidden_costs`

**Definition:** Fees, taxes, surcharges, or mandatory add-ons disclosed late (often only at checkout / pay).

**Examples:**

1. “Convenience fee calculated on the payment page.”
2. “GST and platform fee shown before you pay.”
3. “Resort fee payable at property — not in headline price.”

### 4. `visual_interference`

**Definition:** UI design that obscures the user-friendly choice (tiny text, fake-disabled look, buried controls).

**Examples:**

1. “The ‘No’ button stays grey until you scroll the full terms.”
2. “Unsubscribe is 8pt grey text at the bottom of the email.”
3. “Close X is off-screen on mobile until you scroll.”

### 5. `sneaking`

**Definition:** Items, fees, or options added without clear, affirmative consent (pre-ticked boxes, silent cart add-ons).

**Examples:**

1. “₹2 charity added to cart — remove in cart.”
2. “Extended warranty pre-selected at checkout.”
3. “Insurance toggled on by default for the flight.”

### 6. `forced_continuity`

**Definition:** Subscriptions or trials that roll into paid charges with weak notice or hard-to-find cancellation info.

**Examples:**

1. “Free trial converts to ₹299/month unless cancelled 24h before renewal.”
2. “Membership renews automatically — manage only in the app.”
3. “Wallet auto top-up enabled by default.”

### 7. `misdirection`

**Definition:** Attention steered away from cheaper/safer options or away from unsubscribe/skip paths.

**Examples:**

1. “To unsubscribe, click ‘Manage preferences’ then find the tiny link.”
2. “‘Keep savings’ is huge; ‘Remove coupon’ is a text link.”
3. “‘Skip offers’ is below three promotional banners.”

### 8. `social_proof_manipulation`

**Definition:** Social proof that is misleading, unverifiable, or inflated (“X viewing”, fake-looking reviews).

**Examples:**

1. “4,982 people are viewing this hotel right now.”
2. “Bestseller — 50,000+ orders (unclear methodology).”
3. “‘Editor’s pick’ with no sponsorship disclosure.”

### 9. `bait_and_switch`

**Definition:** Advertised price, product, or terms differ materially from what checkout shows.

**Examples:**

1. “Google ad said ₹499; PDP shows ₹899.”
2. “‘From ₹1,200/night’ becomes ₹2,800 after taxes in flow.”
3. “50% off banner — max discount ₹50 in fine print.”

### 10. `roach_motel`

**Definition:** Easy to start (subscribe, sign up, buy) but disproportionately hard to stop (cancel, delete account, refund).

**Examples:**

1. “Cancel only via email to support with 5-day SLA.”
2. “Delete account option missing; only ‘deactivate’.”
3. “Unsubscribe available in app only, not on the website you used to subscribe.”

### 11. `none`

**Definition:** Neutral informational copy with **no** meaningful dark-pattern tactic in isolation.

**Examples:**

1. “Standard delivery in 5–7 business days.”
2. “Track your order with AWB 1234567890.”
3. “Ingredients: Aqua, Glycerin — patch test recommended.”

---

## Decision rules for ambiguous cases

1. **Multiple cues:** Pick the **dominant** user-facing harm in this snippet. If urgency and social proof appear, choose whichever is **doing more work** to pressure or mislead (often `fake_urgency` if a timer/scarcity is central).
2. **Marketing vs dark pattern:** Ordinary promotional language without pressure or deception → `none`. Add `fake_urgency` only if scarcity/time pressure is **central**.
3. **Checkout fees:** If the snippet explicitly says fees/taxes appear late → `hidden_costs`, not `bait_and_switch`, unless the **headline price** is contradicted.
4. **Pre-ticked add-ons:** Default `sneaking` unless the copy is primarily about renewal (`forced_continuity`).
5. **HTML / noise:** If the snippet is mostly markup, classify based on the **visible user-facing string** after stripping tags mentally.

## Edge cases

- **Humor / parody:** If it clearly mimics a dark pattern for training, label as the **pattern being mimicked**.
- **Non-English:** Use the same taxonomy; judge intent, not language.
- **Too short / empty:** If under ~10 characters or meaningless, use `none` **only if** truly no pattern; otherwise pick best fit.

## How to use the CSV

1. Open `human_validation_set.csv` in Excel, Google Sheets, or a text editor (UTF-8).
2. Do **not** change `id`, `text`, or `label_model` unless you are fixing an obvious export bug.
3. Fill `label_human1`, `label_human2`, `label_human3` with one of the 11 labels **exactly** (lowercase).
4. Each annotator uses **one** column consistently (e.g. Alice → `label_human1`).
5. When all three columns are filled for a row, it will be included in agreement scoring.

## Running agreement metrics (after labeling)

```bash
cd darkshield
python -m ml.dataset.annotation_validator score
```

Results are written to `ml/models/saved/eval_results/annotation_agreement.json`.
