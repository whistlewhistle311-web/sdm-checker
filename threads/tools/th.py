"""스레드 @sdm.check 자동화 (Threads API).

  python threads/tools/th.py check     # 연결 확인
  python threads/tools/th.py refresh   # 장기 토큰 연장(60일). 토큰 문자열이 바뀌면 실패로 알림
  python threads/tools/th.py search    # threads/SEARCH 의 검색어로 최근 글 찾기 → threads/search/최근.json
  python threads/tools/th.py publish   # threads/queue/<이름>/ 중 APPROVED 있고 POSTED 없는 것 게시

queue 폴더: post.json {"text": "...", "reply_to_id": "(답글이면 대상 글 id)"}
APPROVED 는 휘가 승인했거나, 휘가 미리 맡긴 범위 안일 때만 만든다.
토큰은 환경변수 THREADS_TOKEN (GitHub Secrets). 저장소에 쓰지 않는다.
"""
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://graph.threads.net/v1.0"
ROOT = Path(__file__).resolve().parents[2]
TH = ROOT / "threads"


def tok():
    t = os.environ.get("THREADS_TOKEN", "").strip()
    if not t:
        sys.exit("THREADS_TOKEN 없음")
    return t


def call(method, path, base=API, **params):
    params["access_token"] = tok()
    q = urllib.parse.urlencode(params)
    url = f"{base}/{path}"
    req = urllib.request.Request(url + "?" + q) if method == "GET" else \
        urllib.request.Request(url, data=q.encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace").replace(params["access_token"], "***")
        print(f"API 오류 {e.code} {path}: {body}")
        sys.exit(1)


def check():
    me = call("GET", "me", fields="id,username")
    print(f"연결 OK: @{me.get('username')} (id {me.get('id')})")
    if me.get("username") != "sdm.check":
        sys.exit("계정이 sdm.check가 아님 — 중단")
    lim = call("GET", "me/threads_publishing_limit", fields="quota_usage,config,reply_quota_usage,reply_config")
    print("게시·답글 한도:", json.dumps(lim.get("data", lim), ensure_ascii=False))
    return me


def refresh():
    old = tok()
    r = call("GET", "refresh_access_token", base="https://graph.threads.net",
             grant_type="th_refresh_token")
    days = int(r.get("expires_in", 0)) // 86400
    print(f"연장 OK: 앞으로 약 {days}일")
    if hashlib.sha256(r.get("access_token", "").encode()).digest() != hashlib.sha256(old.encode()).digest():
        sys.exit("새 토큰 문자열이 나옴 — 휘가 Secrets THREADS_TOKEN을 새로 넣어야 함 (기존 토큰도 만료 전까지는 작동)")


def search():
    words = [w.strip() for w in (TH / "SEARCH").read_text(encoding="utf-8").splitlines()
             if w.strip() and not w.startswith("#")]
    out = []
    since = int(time.time()) - 3 * 86400
    for w in words:
        r = call("GET", "keyword_search", q=w, search_type="RECENT", since=since,
                 fields="id,text,username,permalink,timestamp")
        for p in r.get("data", []):
            p["keyword"] = w
            out.append(p)
        time.sleep(1)
    seen, uniq = set(), []
    for p in out:
        if p["id"] not in seen and p.get("username") != "sdm.check":
            seen.add(p["id"])
            uniq.append(p)
    (TH / "search").mkdir(exist_ok=True)
    (TH / "search" / "최근.json").write_text(json.dumps(uniq, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"검색 {len(words)}개 단어 → 글 {len(uniq)}개")


def wait_ready(cid):
    for _ in range(20):
        s = call("GET", cid, fields="status").get("status")
        if s in ("FINISHED", None):
            return
        if s in ("ERROR", "EXPIRED"):
            sys.exit(f"컨테이너 {cid} 상태 {s}")
        time.sleep(3)


def publish():
    check()
    q = TH / "queue"
    todo = [d for d in sorted(q.glob("*")) if d.is_dir()
            and (d / "APPROVED").exists() and not (d / "POSTED").exists()] if q.exists() else []
    if not todo:
        print("게시할 글 없음")
        return
    for d in todo:
        p = json.loads((d / "post.json").read_text(encoding="utf-8"))
        args = {"media_type": "TEXT", "text": p["text"]}
        if p.get("reply_to_id"):
            args["reply_to_id"] = p["reply_to_id"]
        cid = call("POST", "me/threads", **args)["id"]
        wait_ready(cid)
        mid = call("POST", "me/threads_publish", creation_id=cid)["id"]
        link = call("GET", mid, fields="permalink").get("permalink", "")
        (d / "POSTED").write_text(
            f"id={mid}\npermalink={link}\nposted_at={time.strftime('%Y-%m-%d %H:%M', time.gmtime(time.time()+9*3600))} KST\n",
            encoding="utf-8")
        print(f"게시 완료: {d.name} → {link}")
        time.sleep(5)


if __name__ == "__main__":
    {"check": check, "refresh": refresh, "search": search, "publish": publish}[
        sys.argv[1] if len(sys.argv) > 1 else "check"]()
