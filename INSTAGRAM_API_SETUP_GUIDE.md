# Instagram API Access for an Analytics Agent — Setup Guide

Goal: give an agent read access to one Instagram professional account's posts and insights (reach, views, follower trends, per-post performance) using the **Instagram API with Instagram Login**. No Facebook Page, no app review, no webhooks.

Use a desktop browser (Chrome recommended) for everything on developers.facebook.com. The mobile app hides several of these screens.

---

## Part 1 — Instagram account

1. The account must be a **Professional** account (Business or Creator).
   - Check: the profile shows a **Professional dashboard** button. If it does, you're done with this part.
   - If not: Instagram → Settings → **Account type and tools** → **Switch to professional account**.
2. Make sure you can log into this account in a desktop browser at instagram.com. The token step later opens a login popup; if the login fails there, reset the password first (this happened during setup — the popup rejected credentials that worked in the app until the password was reset).
3. Keep instagram.com open in a tab, logged in as this account, for the rest of the process.

---

## Part 2 — Create the Meta app

1. Go to https://developers.facebook.com → **My Apps** → **Create App**.
2. On "What do you want your app to do?" pick **Manage messaging and content on Instagram**.
   - Do NOT pick "Authenticate and request data from users with Facebook Login".
3. Name the app, enter a contact email, business portfolio is optional → **Create App**.
4. The dashboard will show **Facebook Login for Business** and possibly **Webhooks** as products. Meta adds these automatically to every app. Ignore them — they do not affect the Instagram setup.
5. Leave the app in **Development mode**. Because it only accesses your own account, it never needs to go Live and never needs App Review.

---

## Part 3 — Open the Instagram setup page

1. In the app dashboard, left sidebar → **Use cases**.
2. Find **Manage messaging and content on Instagram** → click **Customize** (there's also an "About Instagram API" button — not that one).
3. The sidebar now shows two sub-items. Click **API setup with Instagram Login**.
   - Not "API setup with Facebook Login". That page leads with review requirements and has no token generator.
   - The URL should contain `product_route=instagram-business`.
4. Note the **Instagram app ID** and **Instagram app secret** shown at the top. Store them in a secret manager. You need them for token refresh.
5. Click **Add all required permissions**.
6. Confirm `instagram_business_manage_insights` is in the permission list. If it isn't, add it. This is the permission that unlocks account and media insights on Instagram Login. Without it, insights calls return a permissions error.
7. The page may warn: "If you want to track hashtags and insights, switch to API setup with Facebook Login." Ignore it. Insights have been available on Instagram Login since March 2025; only hashtag *search* (other people's posts) requires the Facebook Login route.
8. Skip **Configure webhooks**. Skip **Set up Instagram business login**. Skip **Complete app review**. None apply to reading your own account.

---

## Part 4 — Instagram Tester role

The account must hold the **Instagram Tester** role (not the plain "Tester" role — that one is for Facebook users and produces no Instagram invite).

1. Left sidebar → **App Roles** → **Roles** → **Add People**.
2. In the dialog, scroll to **Additional roles for this app** → select **Instagram Tester** → enter the exact Instagram username → submit.
3. Accept the invite. This is the step that trips everyone: the invite does not appear as a notification and the menu is hidden in most versions of the Instagram app. Go directly to:

   **https://www.instagram.com/accounts/manage_access/**

   (desktop browser, logged in as the account) → **Tester invites** tab → **Accept**.
4. Back on the Roles page, refresh. The username under Instagram Testers must show **Active**, not Pending.
   - If stuck on Pending: check the username spelling exactly matches; re-accept via the link above; if still stuck, remove the tester, add again, accept the new invite.

---

## Part 5 — Generate the token

1. Return to **Instagram → API setup with Instagram Login**. Hard-refresh (Ctrl+Shift+R).
2. In **Generate access tokens**, the account should be listed with a **Generate token** button. If the section says "add your account under tester role", the invite isn't Active — go back to Part 4.
3. Click **Generate token** → Instagram login popup → log in → **Allow**.
   - If the popup rejects correct credentials: log into instagram.com in another tab first; disable ad/tracking blockers and allow third-party cookies; try an incognito window with no extensions; as a last resort reset the Instagram password.
4. Copy the token. It starts with `IGAA` and is long. This is a **long-lived token, valid 60 days**. Treat it as a password.

---

## Part 6 — Verify

Paste each URL into a browser, replacing `TOKEN`.

**Identity:**
```
https://graph.instagram.com/me?fields=user_id,username&access_token=TOKEN
```
Expected: `{"user_id":"1784...","username":"youraccount","id":"..."}`. Save `user_id` — it's needed for every insights call.

**Account insights (confirms the insights permission):**
```
https://graph.instagram.com/v22.0/USER_ID/insights?metric=reach,follower_count&period=day&access_token=TOKEN
```
Expected: JSON with numeric values. A `(#10)` or `(#100)` permission error means `instagram_business_manage_insights` wasn't granted — re-check Part 3 step 6, then regenerate the token (tokens capture the permissions that existed when they were issued).

**Your media list:**
```
https://graph.instagram.com/v22.0/USER_ID/media?fields=id,caption,media_type,timestamp,like_count,comments_count,permalink&access_token=TOKEN
```

**Per-post insights** (pick an `id` from the media list):
```
https://graph.instagram.com/v22.0/MEDIA_ID/insights?metric=reach,saved,shares,likes,comments,views&access_token=TOKEN
```
Available metrics differ by media type: `views` applies to reels/videos; feed images use `impressions`-style metrics on older API versions. If a metric errors, remove it and retry.

---

## Part 7 — Token refresh (mandatory, or the agent dies in 60 days)

Long-lived tokens expire after 60 days. Refresh any time after the token is at least 24 hours old and before it expires:

```
GET https://graph.instagram.com/refresh_access_token
    ?grant_type=ig_refresh_token
    &access_token=CURRENT_TOKEN
```
Response contains a new `access_token` and `expires_in` (seconds). Store the new token and replace the old one.

Recommended: a scheduled job (e.g. Cloud Scheduler → Cloud Function every 30 days) that calls this endpoint and writes the result to Secret Manager. Alert if it fails, because an expired token cannot be refreshed — you'd have to redo Part 5.

---

## Part 8 — Wire it into the agent

### Option A — Direct API calls (recommended if the agent is your own code on GCP)

No MCP needed. The whole surface is three GET endpoints. Minimal Python:

```python
import os, requests

TOKEN = os.environ["IG_ACCESS_TOKEN"]      # from Secret Manager
USER_ID = os.environ["IG_USER_ID"]
BASE = "https://graph.instagram.com/v22.0"

def get(path, **params):
    params["access_token"] = TOKEN
    r = requests.get(f"{BASE}/{path}", params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def account_insights(days=30):
    return get(f"{USER_ID}/insights",
               metric="reach,follower_count", period="day")

def recent_media(limit=25):
    return get(f"{USER_ID}/media",
               fields="id,caption,media_type,timestamp,like_count,comments_count,permalink",
               limit=limit)["data"]

def media_insights(media_id):
    return get(f"{media_id}/insights",
               metric="reach,saved,shares,likes,comments")
```

Rate limit: roughly 200 calls per hour per token. The `x-app-usage` response header shows current usage. For an analytics agent that runs a few times a day this is not a constraint.

### Option B — MCP server (if the agent runs in Claude Desktop, Claude Code, or another MCP client)

Use an MCP server built for the Instagram Login flow (it must accept `IGAA` tokens from graph.instagram.com — servers built for the Facebook Login route expect Page tokens and won't work). Two that fit:

- `William-Gao/instagram-mcp` — Instagram only, Python, explicitly built for Instagram Login. Includes insights tools.
- `@mikusnuz/meta-mcp` — Instagram + Threads, npm.

Claude Desktop / generic MCP config (`claude_desktop_config.json`) using the npm one:

```json
{
  "mcpServers": {
    "instagram": {
      "command": "npx",
      "args": ["-y", "@mikusnuz/meta-mcp"],
      "env": {
        "INSTAGRAM_ACCESS_TOKEN": "IGAA...",
        "INSTAGRAM_USER_ID": "1784..."
      }
    }
  }
}
```

Claude Code:
```
claude mcp add instagram -e INSTAGRAM_ACCESS_TOKEN=IGAA... -e INSTAGRAM_USER_ID=1784... -- npx -y @mikusnuz/meta-mcp
```

Before trusting either server, read its source — it holds your token and makes calls on your behalf. Pin the version rather than using `-y` with latest in production.

---

## Troubleshooting quick reference

| Symptom | Cause | Fix |
|---|---|---|
| Sidebar shows only "Facebook Login for Business" | Normal — auto-added product | Go to Use cases → Customize on the Instagram use case |
| No Instagram use case anywhere | App created with wrong use case; can't be changed | Create a new app, pick the Instagram use case |
| Setup page says "add your account under tester role" | Invite not Active | Accept at instagram.com/accounts/manage_access/, check status on Roles page |
| Tester invite not visible in Instagram | Menu is hidden | Use the direct manage_access URL on desktop |
| Added "Tester" but no invite arrives | Wrong role | Remove, add as **Instagram Tester** |
| Generate token popup rejects correct login | Session/cookie issue or account flag | Log into instagram.com first; incognito; reset password |
| Insights call returns permission error | Permission not on app, or token issued before it was added | Add `instagram_business_manage_insights`, regenerate token |
| Everything stops working after ~2 months | Token expired | Set up the refresh job (Part 7) |

---

## What this setup cannot do

- Hashtag search or reading other accounts' posts — needs the Facebook Login route plus a linked Facebook Page.
- Analytics on accounts you don't own — needs App Review and Advanced Access.
- Real-time reaction to comments/DMs — needs webhooks and a public callback URL.

If any of those become requirements, create a *second* app with "API setup with Facebook Login"; don't modify this one.
