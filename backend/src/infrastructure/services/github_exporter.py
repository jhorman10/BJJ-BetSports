import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class GithubExporterService:
    """Exports ML JSON predictions to a GitHub repository using GitOps.

    Security: Uses git credential helper to avoid embedding tokens in URLs
    (which leak into process tables, logs, and shell history).
    """

    def __init__(self) -> None:
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.github_username = os.getenv("GITHUB_USERNAME", "Worker-Bot")
        self.github_email = os.getenv("GITHUB_EMAIL", "worker@bjj-betsports.local")
        # Format: username/repo
        self.github_repo = os.getenv("GITHUB_REPO")
        self.local_repo_path = "/tmp/github_data_export"
        # Clean URL without credentials — credential helper injects them
        self._repo_url = f"https://github.com/{self.github_repo}.git"

    def export_and_push(
        self, data: List[Dict], filename: str = "latest_predictions.json"
    ) -> bool:
        """Saves data to a JSON file and pushes it to GitHub."""
        if not self.github_token or not self.github_repo:
            logger.warning(
                "⚠️ Github Export skipped: GITHUB_TOKEN or GITHUB_REPO not configured."
            )
            return False

        try:
            # 1. Ensure git is configured (includes credential helper)
            self._configure_git()

            # 2. Clone or pull repo
            self._sync_repo()

            # 3. Write latest data to file
            filepath = os.path.join(self.local_repo_path, filename)
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2, default=str)

            # 4. Commit and push
            return self._commit_and_push(filename)

        except Exception as e:
            logger.error(f"❌ Failed to push to GitHub: {e}")
            return False

    def _configure_git(self) -> None:
        """Sets global git config inside the container and installs credentials."""
        subprocess.run(
            ["git", "config", "--global", "user.name", self.github_username],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "--global", "user.email", self.github_email],
            check=True,
            capture_output=True,
        )
        # Use 'store' credential helper — reads from ~/.git-credentials
        subprocess.run(
            ["git", "config", "--global", "credential.helper", "store"],
            check=True,
            capture_output=True,
        )

        # Write credentials file BEFORE any git operation that needs auth
        # Format: https://<token>@github.com
        # This avoids the token appearing in process args / URLs
        creds_path = Path.home() / ".git-credentials"
        creds_line = f"https://{self.github_token}@github.com\n"
        try:
            creds_path.write_text(creds_line, encoding="utf-8")
            # Restrict permissions (best effort; container FS may ignore)
            creds_path.chmod(0o600)
        except Exception as e:
            logger.warning(f"Could not write git credentials file: {e}")

    def _sync_repo(self) -> None:
        """Clones the repo if it doesn't exist, else pulls latest changes."""
        # Use clean URL — credential helper provides auth from ~/.git-credentials
        repo_url = self._repo_url

        if not os.path.exists(self.local_repo_path):
            logger.info(f"Cloning {self.github_repo} into {self.local_repo_path}...")
            subprocess.run(
                ["git", "clone", repo_url, self.local_repo_path],
                check=True,
                capture_output=True,
            )
        else:
            logger.info(f"Pulling latest from {self.github_repo}...")
            # Use 'git pull --rebase' to avoid ugly merge conflicts on auto-updates
            subprocess.run(
                [
                    "git",
                    "-C",
                    self.local_repo_path,
                    "pull",
                    "--rebase",
                    "origin",
                    "main",
                ],
                check=False,
                capture_output=True,
            )

    def _commit_and_push(self, filename: str) -> bool:
        """Commits the changed JSON and pushes it back up."""
        try:
            # Add changes
            subprocess.run(
                ["git", "-C", self.local_repo_path, "add", filename],
                check=True,
                capture_output=True,
            )

            # Check if there are actually changes
            status_res = subprocess.run(
                ["git", "-C", self.local_repo_path, "status", "--porcelain"],
                capture_output=True,
                text=True,
            )
            if not status_res.stdout.strip():
                logger.info("ℹ️ No new changes to push (JSON is identical).")
                return True

            # Commit
            commit_msg = f"Auto-update ml predictions on {filename}"
            subprocess.run(
                ["git", "-C", self.local_repo_path, "commit", "-m", commit_msg],
                check=True,
                capture_output=True,
            )

            # Push — clean URL, credential helper injects auth
            repo_url = self._repo_url
            subprocess.run(
                ["git", "-C", self.local_repo_path, "push", repo_url, "main"],
                check=True,
                capture_output=True,
            )

            logger.info(
                f"✅ Successfully exported and pushed {filename} to {self.github_repo}"
            )
            return True

        except subprocess.CalledProcessError as e:
            logger.error(
                f"Git execution failed: {e.stderr.decode() if e.stderr else str(e)}"
            )
            raise e
