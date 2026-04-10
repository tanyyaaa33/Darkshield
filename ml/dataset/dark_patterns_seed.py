"""
Hand-curated seed examples for dark pattern detection (Indian e-commerce context).

Each entry: text, label (one of 10 categories), site, vertical.
Total: 220+ examples (22+ per category).
"""

from __future__ import annotations

from typing import Any, Dict, List

_BRANDS_ECOM = ["Amazon.in", "Flipkart", "Myntra", "Nykaa", "BigBasket"]
_BRANDS_FOOD = ["Zomato", "Swiggy"]
_BRANDS_TRAVEL = ["MakeMyTrip", "Cleartrip", "IRCTC"]


def _ex(
    text: str,
    label: str,
    site: str = "amazon.in",
    vertical: str = "ecommerce",
) -> Dict[str, Any]:
    return {"text": text, "label": label, "site": site, "vertical": vertical}


# --- fake_urgency (24+) ---
_FAKE_URGENCY = [
    "Only 2 left in stock — order in the next 00:03:42!",
    "Hurry! Offer ends in 00:15:22. Price may increase after timer.",
    "Sirf 2 bacha! Jaldi karo — limited stock on Amazon.in",
    "Lightning deal: 87% claimed. Timer: 00:09:11",
    "Flash sale ends in 00:01:07 on Flipkart. Don't miss it!",
    "Only 3 rooms left at this price on MakeMyTrip — book now!",
    "Nykaa sale: Limited quantity — 00:45:00 remaining",
    "Myntra End of Reason Sale: Stock flying! Timer running",
    "BigBasket: Only a few slots left for today 6–8 PM delivery",
    "Zomato: FREE delivery ends in 00:12:00 for this restaurant",
    "Swiggy: Offer expires in 00:08:33 — order before it's gone",
    "IRCTC Tatkal opens in 00:04:59 — be ready!",
    "Cleartrip: Flight price locked for 00:19:44 only",
    "Last few tickets at this fare — book in 00:06:06",
    "Hurry! 14 people are viewing this deal right now on Flipkart",
    "Almost gone: 95% sold in Mumbai region on Amazon.in",
    "Deal ends tonight at 11:59 PM — countdown started",
    "Limited period offer — sirf aaj ke liye!",
    "Only 1 left at ₹499 — next price ₹899 after countdown",
    "Fastest fingers first — sale stock almost finished on Myntra",
    "Timer: 00:02:11 — your cart price is not guaranteed after this",
    "Selling fast! Only 4 items left in your size on Nykaa",
    "High demand — complete payment within 00:10:00 to keep price",
    "Offer valid for next 00:30:00 only on BigBasket",
]

# --- confirm_shaming (24+) ---
_CONFIRM_SHAMING = [
    "No thanks, I prefer paying full MRP",
    "No thanks, I don't want to save money today",
    "I'll pay extra — unsubscribe me from savings",
    "Nahi, mujhe discount nahi chahiye (I don't want discount)",
    "Skip protection — I like risky orders",
    "No thanks, I enjoy paying convenience fees",
    "Decline free trial — I love paying from day one",
    "I don't care about my skin — skip Nykaa routine",
    "No thanks, I'd rather miss cashback on Flipkart",
    "Continue without savings — I'm okay wasting money",
    "No thanks, I want slower delivery on Amazon.in",
    "I'll shop without rewards — who needs points?",
    "Skip — I prefer hidden charges at checkout",
    "No thanks, I don't want free returns on Myntra",
    "Decline insurance — I like gambling with my trip on MakeMyTrip",
    "No thanks, I hate cheaper flights on Cleartrip",
    "Skip Zomato Gold — I enjoy paying delivery every time",
    "No thanks, I don't want Swiggy One benefits",
    "I'll pay more — turn off personalized deals",
    "No thanks, I prefer full price groceries on BigBasket",
    "Decline EMI — I want one painful payment",
    "Skip warranty — I trust fate for electronics on Flipkart",
    "No thanks, I don't want IRCTC travel insurance",
    "Continue without meal — I like hungry train journeys",
]

# --- hidden_costs (24+) ---
_HIDDEN_COSTS = [
    "Convenience fee of ₹49 will be added at checkout on Zomato",
    "Taxes and platform fee calculated at final payment on Swiggy",
    "Delivery surge may apply — final price shown before pay on Amazon.in",
    "Packaging fee and GST extra — visible only at checkout on BigBasket",
    "Payment gateway charges applicable on final page for Flipkart",
    "Hotel resort fee payable at property — not included in MakeMyTrip total",
    "Cleartrip: seat selection charges extra during checkout",
    "IRCTC: service charge and GST added before payment gateway",
    "Nykaa: shipping fee waived only above ₹999 — else added at checkout",
    "Myntra: ₹99 styling fee may apply for try-and-buy at checkout",
    "Handling fee and state tax applied at payment step on Amazon.in",
    "Small cart fee ₹29 for orders below ₹199 — revealed at checkout",
    "Dynamic currency conversion fee may apply — final on bank page",
    "Bag fee and municipal charges extra — shown only before pay",
    "Express delivery surcharge added at last step on BigBasket",
    "Platform fee and partner charges — total on payment page Zomato",
    "Additional convenience charges for UPI under ₹100 on Swiggy",
    "GST on delivery fee calculated at checkout Flipkart",
    "Insurance add-on pre-selected — remove at checkout MakeMyTrip",
    "Tips and service charge default selected — edit at checkout",
    "Cross-border fee may apply — disclosed before pay only",
    "Payment processing fee ₹15 for COD — shown at end on Myntra",
    "Eco fee and recycling charge added at checkout for electronics",
    "Priority boarding fee — final amount on Cleartrip checkout",
]

# --- visual_interference (22+) ---
_VISUAL_INTERFERENCE = [
    "The 'No' button is greyed out until you scroll the full terms on Flipkart",
    "Unsubscribe link is tiny light-grey text at bottom on MakeMyTrip emails",
    "Continue button is bright green; 'Skip offers' is barely visible on Amazon.in",
    "Fake disabled look on 'Decline' — must wait 5 seconds on Nykaa popup",
    "Primary CTA covers half the screen — close X is off-screen on Zomato",
    "Toggle for marketing SMS is pre-on and same color as background Myntra",
    "Checkbox for add-ons hidden below fold on BigBasket checkout",
    "Decline protection looks like a broken link on Cleartrip",
    "Radio for 'Standard delivery' appears inactive but is clickable Swiggy",
    "Dark pattern: 'Save card' looks mandatory though optional on Amazon.in",
    "IRCTC page: captcha and continue compete — misaligned buttons",
    "Flipkart: bundled offer selected with checkmark mimicking required field",
    "Nykaa: sample add-on looks like part of product image",
    "Myntra: size guide opens over 'Add to Bag' so mis-taps occur",
    "BigBasket: membership banner blocks cart checkout button",
    "MakeMyTrip: insurance opt-out requires expanding accordion first",
    "Zomato: tip presets huge; custom tip field minimized",
    "Swiggy: 'View cart' hidden behind profile menu on mobile web",
    "Amazon.in: sponsored results styled like organic grid items",
    "Flipkart: exchange banner pushes 'Buy without exchange' to corner",
    "Cleartrip: bundle upsell modal blocks back navigation",
    "Nykaa: free gift auto-applied with confusing remove control",
]

# --- sneaking (22+) ---
_SNEAKING = [
    "₹2 charity donation added to cart automatically on Amazon.in — remove in cart",
    "Flipkart silently added extended warranty — check cart summary",
    "Zomato Plus trial auto-added to restaurant checkout without clear notice",
    "Swiggy Instamart added a ₹5 bag fee by default in cart",
    "MakeMyTrip pre-ticked travel insurance on flight booking",
    "Cleartrip added carbon offset without explicit consent — edit in summary",
    "Nykaa mini sample kit auto-included in bag — uncheck to remove",
    "Myntra added 'Style tips' paid service to cart during sale",
    "BigBasket membership month slipped into order if checkbox missed",
    "Amazon.in Prime add-on suggested as one-click add-to-order",
    "Flipkart SmartPack bundled into phone purchase by default",
    "IRCTC catering combo auto-selected for some trains",
    "Zomato gold renewal checkbox pre-checked on checkout page",
    "Swiggy 'priority support' fee sneaked into final bill",
    "Nykaa 'gift wrap' enabled by default for premium brands",
    "Myntra 'try at home' fee auto-added for select items",
    "BigBasket 'green packaging' charge toggled on silently",
    "MakeMyTrip hotel 'breakfast included' upsell added unless removed",
    "Cleartrip lounge access auto-suggested and added on continue",
    "Amazon.in 'Amazon Pay Later' enrollment prompt adds steps that feel mandatory",
    "Flipkart 'complete protection' auto-on for electronics category",
    "Swiggy coupon auto-applied that increases minimum order value",
]

# --- forced_continuity (22+) ---
_FORCED_CONTINUITY = [
    "Free trial converts to ₹299/month — auto-renew unless cancelled 24h before Nykaa",
    "Zomato Gold renews automatically — manage only in app settings",
    "Swiggy One membership renews yearly — no email reminder before charge",
    "Amazon.in Prime auto-renews on saved card — disable deep in account",
    "Flipkart Plus subscription continues billing silently after promo ends",
    "Myntra Insider renews monthly — cancellation path not shown at signup",
    "BigBasket BBstar auto-renewal — must call support to stop some plans",
    "MakeMyTrip wallet auto top-up enabled by default for 'faster booking'",
    "Cleartrip 'price alert' subscription bills as premium feature after trial",
    "IRCTC partner wallet auto-reload when balance low — turned on by default",
    "Nykaa Pinkbox: recurring beauty box charges until you skip each month",
    "Free sample program enrolls you into paid replenishment Myntra",
    "Zomato Pro trial ends → paid plan without prominent consent banner",
    "Swiggy 'chef's special' subscription rolls into paid after 7 days",
    "Amazon.in Audible free trial converts with minimal pre-charge email",
    "Flipkart 'smart upgrade' program renews device plan automatically",
    "BigBasket scheduled order repeats weekly until manually stopped",
    "MakeMyTrip holiday package EMI auto-debits next instalments",
    "Cleartrip concierge service rolls into quarterly billing",
    "Nykaa auto-replenish for skincare charges monthly silently",
    "Myntra 'trend alerts' premium SMS pack renews weekly",
    "Swiggy 'unlimited refills' club charges after hidden trial window",
]

# --- misdirection (22+) ---
_MISDIRECTION = [
    "To unsubscribe from MakeMyTrip emails, click 'Manage preferences' then find tiny link",
    "Flipkart: 'Keep savings' is huge; 'Remove coupon' is a text link",
    "Amazon.in: 'No rush delivery' buried under 'Recommended fastest'",
    "Nykaa: 'Decline free gift' requires scrolling past glowing reviews",
    "Myntra: 'Exit without offer' hidden under three modals",
    "BigBasket: 'Skip membership' looks like a secondary error message",
    "Zomato: 'Continue without tip' below large preset tip buttons",
    "Swiggy: 'I don't want priority' phrased confusingly next to fees",
    "Cleartrip: 'Book without add-ons' in footer-like strip",
    "IRCTC: insurance decline requires reading paragraph then small checkbox",
    "MakeMyTrip: 'Standard room' less visible than 'Upgrade now'",
    "Flipkart exchange flow pushes 'Yes' with animated arrow",
    "Amazon.in: 'Create account' same size as 'Sign in' for misclicks",
    "Nykaa: shade matcher tool opens before you can skip account creation",
    "Myntra: 'Maybe later' for app install smaller than 'Download now'",
    "BigBasket: slot selection defaults to paid express",
    "Zomato: 'View bill' hidden; 'Pay now' prominent during rush",
    "Swiggy: cancel order path requires multiple confirmations with scary text",
    "Cleartrip: 'Basic fare' collapsed; upsells expanded by default",
    "MakeMyTrip: 'Skip insurance' sounds risky with warning icon",
    "Amazon.in: 'Share data for deals' on by default; opt-out in settings",
    "Flipkart: 'Notify me' for OOS looks like 'Buy now' on mobile",
]

# --- social_proof_manipulation (24+) ---
_SOCIAL_PROOF = [
    "4,982 people are viewing this hotel right now on MakeMyTrip",
    "127 users booked this flight in the last 1 hour on Cleartrip",
    "Zomato: 'Bestseller' badge with fake-looking 50,000+ orders claim",
    "Swiggy: 'Trending in your area' with inflated rider count",
    "Amazon.in: 'Amazon's Choice' with unclear criteria for this category",
    "Flipkart: '1 lakh+ bought this week' without verifiable source",
    "Nykaa: '5★ rated by 20,000 customers' — includes incentivised reviews",
    "Myntra: 'Most wished for' list sponsored but looks editorial",
    "BigBasket: 'Household favourite' tag on private label push",
    "IRCTC partner site: 'High demand — 300 people viewing seats'",
    "MakeMyTrip: 'Only 3 seats left at this fare' pressure line",
    "Cleartrip: fake countdown of 'recent bookings' repeating same numbers",
    "Zomato reviews sorted to highlight short positive blurbs first",
    "Swiggy: 'Popular with similar users' carousel with generic items",
    "Amazon.in: 'Frequently bought together' bundles unrelated essentials",
    "Flipkart: inflated star average by merging variants",
    "Nykaa: 'Editor's pick' for paid partnership without label",
    "Myntra: 'Style score 9.8/10' from unclear methodology",
    "BigBasket: 'Neighbourhood favourite' without neighbourhood data",
    "MakeMyTrip: 'Recommended by travellers' generic quotes",
    "Cleartrip: '92% recommend this airline' small print says survey n=40",
    "Zomato: bot-like 5-star reviews clustered same day",
    "Swiggy: 'Top rated in 2 km' with threshold hidden",
    "Amazon.in: 'Limited time deal' with always-on 'deal' price",
]

# --- bait_and_switch (22+) ---
_BAIT_SWITCH = [
    "Advertised ₹499 on Google for Flipkart — landing shows ₹899",
    "Amazon.in listing headline ₹299; PDP shows ₹449 after 'coupon applied'",
    "MakeMyTrip banner fare ₹1,999; checkout totals ₹3,450 with fees",
    "Cleartrip hotel 'from ₹1,200/night' becomes ₹2,800 after taxes",
    "Zomato 50% OFF banner — max discount ₹50 in fine print",
    "Swiggy 'BOGO' requires minimum order ₹499 not stated upfront",
    "Nykaa 'Flat 40% off' excludes bestsellers in T&C",
    "Myntra 'Starting at ₹299' only for socks; jeans full price",
    "BigBasket '₹1 deals' available only with ₹1,200 basket",
    "IRCTC partner shows low seat fare; convenience fee spikes total",
    "Flipkart exchange value quoted high; final quote lower at pickup",
    "Amazon.in 'Today's deal' price same as yesterday regular price",
    "MakeMyTrip 'free cancellation' only for premium fare tier",
    "Cleartrip 'lowest price guarantee' excludes cashback offers",
    "Zomato 'unlimited' thali has item caps in small text",
    "Swiggy 'no delivery fee' only for first 3 km",
    "Nykaa gift with purchase out of stock but offer banner remains",
    "Myntra 'extra 10% off' applies to non-sale MRP only",
    "BigBasket 'member price' same as competitor non-member price",
    "Amazon.in lightning 'was ₹9,999' uses inflated crossed MRP",
    "Flipkart bundle 'save ₹2,000' vs buying separately actually ₹400",
    "MakeMyTrip 'free meal' only on long-haul international hidden in fare rules",
]

# --- roach_motel (22+) ---
_ROACH_MOTEL = [
    "Cancel Myntra order easy — but close account requires emailing support",
    "Nykaa Pinkbox: skip month hidden; cancel subscription needs chat agent",
    "Zomato Gold: unsubscribe only via app, not website settings",
    "Swiggy One: cancellation buried under 4 menus on mobile",
    "Amazon.in Prime: end membership requires multiple retention screens",
    "Flipkart Plus: deactivate benefits page times out often users report",
    "BigBasket BBstar: stop renewal via call center hours only",
    "MakeMyTrip wallet withdrawal requires KYC and 7-day wait",
    "Cleartrip rewards: redeem easy, but closing account needs ticket",
    "IRCTC linked wallet unlinking requires fax/email legacy flow",
    "Myntra try-and-buy return: pickup slots scarce — feels trapped",
    "Nykaa auto-replenish: 'Turn off' button loads another upsell page",
    "Zomato: delete account option missing; only deactivate",
    "Swiggy: personal data download available but account deletion unclear",
    "Amazon.in: close account path not linked from main help",
    "Flipkart: seller account closure different from buyer — confusing",
    "BigBasket: membership refund policy opaque; chatbot loops",
    "MakeMyTrip: holiday package cancellation fee 90% unless upgrade",
    "Cleartrip: lounge pass cancellation non-refundable fine print",
    "Nykaa PRO membership: must cancel before billing date hidden in FAQ",
    "Myntra Insider: downgrade path not shown during sale season",
    "Zomato corporate billing: exit requires manager approval workflow",
]


def _with_sites(label: str, texts: List[str], sites_verticals: List[tuple]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for i, t in enumerate(texts):
        site, vert = sites_verticals[i % len(sites_verticals)]
        out.append(_ex(t, label, site=site, vertical=vert))
    return out


_SITES_ROT_ECOM = [
    ("amazon.in", "electronics"),
    ("flipkart.com", "electronics"),
    ("myntra.com", "fashion"),
    ("nykaa.com", "fmcg"),
    ("bigbasket.com", "fmcg"),
]
_SITES_ROT_FOOD = [
    ("zomato.com", "food_delivery"),
    ("swiggy.com", "food_delivery"),
]
_SITES_ROT_TRAVEL = [
    ("makemytrip.com", "travel"),
    ("cleartrip.com", "travel"),
    ("irctc.co.in", "travel"),
]


SEED_EXAMPLES: List[Dict[str, Any]] = []
SEED_EXAMPLES += _with_sites("fake_urgency", _FAKE_URGENCY, _SITES_ROT_ECOM + _SITES_ROT_FOOD + _SITES_ROT_TRAVEL)
SEED_EXAMPLES += _with_sites("confirm_shaming", _CONFIRM_SHAMING, _SITES_ROT_ECOM + _SITES_ROT_FOOD + _SITES_ROT_TRAVEL)
SEED_EXAMPLES += _with_sites("hidden_costs", _HIDDEN_COSTS, _SITES_ROT_ECOM + _SITES_ROT_FOOD + _SITES_ROT_TRAVEL)
SEED_EXAMPLES += _with_sites("visual_interference", _VISUAL_INTERFERENCE, _SITES_ROT_ECOM + _SITES_ROT_FOOD + _SITES_ROT_TRAVEL)
SEED_EXAMPLES += _with_sites("sneaking", _SNEAKING, _SITES_ROT_ECOM + _SITES_ROT_FOOD + _SITES_ROT_TRAVEL)
SEED_EXAMPLES += _with_sites("forced_continuity", _FORCED_CONTINUITY, _SITES_ROT_ECOM + _SITES_ROT_FOOD + _SITES_ROT_TRAVEL)
SEED_EXAMPLES += _with_sites("misdirection", _MISDIRECTION, _SITES_ROT_ECOM + _SITES_ROT_FOOD + _SITES_ROT_TRAVEL)
SEED_EXAMPLES += _with_sites("social_proof_manipulation", _SOCIAL_PROOF, _SITES_ROT_ECOM + _SITES_ROT_FOOD + _SITES_ROT_TRAVEL)
SEED_EXAMPLES += _with_sites("bait_and_switch", _BAIT_SWITCH, _SITES_ROT_ECOM + _SITES_ROT_FOOD + _SITES_ROT_TRAVEL)
SEED_EXAMPLES += _with_sites("roach_motel", _ROACH_MOTEL, _SITES_ROT_ECOM + _SITES_ROT_FOOD + _SITES_ROT_TRAVEL)

# Clean / none examples (for balanced training references in builder; also a few explicit seeds)
_NONE_SEEDS = [
    _ex("Add to cart — standard shipping 5–7 business days on Amazon.in", "none", "amazon.in", "electronics"),
    _ex("Track your Flipkart order with AWB number", "none", "flipkart.com", "electronics"),
    _ex("Size chart: chest 38 inch corresponds to M on Myntra", "none", "myntra.com", "fashion"),
    _ex("Ingredients: Aqua, Glycerin — Nykaa skincare label", "none", "nykaa.com", "fmcg"),
    _ex("Delivery slot: tomorrow 10:00 AM – 12:00 PM BigBasket", "none", "bigbasket.com", "fmcg"),
    _ex("Restaurant open till 11 PM — Zomato info", "none", "zomato.com", "food_delivery"),
    _ex("Swiggy order placed — rider assigned", "none", "swiggy.com", "food_delivery"),
    _ex("PNR status: confirmed — IRCTC", "none", "irctc.co.in", "travel"),
    _ex("Hotel check-in 2 PM checkout 11 AM MakeMyTrip", "none", "makemytrip.com", "travel"),
    _ex("Cleartrip: baggage allowance 15 kg economy", "none", "cleartrip.com", "travel"),
    _ex("Return policy: 10 days unused with tags Myntra", "none", "myntra.com", "fashion"),
    _ex("Customer care: help@amazon.in", "none", "amazon.in", "electronics"),
    _ex("Flipkart Seller Hub: update GSTIN", "none", "flipkart.com", "electronics"),
    _ex("Nykaa: cruelty-free badge explanation", "none", "nykaa.com", "fmcg"),
    _ex("BigBasket: organic certification details", "none", "bigbasket.com", "fmcg"),
    _ex("Zomato: menu last updated 2 days ago", "none", "zomato.com", "food_delivery"),
    _ex("Swiggy: allergen information for this dish", "none", "swiggy.com", "food_delivery"),
    _ex("MakeMyTrip: free cancellation within 24h for this fare rule", "none", "makemytrip.com", "travel"),
    _ex("IRCTC: station code NDLS New Delhi", "none", "irctc.co.in", "travel"),
    _ex("Flipkart: EMI available on orders above ₹3,000", "none", "flipkart.com", "electronics"),
]

SEED_EXAMPLES.extend(_NONE_SEEDS)
