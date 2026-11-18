"""admin(전체 셀러) 캘린더 만들기: 테스트 캘린더의 디자인(글꼴·색·카드 스타일·로고)을 그대로 가져와
admin_body.html 과 합쳐 index.html 을 만든다. 데이터는 화면이 열릴 때 각 셀러 사이트의 data.json 을 바로 불러온다.
python build_admin.py  →  index.html, manifest.webmanifest, sw.js"""
import json, hashlib, re
from pathlib import Path

HERE = Path(__file__).parent
SRC = (HERE / "master/template.html").read_text(encoding="utf-8")
head = SRC[:SRC.index("</style>") + len("</style>")]
head = head.replace("__APP_NAME__", "admin · 셀러 전체 캘린더")
brand = next(l for l in SRC.splitlines() if 'class="brand"' in l)
# 셀러 화면(테스트 캘린더 = 기능이 가장 앞선 원본)의 본문과 스크립트 — admin 안에서 셀러를 골라 그대로 그린다
s_end = SRC.index("</style>") + len("</style>")
j_start = SRC.index("<script>\nconst DATA")
TBODY = SRC[s_end:j_start]
TJS = SRC[j_start + len("<script>"):SRC.rindex("</script>")]
LOG_URL = re.search(r'const LOG_URL = "([^"]*)"', TJS).group(1)
TJS = (TJS.replace("/*__DATA__*/null", "window.__ADM.data")
          .replace("/*__IDEAS__*/null", "window.__ADM.ideas")
          .replace("/*__OPINION__*/null", "window.__ADM.opinion")
          .replace('body: JSON.stringify({seller: "__SELLER__",', 'body: JSON.stringify({seller: "admin",')
          .replace('context: context || ""})', 'context: "[__SELLER__] " + (context || "")})')
          .replace("new URL(file, location.href)", "new URL(file, document.baseURI)"))
assert "window.__ADM.data" in TJS and 'seller: "admin"' in TJS and "[__SELLER__]" in TJS
tpl_vars = ("<script>window.ADM_TBODY = " + json.dumps(TBODY, ensure_ascii=False).replace("</", "<\\/")
            + ";\nwindow.ADM_TJS = " + json.dumps(TJS, ensure_ascii=False).replace("</", "<\\/")
            + ";\nwindow.LOG_URL_ADM = " + json.dumps(LOG_URL) + ";</script>\n")
body = (HERE / "admin_body.html").read_text(encoding="utf-8").replace("__BRAND__", brand)
install = (HERE / "master/install_prompt.html").read_text(encoding="utf-8")
# admin 은 APK·아이폰 프로필이 없으니 바로가기만
install = install.replace('id="inst-apk" hidden', 'id="inst-apk" hidden data-off').replace(
    'if (isAndroid) document.getElementById("inst-apk").hidden = false;', "")
install = install.replace('document.getElementById("inst-prof").hidden = false;', "")
install = install.replace('document.getElementById("inst-alt").hidden = false;', "")   # admin 은 APK·프로필 없음: '앱으로 설치하기' 칸을 숨김
install = install.replace('getElementById("who")', 'getElementById("admgate")')

ver = hashlib.sha256((head + body + install + TBODY + TJS).encode()).hexdigest()[:10]
iv = hashlib.sha256((HERE / "icons/icon-512.png").read_bytes()).hexdigest()[:8]
pwa_head = f'''<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="icon-180.png">
<link rel="icon" type="image/png" href="icon-192.png">
<meta name="theme-color" content="#F6F1EA">
'''

# ---------------------------------------------------------------- 페이지 가리기 (2026-11-18 재열님 요청)
AI_META = ('<meta name="robots" content="noindex,nofollow,noarchive,nosnippet,noimageindex,noai,noimageai">\n'
           '<meta name="googlebot" content="noindex,nofollow,noarchive,nosnippet">\n')


def cloak(html, cut="<style>"):
    """cut 앞(메타·제목·아이콘)만 그대로 두고, 나머지(디자인·화면·코드·데이터)는 XOR+base64 로 감싸서
    브라우저에서 열 때만 풀어 document.write 로 그린다. 링크만 읽는 AI·검색 로봇에는 의미 없는 글자만 보인다."""
    import base64, os
    i = html.find(cut, max(0, html.find("</title>")))   # 제목 뒤의 첫 <style> 부터 가림
    if i < 0:
        return html
    head, body = html[:i], html[i:]
    key = os.urandom(16)
    raw = body.encode("utf-8")
    enc = base64.b64encode(bytes(b ^ key[n % 16] for n, b in enumerate(raw))).decode()
    k = base64.b64encode(key).decode()
    loader = ('<script>(function(){var k=atob("%s"),b=atob("%s"),u=new Uint8Array(b.length);'
              'for(var i=0;i<b.length;i++)u[i]=b.charCodeAt(i)^k.charCodeAt(i%%16);'
              'document.write(new TextDecoder().decode(u));})();</script>' % (k, enc))
    if 'name="robots"' in head:
        head = head.split('<meta name="robots"')[0] + head.split('<meta name="robots"', 1)[1].split(">", 1)[1]
    j = head.find("\n", head.find('<meta charset="utf-8">'))   # 문서 형식 선언·글자 설정 다음 줄에 AI 차단 표시
    head = head[:j + 1] + AI_META + head[j + 1:]
    return head + "<noscript>이 캘린더는 휴대폰 브라우저에서 열어 주세요.</noscript>\n" + loader


html = "<!doctype html>\n<html lang=\"ko\">\n<head>\n" + head.replace("<title>", pwa_head + "<title>", 1) + "\n</head>\n<body>\n" + tpl_vars + body + install + f'''
<script>
// 항상 최신 화면: 서버 버전과 다르면(옛 화면이 남아 있으면) 저장해 둔 것을 지우고 새로 불러옴
const APPVER = "{ver}";
if ("serviceWorker" in navigator) navigator.serviceWorker.register(new URL("sw.js?v={ver}", location.href).href).catch(() => {{}});
async function checkVer() {{
  try {{
    const v = (await (await fetch(new URL("version.txt?t=" + Date.now(), location.href).href, {{cache: "no-store"}})).text()).trim();
    if (v && v !== APPVER && sessionStorage.getItem("admReloaded") !== v) {{
      sessionStorage.setItem("admReloaded", v);
      if (window.caches) for (const k of await caches.keys()) await caches.delete(k);
      if (navigator.serviceWorker) for (const r of await navigator.serviceWorker.getRegistrations()) await r.update();
      location.reload();
    }}
  }} catch (e) {{}}
}}
checkVer();
document.addEventListener("visibilitychange", () => {{ if (document.visibilityState === "visible") checkVer(); }});
setInterval(checkVer, 3 * 60 * 1000);   // 켜 둔 채로 있어도 3분마다 새 버전 확인
</script>
</body>
</html>
'''
(HERE / "index.html").write_text(cloak(html), encoding="utf-8")
for n in (180, 192, 512):
    (HERE / f"icon-{n}.png").write_bytes((HERE / f"icons/icon-{n}.png").read_bytes())
manifest = {"id": "./", "name": "admin · 셀러 전체 캘린더", "short_name": "admin 캘린더", "lang": "ko",
            "start_url": "./", "scope": "./", "display": "standalone", "background_color": "#F6F1EA", "theme_color": "#F6F1EA",
            "icons": [{"src": f"icon-192.png?v={iv}", "sizes": "192x192", "type": "image/png", "purpose": "any"},
                      {"src": f"icon-512.png?v={iv}", "sizes": "512x512", "type": "image/png", "purpose": "any"}]}
(HERE / "manifest.webmanifest").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
(HERE / "sw.js").write_text(f'''// admin 캘린더: 항상 최신을 먼저(인터넷 우선), 안 되면 저장해 둔 화면
const C = "admin-{ver}";
self.addEventListener("install", e => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== C).map(k => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener("fetch", e => {{
  if (e.request.method !== "GET" || new URL(e.request.url).origin !== location.origin) return;
  e.respondWith(fetch(e.request, {{cache: "no-store"}}).then(r => {{ const c = r.clone(); caches.open(C).then(x => x.put(e.request, c)); return r; }}).catch(() => caches.match(e.request)));
}});
''', encoding="utf-8")
(HERE / "version.txt").write_text(ver, encoding="utf-8")
# 검토 대기 댓글 여론 목록 (drafts/<저장소>/opinion.json 이 있는 셀러)
(HERE / "drafts").mkdir(exist_ok=True)
pending = sorted(d.name for d in (HERE / "drafts").iterdir() if (d / "opinion.json").exists())
(HERE / "drafts/index.json").write_text(json.dumps(pending), encoding="utf-8")
print("built admin", ver, len(html))
