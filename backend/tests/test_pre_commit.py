r"""
Test Pre-commit Security Hook & Git Hygiene.
Verifies rejection of IRDAI licence pattern (?i)IRDA/IND/SLA-\d+ across plaintext and DOCX XML.
"""

import io
import os
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK_PATH = REPO_ROOT / "scripts" / "hooks" / "pre-commit"


def test_hook_executable_and_installed():
    """Verifies that pre-commit hook exists and has executable permissions."""
    assert HOOK_PATH.exists(), f"Hook not found at {HOOK_PATH}"
    assert os.access(HOOK_PATH, os.X_OK), f"Hook at {HOOK_PATH} is not executable"

    git_hook = REPO_ROOT / ".git" / "hooks" / "pre-commit"
    assert git_hook.exists(), f"Git hook not found at {git_hook}"
    assert os.access(git_hook, os.X_OK), f"Git hook at {git_hook} is not executable"


def test_pre_commit_regex_matching():
    r"""Verifies the regex pattern (?i)IRDA/IND/SLA-\d+ catches all variations."""
    pattern = re.compile(r"(?i)IRDA/IND/SLA-\d+")
    pfx = "IRDA" + "/IND/SLA-"

    positives = [
        f"{pfx}654321",
        f"{pfx.lower()}654321",
        "Irda" + "/Ind/Sla-0001",
        f"Licence: {pfx}999999 attached to report",
        f"PREFIX_{pfx.lower()}42_SUFFIX",
    ]
    for text in positives:
        assert pattern.search(text) is not None, f"Failed to match positive case: {text}"

    negatives = [
        "IRDA" + "/IND/NON-SLA-12345",
        "SLA-654321",
        "IRDA-654321",
        "CLEAN_TEXT_WITHOUT_SECRETS",
        "M-1-2026",
    ]
    for text in negatives:
        assert pattern.search(text) is None, f"Incorrectly matched negative case: {text}"


def test_pre_commit_blocks_staged_secret_in_isolated_repo():
    """
    Spawns an isolated temporary Git repo with the pre-commit hook installed,
    stages a prohibited secret, and asserts the commit is blocked (non-zero exit code).
    """
    pfx = "IRDA" + "/IND/SLA-"
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # 1. Initialize isolated git repo
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        # 2. Install pre-commit hook
        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        hook_target = hooks_dir / "pre-commit"

        with open(HOOK_PATH, "r") as src, open(hook_target, "w") as dst:
            dst.write(src.read())
        hook_target.chmod(0o755)

        # 3. Clean commit should pass
        clean_file = tmp_path / "clean.txt"
        clean_file.write_text("This is completely clean text.\nM-1-2026\n")
        subprocess.run(["git", "add", "clean.txt"], cwd=tmp_path, check=True)
        clean_res = subprocess.run(
            ["git", "commit", "-m", "Clean commit"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        assert clean_res.returncode == 0, f"Clean commit failed: {clean_res.stderr}"

        # 4. Dirty plaintext commit should be BLOCKED
        dirty_file = tmp_path / "leak.txt"
        dirty_file.write_text(f"Surveyor licence number: {pfx}654321\n")
        subprocess.run(["git", "add", "leak.txt"], cwd=tmp_path, check=True)
        dirty_res = subprocess.run(
            ["git", "commit", "-m", "Dirty commit"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        assert dirty_res.returncode != 0, "Pre-commit hook failed to block plaintext secret!"
        assert "COMMIT ABORTED" in dirty_res.stdout or "COMMIT ABORTED" in dirty_res.stderr

        # 5. Reset dirty file
        subprocess.run(["git", "reset", "HEAD", "leak.txt"], cwd=tmp_path, check=True)
        dirty_file.unlink()

        # 6. Dirty DOCX archive should be BLOCKED
        docx_file = tmp_path / "test_leak.docx"
        docx_secret = ("irda" + "/ind/sla-54321")
        with zipfile.ZipFile(docx_file, "w") as z:
            # Word document XML containing the secret
            doc_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
                <w:body>
                    <w:p><w:r><w:t>Licence: {docx_secret}</w:t></w:r></w:p>
                </w:body>
            </w:document>"""
            z.writestr("word/document.xml", doc_xml)
            z.writestr("[Content_Types].xml", "<Types/>")

        subprocess.run(["git", "add", "test_leak.docx"], cwd=tmp_path, check=True)
        docx_res = subprocess.run(
            ["git", "commit", "-m", "DOCX leak commit"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        assert docx_res.returncode != 0, "Pre-commit hook failed to block DOCX secret!"
        assert "COMMIT ABORTED" in docx_res.stdout or "COMMIT ABORTED" in docx_res.stderr


def test_pre_commit_blocks_docx_split_runs():
    """Verifies that pre-commit hook detects secrets split across multiple <w:r><w:t> XML tags."""
    pfx = "IRDA" + "/IND/SLA-"
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.name", "T"], cwd=tmp_path, check=True)

        hook_target = tmp_path / ".git" / "hooks" / "pre-commit"
        hook_target.parent.mkdir(parents=True, exist_ok=True)
        with open(HOOK_PATH, "r") as src, open(hook_target, "w") as dst:
            dst.write(src.read())
        hook_target.chmod(0o755)

        docx_file = tmp_path / "split_leak.docx"
        with zipfile.ZipFile(docx_file, "w") as z:
            doc_xml = f"""<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
                <w:body>
                    <w:p>
                        <w:r><w:t>{pfx}</w:t></w:r>
                        <w:r><w:t>987654</w:t></w:r>
                    </w:p>
                </w:body>
            </w:document>"""
            z.writestr("word/document.xml", doc_xml)
            z.writestr("[Content_Types].xml", "<Types/>")

        subprocess.run(["git", "add", "split_leak.docx"], cwd=tmp_path, check=True)
        res = subprocess.run(["git", "commit", "-m", "split docx leak"], cwd=tmp_path, capture_output=True, text=True)
        assert res.returncode != 0, "Hook failed to block split-run DOCX secret!"


def test_pre_commit_blocks_renamed_dirty_file():
    """Verifies that renaming a file with a secret is caught via --diff-filter=ACMR."""
    pfx = "IRDA" + "/IND/SLA-"
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.name", "T"], cwd=tmp_path, check=True)

        hook_target = tmp_path / ".git" / "hooks" / "pre-commit"
        hook_target.parent.mkdir(parents=True, exist_ok=True)
        with open(HOOK_PATH, "r") as src, open(hook_target, "w") as dst:
            dst.write(src.read())
        hook_target.chmod(0o755)

        (tmp_path / "clean.txt").write_text("clean text")
        subprocess.run(["git", "add", "clean.txt"], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-m", "clean"], cwd=tmp_path, check=True, capture_output=True)

        subprocess.run(["git", "mv", "clean.txt", "renamed.txt"], cwd=tmp_path, check=True)
        (tmp_path / "renamed.txt").write_text(f"Licence: {pfx}778899\n")
        subprocess.run(["git", "add", "renamed.txt"], cwd=tmp_path, check=True)

        res = subprocess.run(["git", "commit", "-m", "rename leak"], cwd=tmp_path, capture_output=True, text=True)
        assert res.returncode != 0, "Hook failed to block renamed file secret!"
