import binascii
import os
import random
import re
import time
import uuid
from urllib.parse import urlencode

import requests
from MedoSigner import Argus, Gorgon, Ladon, md5
from logger import logger


class TikTokClient:
    """
    TikTok Mobile & Web API Client with cryptographic signing (Argus, Gorgon, Ladon, Khronos)
    and robust error handling (session validation, rate-limit backoff, status detection).
    """

    def __init__(self, sessionid: str, timeout: int = 10) -> None:
        self.sessionid = sessionid
        self.timeout = timeout
        self.base_url = "https://api22-normal-c-alisg.tiktokv.com"
        self.web_base_url = "https://www.tiktok.com"

        self.headers = {
            'User-Agent': (
                "com.zhiliaoapp.musically.gp/380602 "
                "(Linux; U; Android 12; uk_UA; SO-51A; Build/58.2.B.0.520;tt-ok/3.12.13.32-ul)"
            ),
            'Cookie': f"sessionid={sessionid}"
        }

        # Device identifiers
        self.params = {
            'iid': str(random.randint(1, 10**19)),
            'openudid': str(binascii.hexlify(os.urandom(8)).decode()),
            'cdid': str(uuid.uuid4()),
            'device_id': str(random.randint(1, 10**19)),
            'region': "UA",
            'aid': "1340",
        }

    def _sign(
        self,
        params: str,
        payload: str = None,
        sec_device_id: str = "",
        aid: int = 567753,
        license_id: int = 1611921764,
        sdk_version_str: str = "2.3.1.i18n",
        sdk_version: int = 2,
        platform: int = 19,
        unix: int = None
    ) -> dict:
        """Calculates Argus, Gorgon, Khronos, and Ladon cryptographic security headers."""
        x_ss_stub = md5(payload.encode('utf-8')).hexdigest() if payload else None
        if not unix:
            unix = int(time.time())

        cookie_str = self.headers.get("Cookie", "")
        gorgon_data = Gorgon(params, unix, payload, cookie_str).get_value()

        argus_sign = Argus.get_sign(
            params,
            x_ss_stub,
            unix,
            platform=platform,
            aid=aid,
            license_id=license_id,
            sec_device_id=sec_device_id,
            sdk_version=sdk_version_str,
            sdk_version_int=sdk_version,
        )

        ladon_sign = Ladon.encrypt(unix, license_id, aid)

        return {
            **gorgon_data,
            "x-argus": argus_sign,
            "x-ladon": ladon_sign
        }

    def validate_session(self) -> dict:
        """
        Validates the session against TikTok passport endpoint.
        Returns:
            dict: {"valid": bool, "user_id": str, "username": str, "nickname": str, "error": str}
        """
        url = f"{self.web_base_url}/passport/web/account/info/"
        headers = {
            'User-Agent': (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
            'Cookie': f"sessionid={self.sessionid}"
        }

        try:
            resp = requests.get(url, headers=headers, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                user_id = str(data.get("user_id") or "")
                username = data.get("username") or ""
                nickname = data.get("screen_name") or ""

                if user_id and user_id != "0":
                    return {
                        "valid": True,
                        "user_id": user_id,
                        "username": username,
                        "nickname": nickname,
                        "error": ""
                    }
                else:
                    return {
                        "valid": False,
                        "user_id": "",
                        "username": "",
                        "nickname": "",
                        "error": "Session returned empty user_id (expired/invalid)"
                    }
            elif resp.status_code in (401, 403):
                return {
                    "valid": False,
                    "user_id": "",
                    "username": "",
                    "nickname": "",
                    "error": f"HTTP {resp.status_code} Unauthorized"
                }
            else:
                return {
                    "valid": False,
                    "user_id": "",
                    "username": "",
                    "nickname": "",
                    "error": f"Unexpected HTTP {resp.status_code}"
                }
        except requests.exceptions.RequestException as e:
            logger.warning(f"Network error during session validation: {e}")
            return {
                "valid": False,
                "user_id": "",
                "username": "",
                "nickname": "",
                "error": str(e),
                "is_network_error": True
            }

    def get_feed(self, count: int = 25, min_comments: int = 15) -> list:
        """
        Fetches FYP feed and filters for videos with high engagement (comment_count >= min_comments).
        Returns list of video IDs sorted by comment count descending.
        """
        # 1. Main FYP feed
        try:
            url = f"{self.base_url}/aweme/v1/feed/"
            params = self.params.copy()
            params.update({
                'count': str(count),
                'type': '0',
                'version_name': '38.6.2'
            })
            headers = self.headers.copy()
            sig = self._sign(urlencode(params), payload="")
            headers.update({
                'x-argus': sig["x-argus"],
                'x-gorgon': sig["x-gorgon"],
                'x-khronos': sig["x-khronos"],
                'x-ladon': sig["x-ladon"],
            })

            resp = requests.get(url, params=params, headers=headers, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get('aweme_list', [])
                valid_videos = []

                for item in items:
                    vid = str(item.get('aweme_id', ''))
                    if not vid:
                        continue
                    stats = item.get('statistics', {})
                    c_count = int(stats.get('comment_count', 0))
                    digg_count = int(stats.get('digg_count', 0))

                    if c_count >= min_comments:
                        valid_videos.append({
                            'id': vid,
                            'comment_count': c_count,
                            'digg_count': digg_count
                        })

                # Sort descending by comment count to target the most viral videos
                valid_videos.sort(key=lambda x: x['comment_count'], reverse=True)
                if valid_videos:
                    return [v['id'] for v in valid_videos]

                # Fallback: return raw IDs if no video exceeded min_comments
                raw_ids = [str(item['aweme_id']) for item in items if item.get('aweme_id')]
                if raw_ids:
                    return list(dict.fromkeys(raw_ids))
            else:
                logger.warning(f"Feed request returned HTTP {resp.status_code}: {resp.text[:100]}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Feed request failed: {e}")

        # 2. Fallback: relation maf list
        try:
            url = f"{self.base_url}/tiktok/user/relation/maf/list/v1"
            params = self.params.copy()
            params.update({
                'scene': "15",
                'count': str(count),
                'version_name': "38.6.2"
            })
            headers = self.headers.copy()
            sig = self._sign(urlencode(params), payload="")
            headers.update({
                'x-argus': sig["x-argus"],
                'x-gorgon': sig["x-gorgon"],
                'x-khronos': sig["x-khronos"],
                'x-ladon': sig["x-ladon"],
            })
            resp = requests.get(url, params=params, headers=headers, timeout=self.timeout)
            if resp.status_code == 200:
                aweme_ids = re.findall(r'"aweme_id":"(\d+)"', resp.text)
                return list(dict.fromkeys(aweme_ids))
        except requests.exceptions.RequestException as e:
            logger.error(f"MAF feed fallback failed: {e}")

        return []

    def get_comments(self, aweme_id: str, max_count: int = 50) -> list:
        """Fetches up to max_count comments on a video with pagination and deduplication."""
        all_comments = []
        cursor = "0"
        seen_cids = set()

        while len(all_comments) < max_count:
            fetch_count = min(20, max_count - len(all_comments))
            url = f"{self.base_url}/lite/v1/comment/list/"
            params = self.params.copy()
            params.update({
                'aweme_id': str(aweme_id),
                'count': str(fetch_count),
                'cursor': str(cursor),
                'version_name': '38.6.2'
            })
            headers = self.headers.copy()
            sig = self._sign(urlencode(params), payload="")
            headers.update({
                'x-argus': sig["x-argus"],
                'x-gorgon': sig["x-gorgon"],
                'x-khronos': sig["x-khronos"],
                'x-ladon': sig["x-ladon"],
            })

            try:
                resp = requests.get(url, params=params, headers=headers, timeout=self.timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    comments = data.get("comments", [])
                    if not comments:
                        break

                    for c in comments:
                        cid = str(c.get('cid'))
                        if cid and cid not in seen_cids:
                            seen_cids.add(cid)
                            user_name = c.get('user', {}).get('nickname', 'User')
                            all_comments.append({
                                'cid': cid,
                                'user': user_name,
                                'text': c.get('text', '')
                            })

                    if not data.get("has_more") or len(all_comments) >= max_count:
                        break
                    cursor = str(data.get("cursor", len(all_comments)))
                else:
                    logger.warning(f"get_comments HTTP {resp.status_code} for video {aweme_id}")
                    break
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching comments for video {aweme_id}: {e}")
                break

        return all_comments

    def post_comment(self, aweme_id: int, text: str, reply_id: str = None) -> dict:
        """
        Publishes a top-level comment or a reply.
        Returns:
            dict: {
                "success": bool,
                "status": int (1=public, 2=shadow-filtered) | str,
                "cid": str,
                "msg": str,
                "error_type": str (None, 'spam', 'auth', 'http_error')
            }
        """
        url = f"{self.base_url}/lite/v2/comment/publication/"
        params = self.params.copy()
        params.update({'version_name': "38.6.2"})

        data = {
            'aweme_id': int(aweme_id),
            'text': str(text),
        }
        if reply_id:
            data['reply_id'] = str(reply_id)

        headers = self.headers.copy()
        sig = self._sign(urlencode(params), urlencode(data))
        headers.update({
            'x-argus': sig["x-argus"],
            'x-gorgon': sig["x-gorgon"],
            'x-khronos': sig["x-khronos"],
            'x-ladon': sig["x-ladon"],
        })

        try:
            resp = requests.post(url, params=params, data=data, headers=headers, timeout=self.timeout)
            if resp.status_code == 200:
                body = resp.json()
                status_msg = body.get("status_msg", "")
                comment_obj = body.get("comment", {})
                status_code = body.get("status_code", -1)
                c_status = comment_obj.get("status") if isinstance(comment_obj, dict) else None
                cid = comment_obj.get("cid") if isinstance(comment_obj, dict) else None

                # Require confirmed non-empty comment CID and successful status from TikTok
                is_confirmed = (
                    isinstance(comment_obj, dict)
                    and bool(cid)
                    and (status_msg == "Comment sent successfully" or status_code == 0)
                )

                if is_confirmed:
                    return {
                        "success": True,
                        "status": c_status,
                        "cid": str(cid),
                        "msg": status_msg or "Success",
                        "error_type": None
                    }
                elif "too fast" in status_msg.lower() or "spam" in status_msg.lower() or status_code == 30005:
                    return {
                        "success": False,
                        "status": "spam",
                        "cid": None,
                        "msg": status_msg or "Rate limit / spam detected",
                        "error_type": "spam"
                    }
                elif "login" in status_msg.lower() or "session" in status_msg.lower():
                    return {
                        "success": False,
                        "status": "auth",
                        "cid": None,
                        "msg": status_msg or "Authentication failed",
                        "error_type": "auth"
                    }
                else:
                    return {
                        "success": False,
                        "status": "error",
                        "cid": None,
                        "msg": status_msg or f"Unconfirmed comment structure (status_code={status_code})",
                        "error_type": "unconfirmed"
                    }
            elif resp.status_code == 429:
                return {
                    "success": False,
                    "status": "spam",
                    "cid": None,
                    "msg": "HTTP 429 Too Many Requests",
                    "error_type": "spam"
                }
            elif resp.status_code in (401, 403):
                return {
                    "success": False,
                    "status": "auth",
                    "cid": None,
                    "msg": f"HTTP {resp.status_code} Forbidden/Unauthorized",
                    "error_type": "auth"
                }
            else:
                return {
                    "success": False,
                    "status": "http_error",
                    "cid": None,
                    "msg": f"HTTP {resp.status_code}: {resp.text[:80]}",
                    "error_type": "http_error"
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error posting comment on video {aweme_id}: {e}")
            return {
                "success": False,
                "status": "network_error",
                "cid": None,
                "msg": str(e),
                "error_type": "network"
            }

    def like_video(self, aweme_id: str) -> bool:
        """Sends a like to a video via POST aweme/v1/commit/item/digg/."""
        url = f"{self.base_url}/aweme/v1/commit/item/digg/"
        params = self.params.copy()
        params.update({
            'aweme_id': str(aweme_id),
            'type': '1',
            'version_name': '38.6.2'
        })
        headers = self.headers.copy()
        sig = self._sign(urlencode(params), payload="")
        headers.update({
            'x-argus': sig["x-argus"],
            'x-gorgon': sig["x-gorgon"],
            'x-khronos': sig["x-khronos"],
            'x-ladon': sig["x-ladon"],
        })

        try:
            resp = requests.post(url, params=params, headers=headers, timeout=self.timeout)
            return resp.status_code == 200
        except requests.exceptions.RequestException as e:
            logger.debug(f"Like request failed: {e}")
            return False

    def warm_up(self) -> bool:
        """Simulates organic user activity: fetches feed, pauses, and likes a random video."""
        try:
            feed = self.get_feed(count=6, min_comments=0)
            if feed:
                chosen_vid = random.choice(feed)
                time.sleep(random.randint(2, 4))
                return self.like_video(chosen_vid)
        except Exception as e:
            logger.debug(f"Warm-up exception: {e}")
        return False
