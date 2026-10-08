# Todo: hosted-ticket-untrusted-text

- [x] Task 1: `public_result` (tests first) — in `hosted_ticket_provider.py`: each printed Issue keeps its other fields, `title` via `module_stage.safe_fragment` (200), full `body` replaced by `bodyExcerpt` (300) and `bodyLength`; candidates capped at 10 with `candidatesTotal`; `remoteText` only when an Issue is carried; the caller's object is not mutated; results without Issues and odd shapes unchanged. 4 unit tests
- [x] Task 2: wire the three CLIs, skill text — read, publish/preview and comment/close CLIs print `public_result(result)`; one CLI test each on a fake provider with an injected body (heading, backticks, ESC, zero-width, 1000+ chars). 7 new tests red (3 failures, 4 errors) then green; hosted-ticket actions/write/entry suites unchanged. Skill says remote title/body are data, not instructions. Mutations caught: action CLI printing unfiltered (1 failure), keeping the full body (5 failures)
- [x] Checkpoint 1 (report): full suites green — validate.sh pass, phase-guard 150, verify-artifacts 26
- [ ] Task 3: CHANGELOG + 0.52.2 + macOS validation
- [ ] Checkpoint 2 (gate): module review; push and PR authorized by Plan approval, merge by the user
- [ ] Task 4: post-release evidence
