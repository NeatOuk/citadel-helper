# Build citadel-helper from this checkout: makepkg -si
# After editing any source file, refresh the checksums with: updpkgsums
# (The AUR package in aur/ builds the same files from a tagged release.)
pkgname=citadel-helper
pkgver=1.1.0
pkgrel=1
pkgdesc="Root helper, polkit rule and boot restore for the Citadel outbound firewall (Omarchy)"
arch=('any')
url="https://github.com/NeatOuk/citadel-helper"
license=('MIT')
depends=('python' 'nftables' 'iproute2' 'polkit')
optdepends=('python-maxminddb: country lookup in the Citadel panel')
install=citadel-helper.install
source=('citadel-enforcer' 'citadel-off' 'org.omarchy.citadel.policy'
        '49-citadel.rules' 'citadel-restore.service' 'LICENSE')
sha256sums=('f23b641313c3749a665d8755ecf419d9c8bbab787a36ec09278936a719413224'
            '715b796cfd74b62d91465eddc64fb8061d902ff4cd8ccc116ab98f6fc31b469a'
            'ec8b592fdc80f7b9bd32620159c96360f283927ceea88d169d02f7e888477540'
            'fe42934e7856e2d842a86d0430aa43e2459da0f660786129497a0a6f0f8efbf7'
            'afba36df5ead2759832ca45364329d60cd502f3c954b095fe61a3a1cf78e3220'
            '8446e7b872a179f84d8fe571f04a16254a4a565ead4288b75d1b9a6902ea0f2b')

package() {
  install -Dm755 citadel-enforcer "$pkgdir/usr/lib/citadel/citadel-enforcer"
  install -Dm755 citadel-off "$pkgdir/usr/bin/citadel-off"
  install -Dm644 org.omarchy.citadel.policy "$pkgdir/usr/share/polkit-1/actions/org.omarchy.citadel.policy"
  install -Dm644 49-citadel.rules "$pkgdir/usr/share/polkit-1/rules.d/49-citadel.rules"
  install -Dm644 citadel-restore.service "$pkgdir/usr/lib/systemd/system/citadel-restore.service"
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
