import unittest
from unittest.mock import patch, MagicMock
import requests
from client import TikTokClient


class TestTikTokClient(unittest.TestCase):
    def setUp(self):
        self.client = TikTokClient("test_session_123456")

    # ==========================================
    # Session Validation Tests
    # ==========================================
    @patch("requests.get")
    def test_validate_session_success(self, mock_get):
        """Verifies successful session validation when passport endpoint returns valid user_id."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": {
                "user_id": "7123456789",
                "username": "tiktok_influencer",
                "screen_name": "Influencer Nick"
            }
        }
        mock_get.return_value = mock_resp

        res = self.client.validate_session()
        self.assertTrue(res["valid"])
        self.assertEqual(res["user_id"], "7123456789")
        self.assertEqual(res["username"], "tiktok_influencer")
        self.assertFalse(res["is_auth_error"])
        self.assertFalse(res["is_temporary"])

    @patch("requests.get")
    def test_validate_session_expired_empty_userid(self, mock_get):
        """Verifies session marked as auth error when HTTP 200 returns empty user_id."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": {
                "user_id": "",
                "username": ""
            }
        }
        mock_get.return_value = mock_resp

        res = self.client.validate_session()
        self.assertFalse(res["valid"])
        self.assertTrue(res["is_auth_error"])
        self.assertFalse(res["is_temporary"])
        self.assertIn("expired/invalid", res["error"])

    @patch("requests.get")
    def test_validate_session_http_401_auth_error(self, mock_get):
        """Verifies HTTP 401 is treated as confirmed auth error."""
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_get.return_value = mock_resp

        res = self.client.validate_session()
        self.assertFalse(res["valid"])
        self.assertTrue(res["is_auth_error"])
        self.assertFalse(res["is_temporary"])
        self.assertIn("401 Unauthorized", res["error"])

    @patch("requests.get")
    def test_validate_session_http_403_auth_error(self, mock_get):
        """Verifies HTTP 403 is treated as confirmed auth error."""
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_get.return_value = mock_resp

        res = self.client.validate_session()
        self.assertFalse(res["valid"])
        self.assertTrue(res["is_auth_error"])
        self.assertFalse(res["is_temporary"])
        self.assertIn("403 Unauthorized", res["error"])

    @patch("requests.get")
    def test_validate_session_http_429_temporary_rate_limit(self, mock_get):
        """Verifies HTTP 429 rate limit is treated as temporary, NOT auth error."""
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_get.return_value = mock_resp

        res = self.client.validate_session()
        self.assertFalse(res["valid"])
        self.assertFalse(res["is_auth_error"])
        self.assertTrue(res["is_temporary"])
        self.assertIn("429 Rate Limited", res["error"])

    @patch("requests.get")
    def test_validate_session_http_500_temporary_server_error(self, mock_get):
        """Verifies HTTP 5xx is treated as temporary server error, NOT auth error."""
        mock_resp = MagicMock()
        mock_resp.status_code = 502
        mock_get.return_value = mock_resp

        res = self.client.validate_session()
        self.assertFalse(res["valid"])
        self.assertFalse(res["is_auth_error"])
        self.assertTrue(res["is_temporary"])
        self.assertIn("502 Server Error", res["error"])

    @patch("requests.get")
    def test_validate_session_network_exception_temporary(self, mock_get):
        """Verifies network connection drops are treated as temporary issues."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection reset by peer")

        res = self.client.validate_session()
        self.assertFalse(res["valid"])
        self.assertFalse(res["is_auth_error"])
        self.assertTrue(res["is_temporary"])
        self.assertTrue(res.get("is_network_error"))

    # ==========================================
    # Real-World Comment Response Verification Tests
    # ==========================================
    @patch("requests.post")
    def test_post_comment_public_confirmed_status_1(self, mock_post):
        """Verifies public comment (comment.status == 1) confirmed with CID."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status_code": 0,
            "status_msg": "Comment sent successfully",
            "comment": {
                "cid": "7320000000000000001",
                "status": 1,
                "text": "Check out my profile!"
            }
        }
        mock_post.return_value = mock_resp

        res = self.client.post_comment(12345, "Check out my profile!")
        self.assertTrue(res["success"])
        self.assertTrue(res["is_public"])
        self.assertFalse(res["is_shadow_filtered"])
        self.assertEqual(res["status"], 1)
        self.assertEqual(res["cid"], "7320000000000000001")
        self.assertIsNone(res["error_type"])

    @patch("requests.post")
    def test_post_comment_shadow_filtered_status_2(self, mock_post):
        """Verifies shadow-filtered comment (comment.status == 2, under moderation/shadowban)."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status_code": 0,
            "status_msg": "Comment sent successfully",
            "comment": {
                "cid": "7320000000000000002",
                "status": 2,
                "text": "Suspicious spammed text"
            }
        }
        mock_post.return_value = mock_resp

        res = self.client.post_comment(12345, "Suspicious spammed text")
        self.assertTrue(res["success"])
        self.assertFalse(res["is_public"])
        self.assertTrue(res["is_shadow_filtered"])
        self.assertEqual(res["status"], 2)
        self.assertEqual(res["cid"], "7320000000000000002")

    @patch("requests.post")
    def test_post_comment_rejected_when_cid_missing(self, mock_post):
        """Verifies that status_code=0 without confirmed CID is treated as unconfirmed/error."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status_code": 0,
            "status_msg": "Comment sent successfully",
            "comment": None
        }
        mock_post.return_value = mock_resp

        res = self.client.post_comment(12345, "Test comment")
        self.assertFalse(res["success"])
        self.assertEqual(res["error_type"], "unconfirmed")
        self.assertIsNone(res["cid"])
        self.assertFalse(res["is_public"])

    @patch("requests.post")
    def test_post_comment_empty_cid_unconfirmed(self, mock_post):
        """Verifies that comment object with empty string cid is rejected as unconfirmed."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status_code": 0,
            "status_msg": "Comment sent successfully",
            "comment": {
                "cid": "",
                "status": 1
            }
        }
        mock_post.return_value = mock_resp

        res = self.client.post_comment(12345, "Test comment")
        self.assertFalse(res["success"])
        self.assertEqual(res["error_type"], "unconfirmed")

    @patch("requests.post")
    def test_post_comment_spam_detection_code_30005(self, mock_post):
        """Verifies that TikTok spam code 30005 is properly recognized."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status_code": 30005,
            "status_msg": "You are commenting too fast",
            "comment": {}
        }
        mock_post.return_value = mock_resp

        res = self.client.post_comment(12345, "Test comment")
        self.assertFalse(res["success"])
        self.assertEqual(res["error_type"], "spam")
        self.assertEqual(res["status"], "spam")

    @patch("requests.post")
    def test_post_comment_http_429_rate_limit(self, mock_post):
        """Verifies HTTP 429 gateway rate limit is categorized as spam/cooldown."""
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_post.return_value = mock_resp

        res = self.client.post_comment(12345, "Test comment")
        self.assertFalse(res["success"])
        self.assertEqual(res["error_type"], "spam")

    @patch("requests.post")
    def test_post_comment_http_401_auth_failure(self, mock_post):
        """Verifies HTTP 401 response triggers auth error."""
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_post.return_value = mock_resp

        res = self.client.post_comment(12345, "Test comment")
        self.assertFalse(res["success"])
        self.assertEqual(res["error_type"], "auth")

    @patch("requests.post")
    def test_post_comment_network_timeout(self, mock_post):
        """Verifies network timeouts are gracefully caught and handled."""
        mock_post.side_effect = requests.exceptions.Timeout("Read timeout")

        res = self.client.post_comment(12345, "Test comment")
        self.assertFalse(res["success"])
        self.assertEqual(res["error_type"], "network")
        self.assertIn("timeout", res["msg"].lower())

    # ==========================================
    # Warm-up, Follow, and Browsing Tests
    # ==========================================
    @patch("requests.post")
    def test_follow_user_success(self, mock_post):
        """Verifies follow_user sends signed request and handles follow_status=1."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status_code": 0,
            "follow_status": 1
        }
        mock_post.return_value = mock_resp

        ok = self.client.follow_user("691234567890")
        self.assertTrue(ok)

    @patch("client.TikTokClient.like_video", return_value=True)
    @patch("client.TikTokClient.follow_user", return_value=True)
    @patch("client.TikTokClient.get_feed_items")
    def test_warm_up_execution(self, mock_get_items, mock_follow, mock_like):
        """Verifies warm_up scrolls items, watches, and executes likes/follows."""
        mock_get_items.return_value = [
            {"id": "7001", "author_id": "1001", "author_name": "user1"},
            {"id": "7002", "author_id": "1002", "author_name": "user2"},
            {"id": "7003", "author_id": "1003", "author_name": "user3"},
        ]

        with patch("time.sleep", return_value=None):
            with patch("random.random", return_value=0.1):  # Guarantees triggers
                stats = self.client.warm_up(min_videos=3, max_videos=3)

        self.assertEqual(stats["watched"], 3)
        self.assertEqual(stats["liked"], 3)
        self.assertEqual(stats["followed"], 3)


if __name__ == "__main__":
    unittest.main()
