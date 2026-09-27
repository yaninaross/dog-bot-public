# Social Media Agent

This repository contains a multi-agent system designed to benchmark external market intelligence and track internal content performance for Instagram and TikTok accounts, specifically tailored for `@leo_the_irish_setter`.

## System Overview

The system is composed of multiple agents that execute sequentially:

1. **Agent #1: External Market Intelligence & Style Guide**
   - Fetches recent posts from benchmark accounts.
   - Analyzes weekly trends and audio tracks.
   - Maintains a living Brand Inspiration Guide.

2. **Agent #2: Decoupled Internal Performance Pipeline**
   - **Pull & Tag Job**: Fetches post insights via Meta Graph API and uses a Gemini LLM to apply a strict 15-attribute luxury taxonomy to the visual content, appending results to `output/post_library.jsonl`.
   - **Analysis Job**: Reads the post library, deterministically groups posts by their LLM tags, computes average performance rates, and generates ranked combinations as `output/hypotheses.json`.

## API Setup (Instagram Login)

Agent #2 connects to the Meta Graph API using the modern **Instagram Login** route, which does NOT require a linked Facebook Page or App Review for fetching insights from your own account. 

Insights on the Instagram Login API have been live since March 2025 and require the `instagram_business_manage_insights` permission.

### How to configure:
1. Ensure your Instagram account is a Professional account (Business or Creator).
2. Create an app on `developers.facebook.com` with the **Manage messaging and content on Instagram** use case.
3. Select **API setup with Instagram Login**.
4. Add the `instagram_business_manage_insights` permission.
5. Add your Instagram account as an **Instagram Tester** in the App Roles and accept the invite at `https://www.instagram.com/accounts/manage_access/`.
6. Generate a long-lived access token (starts with `IGAA`).
7. Save this token as `META_ACCESS_TOKEN` in your `.env` file.

*For detailed setup instructions, please refer to the `INSTAGRAM_API_SETUP_GUIDE.md` file in this repository.*

## Execution

Run the main pipeline:
```bash
python3 main.py
```

The output artifacts are generated in the `output/` directory:
- `WEEKLY_DIGEST.md`
- `BRAND_INSPIRATION_GUIDE.md`
- `post_library.jsonl`
- `hypotheses.json`
- `hypotheses.md`
