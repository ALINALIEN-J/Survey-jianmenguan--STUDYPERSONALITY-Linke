import csv
import io
import os
import secrets
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    Response,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key-in-production")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "questionnaire.db"))
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
COMPLETION_COOKIE = "survey_completed"
COMPLETION_COOKIE_MAX_AGE = 60 * 60 * 24 * 365

QUESTIONS = [
    ("A1", "在学习中，我觉得能够自由地选择学习方式和节奏"),
    ("A2", "我感觉自己的学习目标是出于内心的真实意愿，而非被迫"),
    ("A3", "我能够按照自己的想法安排学习时间和内容"),
    ("A4", "我觉得在学习中有足够的选择权"),
    ("A5", "我能自由地表达自己对学习内容的看法和疑问"),
    ("A6", "我感觉学习过程是自己主动参与的，而非被动接受"),
    ("A7", "我觉得老师的教学方式尊重了我的学习偏好"),
    ("A8", "我能够自主决定是否参加额外的学习活动"),
    ("C1", "我觉得自己在学业上能够胜任大多数学习任务"),
    ("C2", "当我努力时，我能够取得预期的学习成果"),
    ("C3", "我觉得自己的学习能力在不断提升"),
    ("C4", "面对学习困难时，我有信心能够克服"),
    ("C5", "我觉得自己在班级中的学业表现是令人满意的"),
    ("C6", "我能够理解和掌握老师讲授的大部分内容"),
    ("C7", "我觉得自己在某些学科上有独特的优势"),
    ("C8", "当我完成一项学习任务时，我感受到成就感"),
    ("R1", "我觉得老师关心我的学习和成长"),
    ("R2", "我能够与同学建立良好的学习互助关系"),
    ("R3", "当我遇到学习困难时，有人愿意帮助我"),
    ("R4", "我觉得在学校中是被接纳和尊重的"),
    ("R5", "我与父母/监护人在学习方面有良好的沟通"),
    ("R6", "我觉得班级中的学习氛围是支持性的"),
    ("R7", "我能够与同伴分享学习中的喜悦和困惑"),
    ("R8", "我觉得自己的努力被老师和家长认可"),
    ("M1", "我对学习本身感兴趣，而不仅仅是为了考试"),
    ("M2", "我觉得学习新知识是一件令人愉快的事"),
    ("M3", "我愿意主动探索课本以外的知识"),
    ("M4", "我努力学习是为了实现自己的理想和目标"),
    ("M5", "我认为学习对自己的未来发展很重要"),
    ("M6", "我享受解决难题后带来的满足感"),
    ("M7", "即使没有外部奖励，我也愿意投入学习"),
    ("M8", "学习让我感到充实和有成就感"),
]

PERSONALITIES = {
    "0000": ("🦥", "休眠者", "学习啦？着火啦？先睡一觉。", "你信奉“养精蓄锐，伺机而动”。学习不是不努力，只是还没找到真正点燃你的那束光。你不容易被外界压力裹挟，内心有自己的节奏——问题在于，你常把“休息”和“逃避”混为一谈。试着每天先做5分钟再说，让行动带动意愿。"),
    "0001": ("🔥", "独狼", "你是一只孤独的荒原上的狼，离开了狼群。", "你内心炽热，渴望变强，但总觉得自己“不配”或“做不到”。你习惯把目标定得很高，却害怕暴露自己的脆弱。你需要的不是更多压力，而是一个接纳你现状的起点。请记住：真正的强者，是敢于承认自己也需要慢慢来的人。"),
    "0010": ("🫂", "抱抱猫", "猫猫需要很多抱抱和知识！", "你是典型的情感驱动型学习者——有人陪你，你就能发光；没人理你，你就缩成一团。你非常在意关系中的安全感，容易被鼓励或批评左右。建议你试着把“和谁一起学”和“学什么”分开，找到即使独自一人也能享受学习的小角落。"),
    "0011": ("☀️", "小太阳", "嗨喽！很高兴认识你！", "你是人群中的温暖存在，自带感染力。你不太在意成绩高低，更在乎氛围是否融洽。你的学习动力来自“和大家一起变好”，但也容易因为过度照顾他人而忽略自己的进度。试着每天留出30分钟“只为自己学”，你会发现自己比想象中更闪亮。"),
    "0100": ("🦅", "狙击手", "我需要绝对安静、绝对秩序和一点点爱。", "你极度专注，目标明确，追求高效和秩序。你讨厌被打扰，喜欢按自己的规则行事。你的优势是执行力极强，但缺点是不太擅长求助或协作。建议你偶尔放下“必须完美”的执念，允许自己犯错——有时候，80分的完成比100分的完美更有价值。"),
    "0101": ("🚀", "卷心菜战士", "卷但不菜，敢挑战你就来。", "你是典型的“小小卷心菜，绝不认输”型。你享受挑战，喜欢和别人比，但内心深处常常焦虑——怕自己不够好，怕被超越。你的韧性很强，但容易陷入“为了赢而学”的消耗战。试着把目标从“超过别人”换成“超过昨天的自己”，你会发现轻松很多。"),
    "0110": ("🐘", "？！强强！？", "一人得道，朋友同步青云。", "你很强，而且你知道自己很强。但你从不炫耀，反而喜欢拉别人一把。你是团队里的“隐藏大佬”，别人觉得难的事到你手里就变简单了。不过你偶尔会觉得孤独——因为很少有人能跟上你的节奏。试着找一两个真正能和你对话的伙伴，会让学习更有趣。"),
    "0111": ("💎", "六边形木桶", "那还说啥了，这是一个完人，完美的人。", "你是传说中的“全能选手”——各科均衡，情绪稳定，人缘也不错。你几乎没有短板，但也因为太均衡，缺乏一个让人印象深刻的“标签”。你不是天才，但你是最让人放心的存在。建议你试着深挖一个你真正热爱的领域，让自己从“全面”走向“深刻”。"),
    "1000": ("🎨", "艺术家", "试卷上是我肆意涂抹的生命力。", "你是自由的灵魂，讨厌被规则束缚。学习对你来说不是任务，而是表达自我的方式。你喜欢凭感觉走，灵感来了效率惊人，没灵感时一个字都写不出来。你的创造力是天赋，但你需要学会和“枯燥”共处——不是所有知识都能靠灵感获得，有些必须靠耐心。"),
    "1001": ("⛰️", "拓荒者", "我自行我的路，世界在脚下也在眼前。", "你是天生的开路者，不怕走别人没走过的路。你习惯靠自己摸索，即使摔倒也不愿轻易求助。你的独立很强，但有时会陷入“闭门造车”的困境。你需要的不是更努力，而是偶尔抬起头看看别人怎么走——借鉴不是抄袭，是让自己少走弯路。"),
    "1010": ("🦋", "灵感蝴蝶", "花儿相伴，灵光一现。", "你轻盈、灵动、充满好奇心。你的学习方式像蝴蝶采蜜——这里碰一下，那里试一下，兴趣广泛但不持久。你适合在碎片化的探索中学习，但缺点是容易浅尝辄止。建议你选一个最让你心动的方向，先深入一两个月，再决定要不要飞往下一朵花。"),
    "1011": ("🧊", "自适应AI", "仿生人会梦见电子羊吗？", "你像一台精密的学习机器——什么环境都能适应，什么内容都能消化。你情绪波动小，抗压能力强，但有时也让人觉得“太理性了，离人很远”。你不是没有感受，只是习惯把情绪关在门外。试着在学完之后问自己一句：“我开心吗？”——答案会让你更完整。"),
    "1100": ("👑", "高冷帝王", "我只统治我自己，如有异议请哈基咪。", "你是自己的统治者，不轻易被外界干扰。你自律、冷静、决策果断，但有时会显得疏离——不是冷漠，只是觉得解释太累。你有很强的内在秩序，但也容易因为“不合群”而错过一些有趣的可能性。试着偶尔放下“帝王架子”，你会发现平凡里也有宝藏。"),
    "1101": ("🧙", "大魔王", "凡人你们在说什么。", "你拥有可怕的专注力和执行力，一旦进入状态，谁也拦不住你。你不怕困难，甚至享受碾压难题的快感。但你的问题是——容易沉浸在自己的世界里，忘记外面还有别人。你需要的是一面镜子，看清自己也有局限和柔软的一面。"),
    "1110": ("🌈", "神仙下凡", "人生，易如反掌。", "你活得轻松、通透、举重若轻。你不太用力，却总能做得不错——这让别人羡慕，也让别人困惑。你其实不是不努力，只是不喜欢把“努力”挂在脸上。你的挑战在于：当事情真的变难时，你是否还能保持这份轻盈？有时候，承认“我现在有点难”也是一种勇气。"),
    "1111": ("⚡", "天选学星", "完美生物，学习界的神，百年难得一见。", "你是学习界的“天选之人”——天赋、自律、热爱、方法，你全都占齐了。你不是没有瓶颈，只是总能找到突破的方向。你是大家仰望的对象，但也因为太闪耀，有时会让人不敢靠近。请记住：成为神不是目标，成为人、成为自己、成为温暖的存在，才是更高阶的修行。"),
}

ACTIVITY_OPTIONS = [
    "心理辅导/焦虑缓解",
    "职业生涯规划",
    "学科方法/备考策略",
    "专业知识交流及AI使用",
    "志愿者励志故事",
    "沟通表达能力提升技巧",
    "其他",
]


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    answer_columns = ",\n".join(f"q{i} INTEGER NOT NULL" for i in range(1, 33))
    with get_db() as db:
        db.execute(
            f"""
            CREATE TABLE IF NOT EXISTS responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                nickname TEXT NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT NOT NULL,
                grade TEXT NOT NULL,
                is_jmg_student TEXT NOT NULL,
                {answer_columns},
                activities TEXT NOT NULL,
                activity_other TEXT NOT NULL DEFAULT '',
                personality_code TEXT NOT NULL
            )
            """
        )


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(24)
    return session["csrf_token"]


def validate_csrf():
    submitted = request.form.get("csrf_token", "")
    if not submitted or not secrets.compare_digest(submitted, session.get("csrf_token", "")):
        abort(400, description="表单已过期，请刷新页面后重试。")


app.jinja_env.globals["csrf_token"] = csrf_token


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_dashboard"))
        return view(*args, **kwargs)

    return wrapped


@app.route("/")
def index():
    if request.cookies.get(COMPLETION_COOKIE) == "1":
        if session.get("response_id"):
            return redirect(url_for("result"))
        return render_template("index.html", already_submitted=True)
    return render_template(
        "index.html",
        already_submitted=False,
        questions=QUESTIONS,
        activity_options=ACTIVITY_OPTIONS,
    )


@app.post("/submit")
def submit():
    if request.cookies.get(COMPLETION_COOKIE) == "1":
        return redirect(url_for("result" if session.get("response_id") else "index"))
    validate_csrf()
    nickname = request.form.get("nickname", "").strip()
    age_text = request.form.get("age", "").strip()
    gender = request.form.get("gender", "")
    grade = request.form.get("grade", "")
    is_jmg_student = request.form.get("is_jmg_student", "")

    try:
        age = int(age_text)
    except ValueError:
        age = 0

    valid_genders = {"男", "女", "其他", "不愿透露"}
    valid_grades = {"初一", "初二", "初三", "高一", "高二", "高三", "已毕业"}
    if not nickname or len(nickname) > 30 or not 6 <= age <= 100:
        flash("请填写有效的昵称和年龄。", "error")
        return redirect(url_for("index"))
    if gender not in valid_genders or grade not in valid_grades or is_jmg_student not in {"是", "否"}:
        flash("请完整填写个人信息。", "error")
        return redirect(url_for("index"))

    answers = []
    for i in range(1, 33):
        try:
            score = int(request.form.get(f"q{i}", ""))
        except ValueError:
            score = 0
        if score not in range(1, 6):
            flash(f"第 {i} 题尚未作答，请重新检查。", "error")
            return redirect(url_for("index"))
        answers.append(score)

    selected_activities = request.form.getlist("activities")
    if not selected_activities or any(item not in ACTIVITY_OPTIONS for item in selected_activities):
        flash("请至少选择一种希望参加的活动。", "error")
        return redirect(url_for("index"))
    activity_other = request.form.get("activity_other", "").strip()
    if "其他" in selected_activities and not activity_other:
        flash("选择“其他”后，请填写具体活动。", "error")
        return redirect(url_for("index"))
    if len(activity_other) > 200:
        flash("其他活动内容请控制在 200 字以内。", "error")
        return redirect(url_for("index"))

    dimension_averages = [sum(answers[i : i + 8]) / 8 for i in range(0, 32, 8)]
    personality_code = "".join("1" if average > 3 else "0" for average in dimension_averages)
    activity_field = "、".join(selected_activities)

    columns = [
        "created_at", "nickname", "age", "gender", "grade", "is_jmg_student",
        *[f"q{i}" for i in range(1, 33)],
        "activities", "activity_other", "personality_code",
    ]
    values = [
        datetime.now().astimezone().isoformat(timespec="seconds"),
        nickname, age, gender, grade, is_jmg_student,
        *answers, activity_field, activity_other, personality_code,
    ]
    placeholders = ", ".join("?" for _ in values)
    with get_db() as db:
        cursor = db.execute(
            f"INSERT INTO responses ({', '.join(columns)}) VALUES ({placeholders})",
            values,
        )
        response_id = cursor.lastrowid

    session["response_id"] = response_id
    session.pop("csrf_token", None)
    response = redirect(url_for("result"))
    response.set_cookie(
        COMPLETION_COOKIE,
        "1",
        max_age=COMPLETION_COOKIE_MAX_AGE,
        httponly=True,
        samesite="Lax",
    )
    return response


@app.route("/result")
def result():
    response_id = session.get("response_id")
    if not response_id:
        return redirect(url_for("index"))
    with get_db() as db:
        row = db.execute(
            "SELECT nickname, personality_code FROM responses WHERE id = ?", (response_id,)
        ).fetchone()
    if row is None:
        session.pop("response_id", None)
        return redirect(url_for("index"))
    emoji, name, description, interpretation = PERSONALITIES[row["personality_code"]]
    return render_template(
        "result.html",
        nickname=row["nickname"],
        emoji=emoji,
        name=name,
        description=description,
        interpretation=interpretation,
    )


@app.route("/admin-dashboard", methods=["GET", "POST"])
def admin_dashboard():
    if request.method == "POST":
        validate_csrf()
        if secrets.compare_digest(request.form.get("password", ""), ADMIN_PASSWORD):
            session["is_admin"] = True
            session.pop("csrf_token", None)
            return redirect(url_for("admin_dashboard"))
        flash("管理员密码错误。", "error")

    if not session.get("is_admin"):
        return render_template("admin.html", authenticated=False)

    with get_db() as db:
        total = db.execute("SELECT COUNT(*) FROM responses").fetchone()[0]
        stats = []
        for index, (code, text) in enumerate(QUESTIONS, start=1):
            counts = {
                score: db.execute(
                    f"SELECT COUNT(*) FROM responses WHERE q{index} = ?", (score,)
                ).fetchone()[0]
                for score in range(1, 6)
            }
            stats.append({"number": index, "code": code, "text": text, "counts": counts})
    return render_template("admin.html", authenticated=True, total=total, stats=stats)


@app.post("/admin-logout")
@admin_required
def admin_logout():
    validate_csrf()
    session.pop("is_admin", None)
    session.pop("csrf_token", None)
    return redirect(url_for("admin_dashboard"))


@app.route("/admin-download")
@admin_required
def admin_download():
    with get_db() as db:
        rows = db.execute("SELECT * FROM responses ORDER BY id").fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    headers = [
        "ID", "提交时间", "昵称", "年龄", "性别", "年级", "是否剑门关高级中学同学",
        *[f"{code}：{text}" for code, text in QUESTIONS],
        "活动选择", "其他活动文字", "人格编码",
    ]
    writer.writerow(headers)
    for row in rows:
        writer.writerow(list(row))

    csv_bytes = ("\ufeff" + output.getvalue()).encode("utf-8")
    filename = f"questionnaire-{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"
    return Response(
        csv_bytes,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080))) port=int(os.environ.get("PORT", 8080)))
