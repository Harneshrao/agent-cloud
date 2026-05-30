# Private alpha test invite

Copy and send to alpha testers. Update the setup URL before sending.

---

Hey — I'm testing a private alpha of Agent Cloud (deploy Python agents, run tasks, and inspect execution logs).

Could you spend ~15 minutes trying it with **no help from me unless you get blocked?**

### What to do

1. **Create or select a project** (top bar)
2. Go to **Deployments**
3. Click **Deploy sample echo agent**
4. Click **Run your first task**
5. Open the execution trace / logs after it runs
6. Go to **API keys** and create one key
7. Answer the **short feedback** questions on that page

**Full program:** [`docs/FIRST_5_USERS.md`](FIRST_5_USERS.md) · **Founder script:** [`docs/ALPHA_TEST_SCRIPT.md`](ALPHA_TEST_SCRIPT.md)

**Optional challenge**

* Deploy `sample_fail`
* Run it
* Open **Failed tasks**
* Recover by redeploying echo and running again

### While you test

Please say out loud:

* what you expect to happen
* anything confusing
* where you pause or hesitate
* anything that makes you feel unsure whether it worked

### I'm testing

* clarity
* speed
* trust
* whether the next step feels obvious

### If anything breaks

Please send:

* screenshot
* what you clicked
* what you expected

Brutally honest feedback helps the most — don't worry about being polite.

Thanks.

---

## Local setup (attach for dev testers)

```
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
py -3.11 run_all.py
```

Dashboard: http://localhost:3000
