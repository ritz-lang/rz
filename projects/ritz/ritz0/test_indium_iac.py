"""indium's EC2 AMI pipeline lives in projects/indium/iac (AGAST #2747, from #1844).

origin/harland-main carried the Terraform that builds a UEFI AMI for harland
(builder instance -> dd the image onto EBS -> snapshot -> register AMI with
ena_support -> launch). #2747 lands that code on main; running it belongs to
#1849, which owns the AWS account and the cost guard.

Nothing here talks to AWS. The tests check the tree is complete and safe to
keep in the repo:

* every file of the deployment is present;
* state, plans and provider caches are gitignored;
* no credential is committed (access key ids, secret keys, private keys);
* the shell steps that write to real volumes are off unless asked for;
* the README says who runs it (#1849) and that CI never applies it;
* `terraform fmt -check` passes when terraform is installed (offline).
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

RITZ0_DIR = Path(__file__).resolve().parent
IAC = RITZ0_DIR.parent.parent / "indium" / "iac"
DEPLOY = IAC / "deployment"

REQUIRED = [
    IAC / ".gitignore",
    IAC / "README.md",
    DEPLOY / "main.tf",
    DEPLOY / "outputs.tf",
    DEPLOY / "providers.tf",
    DEPLOY / "variables.tf",
    DEPLOY / ".terraform.lock.hcl",
]


def _iac_files():
    return [p for p in IAC.rglob("*") if p.is_file() and ".terraform" not in p.parts]


@pytest.mark.parametrize("path", REQUIRED, ids=lambda p: str(p.relative_to(IAC)))
def test_deployment_file_present(path):
    assert path.is_file(), f"missing {path.relative_to(IAC.parent)}"


def test_state_and_plans_are_gitignored():
    patterns = (IAC / ".gitignore").read_text().split()
    for want in ("*.tfstate", "*.tfstate.*", "*.tfplan"):
        assert want in patterns, f".gitignore lacks {want}"
    assert any(".terraform" in p for p in patterns), ".gitignore lacks .terraform/"


# Patterns that only appear when a credential is pasted in, never in config
# that reads credentials from the environment or a profile.
SECRET_PATTERNS = [
    re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b"),                    # access key id
    re.compile(r"aws_secret_access_key\s*="),                      # secret key
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),             # private key
    re.compile(r"^\s*(access_key|secret_key|token)\s*=", re.M),    # provider creds
]


def test_no_credentials_committed():
    assert IAC.is_dir(), "projects/indium/iac missing"
    hits = []
    for path in _iac_files():
        text = path.read_text(errors="replace")
        for pat in SECRET_PATTERNS:
            for m in pat.finditer(text):
                hits.append(f"{path.relative_to(IAC)}: {m.group(0)}")
    assert not hits, "credentials committed:\n" + "\n".join(hits)


def test_volume_burn_steps_default_off():
    """The ssh+dd steps write to real EBS volumes; they run only on request."""
    variables = (DEPLOY / "variables.tf").read_text()
    m = re.search(r'variable\s+"enable_burn_steps"\s*\{(.*?)\n\}', variables, re.S)
    assert m, "variables.tf must declare enable_burn_steps"
    assert re.search(r"default\s*=\s*false", m.group(1)), "enable_burn_steps must default to false"


def test_readme_says_who_applies_it():
    readme = (IAC / "README.md").read_text()
    assert "#1849" in readme, "README must point at #1849, which runs the pipeline"
    assert re.search(r"never .*terraform apply|terraform apply.* never", readme, re.I | re.S), (
        "README must say CI/agents never run terraform apply"
    )


@pytest.mark.integration  # spawns a process (spawn_guard, AGAST #1805)
@pytest.mark.skipif(shutil.which("terraform") is None, reason="terraform not installed")
def test_terraform_fmt_clean():
    """Offline: fmt reads the files only, no init, no backend, no provider."""
    r = subprocess.run(
        ["terraform", "fmt", "-check", "-recursive", "-diff", str(IAC)],
        capture_output=True, text=True, timeout=60,
    )
    assert r.returncode == 0, r.stdout + r.stderr
