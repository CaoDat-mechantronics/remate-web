"""Tests independent of real cloud credentials or network access."""
import base64
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import image_storage
import data_storage
import server

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4"
    "z8DwHwAFgAI/ScL/nwAAAABJRU5ErkJggg=="
)
DATA_URL = "data:image/png;base64," + base64.b64encode(PNG).decode()


class StorageTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original_dirs = image_storage.LOCAL_FOLDERS.copy()
        self.original_mode = image_storage.IMAGE_STORAGE
        for folder in image_storage.LOCAL_FOLDERS:
            image_storage.LOCAL_FOLDERS[folder] = self.root / folder
        image_storage.IMAGE_STORAGE = "local"
        self.addCleanup(self.restore)

    def restore(self):
        image_storage.LOCAL_FOLDERS.clear()
        image_storage.LOCAL_FOLDERS.update(self.original_dirs)
        image_storage.IMAGE_STORAGE = self.original_mode

    def test_local_all_folders(self):
        for folder in image_storage.LOCAL_FOLDERS:
            src = image_storage.store_image(folder, PNG, "png")
            self.assertTrue(src.startswith(f"/{folder}/"))
            self.assertEqual((self.root / src.lstrip("/")).read_bytes(), PNG)
            image_storage.delete_image(src, folder)
            self.assertFalse((self.root / src.lstrip("/")).exists())

    def test_remote_switch_keeps_provider(self):
        mock_b2 = MagicMock()
        mock_b2.generate_presigned_url.return_value = "https://signed.example/image"
        with patch.object(image_storage, "_save_remote") as save, \
             patch.object(image_storage, "b2_client", return_value=mock_b2), \
             patch.dict("os.environ", {"B2_BUCKET": "bucket"}):
            image_storage.IMAGE_STORAGE = "b2"
            src = image_storage.store_image("uploads", PNG, "png")
            self.assertRegex(src, r"^/media/b2/uploads/[^/]+\.png$")
            save.assert_called_once()
            image_storage.IMAGE_STORAGE = "local"
            self.assertEqual(image_storage.signed_image_url(src), "https://signed.example/image")
            image_storage.delete_image(src, "uploads")
            mock_b2.delete_object.assert_called_once()

    def test_cloudinary_switch_preserves_urls_and_delete(self):
        fake_cloud = MagicMock()
        fake_cloud.uploader.upload.side_effect = lambda stream, **kwargs: {
            "public_id": kwargs["public_id"],
            "format": kwargs["format"],
            "secure_url": "https://res.cloudinary.com/demo/image/upload/" + kwargs["public_id"] + "." + kwargs["format"],
        }
        fake_cloud.utils.cloudinary_url.side_effect = lambda public_id, **kwargs: (
            f"https://res.cloudinary.com/demo/image/upload/{public_id}.{kwargs['format']}", {}
        )
        with patch.object(image_storage, "cloudinary_client", return_value=fake_cloud):
            image_storage.IMAGE_STORAGE = "cloudinary"
            for folder in image_storage.LOCAL_FOLDERS:
                src = image_storage.store_image(folder, PNG, "png")
                self.assertRegex(src, rf"^/media/cloudinary/{folder}/[^/]+\.png$")
                upload_args, upload_kwargs = fake_cloud.uploader.upload.call_args
                self.assertEqual(upload_args[0].read(), PNG)
                self.assertEqual(upload_kwargs["public_id"], "remate/" + src[len('/media/cloudinary/'):].rsplit('.', 1)[0])
                self.assertEqual(upload_kwargs["format"], "png")
                image_storage.IMAGE_STORAGE = "b2"  # current provider changed: old URLs still work
                target = image_storage.signed_image_url(src)
                self.assertEqual(target, f"https://res.cloudinary.com/demo/image/upload/{upload_kwargs['public_id']}.png")
                image_storage.delete_image(src, folder)
                fake_cloud.uploader.destroy.assert_called_with(
                    upload_kwargs["public_id"], resource_type="image", type="upload", invalidate=True
                )
                image_storage.IMAGE_STORAGE = "cloudinary"

    def test_cloudinary_config_required_for_upload(self):
        with patch.dict("os.environ", {
            "CLOUDINARY_URL": "", "CLOUDINARY_CLOUD_NAME": "", "CLOUDINARY_API_KEY": "", "CLOUDINARY_API_SECRET": ""
        }):
            image_storage.cloudinary_client.cache_clear()
            with self.assertRaises(image_storage.ImageStorageError):
                image_storage.cloudinary_client(for_write=True)
        image_storage.cloudinary_client.cache_clear()

    def test_firebase_switch_keeps_provider(self):
        fake_bucket = MagicMock()
        fake_bucket.blob.return_value.generate_signed_url.return_value = "https://signed-firebase.example/"
        with patch.object(image_storage, "firebase_bucket", return_value=fake_bucket):
            image_storage.IMAGE_STORAGE = "firebase"
            src = image_storage.store_image("album", PNG, "png")
            self.assertTrue(src.startswith("/media/firebase/album/"))
            fake_bucket.blob.return_value.upload_from_string.assert_called_once()
            image_storage.IMAGE_STORAGE = "local"
            self.assertEqual(image_storage.signed_image_url(src), "https://signed-firebase.example/")
            image_storage.delete_image(src, "album")
            fake_bucket.blob.return_value.delete.assert_called_once()

    def test_no_arbitrary_paths(self):
        self.assertIsNone(image_storage.signed_image_url("/media/b2/uploads/../../password.txt"))
        self.assertIsNone(image_storage.signed_image_url("/media/b2/admin/secrets.png"))
        self.assertIsNone(image_storage.signed_image_url("/media/evil/uploads/file.png"))
        self.assertIsNone(image_storage._parse_reference("https://example.com/image.png"))
        self.assertIsNone(image_storage._parse_reference("/uploads/../admin.html"))
        self.assertIsNone(image_storage._parse_reference("/media/cloudinary/uploads/../../../secrets.png"))


class HttpTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original_mode = image_storage.IMAGE_STORAGE
        self.original_dirs = image_storage.LOCAL_FOLDERS.copy()
        self.old_data_dir = data_storage.DATA_DIR
        self.old_data_mode = data_storage.DATA_STORAGE
        data_storage.DATA_STORAGE = "local"
        data_storage.DATA_DIR = self.root / "data"
        data_storage.DATA_DIR.mkdir()
        for folder in image_storage.LOCAL_FOLDERS:
            image_storage.LOCAL_FOLDERS[folder] = self.root / folder
        image_storage.IMAGE_STORAGE = "local"
        self.httpd = server.Server(("127.0.0.1", 0), server.Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.cleanup)

    def cleanup(self):
        self.httpd.shutdown()
        self.thread.join(timeout=5)
        self.httpd.server_close()
        data_storage.DATA_DIR = self.old_data_dir
        data_storage.DATA_STORAGE = self.old_data_mode
        image_storage.IMAGE_STORAGE = self.original_mode
        image_storage.LOCAL_FOLDERS.clear()
        image_storage.LOCAL_FOLDERS.update(self.original_dirs)

    def request(self, method, path, data=None, token=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.httpd.server_port, timeout=5)
        headers = {}
        if data is not None:
            headers["Content-Type"] = "application/json"
        if token:
            headers["Authorization"] = "Bearer " + token
        conn.request(method, path, json.dumps(data).encode() if data is not None else None, headers)
        resp = conn.getresponse()
        status, headers, body = resp.status, dict(resp.getheaders()), resp.read()
        conn.close()
        return status, headers, body

    def login(self):
        status, _, raw = self.request("POST", "/api/login", {"username": server.ADMIN_USER, "password": server.ADMIN_PASSWORD})
        self.assertEqual(status, 200)
        return json.loads(raw)["token"]

    def test_local_crud_four_image_groups(self):
        token = self.login()
        status, _, data = self.request("POST", "/api/products", {
            "title": "Test", "category": "Phế liệu", "images": [DATA_URL]
        }, token)
        self.assertEqual(status, 201, data)
        src = json.loads(data)["images"][0]
        self.assertTrue(src.startswith("/uploads/"))
        status, headers, img = self.request("GET", src)
        self.assertEqual(status, 200)
        self.assertEqual(img, PNG)
        status, _, data = self.request("POST", "/api/album", {"image": DATA_URL, "caption": "ok"}, token)
        self.assertEqual(status, 201, data)
        self.assertTrue(json.loads(data)["src"].startswith("/album/"))
        status, _, data = self.request("PUT", "/api/expertise-images/0", {"image": DATA_URL}, token)
        self.assertEqual(status, 200, data)
        self.assertTrue(json.loads(data)["src"].startswith("/expertise/"))
        status, _, data = self.request("PUT", "/api/service-covers/0", {"image": DATA_URL}, token)
        self.assertEqual(status, 200, data)
        self.assertTrue(json.loads(data)["src"].startswith("/service-covers/"))

    def test_remote_b2_upload_via_existing_api(self):
        token = self.login()
        fake_b2 = MagicMock()
        fake_b2.generate_presigned_url.return_value = "https://signed.example/file"
        with patch.object(image_storage, "b2_client", return_value=fake_b2), \
             patch.dict("os.environ", {"B2_BUCKET": "bucket"}):
            image_storage.IMAGE_STORAGE = "b2"
            status, _, raw = self.request("POST", "/api/products", {
                "title": "Cloud", "category": "Vật tư", "images": [DATA_URL]
            }, token)
            self.assertEqual(status, 201, raw)
            src = json.loads(raw)["images"][0]
            self.assertTrue(src.startswith("/media/b2/uploads/"))
            fake_b2.put_object.assert_called_once()
            image_storage.IMAGE_STORAGE = "local"  # switch for NEW uploads
            status, headers, raw = self.request("GET", src)
            self.assertEqual(status, 302)
            self.assertEqual(headers["Location"], "https://signed.example/file")
            self.assertEqual(raw, b"")

    def test_remote_cloudinary_upload_via_existing_api(self):
        token = self.login()
        fake_cloud = MagicMock()
        fake_cloud.uploader.upload.side_effect = lambda stream, **kwargs: {
            "public_id": kwargs["public_id"], "format": kwargs["format"]
        }
        fake_cloud.utils.cloudinary_url.side_effect = lambda public_id, **kwargs: (
            f"https://res.cloudinary.com/demo/image/upload/{public_id}.{kwargs['format']}", {}
        )
        with patch.object(image_storage, "cloudinary_client", return_value=fake_cloud):
            image_storage.IMAGE_STORAGE = "cloudinary"
            status, _, raw = self.request("POST", "/api/products", {
                "title": "Cloudinary product", "category": "Vật tư", "images": [DATA_URL]
            }, token)
            self.assertEqual(status, 201, raw)
            src = json.loads(raw)["images"][0]
            self.assertTrue(src.startswith("/media/cloudinary/uploads/"))
            fake_cloud.uploader.upload.assert_called_once()
            image_storage.IMAGE_STORAGE = "b2"
            status, headers, raw = self.request("GET", src)
            self.assertEqual(status, 302)
            self.assertTrue(headers["Location"].startswith("https://res.cloudinary.com/demo/"))
            self.assertEqual(raw, b"")

    def test_remote_url_redirect_even_in_local_mode(self):
        with patch.object(server, "signed_image_url", return_value="https://signed.example/123") as sign:
            status, headers, body = self.request("GET", "/media/b2/uploads/111-12345678.png")
            self.assertEqual(status, 302)
            self.assertEqual(headers["Location"], "https://signed.example/123")
            self.assertEqual(body, b"")
            sign.assert_called_once()


if __name__ == "__main__":
    unittest.main()
