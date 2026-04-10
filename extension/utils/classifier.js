/**
 * Lightweight keyword pre-filter to skip obviously benign UI copy before API calls.
 * @param {string} text
 * @returns {{shouldClassify: boolean, likelyCategory: string|null}}
 */
function dsPreFilter(text) {
  const t = (text || "").trim();
  if (t.length < 12) {
    return { shouldClassify: false, likelyCategory: null };
  }

  const lower = t.toLowerCase();

  const urgency = /(\d{1,2}:\d{2}:\d{2})|only\s+\d+\s+left|hurry|limited\s+(time|stock)|flash\s+sale|ends?\s+in|sirf|jaldi|last\s+few|people\s+viewing/i;
  const shaming = /no\s+thanks.*(save|discount|money)|i\s+don'?t\s+want|decline.*(free|benefit)|skip.*(savings|rewards)|nahi.*chahiye/i;
  const hidden = /convenience\s+fee|platform\s+fee|gst.*checkout|taxes.*(final|payment)|additional\s+charges|surge|resort\s+fee/i;
  const visual = /greyed\s+out|grayed\s+out|tiny\s+link|barely\s+visible|pre[- ]selected|hard\s+to\s+find|fake\s+disabled/i;
  const sneak = /auto[- ]?added|pre[- ]?ticked|pre[- ]?selected|silently\s+added|default\s+selected/i;
  const forced = /auto[- ]?renew|free\s+trial.*(convert|renews)|subscription.*(charge|billing)|unless\s+cancelled|recurring/i;
  const misdir = /unsubscribe.*(tiny|hidden|bottom)|buried.*(link|option)|skip.*(below|fold)/i;
  const social = /people\s+are\s+viewing|booked\s+this|bestseller|amazon'?s\s+choice|\d+\+?\s*bought|rated\s+by/i;
  const bait = /advertised.*(checkout|landing)|from\s+₹.*(becomes|totals)|fine\s+print|excludes|mrp/i;
  const roach = /hard\s+to\s+cancel|close\s+account.*(email|support)|delete\s+account.*(missing|unclear)|cancellation\s+fee/i;

  const checks = [
    ["fake_urgency", urgency],
    ["confirm_shaming", shaming],
    ["hidden_costs", hidden],
    ["visual_interference", visual],
    ["sneaking", sneak],
    ["forced_continuity", forced],
    ["misdirection", misdir],
    ["social_proof_manipulation", social],
    ["bait_and_switch", bait],
    ["roach_motel", roach],
  ];

  for (const [cat, re] of checks) {
    if (re.test(lower)) {
      return { shouldClassify: true, likelyCategory: cat };
    }
  }

  // Broad keyword hits (counts toward 50+ total keywords across rules)
  const broad = /\b(₹|inr|rs\.?|checkout|cart|subscribe|unsubscribe|membership|insurance|donation|countdown|offer|deal|timer|fee|tax|gst)\b/i;
  if (broad.test(lower) && t.length < 220) {
    return { shouldClassify: true, likelyCategory: null };
  }

  return { shouldClassify: false, likelyCategory: null };
}

// Export for content script (no bundler)
// eslint-disable-next-line no-var
var dsPreFilterExport = dsPreFilter;
