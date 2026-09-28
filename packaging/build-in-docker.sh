#!/bin/sh
# Build (and install-test) the .deb or .rpm in a throwaway container.
#   packaging/build-in-docker.sh deb [image]   (default ubuntu:24.04)
#   packaging/build-in-docker.sh rpm [image]   (default fedora:latest)
# Output lands in packaging/out/.
set -e
kind=$1; here=$(cd "$(dirname "$0")/.." && pwd); out="$here/packaging/out"; mkdir -p "$out"
ver=$(sed -n 's/^VERSION = "\(.*\)"/\1/p' "$here/citadel-enforcer")
case "$kind" in
  deb) img=${2:-ubuntu:24.04}
    docker run --rm -v "$here:/src:ro" -v "$out:/out" "$img" sh -ec '
      export DEBIAN_FRONTEND=noninteractive
      apt-get update -qq && apt-get install -y -qq debhelper make python3 >/dev/null
      cp -r /src /build && cd /build && rm -rf debian && cp -r packaging/debian debian
      dpkg-buildpackage -us -uc -b >/dev/null && cp ../citadel-helper_*.deb /out/
      apt-get install -y -qq ../citadel-helper_*.deb >/dev/null
      grep -q "isInGroup(\"sudo\")" /usr/share/polkit-1/rules.d/49-citadel.rules
      python3 /usr/lib/citadel/citadel-enforcer status >/dev/null 2>&1 || true
      echo "installed: $(dpkg-query -W citadel-helper)"' ;;
  rpm) img=${2:-fedora:latest}
    docker run --rm -v "$here:/src:ro" -v "$out:/out" "$img" sh -ec "
      dnf -q -y install rpm-build make systemd-rpm-macros >/dev/null
      mkdir -p ~/rpmbuild/SOURCES && cd /src && tar --transform 's,^,citadel-helper-$ver/,' -czf ~/rpmbuild/SOURCES/citadel-helper-$ver.tar.gz --exclude=./packaging/out --exclude=./pkg --exclude=./src --exclude='*.pkg.tar.zst' --exclude=.git .
      rpmbuild -bb packaging/rpm/citadel-helper.spec >/dev/null && cp ~/rpmbuild/RPMS/noarch/citadel-helper-*.rpm /out/
      dnf -q -y install ~/rpmbuild/RPMS/noarch/citadel-helper-*.rpm >/dev/null
      grep -q 'isInGroup(\"wheel\")' /usr/share/polkit-1/rules.d/49-citadel.rules
      echo installed: \$(rpm -q citadel-helper)" ;;
  *) echo "usage: $0 deb|rpm [image]"; exit 2 ;;
esac
