# -*- coding: utf-8 -*-
"""
レシピ投稿ミニアプリ（Flask + SQLAlchemy）
- 左カラム：新規投稿フォーム
- 右カラム：レシピ一覧（削除・編集モーダル付き）
"""

from __future__ import annotations
import os
from datetime import datetime
from typing import Optional, List
from dotenv import load_dotenv
from flask import Flask, request, redirect, url_for, render_template
from sqlalchemy import create_engine, String, Integer, Text, DateTime, CheckConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

# ==============================
# 環境変数
# ==============================
load_dotenv()

def get_database_url() -> Optional[str]:
    """Render 用 DATABASE_URL 対応（postgres:// → postgresql+psycopg2://）"""
    url = os.environ.get("DATABASE_URL")
    if url and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    return url

DATABASE_URL = get_database_url()
engine = create_engine(DATABASE_URL, pool_pre_ping=True) if DATABASE_URL else None

# ==============================
# モデル
# ==============================
class Base(DeclarativeBase):
    pass

class Recipe(Base):
    __tablename__ = "recipes"
    __table_args__ = (CheckConstraint("minutes >= 1", name="ck_recipes_minutes_ge_1"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

if engine is not None:
    Base.metadata.create_all(engine)

# ==============================
# Flask アプリ本体
# ==============================
app = Flask(__name__)

def _to_bool_env(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}

# ==============================
# 一覧 & 投稿処理
# ==============================
@app.route("/", methods=["GET", "POST"])
def index():
    errors: List[str] = []
    form_values = {"title": "", "minutes": "", "description": ""}

    # 投稿処理
    if request.method == "POST" and request.form.get("_action") == "create":
        title = (request.form.get("title") or "").strip()
        minutes_raw = (request.form.get("minutes") or "").strip()
        description = (request.form.get("description") or "").strip()
        form_values.update({"title": title, "minutes": minutes_raw, "description": description})

        minutes_val: Optional[int] = None
        if not title:
            errors.append("タイトルは必須です。")
        elif len(title) > 200:
            errors.append("タイトルは200文字以内で入力してください。")

        if not minutes_raw:
            errors.append("所要分数は必須です。")
        else:
            try:
                minutes_val = int(minutes_raw)
                if minutes_val < 1:
                    errors.append("所要分数は1以上で入力してください。")
            except ValueError:
                errors.append("所要分数は整数で入力してください。")

        if engine is None:
            errors.append("データベースが未設定です。")

        if not errors and engine and minutes_val is not None:
            try:
                with Session(engine) as session:
                    recipe = Recipe(title=title, minutes=minutes_val, description=description or None)
                    session.add(recipe)
                    session.commit()
                return redirect(url_for("index"))
            except Exception:
                errors.append("保存中にエラーが発生しました。")

    # 一覧取得
    recipes: List[Recipe] = []
    if engine is not None:
        with Session(engine) as session:
            recipes = session.query(Recipe).order_by(Recipe.created_at.desc(), Recipe.id.desc()).all()

    return render_template(
        "index.html",
        errors=errors,
        recipes=recipes,
        debug=_to_bool_env(os.environ.get("DEBUG"), default=False),
        port=int(os.environ.get("PORT", "8000")),
        db_ready=(engine is not None),
        form_values=form_values,
    )

# ==============================
# 削除処理
# ==============================
@app.route("/delete/<int:recipe_id>", methods=["POST"])
def delete_recipe(recipe_id: int):
    if not engine:
        return redirect(url_for("index"))
    with Session(engine) as session:
        recipe = session.get(Recipe, recipe_id)
        if recipe:
            session.delete(recipe)
            session.commit()
    return redirect(url_for("index"))

# ==============================
# 編集処理
# ==============================
@app.route("/edit/<int:recipe_id>", methods=["POST"])
def edit_recipe(recipe_id: int):
    if not engine:
        return redirect(url_for("index"))

    title = (request.form.get("edit_title") or "").strip()
    minutes_raw = (request.form.get("edit_minutes") or "").strip()
    description = (request.form.get("edit_description") or "").strip()
    try:
        minutes_val = int(minutes_raw)
    except ValueError:
        minutes_val = None

    if not title or not minutes_val or minutes_val < 1:
        return redirect(url_for("index"))

    with Session(engine) as session:
        recipe = session.get(Recipe, recipe_id)
        if recipe:
            recipe.title = title
            recipe.minutes = minutes_val
            recipe.description = description or None
            session.commit()

    return redirect(url_for("index"))

# ==============================
# アプリ起動
# ==============================
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        debug=_to_bool_env(os.environ.get("DEBUG"), default=False),
    )
