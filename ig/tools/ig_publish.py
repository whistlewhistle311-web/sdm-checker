"""인스타 @sdm.check 자동 게시 (Graph API, Facebook 로그인 방식).

사용:
  python ig/tools/ig_publish.py check          # 토큰·계정 연결 확인만 (게시 안 함)
  python ig/tools/ig_publish.py publish         # ig/posts/*/ 중 APPROVED 있고 POSTED 없는 폴더 게시

폴더 형식 (ig/posts/<이름>/):
  1.jpg 2.jpg ... (JPEG만, 최대 10장, 4:5 권장 1080x1350)
  caption.txt     (캡션 전체)
  APPROVED        (휘가 '게시' 승인했을 때만 만든다)
  POSTED          (게시 후 자동 생성: media id, 링크)
토큰은 환경변수 IG_PAGE_TOKEN (GitHub Secrets). 저장소에 쓰지 않는다.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://graph.facebook.com/v26.0"
IG_USER_ID = "17841418949526189"  # @sdm.check (공개 ID, 비밀 아님)
REPO_RAW = "https://raw.githubusercontent.com/whistlewhistle311-web/sdm-checker/main"
ROOT = Path(__file__).resolve().parents[2]
POSTS = ROOT / "ig" / "posts"


def token():
    t = os.environ.get("IG_PAGE_TOKEN", "").strip()
    if not t:
        sys.exit("IG_PAGE_TOKEN 없음")
    return t


def call(method, path, **params):
    params["access_token"] = token()
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    if method == "GET":
        req = urllib.request.Request(url + "?" + data.decode())
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        # 토큰이 오류 메시지에 섞여 나오지 않게 지운다
        body = body.replace(params["access_token"], "***")
        sys.exit(f"API 오류 {e.code} {path}: {body}")


def check():
    me = call("GET", IG_USER_ID, fields="username,media_count")
    print(f"연결 OK: @{me.get('username')} 게시물 {me.get('media_count')}개")
    lim = call("GET", f"{IG_USER_ID}/content_publishing_limit", fields="quota_usage,config")
    print("하루 게시 한도:", json.dumps(lim.get("data", lim), ensure_ascii=False))
    if me.get("username") != "sdm.check":
        sys.exit("계정이 sdm.check가 아님 — 중단")


def wait_ready(cid):
    for _ in range(30):
        s = call("GET", cid, fields="status_code").get("status_code")
        if s == "FINISHED":
            return
        if s in ("ERROR", "EXPIRED"):
            sys.exit(f"컨테이너 {cid} 상태 {s}")
        time.sleep(5)
    sys.exit(f"컨테이너 {cid} 준비 시간 초과")


def publish_folder(d: Path):
    imgs = sorted(p for p in d.iterdir() if p.suffix.lower() in (".jpg", ".jpeg"))
    imgs.sort(key=lambda p: int(p.stem) if p.stem.isdigit() else 999)
    if not 1 <= len(imgs) <= 10:
        sys.exit(f"{d.name}: JPEG 1~10장 필요 (지금 {len(imgs)})")
    caption = (d / "caption.txt").read_text(encoding="utf-8").strip()
    rel = d.relative_to(ROOT).as_posix()
    urls = [f"{REPO_RAW}/{rel}/{urllib.parse.quote(p.name)}" for p in imgs]

    if len(urls) == 1:
        cid = call("POST", f"{IG_USER_ID}/media", image_url=urls[0], caption=caption)["id"]
    else:
        kids = []
        for u in urls:
            k = call("POST", f"{IG_USER_ID}/media", image_url=u, is_carousel_item="true")["id"]
            wait_ready(k)
            kids.append(k)
        cid = call("POST", f"{IG_USER_ID}/media", media_type="CAROUSEL",
                   children=",".join(kids), caption=caption)["id"]
    wait_ready(cid)
    mid = call("POST", f"{IG_USER_ID}/media_publish", creation_id=cid)["id"]
    link = call("GET", mid, fields="permalink").get("permalink", "")
    (d / "POSTED").write_text(f"media_id={mid}\npermalink={link}\nposted_at={time.strftime('%Y-%m-%d %H:%M', time.gmtime(time.time()+9*3600))} KST\n", encoding="utf-8")
    print(f"게시 완료: {d.name} → {link}")


def publish():
    check()
    todo = [d for d in sorted(POSTS.glob("*")) if d.is_dir()
            and (d / "APPROVED").exists() and not (d / "POSTED").exists()]
    if not todo:
        print("게시할 폴더 없음")
        return
    for d in todo:
        publish_folder(d)


if __name__ == "__main__":
    {"check": check, "publish": publish}[sys.argv[1] if len(sys.argv) > 1 else "check"]()
