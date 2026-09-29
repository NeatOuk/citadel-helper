# Installs citadel-helper. Arch uses the PKGBUILD; .deb/.rpm call this with
# ADMIN_GROUP set to the distro's sudo group (wheel on Fedora, sudo on Debian).
PREFIX      ?= /usr
DESTDIR     ?=
ADMIN_GROUP ?= wheel
UNITDIR     ?= $(PREFIX)/lib/systemd/system

.PHONY: install test
install:
	install -Dm755 citadel-enforcer $(DESTDIR)$(PREFIX)/lib/citadel/citadel-enforcer
	install -Dm755 citadel-off $(DESTDIR)$(PREFIX)/bin/citadel-off
	install -Dm644 io.github.neatouk.citadel.policy $(DESTDIR)$(PREFIX)/share/polkit-1/actions/io.github.neatouk.citadel.policy
	install -d $(DESTDIR)$(PREFIX)/share/polkit-1/rules.d
	sed 's/@ADMIN_GROUP@/$(ADMIN_GROUP)/g' 49-citadel.rules.in > $(DESTDIR)$(PREFIX)/share/polkit-1/rules.d/49-citadel.rules
	install -Dm644 citadel-restore.service $(DESTDIR)$(UNITDIR)/citadel-restore.service
	install -Dm644 LICENSE $(DESTDIR)$(PREFIX)/share/licenses/citadel-helper/LICENSE

test:
	python3 tests/test_enforcer.py
