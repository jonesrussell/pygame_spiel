"""No-install archive checks; no game, graphics, network or model execution."""

from email.parser import BytesParser
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def test_wheel_sdist_and_relocated_resources(self):
        # Copy source: build_meta may write build/ and egg-info beside its input.
        with tempfile.TemporaryDirectory() as tmp:
            staging = Path(tmp) / "source"
            shutil.copytree(ROOT, staging, ignore=shutil.ignore_patterns(
                ".git", "__pycache__", "*.egg-info", "build", "dist"))
            output = Path(tmp) / "artifacts"
            output.mkdir()
            script = """
import setuptools.build_meta as backend, sys
destination = sys.argv[1]  # build_meta replaces sys.argv while invoking setup.
backend.build_sdist(destination)
backend.build_wheel(destination)
"""
            env = dict(os.environ, SOURCE_DATE_EPOCH="1786872999", PYTHONDONTWRITEBYTECODE="1")
            result = subprocess.run([sys.executable, "-B", "-c", script, str(output)],
                                    cwd=staging, env=env, capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            wheel, = output.glob("*.whl")
            sdist, = output.glob("*.tar.gz")
            with zipfile.ZipFile(wheel) as archive:
                names = archive.namelist()
                metadata = BytesParser().parsebytes(archive.read(next(
                    n for n in names if n.endswith(".dist-info/METADATA"))))
                self.assertEqual(metadata["Requires-Python"], ">=3.10")
                requirements = metadata.get_all("Requires-Dist")
                self.assertIn('tensorflow==2.13.0', requirements)
                self.assertIn('open-spiel==1.3; extra == "spiel"', requirements)
                self.assertFalse(any(r.startswith("open-spiel") and ";" not in r for r in requirements))
                self.assertIn('gdown==5.2.2; extra == "download"', requirements)
                entries = archive.read(next(n for n in names if n.endswith("/entry_points.txt"))).decode()
                self.assertIn("pygame_spiel = pygame_spiel.main:pygame_spiel", entries)
                self.assertIn("pygame_spiel_download = pygame_spiel.downloads:main", entries)
                self.assertEqual(archive.read(next(n for n in names if n.endswith("/licenses/LICENSE"))),
                                 (ROOT / "LICENSE").read_bytes())
                expected = {p.relative_to(ROOT).as_posix() for p in (ROOT / "pygame_spiel").rglob("*")
                            if p.is_file() and p.suffix in (".py", ".png")}
                actual = {n for n in names if n.startswith("pygame_spiel/")}
                self.assertEqual(actual, expected)
                for name in expected:
                    source, packaged = (ROOT / name).read_bytes(), archive.read(name)
                    if name.endswith(".py"):
                        source, packaged = source.replace(b"\r\n", b"\n"), packaged.replace(b"\r\n", b"\n")
                    self.assertEqual(packaged, source, name)
            with tarfile.open(sdist) as archive:
                members = archive.getmembers()
                prefix = members[0].name.split("/")[0]
                distributed = {m.name.removeprefix(prefix + "/") for m in members if m.isfile()}
                for path in [*ROOT.glob("*.md"), *ROOT.glob("docs/**/*.md"),
                             *ROOT.glob("tests/*.py"), ROOT / "requirements-test.txt",
                             ROOT / "main.py", ROOT / ".github/workflows/checks.yml"]:
                    name = path.relative_to(ROOT).as_posix()
                    self.assertIn(name, distributed)
                    self.assertEqual(archive.extractfile(prefix + "/" + name).read().replace(b"\r\n", b"\n"),
                                     path.read_bytes().replace(b"\r\n", b"\n"), name)
                self.assertEqual(BytesParser().parsebytes(archive.extractfile(prefix + "/PKG-INFO").read())
                                 ["Requires-Python"], ">=3.10")
                # Archives are produced from this staging tree; reject traversal before extraction.
                extracted = Path(tmp) / "roundtrip"
                for member in members:
                    target = (extracted / member.name).resolve()
                    self.assertIn(extracted.resolve(), target.parents)
                    self.assertFalse(member.issym() or member.islnk())
                archive.extractall(extracted, **({"filter": "data"} if hasattr(tarfile, "data_filter") else {}))
            rebuilt = Path(tmp) / "rebuilt"
            rebuilt.mkdir()
            result = subprocess.run([sys.executable, "-B", "-c",
                                     "import setuptools.build_meta as b, sys; b.build_wheel(sys.argv[1])",
                                     str(rebuilt)], cwd=extracted / prefix, env=env,
                                    capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(wheel.read_bytes(), (rebuilt / wheel.name).read_bytes())
            code = r"""
import importlib.abc, sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, *args):
        if fullname.split('.')[0] in ('pygame','pygame_menu','pyspiel','open_spiel','tensorflow','torch','gdown','numpy'):
            raise AssertionError('Unexpected backend: ' + fullname)
sys.meta_path.insert(0, Block())
sys.path.insert(0, sys.argv[1])
import pygame_spiel
assert sys.argv[1] in pygame_spiel.__file__, pygame_spiel.__file__
from pygame_spiel.resources import asset, ModelPaths
for name in sys.argv[2:]:
    assert asset(name).read_bytes().startswith(b'\x89PNG')
ModelPaths()
"""
            images = sorted(p.relative_to(ROOT / "pygame_spiel/images").as_posix()
                            for p in (ROOT / "pygame_spiel/images").rglob("*.png"))
            result = subprocess.run([sys.executable, "-B", "-c", code, str(wheel), *images],
                                    cwd=tmp, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
