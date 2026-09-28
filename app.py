import random
import string
import threading

from flask import Flask, jsonify, request, abort

app = Flask(__name__)
ROOMS = {}
LOCK = threading.Lock()
N = 10


def other_of(room, tok):
    return next((p for t, p in room["players"].items() if t != tok), None)


def get_room(code):
    r = ROOMS.get(code)
    if not r:
        abort(404)
    return r


@app.get("/")
@app.get("/r/<code>")
def page(code=None):
    return PAGE


@app.post("/api/create")
def create():
    with LOCK:
        while True:
            c = "".join(random.choices(string.ascii_lowercase + string.digits, k=5))
            if c not in ROOMS:
                break
        ROOMS[c] = {"players": {}}
    return jsonify(code=c)


@app.post("/api/<code>/join")
def join(code):
    d = request.get_json()
    name = (d.get("name") or "Аноним").strip()[:20]
    with LOCK:
        pl = get_room(code)["players"]
        if d["token"] not in pl:
            if len(pl) >= 2:
                return jsonify(error="В этой комнате уже двое 💞"), 403
            pl[d["token"]] = dict(name=name, questions=None, started=False, answers=[], score=0)
        else:
            pl[d["token"]]["name"] = name
    return jsonify(ok=True)


@app.post("/api/<code>/questions")
def set_questions(code):
    d = request.get_json()
    with LOCK:
        me = get_room(code)["players"].get(d["token"]) or abort(403)
        qs = []
        for x in d["questions"][:N]:
            q = str(x["q"]).strip()[:200]
            opts = [str(o).strip()[:80] for o in x["options"][:4]]
            c = int(x["correct"])
            if not q or len(opts) < 4 or not all(opts) or c not in range(4):
                return jsonify(error="Заполни все вопросы и все варианты ответа"), 400
            qs.append(dict(q=q, options=opts, correct=c))
        if len(qs) != N:
            return jsonify(error="Нужно ровно 10 вопросов"), 400
        me["questions"] = qs
    return jsonify(ok=True)


@app.post("/api/<code>/start")
def start(code):
    d = request.get_json()
    with LOCK:
        r = get_room(code)
        me = r["players"].get(d["token"]) or abort(403)
        o = other_of(r, d["token"])
        if me["questions"] and o and o["questions"]:
            me["started"] = True
    return jsonify(ok=True)


@app.post("/api/<code>/answer")
def answer(code):
    d = request.get_json()
    with LOCK:
        r = get_room(code)
        me = r["players"].get(d["token"]) or abort(403)
        o = other_of(r, d["token"])
        i = len(me["answers"])
        if not o or not o["questions"] or i >= N or int(d["q"]) != i:
            abort(400)
        correct = o["questions"][i]["correct"]
        ch = int(d["choice"])
        me["answers"].append(ch)
        if ch == correct:
            me["score"] += 1
    return jsonify(correct=correct, score=me["score"])


@app.get("/api/<code>/state")
def state(code):
    tok = request.args.get("token")
    with LOCK:
        r = get_room(code)
        me = r["players"].get(tok) or abort(403)
        o = other_of(r, tok)
        s = dict(
            me=dict(name=me["name"], ready=bool(me["questions"]), started=me["started"], done=len(me["answers"])),
            partner=None if not o else dict(name=o["name"], ready=bool(o["questions"]), started=o["started"]),
        )
        if o and me["started"] and o["started"]:
            i = len(me["answers"])
            if i < N:
                q = o["questions"][i]
                s["question"] = dict(i=i, q=q["q"], options=q["options"])
            elif len(o["answers"]) >= N:
                s["results"] = dict(me=me["score"], partner=o["score"])
    return jsonify(s)


PAGE = r"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Love Quiz 💗</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Comfortaa:wght@600;700&family=Nunito:wght@400;600;700&family=Pacifico&display=swap" rel="stylesheet">
<style>
:root{--rose:#e8456b;--deep:#b02a4d;--bg1:#fff1f4;--bg2:#ffd3de;--ink:#4a1f2c}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;font-family:Nunito,system-ui,sans-serif;color:var(--ink);background:linear-gradient(160deg,var(--bg1),var(--bg2));overflow-x:hidden}
#hearts{position:fixed;inset:0;pointer-events:none;z-index:0}
#hearts span{position:absolute;bottom:-40px;opacity:0;color:var(--rose);animation:up linear infinite}
@keyframes up{10%{opacity:.35}100%{transform:translateY(-110vh) rotate(25deg);opacity:0}}
main{position:relative;z-index:1;max-width:520px;margin:0 auto;padding:28px 18px 60px}
h1,.score{font-family:Pacifico,'Comic Sans MS',cursive;font-weight:400;line-height:1.3}h2{font-family:Comfortaa,Nunito,sans-serif;font-weight:700;line-height:1.3}
h1{font-size:2.2rem;text-align:center;margin:12vh 0 8px;color:var(--deep)}
h2{font-size:1.5rem;margin:18px 0 10px}
p,.sub{opacity:.8;line-height:1.5}
.center{text-align:center}
button{font:inherit;font-weight:600;width:100%;padding:15px 18px;margin-top:12px;border:0;border-radius:999px;color:#fff;background:linear-gradient(135deg,#f0648a,var(--deep));box-shadow:0 8px 20px rgba(176,42,77,.28);cursor:pointer;transition:transform .15s}
button:active{transform:scale(.97)}
button.opt{background:rgba(255,255,255,.75);color:var(--ink);text-align:left;border-radius:16px;box-shadow:0 2px 8px rgba(0,0,0,.06);border:2px solid transparent}
button.opt.ok{background:#d6f5df;border-color:#2e9e57;color:#14532d}
button.opt.bad{background:#ffdcdc;border-color:#d63b3b;color:#7f1d1d}
.hide{display:none}
.card{background:rgba(255,255,255,.65);backdrop-filter:blur(8px);border-radius:20px;padding:16px;margin:14px 0;box-shadow:0 6px 24px rgba(176,42,77,.1)}
input:not([type=radio]){width:100%;font:inherit;padding:12px 14px;margin-top:8px;border:1.5px solid #f4b6c6;border-radius:12px;background:#fff;color:var(--ink)}
input:focus{outline:none;border-color:var(--rose)}
.row{display:flex;align-items:center;gap:10px}
.row input[type=radio]{accent-color:var(--rose);width:22px;height:22px;margin-top:8px;flex:none}
.bar{height:8px;background:rgba(255,255,255,.7);border-radius:9px;overflow:hidden}
.bar i{display:block;height:100%;background:linear-gradient(90deg,#f0648a,var(--deep));transition:width .4s}
.err{color:#c0223f;text-align:center}
.score{font-size:3rem;color:var(--deep)}
.link{word-break:break-all;font-size:.9rem;background:#fff;padding:10px;border-radius:12px}
.pulse{display:inline-block;animation:p 1.2s infinite}@keyframes p{50%{transform:scale(1.25)}}
.duo{display:grid;grid-template-columns:1fr 1fr;gap:12px}.duo .score{font-size:2.3rem}
.love h2{margin-top:4px}.love p{font-size:1.02rem}
.gallery{column-count:2;column-gap:14px;margin-top:22px}
.pol{break-inside:avoid;margin:0 0 14px;padding:8px 8px 22px;background:#fff;border-radius:6px;box-shadow:0 8px 22px rgba(176,42,77,.22);transform:rotate(var(--r))}
.pol img{display:block;width:100%;height:auto;border-radius:3px}
</style></head><body>
<div id="hearts"></div><main id="app"></main>
<script>
const $=s=>document.querySelector(s),app=$('#app'),N=10;
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const code=location.pathname.startsWith('/r/')?location.pathname.split('/')[2]:null;
const tok=localStorage.tok||(localStorage.tok=Math.random().toString(36).slice(2)+Date.now().toString(36));
let key='',locked=false;
const api=(p,b)=>fetch('/api/'+p,b?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:tok,...b})}:{}).then(async r=>({ok:r.ok,d:await r.json().catch(()=>({}))}));
for(let i=0;i<14;i++){const s=document.createElement('span');s.textContent='♥';s.style.cssText=`left:${Math.random()*100}%;font-size:${14+Math.random()*26}px;animation-duration:${9+Math.random()*10}s;animation-delay:${Math.random()*10}s`;$('#hearts').append(s)}
const msg=t=>app.innerHTML=`<div class="center"><h2 style="margin-top:20vh">${t}</h2><span class="pulse" style="font-size:2rem">💗</span></div>`;

function home(){app.innerHTML=`<h1>Love Quiz</h1><p class="center">Свидание на расстоянии: придумайте друг другу вопросы и проверьте, как хорошо вы знаете друг друга.</p><button id=go>Создать свидание 💌</button>`;
$('#go').onclick=async()=>{const r=await api('create',{});location.href='/r/'+r.d.code}}
function askName(){app.innerHTML=`<h2 class=center style="margin-top:14vh">Как тебя зовут?</h2><input id=nm maxlength=20 placeholder="Твоё имя"><button id=ok>Войти 💗</button>`;
$('#ok').onclick=()=>{const v=$('#nm').value.trim();if(v){localStorage.name=v;boot()}}}
function setup(){let h=`<h2>Придумай ${N} вопросов про себя ✍️</h2><p class=sub>Кружком отметь правильный вариант.</p>`;
for(let i=0;i<N;i++)h+=`<div class=card><b>Вопрос ${i+1}</b><input class=q maxlength=200 placeholder="Например: Моё любимое блюдо?">`+[0,1,2,3].map(j=>`<label class=row><input type=radio name=r${i} value=${j} ${j?'':'checked'}><input class=o maxlength=80 placeholder="Вариант ${j+1}"></label>`).join('')+`</div>`;
app.innerHTML=h+`<button id=sv>Готово 💗</button><p id=er class=err></p>`;
$('#sv').onclick=async()=>{const questions=[...document.querySelectorAll('.card')].map(c=>({q:c.querySelector('.q').value,options:[...c.querySelectorAll('.o')].map(x=>x.value),correct:+c.querySelector('input[type=radio]:checked').value}));
const r=await api(code+'/questions',{questions});if(!r.ok)return $('#er').textContent=r.d.error||'Ошибка';key='';poll()}}
function waitPartner(p){const u=location.href;app.innerHTML=`<h2 class=center style="margin-top:12vh">${p?esc(p.name)+' ещё пишет вопросы…':'Отправь ссылку любимому человеку'} <span class=pulse>💗</span></h2><p class="link center">${esc(u)}</p><button id=cp>Скопировать ссылку</button>`;
$('#cp').onclick=()=>{navigator.clipboard&&navigator.clipboard.writeText(u);$('#cp').textContent='Скопировано ✓'}}
function ready(p){app.innerHTML=`<h1 style="margin-top:14vh">Всё готово!</h1><p class=center>Вы с ${esc(p.name)} написали вопросы. Нажмите «Начать», когда будете готовы.</p><button id=st>Начать 💘</button>`;
$('#st').onclick=async()=>{await api(code+'/start',{});key='';poll()}}
function quiz(q){app.innerHTML=`<div class=bar><i style="width:${q.i*100/N}%"></i></div><p class=sub>Вопрос ${q.i+1} из ${N}</p><h2>${esc(q.q)}</h2>`+q.options.map((o,j)=>`<button class=opt data-j=${j}>${esc(o)}</button>`).join('')+`<button id=nx class=hide>${q.i==N-1?'Результаты':'Дальше'} →</button>`;
document.querySelectorAll('.opt').forEach(b=>b.onclick=async()=>{if(locked)return;locked=true;const j=+b.dataset.j;const r=await api(code+'/answer',{q:q.i,choice:j});if(!r.ok){locked=false;return}
const c=r.d.correct;document.querySelectorAll('.opt').forEach(x=>{x.disabled=true;if(+x.dataset.j===c)x.classList.add('ok')});if(j!==c)b.classList.add('bad');
$('#nx').classList.remove('hide');$('#nx').onclick=()=>{locked=false;poll()}})}
function results(s){const r=s.results,p=s.partner;
app.innerHTML=`<h1 class=center style="margin-top:6vh">Результаты</h1><div class=duo><div class="card center"><p>Ты</p><div class=score>${r.me}/${N}</div></div><div class="card center"><p>${esc(p.name)}</p><div class=score>${r.partner}/${N}</div></div></div><div class="card center love"><h2>Но неважно, кто сколько баллов набрал 💞</h2><p>Главное — что мы любим друг друга.</p><p>Этот сайт и квиз я сделал для тебя, потому что ты — самый дорогой человек в моей жизни. Я очень люблю тебя и очень по тебе скучаю.</p></div><div class=gallery>`+[1,2,3,4].map(i=>`<figure class=pol style="--r:${[-3,2.5,2,-2.5][i-1]}deg"><img src="/static/${i}.jpg" alt="" loading=lazy></figure>`).join('')+`</div>`}
function render(s){const me=s.me,p=s.partner;let k,f;
if(!me.ready){k='setup';f=setup}else if(s.results){k='res';f=()=>results(s)}
else if(s.question){k='q'+s.question.i;f=()=>quiz(s.question)}
else if(!p||!p.ready){k='wp'+!!p;f=()=>waitPartner(p)}
else if(!me.started){k='rd';f=()=>ready(p)}
else{k='ws'+p.started+me.done;f=()=>msg(p.started?'Ты закончил(а)! Ждём '+esc(p.name)+'…':'Ждём, пока '+esc(p.name)+' нажмёт «Начать»…')}
if(k!==key){key=k;f()}}
async function poll(){if(locked)return;const r=await api(code+'/state?token='+tok);if(r.ok)render(r.d)}
async function boot(){if(!code)return home();if(!localStorage.name)return askName();
const r=await api(code+'/join',{name:localStorage.name});if(!r.ok)return msg(esc(r.d.error||'Комната не найдена'));poll();setInterval(poll,1500)}
boot();
</script></body></html>"""

if __name__ == "__main__":
    app.run(debug=True, port=5000)