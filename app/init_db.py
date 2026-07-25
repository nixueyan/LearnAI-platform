from .database import engine
from .models import Base, Subject, Chapter, Question, Subsection, Resource
from sqlalchemy.orm import Session
import json

subjects = [
    {
        "name": "高等数学",
        "category": "理工",
        "description": "面向大学生的高等数学课程，覆盖函数、导数、积分、级数等核心章节。",
        "cover_image": "high_math.jpg",
        "chapters": [
            (1, "函数与极限", "函数的概念与性质、数列极限、函数极限、连续性。"),
            (2, "导数与微分", "导数的概念、求导法则、高阶导数、微分。"),
            (3, "微分中值定理与导数应用", "中值定理、洛必达法则、函数的单调性与极值、曲线的凹凸性。"),
            (4, "不定积分", "不定积分概念、换元积分法、分部积分法。"),
            (5, "定积分", "定积分概念、微积分基本定理、定积分应用。"),
            (6, "多元函数微分学", "多元函数概念、偏导数、全微分。"),
            (7, "重积分", "二重积分、三重积分。"),
            (8, "级数", "数项级数、幂级数、傅里叶级数。"),
        ],
    },
    {
        "name": "线性代数",
        "category": "理工",
        "description": "学习矩阵、向量空间、线性变换与特征值理论。",
        "cover_image": "linear_algebra.jpg",
        "chapters": [
            (1, "行列式", "二阶与三阶行列式、n阶行列式的定义与性质、行列式按行展开。"),
            (2, "矩阵及其运算", "矩阵的概念、矩阵的加减乘、转置、方阵的行列式。"),
            (3, "矩阵的初等变换与线性方程组", "初等变换、矩阵的秩、线性方程组的解。"),
            (4, "向量组的线性相关性", "向量组的线性组合、线性相关与无关、向量组的秩。"),
            (5, "相似矩阵及二次型", "特征值与特征向量、相似矩阵、二次型标准化。"),
        ],
    },
    {
        "name": "概率论与数理统计",
        "category": "理工",
        "description": "学习随机事件、概率分布、数字特征与统计推断基础。",
        "cover_image": "probability.jpg",
        "chapters": [
            (1, "随机事件与概率", "样本空间、事件关系与运算、古典概型、条件概率。"),
            (2, "随机变量及其分布", "离散型与连续型随机变量、分布函数、常见分布。"),
            (3, "多维随机变量", "联合分布、边缘分布、随机变量的独立性。"),
            (4, "数字特征", "数学期望、方差、协方差与相关系数。"),
            (5, "大数定律与中心极限定理", "切比雪夫不等式、大数定律、中心极限定理。"),
            (6, "样本与抽样分布", "总体与样本、统计量、三大抽样分布。"),
        ],
    },
]

# 按「学科 -> 章节 order -> 小节标题列表」组织，避免线代/概率的章节
# 错误命中高数的小节标题（旧实现用全局序号 1-19 当 key，导致错位）。
SECTION_DEFS = {
    "高等数学": {
        1: ["函数的概念与性质", "数列极限", "函数极限", "连续性"],
        2: ["导数的概念", "求导法则", "高阶导数", "微分"],
        3: ["中值定理", "洛必达法则", "函数的单调性与极值", "曲线的凹凸性"],
        4: ["不定积分概念", "换元积分法", "分部积分法"],
        5: ["定积分概念", "微积分基本定理", "定积分应用"],
        6: ["多元函数概念", "偏导数", "全微分"],
        7: ["二重积分", "三重积分"],
        8: ["数项级数", "幂级数", "傅里叶级数"],
    },
    "线性代数": {
        1: ["二阶与三阶行列式", "全排列与逆序数", "n阶行列式的定义", "行列式的性质", "行列式按行展开"],
        2: ["矩阵的概念", "矩阵的运算", "逆矩阵", "分块矩阵"],
        3: ["矩阵的初等变换", "矩阵的秩", "线性方程组的解"],
        4: ["向量组的线性组合", "线性相关与无关", "向量组的秩", "向量空间"],
        5: ["特征值与特征向量", "相似矩阵", "对称矩阵的对角化", "二次型"],
    },
    "概率论与数理统计": {
        1: ["样本空间与随机事件", "概率的定义与性质", "古典概型", "条件概率与独立性"],
        2: ["随机变量的概念", "离散型随机变量", "分布函数", "连续型随机变量", "常见分布"],
        3: ["二维随机变量", "边缘分布", "条件分布", "独立性"],
        4: ["数学期望", "方差", "协方差与相关系数", "矩"],
        5: ["大数定律", "中心极限定理"],
        6: ["总体与样本", "统计量", "抽样分布"],
    },
}

def _sub_content(title, ch_title):
    return "## " + title + "\n\n本节为「" + ch_title + "」的核心内容，包含定义、定理推导与典型例题。\n\n> 完整讲解可通过学科详情页的 AI 生成功能获取。"

ALL_QUESTIONS = {}

# 题目数据从 questions.json 加载
import os, json as _json
_qfile = os.path.join(os.path.dirname(__file__), "..", "questions.json")
with open(_qfile, "r", encoding="utf-8") as _f:
    ALL_QUESTIONS = {int(k): v for k, v in _json.load(_f).items()}

# 目前只有「高等数学」有真实题库（questions.json 键 1-8），
# 其余学科保持为空（不串用高数题目，避免数据错位）。
QUESTIONS_BY_SUBJECT = {"高等数学": ALL_QUESTIONS}

# 小节内容从 subsections.json 加载
_sfile = os.path.join(os.path.dirname(__file__), "..", "subsections.json")
SECTION_CONTENT_MAP = {}
if os.path.exists(_sfile):
    with open(_sfile, "r", encoding="utf-8") as _f:
        SECTION_CONTENT_MAP = {int(k): v for k, v in _json.load(_f).items()}


def init_data():
    Base.metadata.create_all(bind=engine)
    db = Session(bind=engine)
    try:
        if db.query(Subject).count() == 0:
            # 干净初始化：先清掉可能存在的孤儿数据，再整体重建
            db.query(Subsection).delete()
            db.query(Question).delete()
            db.query(Resource).delete()
            db.query(Chapter).delete()
            db.query(Subject).delete()
            db.commit()

            for subject_data in subjects:
                subject = Subject(
                    name=subject_data["name"],
                    category=subject_data["category"],
                    description=subject_data["description"],
                    cover_image=subject_data["cover_image"],
                )
                db.add(subject)
                db.flush()
                for order, title, summary in subject_data["chapters"]:
                    chapter = Chapter(subject_id=subject.id, title=title, order=order, summary=summary)
                    db.add(chapter)
                    db.flush()
                    # 小节：按「学科 + 章节 order」映射，避免线代/概率错位成高数标题
                    sec_defs = SECTION_DEFS.get(subject_data["name"], {}).get(order, [])
                    for i, sec_title in enumerate(sec_defs):
                        db.add(Subsection(chapter_id=chapter.id, title=sec_title, content=_sub_content(sec_title, title), order=i+1, is_published=True))
                    # 题库：仅当前学科有题目时使用，绝不串用其他学科
                    for q_data in QUESTIONS_BY_SUBJECT.get(subject_data["name"], {}).get(order, []):
                        qtype, diff, qcontent, opts, ans, expl = q_data
                        db.add(Question(chapter_id=chapter.id, question_type=qtype, difficulty=diff, content=qcontent, options=opts if opts else None, answer=ans, explanation=expl if expl else None))
            db.commit()
            # 用 subsections.json 覆盖真实 AI 内容（按小节 id 映射，高数小节 id 1-26）
            if SECTION_CONTENT_MAP:
                for sub in db.query(Subsection).all():
                    if sub.id in SECTION_CONTENT_MAP:
                        sub.content = SECTION_CONTENT_MAP[sub.id]
                db.commit()
                print(f"已加载 {len(SECTION_CONTENT_MAP)} 个小节的完整教学内容")
            # 预置公共资源
            _rfile = os.path.join(os.path.dirname(__file__), "..", "resources.json")
            if os.path.exists(_rfile):
                with open(_rfile, "r", encoding="utf-8") as _f:
                    _resources = _json.load(_f)
                for rd in _resources:
                    db.add(Resource(subject_id=rd["subject_id"], chapter_id=rd["chapter_id"],
                        title=rd["title"], resource_type=rd["resource_type"],
                        content=rd["content"], is_public=True, view_count=0))
                db.commit()
                print(f"已加载 {len(_resources)} 份公共资源")
            print("数据库已初始化（含学科、章节、小节和题库）。")
        else:
            print("数据库已有数据，跳过初始化。")
    finally:
        db.close()

if __name__ == "__main__":
    init_data()
    print("完成。")
