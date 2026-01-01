"""
このファイルは、最初の画面読み込み時にのみ実行される初期化処理が記述されたファイルです。
"""

############################################################
# ライブラリの読み込み
############################################################
import os
import logging
from logging.handlers import TimedRotatingFileHandler
from uuid import uuid4
import sys
import unicodedata
from dotenv import load_dotenv
import streamlit as st
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
import utils
import constants as ct


############################################################
# 設定関連
############################################################
load_dotenv()


############################################################
# 関数定義
############################################################

def initialize():
    """
    画面読み込み時に実行する初期化処理
    """
    # APIキーを確保（Streamlit secrets -> 環境変数 -> .env -> ローカル入力 の順）
    ensure_api_key()

    # 初期化データの用意
    initialize_session_state()
    # ログ出力用にセッションIDを生成
    initialize_session_id()
    # ログ出力の設定
    initialize_logger()
    # RAGのRetrieverを作成
    initialize_retriever()


def initialize_logger():
    """
    ログ出力の設定
    """
    os.makedirs(ct.LOG_DIR_PATH, exist_ok=True)
    
    logger = logging.getLogger(ct.LOGGER_NAME)

    if logger.hasHandlers():
        return

    log_handler = TimedRotatingFileHandler(
        os.path.join(ct.LOG_DIR_PATH, ct.LOG_FILE),
        when="D",
        encoding="utf8"
    )
    formatter = logging.Formatter(
        f"[%(levelname)s] %(asctime)s line %(lineno)s, in %(funcName)s, session_id={st.session_state.session_id}: %(message)s"
    )
    log_handler.setFormatter(formatter)
    logger.setLevel(logging.INFO)
    logger.addHandler(log_handler)


def initialize_session_id():
    """
    セッションIDの作成
    """
    if "session_id" not in st.session_state:
        st.session_state.session_id = uuid4().hex


def initialize_session_state():
    """
    初期化データの用意
    """
    if "messages" not in st.session_state:
        st.session_state.messages = []


def initialize_retriever():
    """
    Retrieverを作成
    """
    # Retriever作成前にAPIキーがセットされていることを想定
    logger = logging.getLogger(ct.LOGGER_NAME)

    if "retriever" in st.session_state:
        return
    
    loader = CSVLoader(ct.RAG_SOURCE_PATH, encoding="utf-8")
    docs = loader.load()

    # OSがWindowsの場合、Unicode正規化と、cp932（Windows用の文字コード）で表現できない文字を除去
    for doc in docs:
        doc.page_content = adjust_string(doc.page_content)
        for key in doc.metadata:
            doc.metadata[key] = adjust_string(doc.metadata[key])

    docs_all = []
    for doc in docs:
        docs_all.append(doc.page_content)

    embeddings = OpenAIEmbeddings()
    db = Chroma.from_documents(docs, embedding=embeddings)

    retriever = db.as_retriever(search_kwargs={"k": ct.TOP_K})

    bm25_retriever = BM25Retriever.from_texts(
        docs_all,
        preprocess_func=utils.preprocess_func,
        k=ct.TOP_K
    )
    ensemble_retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, retriever],
        weights=ct.RETRIEVER_WEIGHTS
    )

    st.session_state.retriever = ensemble_retriever


def ensure_api_key(key_name: str = "OPENAI_API_KEY", prompt_label: str = "OpenAI API Key") -> str:
    """
    APIキーを取得して環境変数に設定するユーティリティ。

    取得順序:
    1. `st.secrets[key_name]` (Streamlit Cloudなど)
    2. 環境変数 `os.environ[key_name]`
    3. `.env` ファイル (既に `load_dotenv()` を呼んでいる)
    4. ローカル実行時は `st.text_input` による入力（セッションのみ）

    見つかった場合は `os.environ[key_name]` に設定し、`openai.api_key` が利用可能であればそちらにも設定します。
    """
    # 1. Streamlit secrets
    key_val = None
    try:
        if hasattr(st, "secrets") and st.secrets.get(key_name):
            key_val = st.secrets.get(key_name)
    except Exception:
        key_val = None

    # 2/3. 環境変数 / .env
    if not key_val:
        key_val = os.environ.get(key_name)

    # 4. ローカルでの手動入力（UIを通じて）
    if not key_val:
        try:
            st.warning("APIキーが設定されていません。ローカル実行の場合は入力してください（セッション内のみ保存されます）。")
            entered = st.text_input(prompt_label, type="password", key="__api_key_input")
            if entered:
                key_val = entered
                os.environ[key_name] = entered
        except Exception:
            # st が UI 表示できない状況ではスキップ
            pass

    # 環境変数に反映
    if key_val:
        os.environ.setdefault(key_name, key_val)
        try:
            import openai
            openai.api_key = key_val
        except Exception:
            pass

    return key_val


def adjust_string(s):
    """
    Windows環境でRAGが正常動作するよう調整
    
    Args:
        s: 調整を行う文字列
    
    Returns:
        調整を行った文字列
    """
    # 調整対象は文字列のみ
    if type(s) is not str:
        return s

    # OSがWindowsの場合、Unicode正規化と、cp932（Windows用の文字コード）で表現できない文字を除去
    if sys.platform.startswith("win"):
        s = unicodedata.normalize('NFC', s)
        s = s.encode("cp932", "ignore").decode("cp932")
        return s
    
    # OSがWindows以外の場合はそのまま返す
    return s