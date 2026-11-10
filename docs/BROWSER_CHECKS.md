# Browser interaction acceptance

`tools/guardian_browser_checks.py` executes only the fixed reviewed fixture under
`eval/browser-fixtures/`. Candidate code and generated JavaScript are never inputs.
The default is a non-executing preview. `--run --out NEW_DIRECTORY` is explicit:

```powershell
python -B tools/guardian_browser_checks.py
python -B tools/guardian_browser_checks.py --run --out work/browser-checks-new
python -B -m unittest tests.test_browser_checks -v
```

The runtime discovers Node and the existing Codex runtime's Playwright package.
It does not install npm packages or browsers. Missing dependencies, launch failure,
denied loopback, timeout, unknown checks and fixture errors stay blocked. The
installed Chrome or Edge channel is used when present on Windows; otherwise the
already installed bundled Chromium is required. Versions and dependency entry
hashes are reported. Channel compatibility is observed for the recorded version,
not guaranteed for arbitrary future releases.

The driver starts an ephemeral **127.0.0.1-only HTTP server**, creates a new
headless browser and nonpersistent context per variant, and intercepts requests
outside that origin. It never accesses a personal browser profile or inherited
storage. Browser background isolation is not guaranteed by page interception;
this is not OS network isolation. The driver closes contexts/browser/server;
the Python timeout terminates the subprocess tree using the existing Guardian
runtime helper. The harness does not change global settings, permissions or
trust, and cannot bypass an effective sandbox restriction.

## Discriminating checks

One baseline and nine deliberately buggy implementations run the same ten
assertions. Results include actual DOM values, focus sequence, accessibility
snapshot, action counts, console exceptions and browser/Playwright versions.
A mutant is rejected only when its exact expected failed-assertion set occurs;
an import error, missing assertion, process failure or timeout never passes it.

| Fixed variant | Required failed assertion(s) |
|---|---|
| baseline | None |
| double-submit | single_enter_and_click, composition_guard |
| composition-unchecked | composition_guard |
| error-clears | error_preserves_draft_focus |
| error-unassociated | error_associated |
| stale-applies | stale_navigation_rejected |
| focus-leak | dialog_keyboard_trapped |
| restore-lost | escape_restores_mounted_fallback |
| cache-unscoped | tenant_locale_cache_separated |
| plural-wrong | plural_rtl_timezone |

Double submission also doubles the legitimate Enter after composition ends; this
is why that variant must fail both action-count assertions. The composition start
and end are **synthetic DOM events**, combined with Playwright keyboard events.
This observes the browser handler guard, not a real operating-system IME.

## Obligation mapping and limits

| Audit items | Actual bounded evidence | Remaining scope |
|---|---|---|
| S05-P1 | Browser Enter/click counts, composition guard, retained draft/focus after error, stale-result rejection | OS IME and server effect/idempotency are separate |
| S06-P1 | Observed focus, keyboard traversal, labeled invalid input, error association and accessibility snapshot | AT announcements, wider task/browser matrix and complete WCAG evaluation |
| RB-S17-1 | Tab/Shift+Tab stay in open dialog, Escape closes and restores mounted heading after opener removal; faulty handlers fail by final focus | No screen reader run; general modal/inert behavior beyond this fixture not inferred |
| RB-S17-2 | Old navigation response cannot overwrite new state or draft | Backend replay/commit-timeout/reauth/reconciliation are not tested here |
| RC-09-EVAL, RC-09-DESIGN | Browser/version, keyboard sequence, focus log and ARIA snapshot retained; error and transition observations | No AT announcement timing or general assistive-technology conformity |
| S04-P1 | DOM execution, tenant/locale/count cache-key separation and console errors | No application framework SSR/hydration or server cache claim |
| S07-P1 | Actual Intl plural and timezone rendering plus RTL direction and tenant/locale separation | Fallback/pseudolocale/expansion and broader locale matrix remain open |
| RB-S19-1, RB-S19-2 | Not covered | No load, SLO, pool, p99 or causal performance conclusion |

WCAG-relevant mappings describe this fixture's observed behavior: keyboard
interaction relates to [WCAG2.2 2.1.1](https://www.w3.org/TR/WCAG22/#keyboard),
focus sequence to [2.4.3](https://www.w3.org/TR/WCAG22/#focus-order), and the
identified error to [3.3.1](https://www.w3.org/TR/WCAG22/#error-identification).
Neither a matching attribute nor an accessibility snapshot establishes complete
conformance or real screen-reader output.

Implementation uses the official [Browser context lifecycle](https://playwright.dev/docs/api/class-browser),
[keyboard API](https://playwright.dev/docs/api/class-keyboard) and
[ARIA snapshot API](https://playwright.dev/docs/api/class-locator#locator-aria-snapshot).

## Recorded local development run

On 2026-11-02, the default sandbox launched Chrome but denied HTTP loopback;
`work/browser-checks-20261102-r1` preserves the blocked result. The reviewed
execution in `r2` obtained loopback access and exposed the original expectation's
omission of the double-submit effect after composition. The fixture was not
weakened: the expected failure set now includes both causally affected checks.
The fresh final `work/browser-checks-20261102-r3/report.json` completed with
**Chrome156.0.8078.76 / Playwright1.62.1**, baseline plus all nine specific mutants
accepted, and 100 assertion observations. All ten variants produced no JavaScript
runtime exception or page request outside the fixture origin. AT and OS IME
remain `NOT_VERIFIED`; no model or professional certification is inferred.

Reports bind the harness and fixture bytes actually executed. A later source
change requires a new run; old evidence is not relabelled as a new revision.
