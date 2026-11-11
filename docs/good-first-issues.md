# Good first issues

These three tasks are not implemented. Each one is small enough for a new contributor. Do not retrain the model, and do not edit `ml/models/saved/eval_results/metrics.json`, `ml/models/saved/model_comparison.json`, or `data/labeled/dataset.csv`.

## 1. Add one allowed shopping site

**Title:** Add ajio.com to the extension allowlist

**Issue:** https://github.com/tanyyaaa33/Darkshield/issues/1

The extension only runs on hosts listed in `extension/manifest.json`. Ajio (`ajio.com`) is an Indian shopping site and is not in that list.

Add both patterns in `host_permissions` and in `content_scripts[0].matches`:

- `*://ajio.com/*`
- `*://www.ajio.com/*`

Keep every host that is already there. Do not switch either list to `<all_urls>`. Do not change `web_accessible_resources`.

Do not retrain the model. Do not edit `ml/models/saved/eval_results/metrics.json`, `ml/models/saved/model_comparison.json`, or `data/labeled/dataset.csv`.

Done when Load unpacked still works and both Ajio patterns are in `host_permissions` and in the content-script `matches`.

## 2. Add a test for one existing pattern

**Title:** Add a test for the fake_urgency prefilter

**Issue:** https://github.com/tanyyaaa33/Darkshield/issues/2

This repo has no test suite. `extension/utils/classifier.js` defines `dsPreFilter` and assigns it to `dsPreFilterExport`. The first rule in that function is `fake_urgency`.

Add one test file and check that existing rule only:

- Input `Only 2 left — offer ends in 00:04:12.` (the first `fake_urgency` example in `data/labeled/ANNOTATION_GUIDE.md`) returns `shouldClassify === true` and `likelyCategory === "fake_urgency"`.
- An input shorter than 12 characters, such as `Only 2`, returns `shouldClassify === false`.

Load the script with Node’s `vm.runInNewContext` and call `dsPreFilterExport`. Run it with `node --test`. Do not add a test-runner dependency.

Do not change the regular expressions in `classifier.js`. Do not retrain the model. Do not edit `metrics.json`, `model_comparison.json`, or `dataset.csv`.

Done when `node --test` on the new file passes.

## 3. Fix one dashboard label

**Title:** Fix the leaderboard "Total Score" label

**Issue:** https://github.com/tanyyaaa33/Darkshield/issues/3

On the Leaderboard page, `dashboard/app.py` renders a card whose eyebrow text is `Total Score`. The number shown is `avg_score`: the mean of `manipulation_score` for the top 20 rows in the current vertical filter. The help line under the number already says it is the average risk in the current view.

Change that eyebrow from `Total Score` to `Average score`.

Do not change how `avg_score` is calculated. Do not change other labels. Do not retrain the model. Do not edit `metrics.json`, `model_comparison.json`, or `dataset.csv`.

Done when the Leaderboard card that displays `avg_score` reads `Average score`.
