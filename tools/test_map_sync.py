#!/usr/bin/env python3
"""Unit tests for tools/map_sync.py — no network, all HTTP stubbed."""

from __future__ import annotations

import io
import os
import shutil
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

# Allow running this file directly (python tools/test_map_sync.py)
sys.path.insert(0, str(Path(__file__).resolve().parent))

import map_sync  # noqa: E402


class _FakeResponse:
    def __init__(self, data: bytes = b"", status: int = 200):
        self._data = data
        self._pos = 0
        self.status = status
        self.headers = {}

    def read(self, n: int | None = None) -> bytes:
        if n is None or n < 0:
            chunk = self._data[self._pos :]
            self._pos = len(self._data)
            return chunk
        chunk = self._data[self._pos : self._pos + n]
        self._pos += len(chunk)
        return chunk

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class _BoomResponse:
    """Response whose read() explodes mid-stream to simulate interruption."""

    def __init__(self, prefix: bytes = b"partial-bytes-"):
        self._prefix = prefix
        self._delivered = False

    def read(self, n: int | None = None) -> bytes:
        if not self._delivered:
            self._delivered = True
            return self._prefix
        raise KeyboardInterrupt("simulated interrupt")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class CollectOfficialEntriesTest(unittest.TestCase):
    def test_filters_to_types_blobs_and_builds_urls(self) -> None:
        payload = {
            "tree": [
                {"path": "types/novice/run_back.map", "type": "blob", "sha": "a" * 40, "size": 100},
                {"path": "types/brutal/crazy one.map", "type": "blob", "sha": "b" * 40, "size": 200},
                # non-blob: ignored
                {"path": "types/solo", "type": "tree", "sha": "c" * 40},
                # not under types/: ignored
                {"path": "maps/not-a-type-map.map", "type": "blob", "sha": "d" * 40, "size": 300},
                {"path": "README.md", "type": "blob", "sha": "e" * 40, "size": 10},
                # symlink: ignored (not a blob)
                {"path": "types/race/symlinked.map", "type": "commit", "sha": "f" * 40},
            ]
        }
        entries = map_sync.collect_official_entries(payload)
        self.assertEqual(set(entries.keys()), {"novice/run_back.map", "brutal/crazy one.map"})
        self.assertEqual(entries["novice/run_back.map"]["sha"], "a" * 40)
        self.assertEqual(entries["novice/run_back.map"]["size"], 100)
        self.assertEqual(entries["novice/run_back.map"]["source_path"], "types/novice/run_back.map")
        self.assertEqual(
            entries["novice/run_back.map"]["download_url"],
            map_sync.OFFICIAL_RAW_BASE + "types/novice/run_back.map",
        )
        # Space must be percent-encoded
        self.assertIn(
            "types/brutal/crazy%20one.map",
            entries["brutal/crazy one.map"]["download_url"],
        )


class ResolveTestingFilenameTest(unittest.TestCase):
    def test_dedupes_collisions(self) -> None:
        taken: set[str] = set()
        a = map_sync.resolve_testing_filename("Foo", "https://x.test/Foo.map", taken)
        b = map_sync.resolve_testing_filename("Foo", "https://x.test/Foo.map", taken)
        c = map_sync.resolve_testing_filename("Foo", "https://x.test/Foo.map", taken)
        self.assertEqual(a, "Foo.map")
        self.assertEqual(b, "Foo (1).map")
        self.assertEqual(c, "Foo (2).map")
        self.assertEqual(taken, {"Foo.map", "Foo (1).map", "Foo (2).map"})

    def test_appends_map_extension_when_missing(self) -> None:
        taken: set[str] = set()
        got = map_sync.resolve_testing_filename("Novice", "https://x.test/download?id=123", taken)
        self.assertTrue(got.endswith(".map"))


class StreamDownloadAtomicityTest(unittest.TestCase):
    def test_cleans_tmp_on_interrupt(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            dest = Path(root) / "subdir" / "interrupted.map"
            with mock.patch.object(urllib.request, "urlopen", return_value=_BoomResponse()):
                with self.assertRaises(KeyboardInterrupt):
                    map_sync.stream_download("https://x.test/any.map", dest)
            self.assertFalse(dest.exists(), "destination should not be present")
            # No orphan temp files should linger
            leftovers = list(dest.parent.glob(".ddnetcontrol-download-*")) if dest.parent.exists() else []
            self.assertEqual(leftovers, [])

    def test_atomic_rename_on_success(self) -> None:
        payload = b"x" * 1024
        with tempfile.TemporaryDirectory() as root:
            dest = Path(root) / "sub" / "ok.map"
            with mock.patch.object(urllib.request, "urlopen", return_value=_FakeResponse(payload)):
                bytes_written = map_sync.stream_download("https://x.test/ok.map", dest)
            self.assertEqual(bytes_written, len(payload))
            self.assertTrue(dest.exists())
            self.assertEqual(dest.read_bytes(), payload)
            leftovers = list(dest.parent.glob(".ddnetcontrol-download-*"))
            self.assertEqual(leftovers, [], f"orphan temp files present: {leftovers}")


class TestingPrecheckTest(unittest.TestCase):
    def test_precheck_aborts_before_any_write_when_url_unreachable(self) -> None:
        # Arrange: temp ddnet_root with pre-existing sentinel in testingmaps/
        with tempfile.TemporaryDirectory() as root:
            types_root = Path(root)
            testing_root = types_root / "testingmaps"
            testing_root.mkdir(parents=True)
            sentinel = testing_root / "existing.map"
            sentinel_bytes = b"pre-existing sentinel content"
            sentinel.write_bytes(sentinel_bytes)

            canned_payload = {
                "Alpha": {"urls": ["https://x.test/Alpha.map"]},
                "Beta": {"urls": ["https://x.test/Beta.map"]},
            }

            def fake_request_json(url: str):
                self.assertEqual(url, map_sync.TESTING_JSON_URL)
                return canned_payload

            def fake_urlopen(request, timeout=0):
                # request is a urllib Request — method is "HEAD" or no-method+Range header
                method = getattr(request, "method", None) or request.get_method()
                if method == "HEAD":
                    raise urllib.error.HTTPError(
                        request.full_url, 404, "Not Found", hdrs=None, fp=io.BytesIO(b"")
                    )
                # Shouldn't reach fallback GET path for a hard 404 from HEAD (not a 405)
                raise AssertionError(f"Unexpected urlopen call: {method} {request.full_url}")

            state = {"version": 1, "official": {"files": {}}, "testing": {"files": {}}}

            with mock.patch.object(map_sync, "request_json", side_effect=fake_request_json), \
                 mock.patch.object(urllib.request, "urlopen", side_effect=fake_urlopen):
                with self.assertRaises(RuntimeError) as ctx:
                    map_sync.sync_testing_maps(types_root, state, dry_run=False)

            self.assertIn("unreachable", str(ctx.exception).lower())
            # Sentinel untouched
            self.assertTrue(sentinel.exists())
            self.assertEqual(sentinel.read_bytes(), sentinel_bytes)
            # Temp dir never created
            self.assertFalse((types_root / ".ddnetcontrol-testingmaps.tmp").exists())
            # State not mutated beyond what's needed
            self.assertNotIn("synced_at", state.get("testing", {}))


class SyncOfficialFilesCountTest(unittest.TestCase):
    def test_state_has_files_count_after_non_dry_run(self) -> None:
        # Minimal smoke: feed a 2-blob tree to collect_official_entries and confirm files_count
        # via a mini-integration with sync_official_types on a temp tree.
        with tempfile.TemporaryDirectory() as root:
            types_root = Path(root)
            # Canned tree with one blob
            canned_tree = {
                "sha": "0" * 40,
                "tree": [
                    {"path": "types/novice/demo.map", "type": "blob", "sha": "abc" + "0" * 37, "size": 5},
                ],
            }
            fake_bytes = b"hello"

            def fake_request_json(url: str):
                self.assertEqual(url, map_sync.OFFICIAL_TREE_URL)
                return canned_tree

            def fake_urlopen(request, timeout=0):
                # Used by stream_download — check_url_reachable is only on testing path
                return _FakeResponse(fake_bytes)

            state = {"version": 1, "official": {"files": {}}, "testing": {"files": {}}}

            with mock.patch.object(map_sync, "request_json", side_effect=fake_request_json), \
                 mock.patch.object(urllib.request, "urlopen", side_effect=fake_urlopen):
                summary = map_sync.sync_official_types(types_root, state, dry_run=False)

            self.assertEqual(summary["created"], 1)
            self.assertIn("files_count", state["official"])
            self.assertEqual(state["official"]["files_count"], 1)
            self.assertEqual(state["official"]["files_count"], len(state["official"]["files"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
