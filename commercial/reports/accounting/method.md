# Accounting method

* **Window.** 1 October 2026 04:00 UTC to 7 October 2026 20:15:04 UTC, i.e. 1 October 00:00 EDT to 7 October 16:15:04 EDT
  (`counts.json`, `window_utc`).
* **Aggregate scope.** `counts.json` is an aggregate over the window; it can include concurrent work outside this design,
  so it is an upper bound on what is attributable to this project. It holds counts only (calls, token totals,
  messages, hours, days); no conversation text.
* **Tokens.** Uncached input 6,524; output 1,261,596; cache-creation 31,934,690; cache-read 891,055,522. Calls: 2,907.
* **Interaction time.** 86 messages; 3.14 hours under the 20-minute rule; 7 calendar days. The field name
  (`designer_active_hours_20min_rule`) records a 20-minute rule; the extractor's exact definition was not among the files
  supplied, and the usual reading (message gaps shorter than 20 minutes belong to one working period) is assumed, not verified.
* **Scheduler time.** `cluster_jobs.psv` is the scheduler record (job id, name, start, end, elapsed, state) of 62 jobs from the
  same window. Elapsed times sum to 18,499 s = 5.1386 h (5.14 h; 5.1 h at one decimal). This is the sum of the jobs'
  wall-clock times, not CPU-hours and not the duration of the project.
* **One implementation pass.** Jobs 43892550 to 43892556 (7 jobs): 2,255 s = 37 min 35 s of summed elapsed time; first start
  to last finish 2,576 s = 42 min 56 s.
* **Rounding.** Hours are rounded as stated; the files hold the unrounded seconds.
* **Not evidenced.** The claim of 21 further jobs and about 2.0 h has no located dataset and is withdrawn.
