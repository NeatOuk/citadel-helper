# citadel-helper

The root side of [Citadel](https://github.com/NeatOuk/citadel), the outbound
firewall for the Omarchy bar. It is a small, audited program that turns
Citadel's policies into nftables rules. It installs a polkit rule so it can do
that without asking for a password, and restores your policies at boot.

Citadel works without it, but then it only **watches**. You see every connection
and can answer at the gate, but nothing is blocked. Install this package to make
Citadel **enforce** what you decide.

## Why a separate package?

Blocking traffic means changing the kernel firewall, and that needs root. An
Omarchy shell plugin can't have root:
- It runs as you, inside the shell.
- The plugin store only copies files into your home directory.

So the one privileged part lives here, as a normal pacman package that you
install on purpose and can remove with pacman.

Keeping it separate also keeps it small enough to read. Everything that runs as
root is one Python file, `citadel-enforcer`, that uses only the standard
library.

## Install

Build and install it from this repository (an AUR package is coming later):

```bash
git clone https://github.com/NeatOuk/citadel-helper.git
cd citadel-helper
makepkg -si
```

Then open Citadel → **Settings** → **Enforcement** and switch it on. Citadel
finds the helper within a few seconds.

**Requirements:**
- Arch Linux or Omarchy
- `python`, `nftables`, `iproute2` and `polkit`
- a kernel with `nft_socket`, cgroup v2 and `INET_DIAG_DESTROY`; the stock Arch kernel has all three
- `python-maxminddb` (optional), for Citadel's country lookup

## What gets installed

| Path | Purpose |
|---|---|
| `/usr/lib/citadel/citadel-enforcer` | The helper. Root-owned; the only thing that ever runs as root. |
| `/usr/share/polkit-1/actions/org.omarchy.citadel.policy` | A polkit action that covers exactly that one program. |
| `/usr/share/polkit-1/rules.d/49-citadel.rules` | Lets the active, local **`wheel`** user run it without a password. Anyone else is asked for an admin password. |
| `/usr/lib/systemd/system/citadel-restore.service` | Re-applies your last policies at boot, before the network comes up. Enabled on install. |
| `/usr/bin/citadel-off` | **Emergency off.** Removes every Citadel rule immediately, from any terminal. |

## How it stays safe

A passwordless root helper is only acceptable if it can't be misused, so
`citadel-enforcer` treats everything it receives as hostile:

- **One table only.** It creates, replaces and deletes `table inet citadel` and never touches anything else in your firewall.
- **Only your own apps.**
  - Rules only ever match traffic from the calling user's processes (`meta skuid`). System services such as WARP, NetworkManager and DNS always pass, so the tunnel and name resolution can't break.
  - App rules must name a cgroup inside the **caller's own** user slice. The caller's uid comes from pkexec, never from the input.
- **Strict validation.**
  - Every address goes through Python's `ipaddress`, and every port must be 1–65535.
  - Cgroup paths are checked against an allow-list pattern, with no `..`.
  - Anything else, including injection attempts, is rejected before nftables is called.
  - Symlinked input files are refused, and inputs have a size limit.
- **No match-all mistakes.** A rule entry with nothing to match is dropped, never turned into "accept or drop everything".
- **Atomic updates.** Each apply replaces the whole table in a single nftables transaction, so there is never a half-applied state.
- **Never breaks what's already running.**
  - Established connections are always accepted.
  - The helper only closes live connections when Citadel explicitly asks, after you block something. Every such request must name an app group (cgroup) inside your own user slice. The helper lists that group's sockets and closes only the ones owned by your uid, one exact connection at a time. Sockets of other users, and root-owned ones such as a `sudo` command started from your terminal, are never touched.

The polkit rule is limited to local, active sessions of `wheel` members. That's
the group that can already become root with sudo on Arch, so the rule gives no
new power, it only skips the password prompt for this one program.

## Commands

Citadel calls these through `pkexec`. You normally never need them yourself.

```
citadel-enforcer apply <spec.json>   build the table from Citadel's spec and save it for boot
citadel-enforcer kill <kill.json>    close your own live connections ([{cgroup, ip?}]; cgroup required)
citadel-enforcer off                 delete the table and the saved spec
citadel-enforcer restore             re-apply the saved spec (used by the boot service)
citadel-enforcer status              JSON: {active, rules, drops, version}
```

The spec is an **ordered** list, and the first match wins. Citadel sorts it most specific first:

```json
{
  "silentDeny": false,
  "blocklist": ["5.188.10.0/23"],
  "rules": [
    {"verdict": "drop",   "cgroup": "user.slice/user-1000.slice/…/app-chromium.scope",
                          "targets": [{"ip": "142.250.0.0/15", "port": 443}]},
    {"verdict": "accept", "targets": [{"ip": "93.184.216.34"}]},
    {"blocklist": true},
    {"verdict": "drop",   "cgroup": "user.slice/user-1000.slice/…/app-example.scope"}
  ]
}
```

- `cgroup` only matches one app, via `socket cgroupv2`.
- `targets` only matches destinations.
- Both together match one app going to specific destinations.
- `silentDeny` (Citadel's Lockdown mode) adds a final drop for anything not allowed earlier.

The last applied spec is kept in `/var/lib/citadel/spec.json`, which only root can read.

## Uninstall

```bash
sudo pacman -R citadel-helper
```

Removing the package switches enforcement off first. Citadel then goes back to watching only.

## Development

```bash
python3 tests/test_enforcer.py   # runs the real enforcer in a private user+network namespace
updpkgsums                       # after changing any file listed in PKGBUILD
makepkg -si                      # build and install from the checkout
```

The tests need no root and never touch your firewall. They check the generated
rules, and that hostile inputs are rejected.

## License

MIT, see [LICENSE](LICENSE).
