# -*- coding: utf-8 -*-
"""
Render 無料プラン向け 最小構成「レシピ投稿ミニアプリ」
- Flask 3 + SQLAlchemy 2 + Render PostgreSQL（DATABASE_URL）
- 分割構成版（app.py / templates / static）
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
# 環境変数ロード
# ==============================
load_dotenv()

# ==============================
# DB接続設定
# ==============================
def get_database_url() -> Optional[str]:
    url = os.environ.get("DATABASE_URL")
    if url and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    return url

DATABASE_URL = get_database_url()
engine = create_engine(DATABASE_URL, pool_pre_ping=True) if DATABASE_URL else None


# ==============================
# モデル定義
# ==============================
class Base(DeclarativeBase):
    pass


class Recipe(Base):
    __tablename__ = "recipes"
    __table_args__ = (CheckConstraint("minutes >= 1", name="ck_recipes_minutes_ge_1"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


if engine is not None:
    Base.metadata.create_all(engine)


# ==============================
# Flask アプリ設定
# ==============================
app = Flask(__name__)


def _to_bool_env(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


@app.route("/", methods=["GET", "POST"])
def index():
    errors: List[str] = []
    form_values = {"title": "", "minutes": "", "description": ""}

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        minutes_raw = (request.form.get("minutes") or "").strip()
        description = (request.form.get("description") or "").strip()

        form_values.update({"title": title, "minutes": minutes_raw, "description": description})

        # --- バリデーション ---
        if not title:
            errors.append("タイトルは必須です。")
        if len(title) > 200:
            errors.append("タイトルは200文字以内で入力してください。")

        minutes_val: Optional[int] = None
        if not minutes_raw:
            errors.append("所要分数は必須です。")
        else:
            try:
                minutes_val = int(minutes_raw)
                if minutes_val < 1:
                    errors.append("所要分数は1以上の整数で入力してください。")
            except ValueError:
                errors.append("所要分数は整数で入力してください。")

        if engine is None:
            errors.append("データベースが未設定のため保存できません。DATABASE_URL を設定してください。")

        if not errors and engine is not None and minutes_val is not None:
            try:
                with Session(engine) as session:
                    session.add(Recipe(title=title, minutes=minutes_val, description=description or None))
                    session.commit()
                return redirect(url_for("index"))
            except Exception:
                errors.append("保存中にエラーが発生しました。")

    recipes: List[Recipe] = []
    if engine is not None:
        try:
            with Session(engine) as session:
                recipes = session.query(Recipe).order_by(Recipe.created_at.desc(), Recipe.id.desc()).all()
        except Exception:
            recipes = []

    port = int(os.environ.get("PORT", "8000"))
    debug = _to_bool_env(os.environ.get("DEBUG"), default=False)
    return render_template(
        "index.html",
        errors=errors,
        recipes=recipes,
        debug=str(debug),
        port=port,
        db_ready=(engine is not None),
        form_values=form_values,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    debug = _to_bool_env(os.environ.get("DEBUG"), default=False)
    app.run(host="0.0.0.0", port=port, debug=debug)
