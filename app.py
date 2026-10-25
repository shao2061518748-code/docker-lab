import json
import os
import time

import redis
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
r = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True, socket_timeout=3)

PAGE = """
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>快件驿站 · 快递取件系统</title>
<style>
  * { box-sizing: border-box; }
  body { margin:0; font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif;
         background:#eef2f7; color:#1f2937; }
  header { background:#1d4ed8; color:#fff; padding:18px 32px; }
  header h1 { margin:0; font-size:20px; letter-spacing:1px; }
  header span { opacity:.8; font-size:13px; }
  main { max-width:900px; margin:24px auto; padding:0 16px; display:grid;
         grid-template-columns: 1fr 1fr; gap:16px; }
  .card { background:#fff; border-radius:10px; padding:20px 22px;
          box-shadow:0 1px 3px rgba(16,24,40,.08); }
  .card h2 { margin:0 0 14px; font-size:16px; color:#1d4ed8; }
  label { display:block; font-size:13px; color:#4b5563; margin:10px 0 4px; }
  input { width:100%; padding:8px 10px; border:1px solid #d1d5db; border-radius:6px;
          font-size:14px; }
  button { margin-top:14px; background:#1d4ed8; color:#fff; border:0; border-radius:6px;
           padding:9px 18px; font-size:14px; cursor:pointer; }
  button:hover { background:#1e40af; }
  .row { font-size:13px; margin:6px 0; color:#374151; }
  .ok { color:#047857; font-weight:600; }
  .bad { color:#b91c1c; font-weight:600; }
  .result { margin-top:14px; font-size:14px; line-height:1.7; }
  footer { text-align:center; color:#9ca3af; font-size:12px; margin:28px 0; }
</style>
</head>
<body>
<header><h1>快件驿站 · 快递取件系统</h1>
  <span>Flask + Redis 容器化部署 · Docker Compose</span></header>
<main>
  <section class="card">
    <h2>登记入库</h2>
    <form method="post" action="/register">
      <label>运单号</label>
      <input name="code" placeholder="如 SF1234567890" required>
      <label>收件人</label>
      <input name="name" placeholder="收件人姓名" required>
      <label>货架位</label>
      <input name="shelf" placeholder="如 A-03-12" required>
      <button type="submit">登记入库</button>
    </form>
  </section>
  <section class="card">
    <h2>查询取件</h2>
    <form method="get" action="/query">
      <label>运单号</label>
      <input name="code" placeholder="输入运单号查询" required>
      <button type="submit">查询状态</button>
    </form>
  </section>
</main>
<footer>容器: flask-app · redis-server ｜ 数据持久化: redis-data volume</footer>
</body>
</html>
"""

RESULT = """
<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>查询结果 · 快递取件系统</title>
<style>
 body { margin:0; font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;
        background:#eef2f7; color:#1f2937; }
 header { background:#1d4ed8; color:#fff; padding:18px 32px; }
 header h1 { margin:0; font-size:20px; }
 main { max-width:760px; margin:24px auto; padding:0 16px; }
 .card { background:#fff; border-radius:10px; padding:22px 24px;
         box-shadow:0 1px 3px rgba(16,24,40,.08); }
 .row { font-size:14px; margin:10px 0; }
 .k { color:#6b7280; display:inline-block; width:88px; }
 .ok { color:#047857; font-weight:600; }
 .bad { color:#b91c1c; font-weight:600; }
 form { margin-top:18px; }
 button { background:#1d4ed8; color:#fff; border:0; border-radius:6px;
          padding:9px 18px; font-size:14px; cursor:pointer; }
 a { color:#1d4ed8; text-decoration:none; font-size:13px; }
</style></head><body>
<header><h1>快件驿站 · 查询结果</h1></header>
<main><div class="card">{{ body | safe }}</div></main>
</body></html>
"""


def records_key():
    return "packages"


@app.get("/")
def index():
    return render_template_string(PAGE)


@app.post("/register")
def register():
    code = (request.form.get("code") or "").strip()
    name = (request.form.get("name") or "").strip()
    shelf = (request.form.get("shelf") or "").strip()
    if not code or not name or not shelf:
        return render_template_string(RESULT, body='<span class="bad">运单号、收件人、货架位均不能为空</span>')
    record = {
        "code": code,
        "name": name,
        "shelf": shelf,
        "status": "待取件",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    r.hset(records_key(), code, json.dumps(record, ensure_ascii=False))
    body = (
        '<div class="row"><span class="k">运单号</span><b>%s</b></div>'
        '<div class="row"><span class="k">收件人</span>%s</div>'
        '<div class="row"><span class="k">货架位</span>%s</div>'
        '<div class="row"><span class="k">状态</span><span class="ok">登记成功，待取件</span></div>'
        '<div class="row"><span class="k">入库时间</span>%s</div>'
        '<form method="get" action="/query"><input type="hidden" name="code" value="%s">'
        '<button type="submit">查看该快件状态</button></form>'
        '<p><a href="/">← 返回首页</a></p>'
    ) % (code, name, shelf, record["created_at"], code)
    return render_template_string(RESULT, body=body)


@app.get("/query")
def query():
    code = (request.args.get("code") or "").strip()
    raw = r.hget(records_key(), code)
    if not raw:
        body = (
            '<div class="row"><span class="k">运单号</span><b>%s</b></div>'
            '<div class="row"><span class="k">查询结果</span><span class="bad">未找到该快件</span></div>'
            '<p><a href="/">← 返回首页</a></p>'
        ) % code
        return render_template_string(RESULT, body=body)
    rec = json.loads(raw)
    body = (
        '<div class="row"><span class="k">运单号</span><b>%s</b></div>'
        '<div class="row"><span class="k">收件人</span>%s</div>'
        '<div class="row"><span class="k">货架位</span>%s</div>'
        '<div class="row"><span class="k">当前状态</span><span class="ok">%s</span></div>'
        '<div class="row"><span class="k">入库时间</span>%s</div>'
        '<form method="post" action="/pickup"><input type="hidden" name="code" value="%s">'
        '<button type="submit">确认取件</button></form>'
        '<p><a href="/">← 返回首页</a></p>'
    ) % (rec["code"], rec["name"], rec["shelf"], rec["status"], rec["created_at"], rec["code"])
    return render_template_string(RESULT, body=body)


@app.post("/pickup")
def pickup():
    code = (request.form.get("code") or "").strip()
    raw = r.hget(records_key(), code)
    if not raw:
        return render_template_string(RESULT, body='<span class="bad">未找到该快件</span>')
    rec = json.loads(raw)
    rec["status"] = "已取件"
    rec["picked_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    r.hset(records_key(), code, json.dumps(rec, ensure_ascii=False))
    body = (
        '<div class="row"><span class="k">运单号</span><b>%s</b></div>'
        '<div class="row"><span class="k">收件人</span>%s</div>'
        '<div class="row"><span class="k">取件时间</span>%s</div>'
        '<div class="row"><span class="k">状态</span><span class="ok">已取件</span></div>'
        '<p><a href="/">← 返回首页</a></p>'
    ) % (rec["code"], rec["name"], rec["picked_at"])
    return render_template_string(RESULT, body=body)


@app.get("/api/health")
def health():
    try:
        r.ping()
        return jsonify(ok=True, redis=True, service="flask-app")
    except Exception as exc:  # noqa: BLE001
        return jsonify(ok=False, redis=False, error=str(exc)), 500


@app.get("/api/packages")
def list_packages():
    items = [json.loads(v) for v in r.hvals(records_key())]
    return jsonify(count=len(items), items=items)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
