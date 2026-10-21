import unittest
from unittest.mock import patch, MagicMock
from client import TikTokClient


class TestTikTokClientCommentVerification(unittest.TestCase):
    def setUp(self):
        self.client = TikTokClient("test_session_123456")

    @patch("requests.post")
    def test_post_comment_success_with_confirmed_cid(self, mock_post):
        """Verifies that post_comment succeeds when status_msg/code=0 AND confirmed cid is present."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status_code": 0,
            "status_msg": "Comment sent successfully",
            "comment": {
                "cid": "7199999999999999999",
                "status": 1,
                "text": "Great video!"
            }
        }
        mock_post.return_value = mock_resp

        res = self.client.post_comment(12345, "Great video!")
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], 1)
        self.assertEqual(res["cid"], "7199999999999999999")
        self.assertIsNone(res["error_type"])

    @patch("requests.post")
    def test_post_comment_rejected_when_cid_missing(self, mock_post):
        """Verifies that status_code=0 without confirmed CID is treated as unconfirmed/error."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status_code": 0,
            "status_msg": "Comment sent successfully",
            "comment": None  # Missing comment object or cid
        }
        mock_post.return_value = mock_resp

        res = self.client.post_comment(12345, "Test comment")
        self.assertFalse(res["success"])
        self.assertEqual(res["error_type"], "unconfirmed")
        self.assertIsNone(res["cid"])

    @patch("requests.post")
    def test_post_comment_spam_detection(self, mock_post):
        """Verifies that spam rate-limiting responses are properly categorized."""
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


if __name__ == "__main__":
    unittest.main()
