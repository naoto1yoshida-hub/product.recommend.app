"""
このファイルは、画面表示に特化した関数定義のファイルです。
"""

############################################################
# ライブラリの読み込み
############################################################
import logging
import streamlit as st
import constants as ct
import csv
import difflib
from pathlib import Path


############################################################
# 関数定義
############################################################

def display_app_title():
    """
    タイトル表示
    """
    st.markdown(f"## {ct.APP_NAME}")


def display_initial_ai_message():
    """
    AIメッセージの初期表示
    """
    with st.chat_message("assistant", avatar=ct.AI_ICON_FILE_PATH):
        st.markdown("こちらは対話型の商品レコメンド生成AIアプリです。「こんな商品が欲しい」という情報・要望を画面下部のチャット欄から送信いただければ、おすすめの商品をレコメンドいたします。")
        st.markdown("**入力例**")
        st.info("""
        - 「長時間使える、高音質なワイヤレスイヤホン」
        - 「机のライト」
        - 「USBで充電できる加湿器」
        """)


def display_conversation_log():
    """
    会話ログの一覧表示
    """
    for message in st.session_state.messages:
        if message["role"] == "user":
            with st.chat_message("user", avatar=ct.USER_ICON_FILE_PATH):
                st.markdown(message["content"])
        else:
            with st.chat_message("assistant", avatar=ct.AI_ICON_FILE_PATH):
                display_product(message["content"])


def display_product(result):
    """
    商品情報の表示

    Args:
        result: LLMからの回答
    """
    logger = logging.getLogger(ct.LOGGER_NAME)

    def _get_stock_status_by_id(product_id: str) -> str:
        """CSVから商品IDに対応する`stock_status`を返す。見つからなければ空文字を返す。"""
        csv_path = Path(__file__).resolve().parents[0] / "data" / "products.csv"
        try:
            with csv_path.open(encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if str(row.get("id")) == str(product_id):
                        return row.get("stock_status", "")
        except Exception:
            return ""
        return ""

    # LLMレスポンスのテキストを辞書に変換
    product_lines = result[0].page_content.split("\n")
    product = {item.split(": ")[0]: item.split(": ")[1] for item in product_lines}

    # 在庫状況を取得（LLM出力に含まれなければCSVから参照）
    stock_status = product.get("stock_status", "")
    if not stock_status:
        stock_status = _get_stock_status_by_id(product.get("id", ""))

    st.markdown("以下の商品をご提案いたします。")

    # 「商品名」と「価格」
    st.success(f"""
            商品名：{product['name']}（商品ID: {product['id']}）\n
            価格：{product['price']}
    """)

    # 「商品カテゴリ」と「メーカー」と「ユーザー評価」
    st.code(f"""
        商品カテゴリ：{product['category']}\n
        メーカー：{product['maker']}\n
        評価：{product['score']}({product['review_number']}件)
    """, language=None, wrap_lines=True)

    # 商品画像
    st.image(f"images/products/{product['file_name']}", width=400)

    # 商品説明
    st.code(product['description'], language=None, wrap_lines=True)

    # おすすめ対象ユーザー
    def _read_csv_rows():
        csv_path = Path(__file__).resolve().parents[0] / "data" / "products.csv"
        try:
            with csv_path.open(encoding="utf-8") as f:
                reader = csv.DictReader(f)
                return list(reader)
        except Exception:
            return []

    def _get_stock_status_by_id(product_id: str) -> str:
        """CSVから商品IDに対応する`stock_status`を返す。見つからなければ空文字を返す。"""
        for row in _read_csv_rows():
            if str(row.get("id")) == str(product_id):
                return row.get("stock_status", "")
        return ""

    def _find_best_row_by_name(name: str, threshold: float = 0.60):
        """名前に対して部分一致→類似度順で最良行を返す。見つからなければ None を返す。

        1) 完全一致
        2) 部分一致（部分文字列）
        3) difflib の類似度が閾値以上
        """
        if not name:
            return None
        rows = _read_csv_rows()
        name_lower = name.strip().lower()

        # 1) 完全一致
        for r in rows:
            if str(r.get("name", "")).strip().lower() == name_lower:
                return r

        # 2) 部分一致（部分文字列）
        for r in rows:
            if name_lower in str(r.get("name", "")).strip().lower():
                return r

        # 3) 類似度スコアで最良行を選択
        best = None
        best_score = 0.0
        for r in rows:
            rname = str(r.get("name", "")).strip().lower()
            if not rname:
                continue
            score = difflib.SequenceMatcher(None, name_lower, rname).ratio()
            if score > best_score:
                best_score = score
                best = r

        if best and best_score >= threshold:
            return best
        return None

    if stock_status == ct.STOCK_OUT_LABEL:
        st.markdown(
            f"""
            <div style="border:4px solid #d9534f; background:#ffecec; padding:16px; color:#7a1a1a; border-radius:6px; margin:12px 0;">
                <span style="font-weight:700; margin-right:8px;">{ct.STOCK_ICON_OUT}</span>
                申し訳ございませんが、本商品は在庫切れとなっております。入荷までもうしばらくお待ちください。
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 商品ページのリンク
    st.link_button("商品ページを開く", type="primary", use_container_width=True, url="https://google.com")