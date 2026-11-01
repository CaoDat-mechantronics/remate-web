"""Data persistence tests using a simulated B2 API; no real account required."""
import base64
import http.client
import io
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from botocore.exceptions import ClientError

import data_storage
import image_storage
import server

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4"
    "z8DwHwAFgAI/ScL/nwAAAABJRU5ErkJggg=="
)
DATA_URL = "data:image/png;base64," + base64.b64encode(PNG).decode()


def error(code, status):
    return ClientError({"Error": {"Code": code}, "ResponseMetadata": {"HTTPStatusCode": status}}, "GetObject")


class FakeB2:
    def __init__(self):
        self.objects = {}
        self.fail_reads = False
        self.fail_writes = False

    def get_object(self, Bucket, Key):
        if self.fail_reads:
            raise error("AccessDenied", 403)
        if Key not in self.objects:
            raise error("NoSuchKey", 404)
        return {"Body": io.BytesIO(self.objects[Key])}

    def head_object(self, Bucket, Key):
        if Key not in self.objects:
            raise error("404", 404)
        return {"ContentLength": len(self.objects[Key])}

    def put_object(self, Bucket, Key, Body, **kwargs):
        if self.fail_writes:
            raise error("AccessDenied", 403)
        self.objects[Key] = bytes(Body)
        return {"ETag": '"test"'}

    def generate_presigned_url(self, *args, **kwargs):
        return "https://signed.example/ok"

    def delete_object(self, Bucket, Key):
        self.objects.pop(Key, None)


class DataStorageTests(unittest.TestCase):
    def setUp(self):
        self.old_mode = data_storage.DATA_STORAGE
        self.old_local = data_storage.DATA_DIR
        self.old_image_mode = image_storage.IMAGE_STORAGE
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.fake = FakeB2()
        self.patch_client = patch("data_storage.b2_client", return_value=self.fake)
        self.patch_client.start()
        self.addCleanup(self.patch_client.stop)
        self.env_patch = patch.dict(os.environ, {"B2_BUCKET": "test-bucket"})
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        data_storage.DATA_STORAGE = "b2"
        data_storage.DATA_DIR = Path(self.temp.name) / "local"
        self.addCleanup(self.restore)

    def restore(self):
        data_storage.DATA_STORAGE = self.old_mode
        data_storage.DATA_DIR = self.old_local
        image_storage.IMAGE_STORAGE = self.old_image_mode

    def test_initialize_uploads_all_json_and_linked_images(self):
        data_storage.initialize()
        self.assertIn(data_storage.MARKER, self.fake.objects)
        for kind in data_storage.KINDS:
            self.assertIn(f"data/{kind}.json", self.fake.objects)
            values = data_storage.read_all(kind)
            self.assertIsInstance(values, list)
        album = data_storage.read_all("album")
        self.assertTrue(all(v["src"].startswith("/media/b2/album/") for v in album))
        self.assertIn(album[0]["src"].replace("/media/b2/", ""), self.fake.objects)

    def test_b2_survives_new_process_boot_without_seed_reset(self):
        data_storage.initialize()
        data_storage.write_all("products", [{"id": "my-product", "title": "Uploaded"}])
        data_storage.initialize()
        self.assertEqual(data_storage.read_all("products"), [{"id": "my-product", "title": "Uploaded"}])

    def test_missing_existing_data_never_falls_back_to_seed(self):
        data_storage.initialize()
        del self.fake.objects["data/products.json"]
        with self.assertRaises(data_storage.DataStorageError):
            data_storage.initialize()
        with self.assertRaises(data_storage.DataStorageError):
            data_storage.read_all("products")

    def test_b2_failure_never_returns_empty_or_writes_local(self):
        data_storage.initialize()
        self.fake.fail_reads = True
        with self.assertRaises(data_storage.DataStorageError):
            data_storage.read_all("products")
        self.fake.fail_reads = False
        self.fake.fail_writes = True
        with self.assertRaises(data_storage.DataStorageError):
            data_storage.write_all("products", [])
        self.assertFalse(data_storage.local_path("products").exists())

    def test_local_storage_switch(self):
        data_storage.DATA_STORAGE = "local"
        data_storage.initialize()
        data_storage.write_all("services", [{"title": "local"}])
        self.assertEqual(data_storage.read_all("services")[0]["title"], "local")
        self.assertFalse(self.fake.objects)

    def test_http_album_expertise_service_cover_json_on_b2(self):
        data_storage.initialize()
        image_storage.IMAGE_STORAGE = "b2"
        with patch.object(image_storage, "b2_client", return_value=self.fake):
            httpd = server.Server(("127.0.0.1", 0), server.Handler)
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            try:
                def request(method, path, payload=None, token=None):
                    conn = http.client.HTTPConnection("127.0.0.1", httpd.server_port, timeout=8)
                    headers = {"Content-Type": "application/json"}
                    if token:
                        headers["Authorization"] = "Bearer " + token
                    conn.request(method, path, json.dumps(payload).encode() if payload is not None else None, headers)
                    resp = conn.getresponse()
                    status, body = resp.status, resp.read()
                    conn.close()
                    return status, json.loads(body)

                status, body = request("POST", "/api/login", {"username": server.ADMIN_USER, "password": server.ADMIN_PASSWORD})
                self.assertEqual(status, 200)
                token = body["token"]
                status, item = request("POST", "/api/album", {"image": DATA_URL, "caption": "B2 album"}, token)
                self.assertEqual(status, 201)
                self.assertTrue(item["src"].startswith("/media/b2/album/"))
                self.assertTrue(any(x["id"] == item["id"] for x in data_storage.read_all("album")))
                status, result = request("PUT", "/api/expertise-images/0", {"image": DATA_URL}, token)
                self.assertEqual(status, 200)
                self.assertEqual(data_storage.read_all("expertise-images")[0]["src"], result["src"])
                status, result = request("PUT", "/api/service-covers/1", {"image": DATA_URL}, token)
                self.assertEqual(status, 200)
                self.assertEqual(data_storage.read_all("service-covers")[1]["src"], result["src"])
            finally:
                httpd.shutdown()
                thread.join(timeout=5)
                httpd.server_close()

    def test_http_backend_failure_returns_503_not_empty(self):
        data_storage.initialize()
        self.fake.fail_reads = True
        httpd = server.Server(("127.0.0.1", 0), server.Handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            conn = http.client.HTTPConnection("127.0.0.1", httpd.server_port, timeout=5)
            conn.request("GET", "/api/products")
            resp = conn.getresponse()
            self.assertEqual(resp.status, 503)
            self.assertIn("B2", resp.read().decode())
            conn.close()
        finally:
            httpd.shutdown()
            thread.join(timeout=5)
            httpd.server_close()

    def test_http_crud_persists_after_reconnect(self):
        data_storage.initialize()
        image_storage.IMAGE_STORAGE = "b2"
        with patch.object(image_storage, "b2_client", return_value=self.fake):
            httpd = server.Server(("127.0.0.1", 0), server.Handler)
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            try:
                def request(method, path, payload=None, token=None):
                    conn = http.client.HTTPConnection("127.0.0.1", httpd.server_port, timeout=8)
                    headers = {"Content-Type": "application/json"}
                    if token:
                        headers["Authorization"] = "Bearer " + token
                    conn.request(method, path, json.dumps(payload).encode() if payload is not None else None, headers)
                    resp = conn.getresponse()
                    result = resp.status, resp.read()
                    conn.close()
                    return result

                status, body = request("POST", "/api/login", {"username": server.ADMIN_USER, "password": server.ADMIN_PASSWORD})
                self.assertEqual(status, 200)
                token = json.loads(body)["token"]
                status, body = request("POST", "/api/products", {"title": "B2 test", "category": "Vật tư", "images": [DATA_URL]}, token)
                self.assertEqual(status, 201, body)
                item = json.loads(body)
                self.assertTrue(item["images"][0].startswith("/media/b2/uploads/"))
                self.assertEqual(json.loads(self.fake.objects["data/products.json"])[-1]["title"], "B2 test")
                self.assertIn(item["images"][0].removeprefix("/media/b2/"), self.fake.objects)
                # Simulated restart: run initialization again, retains customer data.
                data_storage.initialize()
                status, body = request("GET", "/api/products")
                self.assertEqual(status, 200)
                self.assertTrue(any(v["id"] == item["id"] for v in json.loads(body)))
                status, body = request("PUT", "/api/products/" + item["id"], {"title": "B2 edited", "category": "Vật tư", "images": item["images"]}, token)
                self.assertEqual(status, 200, body)
                self.assertEqual(data_storage.read_all("products")[-1]["title"], "B2 edited")
                status, body = request("DELETE", "/api/products/" + item["id"], token=token)
                self.assertEqual(status, 200, body)
                self.assertFalse(any(v["id"] == item["id"] for v in data_storage.read_all("products")))
            finally:
                httpd.shutdown()
                thread.join(timeout=5)
                httpd.server_close()


if __name__ == "__main__":
    unittest.main()
