# Alpha test script — send to testers

Copy the **Tester invite** section below. Founder: run `py -3.11 scripts/dev_doctor.py --readiness` before sending.

---

## Tester invite

Hey — I'm testing a private alpha of **Agent Cloud** and would love 15 minutes of honest feedback.

Could you try this with **no help from me unless you get blocked for more than 5 minutes?**

### What to do

1. Create or select a project
2. Open **Deployments**
3. Click **Deploy sample echo agent**
4. Click **Run your first task**
5. Open **Runs & traces**
6. Click **Run again**
7. Go to **API keys** and create one key

### While testing

Please say out loud:

* what you expect to happen
* anything confusing
* where you hesitate
* anything that makes you unsure whether it worked

### If anything breaks

Please send:

* screenshot
* what you clicked
* what you expected

Brutally honest feedback helps the most — don't worry about being polite.

Thanks.

---

## Optional challenge (do not send unless user finishes early)

* Deploy `sample_fail`, run it, open **Failed tasks**, recover by redeploying echo and running again

---

## Founder checklist (do not send)

| Step | Action |
|------|--------|
| T−1 day | `py -3.11 scripts/dev_doctor.py --readiness` → **READY FOR TESTER** on hosted env |
| T−0 | Send invite + dashboard URL + support channel |
| T+0 | Watch `/founder` for funnel events (no hovering) |
| T+1 | Fill scorecard: [`templates/USER_SESSION_SCORECARD.md`](templates/USER_SESSION_SCORECARD.md) |
| T+3 | 15-min interview if needed |
| After 5 | Cohort review in [`FIRST_5_USERS.md`](FIRST_5_USERS.md) |

---

## Hosted environment note

Replace localhost with your alpha URL. Include only if self-hosting:

```
Dashboard: https://your-alpha.example.com
Support: you@company.com or #alpha Slack
```

For local dev testers only, attach [`DEV_HEALTHCHECK.md`](DEV_HEALTHCHECK.md) setup block.

---

## Success definition

**User succeeded** if they: deployed echo → completed a run → viewed trace → ran again → created API key (without founder help).

**Session succeeded for PMF** if they did the above and rated “would use again” ≥4 on the API keys feedback prompt.
