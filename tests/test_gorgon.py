import hashlib
import unittest
import time
from MedoSigner import Gorgon


class TestGorgon(unittest.TestCase):
    def setUp(self):
        self.unix = int(time.time())
        self.gorgon = Gorgon(
            params="aid=1340&version_name=38.6.2",
            unix=self.unix,
            data="aweme_id=12345&text=test",
            cookies="sessionid=abc123xyz"
        )

    def test_hash_correctness(self):
        """Verifies that Gorgon.hash correctly hashes the passed data string, not self.data."""
        test_str = "hello_world_tiktok"
        expected_md5 = hashlib.md5(test_str.encode('utf-8')).hexdigest()
        
        # Must match the MD5 of test_str
        self.assertEqual(self.gorgon.hash(test_str), expected_md5)
        
        # Empty string must return 32 zeros
        self.assertEqual(self.gorgon.hash(""), "0" * 32)
        self.assertEqual(self.gorgon.hash(None), "0" * 32)

    def test_hash_does_not_mix_inputs(self):
        """Verifies that hashing string A does NOT return the hash of self.data or string B."""
        str_a = "query_params_abc"
        str_b = "post_payload_xyz"
        
        hash_a = self.gorgon.hash(str_a)
        hash_b = self.gorgon.hash(str_b)
        
        self.assertNotEqual(hash_a, hash_b)
        self.assertEqual(hash_a, hashlib.md5(str_a.encode('utf-8')).hexdigest())
        self.assertEqual(hash_b, hashlib.md5(str_b.encode('utf-8')).hexdigest())

    def test_get_base_string_format(self):
        """Verifies that base_string is always 96 hex characters (3 x 32 hex chars)."""
        base_str = self.gorgon.get_base_string()
        self.assertEqual(len(base_str), 96)
        
        # Check components
        expected_p_hash = hashlib.md5("aid=1340&version_name=38.6.2".encode('utf-8')).hexdigest()
        expected_d_hash = hashlib.md5("aweme_id=12345&text=test".encode('utf-8')).hexdigest()
        expected_c_hash = hashlib.md5("sessionid=abc123xyz".encode('utf-8')).hexdigest()
        
        self.assertEqual(base_str[:32], expected_p_hash)
        self.assertEqual(base_str[32:64], expected_d_hash)
        self.assertEqual(base_str[64:96], expected_c_hash)

    def test_get_base_string_with_none_payload_and_cookies(self):
        """Verifies get_base_string works when data and cookies are None (GET requests)."""
        get_gorgon = Gorgon(params="aid=1340", unix=self.unix, data=None, cookies=None)
        base_str = get_gorgon.get_base_string()
        self.assertEqual(len(base_str), 96)
        
        expected_p_hash = hashlib.md5("aid=1340".encode('utf-8')).hexdigest()
        self.assertEqual(base_str[:32], expected_p_hash)
        self.assertEqual(base_str[32:64], "0" * 32)
        self.assertEqual(base_str[64:96], "0" * 32)

    def test_get_value_structure(self):
        """Verifies that get_value returns valid headers matching TikTok specifications."""
        val = self.gorgon.get_value()
        self.assertIn("x-gorgon", val)
        self.assertIn("x-khronos", val)
        self.assertIn("x-ss-req-ticket", val)
        
        # x-gorgon must start with prefix 0404b0d30000 and have length 52
        x_gorgon = val["x-gorgon"]
        self.assertTrue(x_gorgon.startswith("0404b0d30000"))
        self.assertEqual(len(x_gorgon), 52)
        self.assertEqual(val["x-khronos"], str(self.unix))
        self.assertEqual(val["x-ss-req-ticket"], str(self.unix * 1000))

    def test_argus_and_ladon_signatures(self):
        """Verifies that Argus and Ladon return non-empty base64 string signatures."""
        from MedoSigner import Argus, Ladon

        query_str = "aid=1340&device_id=7123456789012345678&version_name=38.6.2"
        argus_sign = Argus.get_sign(
            queryhash=query_str,
            data=None,
            timestamp=self.unix,
            aid=1340,
            license_id=1611921764,
            platform=19
        )
        self.assertIsInstance(argus_sign, str)
        self.assertTrue(len(argus_sign) > 20)

        ladon_sign = Ladon.encrypt(self.unix, 1611921764, 1340)
        self.assertIsInstance(ladon_sign, str)
        self.assertTrue(len(ladon_sign) > 20)


if __name__ == "__main__":
    unittest.main()
