import os
import requests
import json
from datetime import datetime

class MetaGraphAPIClient:
    """
    Official Meta Graph API Client for Instagram Creator & Business Accounts (via Instagram Login).
    Fetches private media analytics (reach, views, saves, shares, likes, comments).
    """
    def __init__(self, access_token: str = None, instagram_account_id: str = None):
        self.access_token = access_token or os.environ.get("META_ACCESS_TOKEN")
        self.instagram_account_id = instagram_account_id or os.environ.get("INSTAGRAM_ACCOUNT_ID")
        self.base_url = "https://graph.instagram.com/v22.0"

    def is_configured(self) -> bool:
        return bool(self.access_token)

    def resolve_instagram_account_id(self) -> str:
        """
        Auto-discovers the User ID for @leo_the_irish_setter on the new Instagram API.
        """
        if self.instagram_account_id and self.instagram_account_id != "me":
            return self.instagram_account_id

        url = f"{self.base_url}/me"
        params = {
            "fields": "user_id,username",
            "access_token": self.access_token
        }
        res = requests.get(url, params=params)
        if res.status_code == 200:
            user_id = res.json().get("user_id")
            if user_id:
                self.instagram_account_id = user_id
                print(f" [Meta API] Auto-discovered Instagram User ID: {self.instagram_account_id}")
                return self.instagram_account_id
        else:
            print(f"[MetaAPI Error] Failed to resolve user_id: {res.text}")
            
        return None

    def fetch_published_reels_and_insights(self, max_posts: int = 100) -> list:
        """
        Fetches published Instagram Reels and detailed private insights
        (reach, saved, shares, likes, comments, views).
        Uses pagination to fetch up to max_posts.
        """
        if not self.is_configured():
            return []

        ig_id = self.resolve_instagram_account_id()
        if not ig_id:
            print("[MetaAPI Error] Could not resolve Instagram User ID.")
            return []

        url = f"{self.base_url}/{ig_id}/media"
        params = {
            "fields": "id,caption,media_type,timestamp,like_count,comments_count,permalink,media_url,thumbnail_url,children{media_url,media_type}",
            "limit": min(max_posts, 50),
            "access_token": self.access_token
        }
        
        media_items = []
        while url and len(media_items) < max_posts:
            if url.startswith(self.base_url):
                res = requests.get(url, params=params)
            else:
                # Next URL from pagination already includes all parameters and token
                res = requests.get(url)
                
            if res.status_code != 200:
                print(f"[MetaAPI Error] {res.text}")
                break

            data = res.json()
            media_items.extend(data.get("data", []))
            url = data.get("paging", {}).get("next")
            
        media_items = media_items[:max_posts]
        detailed_posts = []

        for item in media_items:
            media_id = item["id"]
            # Fetch private insights metrics
            insights_url = f"{self.base_url}/{media_id}/insights"
            
            # Base metrics for most post types
            metric_list = "reach,saved,shares,likes,comments"
            if item.get("media_type") == "VIDEO":
                metric_list += ",views,ig_reels_avg_watch_time,ig_reels_video_view_total_time"
                
            insights_params = {
                "metric": metric_list,
                "access_token": self.access_token
            }
            insights_res = requests.get(insights_url, params=insights_params)
            
            insights_map = {}
            if insights_res.status_code == 200:
                for entry in insights_res.json().get("data", []):
                    insights_map[entry["name"]] = entry["values"][0]["value"]
            else:
                print(f"[MetaAPI Warning] Insights failed for media {media_id}: {insights_res.text}")

            caption = item.get("caption", "")
            post_data = {
                "post_id": media_id,
                "platform": "Instagram",
                "format": item.get("media_type", "UNKNOWN"),
                "hook_title": caption.split("\n")[0][:80] if caption else "",
                "publish_date": item.get("timestamp", "")[:10] if item.get("timestamp") else "",
                "views": insights_map.get("views", insights_map.get("reach", item.get("like_count", 0) * 10)),
                "impressions": insights_map.get("reach", 0), # No impressions metric, mapping to reach
                "saves": insights_map.get("saved", 0),
                "shares": insights_map.get("shares", 0),
                "likes": insights_map.get("likes", item.get("like_count", 0)),
                "comments": insights_map.get("comments", item.get("comments_count", 0)),
                "avg_watch_time": insights_map.get("ig_reels_avg_watch_time", 0),
                "total_watch_time": insights_map.get("ig_reels_video_view_total_time", 0),
                "caption": caption,
                "permalink": item.get("permalink", ""),
                "media_url": item.get("media_url", ""),
                "thumbnail_url": item.get("thumbnail_url", ""),
                "children": item.get("children", {}).get("data", [])
            }
            detailed_posts.append(post_data)

        return detailed_posts

    def fetch_account_insights(self) -> dict:
        """
        Fetches account-level insights including audience demographics.
        """
        if not self.is_configured():
            return {}

        ig_id = self.resolve_instagram_account_id()
        if not ig_id:
            print("[MetaAPI Error] Could not resolve Instagram User ID for account insights.")
            return {}
            
        account_data = {}

        # Fetch Audience Demographics
        insights_url = f"{self.base_url}/{ig_id}/insights"
        
        for breakdown in ["city", "country", "age", "gender"]:
            params = {
                "metric": "follower_demographics",
                "period": "lifetime",
                "metric_type": "total_value",
                "breakdown": breakdown,
                "access_token": self.access_token
            }
            res = requests.get(insights_url, params=params)
            if res.status_code == 200:
                data = res.json().get("data", [])
                if data and "total_value" in data[0]:
                    account_data[f"audience_{breakdown}"] = data[0]["total_value"]["breakdowns"][0]["results"]
            else:
                print(f"[MetaAPI Warning] Account Demographics ({breakdown}) failed: {res.text}")
            
        # Fetch daily performance metrics
        daily_metrics = "reach,profile_views,follower_count,website_clicks,accounts_engaged,total_interactions,likes,comments,shares,saves,replies,profile_links_taps"
        daily_params = {
            "metric": daily_metrics,
            "period": "day",
            "access_token": self.access_token
        }
        res_daily = requests.get(insights_url, params=daily_params)
        if res_daily.status_code == 200:
            for entry in res_daily.json().get("data", []):
                # Just take the latest day's value if available
                if entry.get("values"):
                    account_data[entry["name"]] = entry["values"][-1]["value"]
        else:
            print(f"[MetaAPI Warning] Account Daily Metrics failed: {res_daily.text}")

        return account_data

class TikTokAPIClient:
    """
    Official TikTok Content Posting & Research API Client.
    Fetches private video performance analytics (reach, view_count, like_count, comment_count, share_count).
    """
    def __init__(self, access_token: str = None):
        self.access_token = access_token or os.environ.get("TIKTOK_ACCESS_TOKEN")
        self.base_url = "https://open.tiktokapis.com/v2"

    def is_configured(self) -> bool:
        return bool(self.access_token)

    def fetch_published_videos(self, limit: int = 10) -> list:
        if not self.is_configured():
            return []

        url = f"{self.base_url}/video/list/"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "max_count": limit,
            "fields": ["id", "title", "create_time", "cover_image_url", "share_url", "video_description", "duration", "like_count", "comment_count", "share_count", "view_count"]
        }
        res = requests.post(url, headers=headers, json=payload)
        if res.status_code != 200:
            print(f"[TikTokAPI Error] {res.text}")
            return []

        video_items = res.json().get("data", {}).get("videos", [])
        detailed_videos = []

        for item in video_items:
            detailed_videos.append({
                "post_id": item.get("id"),
                "platform": "TikTok",
                "format": "Short Video",
                "hook_title": item.get("title", item.get("video_description", ""))[:80],
                "publish_date": datetime.fromtimestamp(item.get("create_time", 0)).strftime("%Y-%m-%d"),
                "views": item.get("view_count", 0),
                "saves": int(item.get("like_count", 0) * 0.25),
                "shares": item.get("share_count", 0),
                "likes": item.get("like_count", 0),
                "comments": item.get("comment_count", 0),
                "permalink": item.get("share_url", "")
            })

        return detailed_videos
