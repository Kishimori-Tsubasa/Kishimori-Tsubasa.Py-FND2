#ライブラリのインポート
import os
import cv2
import time
import logging
import configparser
import tkinter as tk
import RPi.GPIO as GPIO
from libcamera import controls
from picamera2 import Picamera2
from tkinter import simpledialog
from smb.SMBConnection import SMBConnection
from logging.handlers import RotatingFileHandler

# ロガーの設定
def setup_logging():
    """グローバルなロガーを設定します。"""
    global logger
    logger = logging.getLogger('Camera_Logger')
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    # ローテートファイルハンドラの設定
    rotating_handler = RotatingFileHandler('camera.log', maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
    rotating_handler.setLevel(logging.DEBUG)
    rotating_handler.setFormatter(formatter)
    # コンソールハンドラの設定
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    # ハンドラをロガーに追加
    logger.addHandler(rotating_handler)
    logger.addHandler(console_handler)

#フォルダの存在確認+作成
def check_and_create_folder(conn, share_name, parent_path, remote_folder):
    """
    指定された共有内のルートディレクトリに対して、remote_folderの存在を確認し、
    存在しなければ新たに作成します。
    """
    path = parent_path + remote_folder
    parts = path.strip('/').split('/')
    current_path = ''
    
    for part in parts:
        current_path = f"{current_path}/{part}" if current_path else part
        
        try:
            conn.listPath(share_name, current_path)
            print(f"フォルダ '{part}' は既に存在します。")
            
        except Exception:
            print(f"フォルダ '{part}' は存在しません。作成します。") 
            conn.createDirectory(share_name, current_path)
            print(f"Created: {current_path}")

# Sambaアップロード機能
def upload_files_to_server(video_directory, video_file):
    """録画した動画をWindowsサーバーにアップロード"""
    try:
        # 設定ファイルの読み込み
        inifile = configparser.ConfigParser()
        inifile.read('settings.ini', encoding='utf-8')
        
        # SMB接続情報の取得
        USER_ID = inifile.get('DEFAULT', 'USER_ID')
        PASSWORD = inifile.get('DEFAULT', 'PASSWORD')
        CLIENT_MACHINE_NAME = inifile.get('DEFAULT', 'CLIENT_MACHINE_NAME')
        SERVER_NAME = inifile.get('DEFAULT', 'SERVER_NAME')
        SERVER_IP = inifile.get('DEFAULT', 'SERVER_IP')
        SERVER_PORT = int(inifile.get('DEFAULT', 'SERVER_PORT'))
        SHARE_NAME = inifile.get('DEFAULT', 'SHARE_NAME')
        REMOTE_VIDEO_DIRECTORY = inifile.get('DEFAULT', 'REMOTE_VIDEO_DIRECTORY')
        
        logger.info("Windowsサーバーへのアップロードを開始します")
        
        # SMB接続を確立
        conn = SMBConnection(USER_ID, PASSWORD, CLIENT_MACHINE_NAME, SERVER_NAME, use_ntlm_v2=True)
        if not conn.connect(SERVER_IP, SERVER_PORT):
            raise ConnectionError("SMB接続に失敗しました")
        
        logger.info("SMB接続に成功しました")
        
        # 動画ファイルのアップロード
        if os.path.exists(video_file):
            video_filename = os.path.basename(video_file)
            remote_video_path = os.path.join(REMOTE_VIDEO_DIRECTORY, video_directory, video_filename).replace('\\', '/')
            
            # フォルダチェック＆必要なら作成
            check_and_create_folder(conn, SHARE_NAME, REMOTE_VIDEO_DIRECTORY, video_directory)
            
            with open(video_file, 'rb') as file_obj:
                conn.storeFile(SHARE_NAME, remote_video_path, file_obj)
            logger.info(f"動画ファイル '{video_filename}' をアップロードしました")
        else:
            logger.warning(f"動画ファイル '{video_file}' が存在しません")
        
        # 接続を閉じる
        conn.close()
        logger.info("Windowsサーバーへのアップロードが完了しました")
        return True
        
    except Exception as e:
        logger.error(f"Windowsサーバーへのアップロード中にエラーが発生しました: {e}")
        return False

#プレビューウィンドウの設定
def imshow_fullscreen(winname, img):
    cv2.namedWindow(winname, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(winname,cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    cv2.imshow(winname, img)
    
#カメラの設定
def setting_camera(picam2):
    picam2.configure(picam2.create_video_configuration(main={"format":'XRGB8888'}))
    picam2.start()
    #ピントを手動で合わせる
    #picam2.set_controls({"AfMode":controls.AfModeEnum.Manual,"LensPosition":10,"AfSpeed":controls.AfSpeedEnum.Fast})
    #ピントを自動で合わせる
    picam2.set_controls({"AfMode":controls.AfModeEnum.Continuous,"AfSpeed":controls.AfSpeedEnum.Fast})

#メイン処理
def main():
    # ロガーの設定
    setup_logging()
    
    #ボタン用PINNoの設定
    ON = 22
    OFF = 23
    
    #GPIOの設定
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(ON,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(OFF,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)

    #カメラの設定
    picam2 = Picamera2()
    setting_camera(picam2)
    
    #依頼No入力ダイアログ表示+フォルダ作成
    root = tk.Tk()
    root.withdraw()
    
    path = simpledialog.askstring(title="recording",prompt="依頼No入力")
    
    year_path = "20" + path[3:5]
    path = os.path.join(year_path,path)
    
    os.makedirs(path, exist_ok=True)

    filename = ""

    try:
        while True:
            
            #リアルタイム映像を表示
            frame = picam2.capture_array("main")
            imshow_fullscreen("Image",frame)
            key = cv2.waitKey(1) & 0xff
            
            #黄ボタンが押されたとき
            if GPIO.input(ON) == 1:
                
                #試験片名入力ダイアログ表示
                filename = simpledialog.askstring(title="recording",prompt="試験片名入力")
                
                #動画保存フォルダ作成
                video_file = path + "/" + filename + '.mp4'
                
                #録画開始
                picam2.start_and_record_video(video_file)
                
                #ログ表示
                logger.info(f"録画開始: {filename}")
                
                while True:
                    
                    #リアルタイム映像を表示
                    frame = picam2.capture_array("main")
                    imshow_fullscreen("Image",frame)
                    cv2.waitKey(1)
                    
                    #赤ボタンが押されたとき
                    if GPIO.input(OFF) == 1:
                        
                        #ログ表示
                        logger.info("録画停止1")
                        
                        #カメラの設定を開放
                        picam2.stop_recording()
                        picam2.stop()
                        
                        # ファイルアップロード
                        upload_files_to_server(path, video_file)
                        
                        #カメラの設定
                        setting_camera(picam2)
                        
                        #チャタリング防止
                        cv2.waitKey(500)
                        break
            
            #赤ボタンが押されたとき(プログラム終了)
            elif GPIO.input(OFF) == 1:
                logger.info("プログラム終了")
                break
                
            elif key != 255 or cv2.getWindowProperty('Image',cv2.WND_PROP_AUTOSIZE) == -1:
                break

    except KeyboardInterrupt:
        logger.info("キーボード割り込みでプログラム終了")
        
    finally:
        
        #カメラの設定を開放
        picam2.stop()
        cv2.destroyAllWindows()
        GPIO.cleanup()

if __name__ == '__main__':
    main()
