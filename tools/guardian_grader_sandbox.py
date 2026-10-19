"""Fail-closed, rootless Docker grading; never import target code on the host.

Only declarative oracles are trusted. Images must already exist locally and be
pinned by digest. Rootless Docker is required, not silently substituted with a
privileged daemon. Container security is a prerequisite, not an isolation claim
based on Python flags. Docker's writable tmpfs is the only mutable filesystem.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import uuid
import ast
import sys
import stat
import re

MAX_SOURCE_BYTES = 16_384
MAX_AST_NODES = 4096
MAX_AST_DEPTH = 64


class SandboxUnavailable(ValueError):
    pass

def image_identity(reference):
    """Normalize Docker's short RepoDigests spelling without relaxing the pin."""
    if not isinstance(reference,str):return None
    match=re.fullmatch(r'([a-z0-9][a-z0-9._:/-]*)@sha256:([a-f0-9]{64})',reference)
    if not match:return None
    parts=match[1].split('/')
    if len(parts)>1 and ('.' in parts[0] or ':' in parts[0] or parts[0]=='localhost'):
        registry=parts.pop(0)
    else:registry='docker.io'
    if registry=='index.docker.io':registry='docker.io'
    parts[-1]=parts[-1].split(':',1)[0]
    if registry=='docker.io' and len(parts)==1:parts.insert(0,'library')
    return registry+'/'+('/'.join(parts))+'@sha256:'+match[2]


def strict_json(text):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError("Duplicate JSON key")
            out[key] = value
        return out
    return json.loads(text, object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))


def probe(image: str | None = None) -> dict:
    image = image or os.environ.get("GUARDIAN_GRADER_IMAGE", "")
    binary = shutil.which("docker")
    result = {"available": False, "status": "NOT VERIFIED", "backend": "rootless-docker",
              "image": image, "reason": "Requires local digest-pinned image and rootless Docker"}
    if not binary or image_identity(image) is None:
        return result
    try:
        info = strict_json(subprocess.run([binary, "info", "--format", "{{json .SecurityOptions}}"],
                         capture_output=True, text=True, timeout=10, check=True).stdout)
        if not isinstance(info, list) or not any("rootless" in x for x in info):
            return result
        inspected = strict_json(subprocess.run([binary, "image", "inspect", image], capture_output=True,
                                    text=True, timeout=10, check=True).stdout)
        if not inspected or image_identity(image) not in [image_identity(ref) for ref in inspected[0].get("RepoDigests", [])]:
            return result
        if inspected[0].get("Config", {}).get("Volumes"):
            return {**result, "reason": "Image-declared writable volumes are forbidden"}
        name = "guardian-probe-" + uuid.uuid4().hex
        try:
            test = subprocess.run(container_command(binary, image, name) +
                                  ["-I", "-B", "-c", PREFLIGHT], capture_output=True, text=True,
                                  timeout=20, check=True)
            if strict_json(test.stdout) != {"limits_verified": True}:
                return result
        finally:
            subprocess.run([binary, "rm", "--force", name], stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=False)
        return {**result, "available": True, "status": "AVAILABLE", "binary": binary,
                "reason": "Rootless, digest, uid, read-only filesystem, network and cgroup limits verified"}
    except (OSError, ValueError, subprocess.SubprocessError):
        return result


PREFLIGHT = r'''import os, json
from pathlib import Path
assert os.getuid() == 65534
assert os.getpid() == 1  # Docker's default private PID namespace, no --init.
cg = Path("/sys/fs/cgroup")
assert int((cg/"memory.max").read_text()) <= 134217728
assert int((cg/"pids.max").read_text()) <= 32
quota, period = (cg/"cpu.max").read_text().split()
assert quota != "max" and int(quota)/int(period) <= .5
assert set(Path("/sys/class/net").iterdir()) == {Path("/sys/class/net/lo")}
try:
    Path("/escape-test").write_text("forbidden")
except OSError:
    pass
else:
    raise RuntimeError("Writable root filesystem")
assert not Path("/root/.codex").exists()
print(json.dumps({"limits_verified":True}))
'''


def container_command(binary, image, name, workspace=None):
    command = [binary, "run", "--name", name, "--rm", "--pull=never", "--network=none",
               "--log-driver=none", "--ipc=none", "--cgroupns=private",
               "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges", "--user=65534:65534",
               "--pids-limit=32", "--memory=128m", "--memory-swap=128m", "--cpus=0.5",
               "--ulimit", "fsize=1048576:1048576", "--ulimit", "nofile=64:64",
               "--tmpfs", "/tmp:rw,noexec,nosuid,size=8m,mode=1777"]
    if workspace is not None:
        command += ["--mount", "type=bind,src=" + str(workspace) + ",dst=/workspace,readonly"]
    return command + ["--workdir=/tmp", "--env=HOME=/nonexistent", "--env=PYTHONDONTWRITEBYTECODE=1",
                      "--entrypoint=python3", "-i", image]


# No expected answers are sent to the target. Each vector starts a new container.
# A successful protocol response alone is never a passing score: the host oracle
# checks exact result/exception, expected type, process termination and all vectors.
WORKER = r'''
import sys, json, importlib.util
request = json.loads(sys.stdin.read())
spec = importlib.util.spec_from_file_location("target", "/workspace/" + request["file"])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
try:
    value = getattr(module, request["function"])(*request["args"])
    result = {"kind": "value", "value": value}
except Exception as exc:
    result = {"kind": "exception", "type": type(exc).__name__}
sys.stdout.write(json.dumps(result, allow_nan=False, separators=(",", ":")))
'''


def validate_oracle(payload):
    if not isinstance(payload, dict) or set(payload) != {"schema_version", "cases"} or payload["schema_version"] != 2:
        raise ValueError("A reviewed declarative oracle schema_version=2 is required; executable host graders are forbidden")
    if not isinstance(payload["cases"], dict) or not payload["cases"]:
        raise ValueError("Oracle cases missing")
    for case in payload["cases"].values():
        if not isinstance(case, dict) or set(case) != {"checks"} or not isinstance(case["checks"], dict) or not case["checks"]:
            raise ValueError("Oracle checks missing")
        for vectors in case["checks"].values():
            if not isinstance(vectors, list) or not 1 <= len(vectors) <= 100:
                raise ValueError("Oracle requires bounded nonempty vectors")
            for vector in vectors:
                if not isinstance(vector, dict) or set(vector) != {"file", "function", "args", "expected"}:
                    raise ValueError("Malformed oracle vector")
                path = Path(vector["file"])
                if path.is_absolute() or len(path.parts) != 1 or path.suffix != ".py" or not path.stem.isidentifier():
                    raise ValueError("Target file must be a top-level Python module")
                if not isinstance(vector["function"], str) or not vector["function"].isidentifier() or not isinstance(vector["args"], list):
                    raise ValueError("Invalid target call")
                expected = vector["expected"]
                if not isinstance(expected, dict) or (set(expected) != {"kind", "value"} and set(expected) != {"kind", "type"}):
                    raise ValueError("Invalid expected result")
                if expected.get("kind") not in ("value", "exception"):
                    raise ValueError("Invalid expected result kind")
    return payload


def _same(actual, expected):
    # bool must not compare equal to int, including nested output.
    return type(actual) is type(expected) and (
        actual.keys() == expected.keys() and all(_same(actual[k], expected[k]) for k in actual)
        if isinstance(actual, dict) else
        len(actual) == len(expected) and all(_same(a, b) for a, b in zip(actual, expected))
        if isinstance(actual, list) else actual == expected)


def _validate_pure_source(source: str) -> None:
    """A deliberately narrow fixture language, not a general Python sandbox.

    Without a trusted interpreter, arbitrary Python can forge its own output or
    monkeypatch an in-process test runner. Refuse that surface before execution.
    Container controls remain mandatory even after this structural restriction.
    Unsupported real application code is NOT VERIFIED, never silently approved.
    """
    tree = ast.parse(source)
    count = 0
    pending = [(tree, 0)]
    while pending:
        node, depth = pending.pop()
        count += 1
        if count > MAX_AST_NODES or depth > MAX_AST_DEPTH:
            raise ValueError("Pure fixture AST exceeds node/depth budget")
        pending.extend((child, depth + 1) for child in ast.iter_child_nodes(node))
    safe_calls = {"isinstance", "list", "dict", "len", "type", "set", "int", "str",
                  "sorted", "range", "enumerate", "zip", "ValueError", "TypeError"}
    methods = {"strip", "append", "add", "get", "items", "keys", "values", "copy"}
    denied = (ast.Import, ast.ImportFrom, ast.ClassDef, ast.Global, ast.Nonlocal,
              ast.AsyncFunctionDef, ast.Await, ast.Yield, ast.YieldFrom, ast.Lambda)
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            continue
        if not isinstance(node, ast.FunctionDef) or node.decorator_list or node.args.defaults or node.args.kw_defaults:
            raise ValueError("Only pure fixture functions are supported; application grading NOT VERIFIED")
    for node in ast.walk(tree):
        if isinstance(node, denied):
            raise ValueError("Target exceeds reviewed pure-function grading language")
        if isinstance(node, ast.Name) and node.id.startswith("_"):
            raise ValueError("Private runtime access forbidden in pure fixture")
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)) and node.id in safe_calls:
            raise ValueError("Shadowing grading builtins is forbidden")
        if isinstance(node, ast.Attribute) and node.attr not in methods:
            raise ValueError("Unsupported runtime attribute in pure fixture")
        if isinstance(node, ast.Call):
            if not ((isinstance(node.func, ast.Name) and node.func.id in safe_calls) or
                    (isinstance(node.func, ast.Attribute) and node.func.attr in methods)):
                raise ValueError("Only reviewed pure builtin calls are supported")


def validate_pure_target(path: Path) -> None:
    """Bound file bytes before reading and parse in a killable helper process.

    The helper parses data only, never compiles/evaluates/imports the target.
    POSIX adds CPU limits, Linux adds address-space limits; Windows uses fixed input/node
    budgets and parent timeout, not a claimed Windows Job Object memory limit.
    """
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
        raise ValueError("Linked source files are forbidden")
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as stream:
        metadata = os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_SOURCE_BYTES:
            raise ValueError("Pure fixture source must be a regular file <=16384 bytes")
        source = stream.read(MAX_SOURCE_BYTES + 1)
    if len(source) > MAX_SOURCE_BYTES:
        raise ValueError("Pure fixture source byte budget exceeded")
    try:
        result = subprocess.run([sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--validate-pure"],
                                input=source, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                timeout=3, check=False)
    except subprocess.SubprocessError as exc:
        raise ValueError("Pure fixture AST helper exceeded runtime budget") from exc
    if result.returncode != 0 or result.stdout not in (b"VALID\n", b"VALID\r\n"):
        raise ValueError("Target rejected by bounded pure-function AST validator")


def execute_vector(workspace: Path, vector: dict, timeout: int, backend: dict) -> bool:
    try:
        validate_pure_target(workspace / vector["file"])
    except (OSError, ValueError, SyntaxError):
        return False
    if "," in str(workspace):
        raise ValueError("Comma in bind path is unsupported")
    name = "guardian-grade-" + uuid.uuid4().hex
    command = container_command(backend["binary"], backend["image"], name, workspace) + ["-I", "-B", "-c", WORKER]
    request = {k: v for k, v in vector.items() if k != "expected"}
    # A reader caps host storage/memory even if a target floods stdout. Killing
    # only the Docker client is insufficient; the finally clause removes server-side container.
    import threading
    try:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        output = bytearray()
        overflow = threading.Event()
        def reader():
            while True:
                block = process.stdout.read(4096)
                if not block:
                    return
                if len(output) + len(block) > 65536:
                    overflow.set()
                    process.kill()
                    return
                output.extend(block)
        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        try:
            process.stdin.write(json.dumps(request).encode())
            process.stdin.close()
            process.wait(timeout=timeout)
            thread.join(timeout=5)
            if process.returncode != 0 or overflow.is_set() or thread.is_alive():
                return False
            actual = strict_json(output.decode("utf-8"))
            return _same(actual, vector["expected"])
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)
            thread.join(timeout=5)

    except (OSError, ValueError, UnicodeError, subprocess.SubprocessError):
        return False
    finally:
        # Kill container even when client timeout/cancellation loses the connection.
        try:
            removed = subprocess.run([backend["binary"], "rm", "--force", name], stdin=subprocess.DEVNULL,
                                     capture_output=True, text=True, timeout=15, check=False)
            if removed.returncode and "No such container" not in removed.stderr:
                raise SandboxUnavailable("Container cleanup not confirmed; stop evaluation")
        except (OSError, subprocess.SubprocessError) as exc:
            raise SandboxUnavailable("Container cleanup could not be verified; stop evaluation") from exc


def grade_oracle(checker: Path, case_id: str, workspace: Path, checks: list[str], timeout: int) -> dict:
    oracle = validate_oracle(strict_json(checker.read_text(encoding="utf-8")))
    case = oracle["cases"].get(case_id)
    if not case or len(set(checks)) != len(checks) or set(checks) != set(case["checks"]):
        raise ValueError("Requested checks must exactly match the complete independent oracle")
    backend = probe()
    if not backend["available"]:
        raise SandboxUnavailable(backend["reason"] + "; grading NOT VERIFIED")
    if workspace.is_symlink() or any(p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction()) for p in workspace.rglob("*")):
        raise ValueError("Oracle workspace must not contain links")
    executed = []
    for check in checks:
        for index, vector in enumerate(case["checks"][check]):
            validate_pure_target(workspace / vector["file"])
            passed = execute_vector(workspace, vector, timeout, backend)
            executed.append({"check": check, "vector": index, "passed": passed})
    return {"passed": all(x["passed"] for x in executed), "checks": executed,
            "oracle_sha256": hashlib.sha256(checker.read_bytes()).hexdigest(),
            "backend": {k: v for k, v in backend.items() if k != "binary"}}


if __name__ == "__main__":
    if sys.argv[1:] != ["--validate-pure"]:
        raise SystemExit(2)
    try:
        if os.name != "nt":
            import resource
            resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
            if sys.platform.startswith("linux"):
                resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
        data = sys.stdin.buffer.read(MAX_SOURCE_BYTES + 1)
        if len(data) > MAX_SOURCE_BYTES:
            raise ValueError("Input byte limit")
        _validate_pure_source(data.decode("utf-8"))
        sys.stdout.write("VALID\n")
    except (ValueError, SyntaxError, UnicodeError, MemoryError, RecursionError):
        raise SystemExit(2)
