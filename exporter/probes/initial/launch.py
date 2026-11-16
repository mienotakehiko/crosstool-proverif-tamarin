"""Fail-closed Docker launcher. No pulling, building or shared output paths."""
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import tarfile
import tempfile
from common import dump, run, sha

ROOT = Path(__file__).resolve().parent
IMAGE = "sha256:70093355b2b5ad24b5ada7b4e9b405008bd467a39209850cc8fcca830a420793"


def resource_gate(text):
    info = json.loads(text)
    # Require modest headroom over the enforced container cap.
    if info.get("NCPU", 0) < 1 or info.get("MemTotal", 0) < 2304 * 1024 * 1024:
        raise RuntimeError("docker_resource_gate: need 1 CPU and 2304 MiB daemon RAM")


def docker_command(snapshot, out, name):
    return ["docker", "run", "--rm", "--pull", "never", "--network", "none",
            "--cpus=1", "--memory=2g", "--memory-swap=2g", "--pids-limit=128",
            "--cap-drop=ALL", "--security-opt=no-new-privileges", "--read-only",
            "--user", "%s:%s" % (os.getuid(), os.getgid()), "--name", name,
            "--env", "PYTHONDONTWRITEBYTECODE=1", "--env", "HOME=/work",
            "--tmpfs", "/tmp:rw,nosuid,nodev,size=128m",
            "--volume", str(snapshot) + ":/kit:ro", "--volume", str(out) + ":/work",
            "--workdir", "/work", IMAGE, "python3", "-B", "/kit/run_inside.py", "/kit", "/work"]


def verify_inputs(root):
    entries = json.loads((root / "KIT_HASHES.json").read_text())
    for rel, expected in entries.items():
        p = Path(rel)
        if p.is_absolute() or ".." in p.parts or (root / p).is_symlink():
            raise RuntimeError("unsafe_manifest_path")
        if sha(root / p) != expected:
            raise RuntimeError("kit_hash_mismatch:" + rel)


def main():
    base = ROOT / "pinned_runs"
    base.mkdir(exist_ok=True)
    if shutil.disk_usage(ROOT).free < 512 * 1024 * 1024:
        raise SystemExit("disk_resource_gate: need 512 MiB free")
    out = Path(tempfile.mkdtemp(prefix="pinned_", dir=base))
    snapshot = out / "inputs"
    snapshot.mkdir()
    name = "state-probe-" + out.name.replace("_", "-")
    status = {"mode": "pinned", "complete": False, "image": IMAGE, "container": name}
    rc = 1
    started = False
    def interrupted(signum, frame):
        raise KeyboardInterrupt("signal_%s" % signum)
    signal.signal(signal.SIGTERM, interrupted)
    try:
        verify_inputs(ROOT)
        for rel in json.loads((ROOT / "KIT_HASHES.json").read_text()):
            dest = snapshot / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, dest)
        shutil.copy2(ROOT / "KIT_HASHES.json", snapshot)
        status["snapshot_hashes"] = {str(p.relative_to(snapshot)): sha(p) for p in snapshot.rglob("*") if p.is_file()}
        dump(out / "summary.json", [])
        if run(out, "docker_info", ["docker", "info", "--format", "{{json .}}"], 10)["rc"]:
            raise RuntimeError("docker_unavailable")
        resource_gate((out / "docker_info.stdout.txt").read_text())
        if run(out, "image", ["docker", "image", "inspect", "--format", "{{.Id}}", IMAGE], 10)["rc"]:
            raise RuntimeError("pinned_image_not_present")
        if (out / "image.stdout.txt").read_text().strip() != IMAGE:
            raise RuntimeError("image_id_mismatch")
        started = True
        # 16 rows x 3 phases x 60 sec, plus short startup headroom.
        meta = run(out, "container", docker_command(snapshot, out, name), 2910)
        rc = meta["rc"]
        status["complete"] = rc == 0
    except BaseException as exc:
        status["error"] = repr(exc)
        print(status["error"], file=sys.stderr)
    finally:
        if started:
            # Kill only this uniquely named owned container, never a global pkill.
            run(out, "cleanup", ["docker", "rm", "--force", name], 10)
        dump(out / "launcher_status.json", status)
        if not (out / "summary.json").exists():
            dump(out / "summary.json", [])
        dump(out / "evidence_hashes.json", {str(p.relative_to(out)): sha(p) for p in out.rglob("*") if p.is_file()})
        archive = out.with_suffix(".tar.gz")
        with tarfile.open(archive, "x:gz") as tar:
            tar.add(out, arcname=out.name)
        dump(archive.with_suffix(".sha256.json"), {archive.name: sha(archive)})
        print("RESULT_DIR=" + str(out))
        print("ARCHIVE=" + str(archive))
    return rc


if __name__ == "__main__":
    sys.exit(main())
