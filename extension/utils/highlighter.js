/**
 * DOM annotation for detected dark patterns: wrap + tooltip + pulse for high confidence.
 */

const DS_CATEGORY_COLORS = {
  fake_urgency: "#FF4444",
  confirm_shaming: "#FF8C00",
  hidden_costs: "#FFD700",
  visual_interference: "#9B59B6",
  sneaking: "#E74C3C",
  forced_continuity: "#3498DB",
  misdirection: "#3498DB",
  social_proof_manipulation: "#3498DB",
  bait_and_switch: "#3498DB",
  roach_motel: "#3498DB",
  none: "#2ECC71",
};

function dsCategoryColor(category) {
  return DS_CATEGORY_COLORS[category] || "#3498DB";
}

function dsHumanCategory(category) {
  return String(category || "none").replace(/_/g, " ");
}

/**
 * Wrap a text node in a highlighted span and attach tooltip.
 * @param {Text} textNode
 * @param {string} category
 * @param {number} confidence 0-1
 * @param {string} explanation
 */
function dsHighlightTextNode(textNode, category, confidence, explanation) {
  if (!textNode || textNode.nodeType !== Node.TEXT_NODE) return;
  const parent = textNode.parentNode;
  if (!parent) return;
  if (parent.closest && parent.closest(".ds-highlight")) return;

  const span = document.createElement("span");
  span.className = `ds-highlight ds-${category}${confidence > 0.85 ? " ds-pulse" : ""}`;
  span.style.outlineColor = dsCategoryColor(category);
  span.dataset.dsCategory = category;
  span.dataset.dsConfidence = String(confidence);
  span.dataset.dsExplanation = explanation || "";

  const tooltip = document.createElement("div");
  tooltip.className = "ds-tooltip";
  tooltip.innerHTML = `
    <div class="ds-tooltip-title">${dsHumanCategory(category)}</div>
    <div class="ds-tooltip-meta">${Math.round(confidence * 100)}% confidence</div>
    <div class="ds-tooltip-body">${explanation || ""}</div>
  `;
  tooltip.style.borderColor = dsCategoryColor(category);

  parent.replaceChild(span, textNode);
  span.appendChild(textNode);
  span.appendChild(tooltip);

  span.addEventListener("mouseenter", () => {
    tooltip.classList.add("ds-tooltip-visible");
  });
  span.addEventListener("mouseleave", () => {
    tooltip.classList.remove("ds-tooltip-visible");
  });
}

// eslint-disable-next-line no-var
var dsHighlighter = {
  dsHighlightTextNode,
  dsCategoryColor,
};
