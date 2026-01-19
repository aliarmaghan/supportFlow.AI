Run comprehensive test? (y/n): n
Running individual tests...
Loaded 55 articles from src/data/FAQs.json
🏭 Testing Production Memory System with Groq
============================================================

👤 CUSTOMER: First message (New Conversation)
====================================================================================================
🆔 Conversation ID: affb2470...

🔍 Classification: INTEGRATION | Priority: URGENT

😤 Sentiment: frustrated
🚨 Escalation Required: True
⚡ Processing Time: 8132ms
🤖 GROQ RESPONSE:
Hi [Name],

I’m really sorry you’re experiencing checkout failures — I understand how critical this is for your business. I’ve flagged this as a **high‑priority integration issue** and will have our senior engineering team investigate right away.

**In the meantime, could you please check the following items?**
These steps often surface the most common causes of Stripe‑related checkout errors:

1. **API keys**
   - Log into your Stripe dashboard → **Developers > API keys**.
   - Verify that the **Live secret key** (or Test key, if you’re in test mode) matches the one configured in our platform’s **Payments > Stripe** settings.
   - Ensure the key hasn’t been rotated or revoked recently.

2. **Webhook endpoint**
   - In Stripe → **Developers > Webhooks**, confirm the endpoint URL is still active and shows a **green “Enabled”** status.
   - Review the recent webhook event logs for any **400/500** responses from our side.
   - If you see errors, copy the most recent payload and response details—they’ll help us pinpoint the failure.

3. **Account status**
   - Check the **Stripe Dashboard → Settings → Account details** for any alerts (e.g., required verification, payout holds, or compliance notices). 

   - Verify that your account isn’t in **“restricted”** mode.

4. **Recent changes**
   - Have any of the following been updated in the last 24 h?
     - New pricing plans or product SKUs in our app
     - Custom field mappings for the Stripe integration
     - Deployments or code pushes to your checkout page
   - If so, reverting the change (or temporarily disabling it) can isolate the issue.

5. **Error details shown to customers**
   - Capture a screenshot or exact error message (e.g., “card declined”, “payment intent failed”, or a generic 5xx).
   - If possible, reproduce the checkout in an incognito window and note the network response (you can view this in Chrome DevTools → Network tab). 

**What happens next**

- I’ve opened an **Urgent Escalation

----------------------------------------
👤 CUSTOMER: Follow-up with technical details
====================================================================================================
🔍 Classification: INTEGRATION | Priority: URGENT
😤 Sentiment: frustrated
⚡ Processing Time: 4188ms
🤖 GROQ RESPONSE:
Hi [Name],

I’m sorry to hear the checkout is returning **401 Unauthorized**—that explains the sudden drop in sales. A 401 from Stripe means the request can’t be authenticated, and it can happen even when the keys look unchanged. Here are the most common reasons and the exact steps you can take right now:  

---

### 1️⃣ Verify you’re using the **correct secret key** (not the publishable key)

| Where to check | What to look for |
|----------------|------------------|
| **Stripe → Developers → API keys** | The **Live secret key** starts with `sk_live_`. The **Test secret key** starts with `sk_test_`. |
| **Our platform → Settings → Payments → Stripe** | Ensure the value matches the **Live secret key** exactly (no extra spaces, line‑breaks, or hidden characters). |

*If the key in our UI is a test key while your checkout is in live mode, Stripe will reject the call with 401.*

---

### 2️⃣ Key rotation or revocation by Stripe

- **Automatic rotation** can occur if Stripe detects a security issue (e.g., compromised key).
- In the **API keys** page, look for a **“Revoked”** label next to the key you’re using. If it’s revoked, generate a **new secret key**, copy it, and replace the old one in our settings.

**Action:** If you see a revoked key, click **“Create secret key”**, then immediately update our Stripe integration with the new value.

---

### 3️⃣ Account status restrictions

- Go to **Stripe → Settings → Account details → Restrictions**.
- Any **“Restricted”** or **“Disabled”** status (e.g., due to verification, payout holds, or compliance alerts) will cause all API calls to be rejected with 401.

**Action:** Resolve any alerts shown (upload documents, verify identity, etc.) or let us know the exact message so we can guide you through it.     

---

### 4️⃣ IP‑

----------------------------------------
👤 CUSTOMER: Additional troubleshooting info
====================================================================================================
🔍 Classification: INTEGRATION | Priority: URGENT
😤 Sentiment: frustrated
⚡ Processing Time: 4782ms
🤖 GROQ RESPONSE:
Hi [Name],

Thanks for digging into the logs. Let’s untangle the two issues and get your checkout back online as fast as possible.

---

## 1️⃣ Why the **401 Unauthorized** errors are still showing

The 401 response is generated **when our platform contacts Stripe’s API** (e.g., to create a PaymentIntent). It isn’t caused by webhook failures, but a broken authentication flow can be triggered by the same code change you deployed yesterday. Here’s what to verify first:

| Step | What to do | Why it matters |
|------|------------|----------------|
| **a. Confirm the secret key in our UI** | Open **Settings → Payments → Stripe** and copy‑paste the **Live secret key** from Stripe → Developers → API keys. Ensure there are no extra spaces or line‑breaks. | A stray whitespace or an old test key will instantly produce 401. |
| **b. Check for key revocation** | In Stripe → Developers → API keys, see if the key you’re using is marked **Revoked**. If so, generate a new secret key and replace it in our settings. | Revoked keys are rejected with 401 regardless of the string value. |
| **c. Verify account status** | Stripe → Settings → Account details → look for any **“Restricted”** or **“Disabled”** notices. Resolve any compliance alerts. | A restricted account blocks all API calls with 401. |
| **d. Review recent code changes** | Locate the commit(s) from yesterday that touch the **payment‑service** or **Stripe client**. Specifically check: <br>• Any hard‑coded API key overrides <br>• Changes to the request headers (e.g., missing `Authorization: Bearer <key>`) <br>• New environment‑variable handling (e.g., `process.env.STRIPE_KEY` not being set in production) | A typo or missing env var will cause the request to be sent without a valid key, resulting in 401. |


----------------------------------------
👤 CUSTOMER: Update after trying suggestions
🔍 Classification: TECHNICAL | Priority: LOW
😤 Sentiment: positive
⚡ Processing Time: 11182ms
🤖 GROQ RESPONSE:
I’m glad to hear the rollback cleared the webhook errors and your payments are back up and running! 🎉

If anything else comes up—or you’d like a quick review of the deployment process to prevent similar hiccups in the future—just let me know. I’m here to help.

Have a great day!

============================================================
📊 PRODUCTION DATABASE SUMMARY
============================================================
💾 Conversation ID: affb2470-4bad-487e-a8f2-1e13da067207
👤 Customer ID: test_customer_456
📈 Status: ESCALATED
🏷️  Category: TECHNICAL
⚠️  Priority: LOW
💬 Total Messages: 9
🚨 Escalated: NO
🔍 Classifications Made: 2
📚 KB Articles Referenced: 0

📈 CLASSIFICATION EVOLUTION:
   1. INTEGRATION - URGENT (Escalation: True)
   2. TECHNICAL - LOW (Escalation: False)
Loaded 55 articles from src/data/FAQs.json

====
📊 Total Conversations: 3
📈 Common Categories: {'technical': 1, 'integration': 2}
🚨 Escalation Rate: 100.0%
⏱️  Avg Resolution Time: 0.0 minutes

📋 RECENT CONVERSATION HISTORY:
   1. 🚨 affb2470... | TECHNICAL | ESCALATED
   2. 🚨 8d949272... | INTEGRATION | ESCALATED
   3. 🚨 64209df2... | INTEGRATION | ESCALATED