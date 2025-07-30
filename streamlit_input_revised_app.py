import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw
import os
import glob
from streamlit_image_coordinates import streamlit_image_coordinates
import csv
import io

# --- 定数と定義 ---
BASEBALL_FIELD_IMG = "baseballfield.jpg"
IMAGE_SIZE = (750, 750)

PITCH_TYPE_COLORS = {
    "ストレート": "red",
    "スライダー": "blue",
    "チェンジアップ": "yellow",
    "フォーク": "orange",
    "カットボール": "skyblue",
    "ツーシーム": "pink",
    "カーブ": "purple",
}
HIT_TYPE_SHAPES = {
    "ゴロ": "ellipse",
    "フライ": "rectangle",
    "ライナー": "triangle",
}

# --- セッションステートの初期化 ---
if "click_coords" not in st.session_state:
    st.session_state.click_coords = []
if "marker_data" not in st.session_state:
    st.session_state.marker_data = []
if "last_click_coords" not in st.session_state:
    st.session_state.last_click_coords = None


# --- ヘルパー関数 ---
def draw_shape(draw_obj, shape, x, y, size, color):
    h_size = size / 2
    if shape == "ellipse":
        draw_obj.ellipse(
            (x - h_size, y - h_size, x + h_size, y + h_size), fill=color, outline=color
        )
    elif shape == "rectangle":
        draw_obj.rectangle(
            (x - h_size, y - h_size, x + h_size, y + h_size), fill=color, outline=color
        )
    elif shape == "triangle":
        points = [(x, y - h_size), (x - h_size, y + h_size), (x + h_size, y + h_size)]
        draw_obj.polygon(points, fill=color, outline=color)


# --- Streamlit アプリケーション ---
st.set_page_config(layout="wide")
st.title("⚾ 打球分析アプリ - データ入力")

# ベース画像の読み込み
try:
    base_img = Image.open(BASEBALL_FIELD_IMG).resize(IMAGE_SIZE)
except FileNotFoundError:
    st.error(
        f"{BASEBALL_FIELD_IMG}が見つかりません。アプリと同じフォルダに配置してください。"
    )
    st.stop()

# 2カラムレイアウト
col1, col2 = st.columns([1, 2])

# col1: 操作パネル
with col1:
    st.header("操作パネル")

    all_csv_files = glob.glob("*.csv")
    team_files = sorted([f for f in all_csv_files if not f.endswith("_data.csv")])

    selected_team_file = st.selectbox("チームを選択", team_files)

    selected_player = None
    if selected_team_file:
        try:
            roster_df = pd.read_csv(selected_team_file, encoding="cp932", header=None)
            player_list = roster_df.iloc[:, 0].tolist()
            selected_player = st.selectbox("選手を選択", player_list)
        except Exception as e:
            st.error(f"{selected_team_file}の読み込みに失敗しました: {e}")

    if st.button("マーカーをクリア"):
        st.session_state.click_coords = []
        st.session_state.marker_data = []
        st.session_state.last_click_coords = None

    opponents = st.selectbox("対戦相手", ["京大以外", "京大"])
    pitcherLR = st.selectbox("対右or対左", ["右", "左"])
    runners = st.selectbox("塁状況", ["なし", "1塁", "得点圏"])
    strikes = st.selectbox("ストライク", [0, 1, 2])
    pitch_type = st.selectbox("球種", list(PITCH_TYPE_COLORS.keys()))
    hit_type = st.selectbox("打球性質/結果", list(HIT_TYPE_SHAPES.keys()))

    prepare_button = st.button("データダウンロードの準備")

# col2: 画像表示とインタラクション
with col2:
    st.header("打球位置")
    st.write("打球位置をクリックしてください")

    value = streamlit_image_coordinates(base_img, key="input_image")

    if value and selected_team_file and selected_player:
        x, y = value["x"], value["y"]
        current_coords = (x, y)

        # 前回と異なるクリックなら処理（同じなら無視）
        if current_coords != st.session_state.last_click_coords:
            st.session_state.last_click_coords = current_coords
            st.session_state.click_coords.append(current_coords)

            st.session_state.marker_data.append(
                {
                    "team_name": selected_team_file,
                    "player_name": selected_player,
                    "opponents": opponents,
                    "pitcherLR": pitcherLR,
                    "runners": runners,
                    "strikes": strikes,
                    "pitch_type": pitch_type,
                    "hit_type": hit_type,
                    "x_coord": x,
                    "y_coord": y,
                }
            )

    # マーカー付き画像の作成
    img_with_plot = base_img.copy()
    draw = ImageDraw.Draw(img_with_plot)

    for marker in st.session_state.marker_data:
        x, y = marker["x_coord"], marker["y_coord"]
        shape = HIT_TYPE_SHAPES.get(marker["hit_type"], "ellipse")
        color = PITCH_TYPE_COLORS.get(marker["pitch_type"], "gray")
        draw_shape(draw, shape, x, y, 20, color)

    st.image(img_with_plot)

    # マーカー一覧
    if st.session_state.marker_data:
        st.subheader("入力済みデータ一覧")
        df = pd.DataFrame(st.session_state.marker_data)
        st.dataframe(df)

    # CSV出力処理
    if prepare_button:
        if selected_team_file and selected_player and st.session_state.marker_data:
            output = io.BytesIO()
            text_wrapper = io.TextIOWrapper(output, encoding="cp932", newline="")
            writer = csv.DictWriter(
                text_wrapper, fieldnames=list(st.session_state.marker_data[0].keys())
            )
            writer.writeheader()
            writer.writerows(st.session_state.marker_data)
            text_wrapper.flush()  # ← これが重要！
            output.seek(0)
            csv_data = output.read()  # バイト列を読む

            st.success("データ準備が完了しました！")
            st.download_button(
                label="CSVデータをダウンロード",
                data=csv_data,
                file_name="hitting_data.csv",
                mime="text/csv",
            )
    else:
        st.warning("チームと選手を選択し、マーカーを追加してください。")
