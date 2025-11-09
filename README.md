# レシピ投稿ミニアプリ（Flask + SQLAlchemy + Render PostgreSQL）

単一ファイル `app.py` で **一覧表示 + 新規追加** ができる最小構成のデモです。Render の無料プランで公開できます。

## 技術スタック
- Flask==3.0.3
- SQLAlchemy==2.0.36
- psycopg2-binary==2.9.9
- python-dotenv==1.0.1
- （任意）gunicorn==22.0.0

## データモデル
- テーブル: `recipes`
- カラム:
  - `id` (PK, autoincrement)
  - `title` (必須, 文字列, 上限200)
  - `minutes` (必須, 整数, 1以上)
  - `description` (任意, テキスト)
  - `created_at` (作成日時, 既定: 現在時刻 / UTC想定)
- 起動時に `Base.metadata.create_all(engine)` で自動作成。

## 使い方（アプリ）
トップ `/` で以下を実行できます。
- 既存レシピ一覧（新しい順）
- 新規追加フォーム（タイトル必須 / 所要分数: 整数かつ1以上 / 説明は任意）
- 送信成功時は同ページにリダイレクト（PRG）

---

## Render セットアップ手順

1. **GitHubへプッシュ**  
   リポジトリに以下を含めて push:
