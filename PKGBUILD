# Build citadel-helper from this checkout: makepkg -si
# After editing any source file, refresh the checksums with: updpkgsums
# (The AUR package in aur/ builds the same files from a tagged release.)
pkgname=citadel-helper
pkgver=1.3.1
pkgrel=1
pkgdesc="Root helper, polkit rule and boot restore for the Citadel outbound firewall"
arch=('any')
url="https://github.com/NeatOuk/citadel-helper"
license=('MIT')
depends=('python' 'nftables' 'iproute2' 'polkit')
optdepends=('python-maxminddb: country lookup in the Citadel panel')
install=citadel-helper.install
source=('citadel-enforcer' 'citadel-off' 'io.github.neatouk.citadel.policy'
        '49-citadel.rules.in' 'citadel-restore.service' 'LICENSE')
sha256sums=('10176ee597ede7373a4edc0896f1ec63d1e221c1cedafe0e02d1fdb7588ed596'
            '715b796cfd74b62d91465eddc64fb8061d902ff4cd8ccc116ab98f6fc31b469a'
            'ccb21f98fffa61b1a220dada9b5af276918039333f1fccf08862361f0e01eacc'
            '28c97efa997e19b1c270e005fd84ca176c1e8f5d8f2d661eb0ebf5178e65628b'
            'afba36df5ead2759832ca45364329d60cd502f3c954b095fe61a3a1cf78e3220'
            '8446e7b872a179f84d8fe571f04a16254a4a565ead4288b75d1b9a6902ea0f2b')

package() {
  install -Dm755 citadel-enforcer "$pkgdir/usr/lib/citadel/citadel-enforcer"
  install -Dm755 citadel-off "$pkgdir/usr/bin/citadel-off"
  install -Dm644 io.github.neatouk.citadel.policy "$pkgdir/usr/share/polkit-1/actions/io.github.neatouk.citadel.policy"
  sed 's/@ADMIN_GROUP@/wheel/g' 49-citadel.rules.in > 49-citadel.rules
  install -Dm644 49-citadel.rules "$pkgdir/usr/share/polkit-1/rules.d/49-citadel.rules"
  install -Dm644 citadel-restore.service "$pkgdir/usr/lib/systemd/system/citadel-restore.service"
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
