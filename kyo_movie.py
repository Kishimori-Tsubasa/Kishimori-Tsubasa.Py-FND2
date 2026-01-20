import os
import tkinter as tk
from tkinter import simpledialog
from picamera2 import Picamera2

# -----------------------------
# メイン処理（抜粋）
# -----------------------------
def main():

    # Tkinter初期化（メインウィンドウ非表示）
    root = tk.Tk()
    root.withdraw()

    # -----------------------------
    # ① 依頼Noの入力
    # -----------------------------
    request_no = simpledialog.askstring(
        title = "recording",
        prompt = "依頼No入力"
    )

    if not request_no:
        print("依頼Noが入力されなかったため終了します")
        return

    # 依頼Noから年度フォルダを作成（例：ABCD24 → 2024）
    year_path = "20" + request_no[3:5]
    save_dir = os.path.join(year_path, request_no)

    # フォルダ作成（既に存在していてもエラーにしない）
    os.makedirs(save_dir, exist_ok=True)

    # -----------------------------
    # ② 試験片ナンバー（名前）入力
    # -----------------------------
    specimen_name = simpledialog.askstring(
        title = "recording",
        prompt = "試験片名入力"
    )

    if not specimen_name:
        print("試験片名が入力されなかったため終了します")
        return

    # -----------------------------
    # ③ 動画保存パスの作成
    # -----------------------------
    video_file = os.path.join(
        save_dir,
        f"{specimen_name}.mp4"
    )

    print(f"動画保存先: {video_file}")

    # -----------------------------
    # ④ 動画録画開始
    # -----------------------------
    picam2 = Picamera2()
    picam2.start()
    picam2.start_and_record_video(video_file)

    print("録画開始")
