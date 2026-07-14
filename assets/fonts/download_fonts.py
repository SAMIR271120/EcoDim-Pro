"""
Telecharge les polices TTF necessaires pour le rapport PDF EcoDim Pro.
Polices : Space Grotesk, Inter, JetBrains Mono (Google Fonts - licence OFL)
"""
import os
import urllib.request

FONTS_DIR = os.path.dirname(os.path.abspath(__file__))
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}


def download_font(name, url):
    dest = os.path.join(FONTS_DIR, name)
    if os.path.exists(dest) and os.path.getsize(dest) > 10000:
        print("  OK deja present : %s (%d bytes)" % (name, os.path.getsize(dest)))
        return True
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
        with open(dest, "wb") as f:
            f.write(data)
        size = os.path.getsize(dest)
        if size < 5000:
            os.remove(dest)
            print("  FAIL trop petit (%d bytes) : %s" % (size, name))
            return False
        print("  OK : %s (%d bytes)" % (name, size))
        return True
    except Exception as e:
        print("  FAIL : %s -- %s" % (name, e))
        return False


if __name__ == "__main__":
    print("=== Telechargement des polices EcoDim Pro ===")

    # Space Grotesk via GitHub (repo officiel)
    # Essayer plusieurs URL car le repo a change
    sg_urls = [
        ("SpaceGrotesk-Bold.ttf",
         "https://github.com/floriankarsten/space-grotesk/raw/master/fonts/ttf/SpaceGrotesk-Bold.ttf"),
        ("SpaceGrotesk-Medium.ttf",
         "https://github.com/floriankarsten/space-grotesk/raw/master/fonts/ttf/SpaceGrotesk-Medium.ttf"),
    ]
    sg_fallback = [
        ("SpaceGrotesk-Bold.ttf",
         "https://fonts.gstatic.com/s/spacegrotesk/v16/V8mDoQDjQSkFtoMM3T6r8E7mF71Q-gozuEnF.ttf"),
        ("SpaceGrotesk-Medium.ttf",
         "https://fonts.gstatic.com/s/spacegrotesk/v16/V8mDoQDjQSkFtoMM3T6r8E7mF71Q-gozuEnF.ttf"),
    ]

    for name, url in sg_urls:
        if not download_font(name, url):
            # Try fallback
            for fn, fu in sg_fallback:
                if fn == name:
                    download_font(name, fu)
                    break

    # JetBrains Mono via GitHub direct
    jb_urls = [
        ("JetBrainsMono-Medium.ttf",
         "https://github.com/JetBrains/JetBrainsMono/raw/master/fonts/ttf/JetBrainsMono-Medium.ttf"),
        ("JetBrainsMono-SemiBold.ttf",
         "https://github.com/JetBrains/JetBrainsMono/raw/master/fonts/ttf/JetBrainsMono-SemiBold.ttf"),
    ]
    for name, url in jb_urls:
        download_font(name, url)

    # Inter via GitHub (repo officiel rsms/inter)
    inter_urls = [
        ("Inter-Regular.ttf",
         "https://github.com/rsms/inter/raw/main/docs/font-files/Inter-Regular.ttf"),
        ("Inter-Medium.ttf",
         "https://github.com/rsms/inter/raw/main/docs/font-files/Inter-Medium.ttf"),
    ]
    # Essayer aussi via releases
    inter_fallback = [
        ("Inter-Regular.ttf",
         "https://fonts.gstatic.com/s/inter/v19/UcCO3FwrK3iLTeHuS_nVMrMxCp50SjIw2boKoduKmMEVuLyfAZ9hiJ-Ek-_EeA.woff2"),
        ("Inter-Medium.ttf",
         "https://fonts.gstatic.com/s/inter/v19/UcCO3FwrK3iLTeHuS_nVMrMxCp50SjIw2boKoduKmMEVuI6fAZ9hiJ-Ek-_EeA.woff2"),
    ]
    for name, url in inter_urls:
        if not download_font(name, url):
            for fn, fu in inter_fallback:
                if fn == name:
                    download_font(name, fu)
                    break

    print("\n=== Resultat ===")
    needed = [
        "SpaceGrotesk-Bold.ttf", "SpaceGrotesk-Medium.ttf",
        "Inter-Regular.ttf", "Inter-Medium.ttf",
        "JetBrainsMono-Medium.ttf", "JetBrainsMono-SemiBold.ttf"
    ]
    for name in needed:
        path = os.path.join(FONTS_DIR, name)
        ok = os.path.exists(path) and os.path.getsize(path) > 10000
        print("  [%s] %s" % ("OK" if ok else "MANQUANT", name))
