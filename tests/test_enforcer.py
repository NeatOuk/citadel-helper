#!/usr/bin/env python3
"""Sandbox tests for citadel-enforcer. No root needed, the host firewall is
never touched: each case runs the real enforcer inside a fresh user + network
namespace (`unshare -rn`), where nftables works on a private, empty ruleset.

Run: python3 tests/test_enforcer.py
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ENFORCER = os.path.join(HERE, "..", "citadel-enforcer")
UID = os.getuid()
SLICE = "user.slice/user-%d.slice/user@%d.service/app.slice" % (UID, UID)

# Runs the enforcer with its state dir redirected into the temp dir, then
# prints the resulting ruleset so the test can inspect it.
RUNNER = r'''
import runpy, sys, json, subprocess
sys.argv = ["citadel-enforcer"] + sys.argv[2:]
g = runpy.run_path(%(enforcer)r, run_name="citadel_enforcer_test")
for fn in ("apply_validated", "cmd_restore", "cmd_off"):
    g[fn].__globals__["STATE_DIR"] = %(state)r
    g[fn].__globals__["SAVED_SPEC"] = %(state)r + "/spec.json"
try:
    g["main"]()
finally:
    out = subprocess.run(["nft", "list", "ruleset"], capture_output=True, text=True).stdout
    sys.stderr.write("\n@@RULESET@@\n" + out)
'''


def run(tmp, args, spec=None, pkexec_uid=True):
    runner = os.path.join(tmp, "runner.py")
    with open(runner, "w") as f:
        f.write(RUNNER % {"enforcer": ENFORCER, "state": os.path.join(tmp, "state")})
    if spec is not None:
        with open(os.path.join(tmp, "spec.json"), "w") as f:
            f.write(spec if isinstance(spec, str) else json.dumps(spec))
    env = dict(os.environ)
    if pkexec_uid:
        env["PKEXEC_UID"] = str(UID)
    else:
        env.pop("PKEXEC_UID", None)
    p = subprocess.run(["unshare", "-rn", sys.executable, runner, "x"] + args,
                       capture_output=True, text=True, env=env)
    err, _, ruleset = p.stderr.partition("@@RULESET@@")
    return p.returncode, p.stdout.strip(), err.strip(), ruleset


passed = failed = 0


def check(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
    else:
        failed += 1
        print("FAIL", name, detail)


def main():
    if subprocess.run(["unshare", "-rn", "true"]).returncode != 0:
        print("SKIP: unprivileged user namespaces are not available")
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        spec_path = os.path.join(tmp, "spec.json")
        # a scope that exists on this machine, so cgroup rules are emitted
        with open("/proc/self/cgroup") as f:
            own_cg = f.read().strip().split("::", 1)[1].lstrip("/")

        good = {"silentDeny": False, "blocklist": ["5.188.10.0/23"], "rules": [
            {"verdict": "drop", "targets": [{"ip": "1.1.1.1", "port": 443}]},
            {"verdict": "accept", "targets": [{"ip": "1.1.1.1"}]},
            {"blocklist": True},
            {"verdict": "drop", "cgroup": own_cg},
            {"verdict": "drop", "cgroup": SLICE + "/not-running.scope"},
            {"verdict": "accept"},
        ]}
        rc, out, err, rs = run(tmp, ["apply", spec_path], good)
        check("apply succeeds", rc == 0, err)
        check("own table only", "table inet citadel" in rs and rs.count("table ") == 1, rs)
        check("order kept (port drop before host accept)",
              rs.find("ip daddr 1.1.1.1 th dport 443") < rs.find("ip daddr 1.1.1.1 accept"), rs)
        check("never filters other users", "meta skuid != %d accept" % UID in rs, rs)
        check("DNS always passes", "th dport 53 accept" in rs, rs)
        check("blocklist loaded", "5.188.10.0/23" in rs, rs)
        check("stale cgroup skipped", "not-running.scope" not in rs, rs)
        check("empty entry never becomes match-all",
              "\n\t\taccept\n" not in rs and "\n\t\tcounter packets 0 bytes 0 drop\n" not in rs, rs)
        check("saved for boot", os.path.exists(os.path.join(tmp, "state", "spec.json")))

        check("no log rule unless asked", "log prefix" not in rs, rs)
        rc, out, err, rs = run(tmp, ["apply", spec_path], dict(good, logNew=True))
        check("logNew adds the fixed log rule", rc == 0 and 'log prefix "citadel: "' in rs and "limit rate 20/second" in rs, rs)
        check("log rule sits before user rules",
              rs.find('log prefix "citadel: "') < rs.find("ip daddr 1.1.1.1 th dport 443"), rs)
        rc, out, err, rs = run(tmp, ["apply", spec_path], dict(good, logNew="yes"))
        check("logNew must be a real boolean", rc == 0 and "log prefix" not in rs, rs)

        rc, out, err, rs = run(tmp, ["apply", spec_path], dict(good, silentDeny=True))
        check("lockdown adds final drop", rc == 0 and rs.rstrip().split("\n")[-3].strip().endswith("drop"), rs)

        hostile = {
            "other user's cgroup": {"rules": [{"verdict": "drop", "cgroup": "user.slice/user-0.slice/x.scope"}]},
            "system service": {"rules": [{"verdict": "drop", "cgroup": "system.slice/warp-svc.service"}]},
            "path escape": {"rules": [{"verdict": "drop", "cgroup": "user.slice/user-%d.slice/../../system.slice" % UID}]},
            "quote injection": {"rules": [{"verdict": "drop", "cgroup": 'user.slice/user-%d.slice/a" accept; drop' % UID}]},
            "address injection": {"rules": [{"verdict": "drop", "targets": [{"ip": "1.1.1.1 } ; flush ruleset ; {"}]}]},
            "port out of range": {"rules": [{"verdict": "drop", "targets": [{"ip": "1.1.1.1", "port": 70000}]}]},
            "port injection": {"rules": [{"verdict": "drop", "targets": [{"ip": "1.1.1.1", "port": "443 accept"}]}]},
            "unknown verdict": {"rules": [{"verdict": "reject", "targets": [{"ip": "1.1.1.1"}]}]},
            "not an object": [1, 2, 3],
            "not json": "hello",
        }
        for name, spec in hostile.items():
            rc, out, err, rs = run(tmp, ["apply", spec_path], spec)
            check("rejects " + name, rc != 0 and "table inet citadel" not in rs, err or rs)

        rc, out, err, rs = run(tmp, ["apply", spec_path], good, pkexec_uid=False)
        check("apply requires pkexec", rc != 0 and "pkexec" in err, err)

        os.symlink("/etc/hostname", os.path.join(tmp, "link.json"))
        rc, out, err, rs = run(tmp, ["apply", os.path.join(tmp, "link.json")])
        check("refuses symlinked spec", rc != 0, err)

        p = subprocess.run([sys.executable, ENFORCER, "status"], capture_output=True, text=True)
        check("refuses to run without root", p.returncode != 0 and "root" in p.stderr, p.stderr)

        # ---- kill: the reviewer's case (an ip without a cgroup) must be refused
        kill_path = os.path.join(tmp, "kill.json")
        for name, spec in {
            "kill with only an ip": [{"ip": "1.1.1.1"}],
            "kill with an empty cgroup": [{"cgroup": "", "ip": "1.1.1.1"}],
            "kill in another user's slice": [{"cgroup": "user.slice/user-0.slice/x.scope"}],
            "kill in a system service": [{"cgroup": "system.slice/warp-svc.service", "ip": "1.1.1.1"}],
            "kill with a bad ip": [{"cgroup": own_cg, "ip": "1.1.1.1; reboot"}],
        }.items():
            with open(kill_path, "w") as f:
                json.dump(spec, f)
            rc, out, err, rs = run(tmp, ["kill", kill_path])
            check("rejects " + name, rc != 0, out + err)

        # ---- kill never closes a socket that belongs to someone else. In the
        # namespace the sockets report uid 0, i.e. not the caller's uid.
        with open(kill_path, "w") as f:
            json.dump([{"cgroup": own_cg}], f)
        probe = os.path.join(tmp, "probe.sh")
        with open(probe, "w") as f:
            f.write("ip link set lo up\n"
                    "python3 -c 'import socket,time\n"
                    "s=socket.socket(); s.bind((\"127.0.0.1\",45001)); s.listen()\n"
                    "c=socket.create_connection((\"127.0.0.1\",45001)); a,_=s.accept()\n"
                    "time.sleep(4)' &\n"
                    "sleep 1\n"
                    "PKEXEC_UID=%d %s %s x kill %s\n"
                    "echo ALIVE=$(ss -tn -H state established | grep -c 45001)\n" % (UID, sys.executable, os.path.join(tmp, "runner.py"), kill_path))
        p = subprocess.run(["unshare", "-rn", "sh", probe], capture_output=True, text=True)
        res = next((json.loads(l) for l in p.stdout.splitlines() if l.startswith("{")), {})
        alive = next((l for l in p.stdout.splitlines() if l.startswith("ALIVE=")), "")
        check("kill skips sockets of another owner", res.get("killed") == 0 and res.get("skipped_other_owner", 0) >= 1, p.stdout + p.stderr)
        check("their connection stays up", alive in ("ALIVE=2", "ALIVE=1"), alive + p.stderr)

        rc, out, err, rs = run(tmp, ["apply", spec_path], dict(good, logNew=True))
        with open(os.path.join(tmp, "status_runner.py"), "w") as f:
            f.write(RUNNER % {"enforcer": ENFORCER, "state": os.path.join(tmp, "state")})
        env = dict(os.environ, PKEXEC_UID=str(UID))
        p = subprocess.run(["unshare", "-rn", "sh", "-c",
                            "%s %s x apply %s >/dev/null && %s %s x status" % (sys.executable, os.path.join(tmp, "status_runner.py"), spec_path,
                                                                             sys.executable, os.path.join(tmp, "status_runner.py"))],
                           capture_output=True, text=True, env=env)
        st = json.loads(p.stdout.strip().splitlines()[-1]) if p.stdout.strip() else {}
        check("status reports version and logging", st.get("version") == "1.2.1" and st.get("logging") is True, p.stdout + p.stderr)

        rc, out, err, rs = run(tmp, ["off"])
        check("off removes the table", rc == 0 and "citadel" not in rs, rs)

    # ---- parser: uid is read per socket; root sockets have no uid field
    import runpy
    g = runpy.run_path(ENFORCER, run_name="citadel_enforcer_parse")
    sample = ("ESTAB 0 0 172.16.5.6:45538 104.17.24.14:443 timer:(keepalive,12sec,0) uid:1000 ino:1 sk:2 cgroup:/user.slice/x\n"
              "ESTAB 0 0 172.16.0.2:34731 162.159.36.1:443 ino:3 sk:4 cgroup:/user.slice/x\n"
              "UNCONN 0 0 [2001:db8::5]:5353 [2606:4700::1]:443 uid:1000 ino:5\n"
              "ESTAB 0 0 [fe80::1%wlan0]:22 [fe80::2%wlan0]:50000 uid:1001 ino:6\n")
    got = [(str(a), lp, str(b), rp, u) for a, lp, b, rp, u in g["parse_sockets"](sample)]
    check("parser reads owner uids (root = 0)", got == [
        ("172.16.5.6", 45538, "104.17.24.14", 443, 1000),
        ("172.16.0.2", 34731, "162.159.36.1", 443, 0),
        ("2001:db8::5", 5353, "2606:4700::1", 443, 1000),
        ("fe80::1", 22, "fe80::2", 50000, 1001)], got)

    print("%d passed, %d failed" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
