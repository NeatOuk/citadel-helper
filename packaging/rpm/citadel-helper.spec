Name:           citadel-helper
Version:        1.3.2
Release:        1%{?dist}
Summary:        Root helper for the Citadel outbound firewall
License:        MIT
URL:            https://github.com/NeatOuk/citadel-helper
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch
BuildRequires:  make
BuildRequires:  systemd-rpm-macros
Requires:       python3
Requires:       nftables
Requires:       iproute
Requires:       polkit
%{?systemd_requires}

%description
A small, strictly validating root helper (called through pkexec) that turns
Citadel's per-app policies into one nftables table, restores them at boot,
and closes only the calling user's own connections. Members of the wheel
group can use it without a password prompt.

%prep
%autosetup

%build

%install
make install DESTDIR=%{buildroot} PREFIX=%{_prefix} ADMIN_GROUP=wheel UNITDIR=%{_unitdir}
rm -rf %{buildroot}%{_datadir}/licenses

%post
%systemd_post citadel-restore.service
if [ $1 -eq 1 ]; then systemctl enable citadel-restore.service >/dev/null 2>&1 || :; fi

%preun
if [ $1 -eq 0 ]; then %{_prefix}/lib/citadel/citadel-enforcer off >/dev/null 2>&1 || :; fi
%systemd_preun citadel-restore.service

%postun
%systemd_postun citadel-restore.service

%files
%license LICENSE
%{_prefix}/lib/citadel/citadel-enforcer
%{_bindir}/citadel-off
%{_datadir}/polkit-1/actions/io.github.neatouk.citadel.policy
%{_datadir}/polkit-1/rules.d/49-citadel.rules
%{_unitdir}/citadel-restore.service

%changelog
* Tue Sep 29 2026 Neat Ouk <neatk13@gmail.com> - 1.3.2-1
- The admin group may also read systemd-resolved's query results (host names)

* Mon Sep 28 2026 Neat Ouk <neatk13@gmail.com> - 1.3.1-1
- Neutral polkit action; the admin group is the distro's own (wheel)
