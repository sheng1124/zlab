# This Python file uses the following encoding: utf-8
import sys
import os
import cv2
import time
import shutil
import PySide6.QtWidgets as QtWidgets
import PySide6.QtCore as QtCore
import PySide6.QtMultimedia as QtMultimedia
import PySide6.QtGui as QtGui

#vt互動介面定義
class vt(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.func_dict = {'錄影':self.video_recorder, '影片截圖':self.video_cut, '輸出成影片':self.output_video}

        # 定義主介面
        self.main_ui_layout = QtWidgets.QVBoxLayout()
        self.main_ui_layout.setAlignment(QtCore.Qt.AlignTop)
        # 功能選單
        self.func_combo = QtWidgets.QComboBox()
        self.func_combo.addItems(self.func_dict.keys())
        self.func_combo.currentIndexChanged.connect(self.func_change)
        self.main_ui_layout.addWidget(self.func_combo)

        # 錄影介面定義
        self.record_widgets_args = self.ini_recorder_ui()
        self.main_ui_layout.addWidget(self.recorder_ui)
        
        self.main_ui = QtWidgets.QWidget()
        self.main_ui.setLayout(self.main_ui_layout)
        self.setCentralWidget(self.main_ui)

    #初始化錄影功能介面
    def ini_recorder_ui(self):
        self.recorder_ui = QtWidgets.QGroupBox()
        recoder_layout = QtWidgets.QVBoxLayout()
        recoder_layout.setAlignment(QtCore.Qt.AlignTop)
        record_widgets_args = {}

        # 第一行 選擇相機
        line1 = QtWidgets.QHBoxLayout()
        line1.setAlignment(QtCore.Qt.AlignLeft)
        line1.addWidget(QtWidgets.QLabel('選擇相機: '))
        # 偵測連接到的相機並製作成選單
        available_cameras = QtMultimedia.QMediaDevices.videoInputs()
        camera_combo = QtWidgets.QComboBox()
        camera_combo.addItems([e.description() for e in available_cameras])
        camera_combo.addItems(['使用網路相機'])
        camera_combo.currentIndexChanged.connect(self.camera_change)
        line1.addWidget(camera_combo)
        record_widgets_args['camera_combo'] = camera_combo
        # 若選擇使用網路相機 要可以輸入網址
        line1.addWidget(QtWidgets.QLabel('網路相機位置: '))
        recoder_edit1 = QtWidgets.QLineEdit()
        if camera_combo.currentText() != '使用網路相機':
            recoder_edit1.setDisabled(True)
        recoder_edit1.setPlaceholderText("ex: rtsp://163.0.0.1 、 http://163.0.0.1")
        line1.addWidget(recoder_edit1)
        recoder_layout.addItem(line1)
        record_widgets_args['web_camera_edit'] = recoder_edit1

        # 第二行
        if len(available_cameras) == 0:
            # 未偵測到相機提示沒有找到相機
            line2 = QtWidgets.QHBoxLayout()
            line2.addWidget(QtWidgets.QLabel('未偵測到相機'))
            recoder_layout.addItem(line2)
        
        # 第三行 選擇儲存位置
        line4 = QtWidgets.QHBoxLayout()
        line4.addWidget(QtWidgets.QLabel('選擇要儲存的資料夾: '))
        save_folder_edit = QtWidgets.QLineEdit()
        open_folder = save_folder_edit.addAction(
            qApp.style().standardIcon(QtWidgets.QStyle.SP_DirOpenIcon), QtWidgets.QLineEdit.TrailingPosition
        )
        open_folder.triggered.connect(self.on_open_folder)
        save_folder_edit.setText(os.path.join(QtCore.QDir.currentPath(), 'data', 'record'))
        line4.addWidget(save_folder_edit)
        recoder_layout.addItem(line4)
        record_widgets_args['save_folder_edit'] = save_folder_edit

        # 第四行設定影像尺寸
        line5 = QtWidgets.QHBoxLayout()
        line5.setAlignment(QtCore.Qt.AlignLeft)
        line5.addWidget(QtWidgets.QLabel('選擇影像尺寸: '))
        size_combo = QtWidgets.QComboBox()
        size_combo.addItems(['480p', '720p', '1080p', '自訂尺寸'])
        size_combo.currentIndexChanged.connect(self.size_change)
        line5.addWidget(size_combo)
        record_widgets_args['size_combo'] = size_combo
        line5.addWidget(QtWidgets.QLabel('影像尺寸，寬: '))
        img_W = QtWidgets.QLineEdit()
        img_W.setText('640')
        line5.addWidget(img_W)
        record_widgets_args['img_W_edit'] = img_W
        line5.addWidget(QtWidgets.QLabel('高: '))
        img_H = QtWidgets.QLineEdit()
        img_H.setText('480')
        line5.addWidget(img_H)
        record_widgets_args['img_H_edit'] = img_H
        recoder_layout.addItem(line5)

        # 第五行設定錄影形式 fps 縮時
        line6 = QtWidgets.QHBoxLayout()
        line6.setAlignment(QtCore.Qt.AlignLeft)
        line6.addWidget(QtWidgets.QLabel('設定錄影形式: '))
        recorder_type_combo = QtWidgets.QComboBox()
        line6.addWidget(recorder_type_combo)
        recorder_type_combo.addItems(['一般錄影', '縮時攝影'])
        record_widgets_args['recorder_type_combo'] = recorder_type_combo
        line6.addWidget(QtWidgets.QLabel('FPS / 縮時間隔'))
        fps = QtWidgets.QLineEdit()
        fps.setText('15')
        line6.addWidget(fps)
        record_widgets_args['fps_edit'] = fps
        recoder_layout.addItem(line6)

        # 第六行設定錄影格式
        line7 = QtWidgets.QHBoxLayout()
        line7.setAlignment(QtCore.Qt.AlignLeft)
        line7.addWidget(QtWidgets.QLabel('設定儲存格式: '))
        save_type_combo = QtWidgets.QComboBox()
        line7.addWidget(save_type_combo)
        save_type_combo.addItems(['儲存成影片', '儲存成影像'])
        record_widgets_args['save_type_combo'] = save_type_combo
        recoder_layout.addItem(line7)

        # 設定開始/停止錄影按鈕
        line8 = QtWidgets.QHBoxLayout()
        start_record_btn = QtWidgets.QPushButton(text='開始錄影')
        start_record_btn.clicked.connect(self.start_record)
        start_record_btn.setEnabled(True)
        line8.addWidget(start_record_btn)
        line8.addWidget(QtWidgets.QLabel(' '))
        stop_record_btn = QtWidgets.QPushButton(text='暫停錄影')
        stop_record_btn.clicked.connect(self.stop_record)
        stop_record_btn.setEnabled(False)
        line8.addWidget(stop_record_btn)
        line8.addWidget(QtWidgets.QLabel(' '))
        end_record_btn = QtWidgets.QPushButton(text='結束錄影')
        end_record_btn.clicked.connect(self.end_record)
        end_record_btn.setEnabled(False)
        line8.addWidget(end_record_btn)
        recoder_layout.addItem(line8)
        record_widgets_args['is_recording'] = 0
        record_widgets_args['record_btns'] = {
            'start':start_record_btn, 'stop':stop_record_btn, 'end':end_record_btn}
        
        # 顯示視窗
        line9 = QtWidgets.QHBoxLayout()
        record_window = QtWidgets.QLabel(self)
        record_window.setFixedSize(640, 480)
        line9.addWidget(record_window)
        recoder_layout.addItem(line9)
        record_widgets_args['record_window'] = record_window

        #佈局
        self.recorder_ui.setLayout(recoder_layout)

        # 定義相機
        self.camera = Camera(self)
        #self.camera.finished.connect(self.close)
        self.camera.update_frame.connect(self.set_record_image)

        return record_widgets_args

    #選單內容變更就切換功能
    @QtCore.Slot()
    def func_change(self):
        func = self.func_dict[self.func_combo.currentText()]
        func()
    
    #相機選單切換至網路相機
    @QtCore.Slot()
    def camera_change(self):
        re = self.record_widgets_args['web_camera_edit']
        if self.record_widgets_args['camera_combo'].currentText() != '使用網路相機':
            re.setDisabled(True)
        else:
            re.setDisabled(False)
    
    #相機儲存的影片尺寸預設修改
    @QtCore.Slot()
    def size_change(self):
        size_combo = self.record_widgets_args['size_combo']
        w, h = self.record_widgets_args['img_W_edit'], self.record_widgets_args['img_H_edit']
        if size_combo.currentText() == '480p':
            w.setText('640')
            h.setText('480')
        elif size_combo.currentText() == '720p':
            w.setText('1280')
            h.setText('720')
        elif size_combo.currentText() == '1080p':
            w.setText('1920')
            h.setText('1080')
        else:
            w.setText('')
            h.setText('')
    
    #設定儲存路徑
    @QtCore.Slot()
    def on_open_folder(self):
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Open Directory", QtCore.QDir.homePath(), QtWidgets.QFileDialog.ShowDirsOnly)
        if dir_path:
            dest_dir = QtCore.QDir(dir_path)
            self.record_widgets_args['save_folder_edit'].setText(
                QtCore.QDir.fromNativeSeparators(dest_dir.path()))
    
    # 將錄影的影像顯示在UI上
    @QtCore.Slot(QtGui.QImage)
    def set_record_image(self, image):
        self.record_widgets_args['record_window'].setPixmap(QtGui.QPixmap.fromImage(image))

    @QtCore.Slot()
    def start_record(self):
        if not self.check_record():
            return
        self.record_widgets_args['record_btns']['start'].setEnabled(False)
        self.record_widgets_args['record_btns']['stop'].setEnabled(True)
        self.record_widgets_args['record_btns']['end'].setEnabled(True)
        if self.record_widgets_args['is_recording'] == 0:
            self.camera.status = 1
            self.camera.set_args(self.record_widgets_args)
            self.camera.start()
            self.record_widgets_args['is_recording'] = 1
            
        elif self.record_widgets_args['is_recording'] == 2:
            self.camera.status = 1
            self.record_widgets_args['is_recording'] = 1
            
    @QtCore.Slot()
    def stop_record(self):
        self.camera.status = 2
        self.record_widgets_args['is_recording'] = 2
        self.record_widgets_args['record_btns']['start'].setEnabled(True)
        self.record_widgets_args['record_btns']['stop'].setEnabled(False)
        self.record_widgets_args['record_btns']['end'].setEnabled(True)
        
    @QtCore.Slot()
    def end_record(self):
        self.camera.status = 0
        self.record_widgets_args['is_recording'] = 0
        self.record_widgets_args['record_btns']['stop'].setEnabled(False)
        self.record_widgets_args['record_btns']['end'].setEnabled(False)
        time.sleep(3)
        self.record_widgets_args['record_btns']['start'].setEnabled(True)

    def check_record(self):
        print(self.record_widgets_args.keys())
        if (self.record_widgets_args['camera_combo'].currentText() == '使用網路相機' and 
            not self.record_widgets_args['web_camera_edit'].text()):
            print('no web camera address')
            return 0
        w, h = int(self.record_widgets_args['img_W_edit'].text()), int(self.record_widgets_args['img_H_edit'].text())
        if w < 1 or h < 1:
            print('w h must >= 1')
            return 0
        fps = int(self.record_widgets_args['fps_edit'].text())
        if fps < 1:
            print('fps must >= 1')
            return 0
        return 1

    #顯示錄影功能介面
    def video_recorder(self):
        self.recorder_ui.show()

    #顯示影片截圖成影像的介面
    def video_cut(self):
        self.recorder_ui.hide()

    #顯示將影像輸出成影片的介面
    def output_video(self):
        self.recorder_ui.hide()


class Camera(QtCore.QThread):
    update_frame = QtCore.Signal(QtGui.QImage)

    def __init__(self, parent=None) -> None:
        QtCore.QThread.__init__(self, parent)
        self.status = False
    
    #設定參數
    def set_args(self, args):
        # 設定相機id
        if args['camera_combo'].currentText() == '使用網路相機':
            self.camera_id = args['web_camera_edit'].text()
        else:
            self.camera_id = args['camera_combo'].currentIndex()
        
        # 設定錄影存擋路徑
        self.save_folder = args['save_folder_edit'].text()

        # 設定存擋影像尺寸 fps 
        self.H, self.W = int(args['img_H_edit'].text()), int(args['img_W_edit'].text())
        self.fps = int(args['fps_edit'].text()) + 1
        print(self.fps)
        if args['recorder_type_combo'].currentIndex() == 1:
            self.fps = 1 / self.fps
        
        # 設定錄影格式
        self.save_in_video = args['save_type_combo'].currentIndex()
    
    def ini_write_env(self):
        # 檢查存擋路徑
        if not os.path.isdir(self.save_folder):
            os.makedirs(self.save_folder)
        self.save_file = ''

        # 設定時間
        twlocaltime = time.localtime(time.time())
        localtime = time.asctime(twlocaltime)
        dirname = '{}-{}-{}-{}'.format( #日-時-分-秒
            localtime[8:10],
            localtime[11:13],
            localtime[14:16],
            localtime[17:19])
        
        self.save_file_dir = os.path.join(self.save_folder, dirname)
        if not os.path.isdir(self.save_file_dir):
            os.makedirs(self.save_file_dir)

        # 若要存成影片
        if self.save_in_video == 0:
            # 設定檔名
            self.save_file = os.path.join(self.save_folder, f'{dirname}.mp4')
        
        # 若要存成影像
        elif self.save_in_video == 1:
            self.save_file = self.save_file_dir

    # 將拍下來的影像轉成影片
    def write_to_video(self):
        # 取得所有錄影影像路徑 按時間大小排序
        files = sorted(os.listdir(self.save_file_dir), key = lambda id:float(id[:-4]))
        # 計算平均 fps 
        time_list = [int(float(ftime[:-4])) for ftime in files]
        x_time_list = [] # 不重複列表，要用來計算每個秒數有多少張影像
        for e in time_list:
            if e not in x_time_list:
                x_time_list.append(e)
        #計算每個秒數有多少張影像
        count_list = [time_list.count(e) for e in x_time_list]
        #計算平均每秒有多少影像就是等遺下影片要設定的播放FPS
        avg_fps = sum(count_list) / len(count_list)
        
        # 寫入影片
        fourcc = cv2.VideoWriter_fourcc(*'MP4V')
        out = cv2.VideoWriter(self.save_file, fourcc, avg_fps, (self.W, self.H))
        for filename in files:
            #讀取每個影像
            frame = cv2.imread(os.path.join(self.save_file_dir, filename), cv2.IMREAD_COLOR)
            #寫入影像
            out.write(frame)
        out.release()

        # 刪除資料夾
        shutil.rmtree(self.save_file_dir)



    def run(self):
        # 開啟相機
        self.cap = cv2.VideoCapture(self.camera_id)
        
        # 設定儲存環境
        self.ini_write_env()

        #設定時間
        last_time = time.time()
        while self.status:
            # 擷取影像
            try:
                ret, frame = self.cap.read()
            except Exception as e:
                continue

            # Reading the image in RGB to display it
            color_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Creating and scaling QImage
            h, w, ch = color_frame.shape
            img = QtGui.QImage(color_frame.data, w, h, ch * w, QtGui.QImage.Format_RGB888)
            scaled_img = img.scaled(640, 480, QtCore.Qt.KeepAspectRatio)

            # Emit signal
            self.update_frame.emit(scaled_img)

            # 檢查滿不滿足錄影條件 不滿足不存擋
            now_time = time.time()
            if self.status == 1 and now_time - last_time > 1/(self.fps):
                frame = cv2.resize(frame, (self.W, self.H), interpolation=cv2.INTER_AREA)
                # 存成影像
                filepath = os.path.join(self.save_file_dir, str(now_time) + '.jpg')
                cv2.imwrite(filepath, frame)
                # 更新檢查時間點
                last_time = now_time

            # 暫停錄影不儲存影像
            else:
                pass
            
        self.cap.release()
        if self.save_in_video == 0:
            self.write_to_video()
        print('finish')
    


    

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    widget = vt()
    widget.resize(800, 600)
    widget.show()
    sys.exit(app.exec())
