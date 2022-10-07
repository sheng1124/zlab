# This Python file uses the following encoding: utf-8
import sys
import os
import PySide6.QtWidgets as QtWidgets
import PySide6.QtCore as QtCore
import PySide6.QtMultimedia as QtMultimedia

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
        self.ini_recorder_ui()
        self.main_ui_layout.addWidget(self.recorder_ui)
        
        self.main_ui = QtWidgets.QWidget()
        self.main_ui.setLayout(self.main_ui_layout)
        self.setCentralWidget(self.main_ui)

    #初始化錄影功能介面
    def ini_recorder_ui(self):
        self.recorder_ui = QtWidgets.QGroupBox()
        recoder_layout = QtWidgets.QVBoxLayout()
        recoder_layout.setAlignment(QtCore.Qt.AlignTop)

        # 第一行 選擇相機
        line1 = QtWidgets.QHBoxLayout()
        line1.setAlignment(QtCore.Qt.AlignLeft)
        line1.addWidget(QtWidgets.QLabel('選擇相機: '))
        # 偵測連接到的相機並製作成選單
        available_cameras = QtMultimedia.QMediaDevices.videoInputs()
        self.camera_combo = QtWidgets.QComboBox()
        self.camera_combo.addItems([e.description() for e in available_cameras])
        self.camera_combo.addItems(['使用網路相機'])
        self.camera_combo.currentIndexChanged.connect(self.camera_change)
        line1.addWidget(self.camera_combo)
        # 若選擇使用網路相機 要可以輸入網址
        line1.addWidget(QtWidgets.QLabel('網路相機位置: '))
        self.recoder_edit1 = QtWidgets.QLineEdit()
        if self.camera_combo.currentText() != '使用網路相機':
            self.recoder_edit1.setDisabled(True)
        self.recoder_edit1.setPlaceholderText("ex: rtsp://163.0.0.1 、 http://163.0.0.1")
        line1.addWidget(self.recoder_edit1)
        recoder_layout.addItem(line1)

        # 第二行
        if len(available_cameras) == 0:
            # 未偵測到相機提示沒有找到相機
            line2 = QtWidgets.QHBoxLayout()
            line2.addWidget(QtWidgets.QLabel('未偵測到相機'))
            recoder_layout.addItem(line2)
        
        # 第三行 選擇儲存位置
        line4 = QtWidgets.QHBoxLayout()
        line4.addWidget(QtWidgets.QLabel('選擇要儲存的資料夾: '))
        self.recoder_folder_edit2 = QtWidgets.QLineEdit()
        self.recoder_open_folder = self.recoder_folder_edit2.addAction(
            qApp.style().standardIcon(QtWidgets.QStyle.SP_DirOpenIcon), QtWidgets.QLineEdit.TrailingPosition
        )
        self.recoder_open_folder.triggered.connect(self.on_open_folder)
        self.recoder_folder_edit2.setText(os.path.join(QtCore.QDir.currentPath(), 'data', 'record'))
        line4.addWidget(self.recoder_folder_edit2)
        recoder_layout.addItem(line4)

        # 第四行設定影像尺寸
        line5 = QtWidgets.QHBoxLayout()
        line5.setAlignment(QtCore.Qt.AlignLeft)
        line5.addWidget(QtWidgets.QLabel('選擇影像尺寸: '))
        self.size_combo = QtWidgets.QComboBox()
        self.size_combo.addItems(['480p', '720p', '1080p', '自訂尺寸'])
        self.size_combo.currentIndexChanged.connect(self.size_change)
        line5.addWidget(self.size_combo)
        line5.addWidget(QtWidgets.QLabel('影像尺寸，寬: '))
        self.img_W = QtWidgets.QLineEdit()
        self.img_W.setText('480')
        line5.addWidget(self.img_W)
        line5.addWidget(QtWidgets.QLabel('高: '))
        self.img_H = QtWidgets.QLineEdit()
        self.img_H.setText('640')
        line5.addWidget(self.img_H)
        recoder_layout.addItem(line5)

        # 第五行設定錄影形式 fps 縮時
        line6 = QtWidgets.QHBoxLayout()
        line6.setAlignment(QtCore.Qt.AlignLeft)
        line6.addWidget(QtWidgets.QLabel('設定錄影形式: '))
        self.recorder_type_combo = QtWidgets.QComboBox()
        line6.addWidget(self.recorder_type_combo)
        self.recorder_type_combo.addItems(['一般錄影', '縮時攝影'])
        line6.addWidget(QtWidgets.QLabel('FPS / 縮時間隔'))
        self.fps = QtWidgets.QLineEdit()
        self.fps.setText('30')
        line6.addWidget(self.fps)
        recoder_layout.addItem(line6)

        # 第六行設定錄影格式
        line7 = QtWidgets.QHBoxLayout()
        line7.setAlignment(QtCore.Qt.AlignLeft)
        line7.addWidget(QtWidgets.QLabel('設定儲存格式: '))
        self.save_type_combo = QtWidgets.QComboBox()
        line7.addWidget(self.save_type_combo)
        self.save_type_combo.addItems(['儲存成影片', '儲存成影像'])
        recoder_layout.addItem(line7)

        # 設定開始/停止錄影按鈕
        line8 = QtWidgets.QHBoxLayout()
        self.start_record_btn = QtWidgets.QPushButton(text='開始錄影')
        line8.addWidget(self.start_record_btn)
        line8.addWidget(QtWidgets.QLabel(' '))
        self.stop_record_btn = QtWidgets.QPushButton(text='暫停錄影')
        line8.addWidget(self.stop_record_btn)
        line8.addWidget(QtWidgets.QLabel(' '))
        self.end_record_btn = QtWidgets.QPushButton(text='結束錄影')
        line8.addWidget(self.end_record_btn)
        recoder_layout.addItem(line8)

        #佈局
        self.recorder_ui.setLayout(recoder_layout)

    #選單內容變更就切換功能
    @QtCore.Slot()
    def func_change(self):
        func = self.func_dict[self.func_combo.currentText()]
        func()
    
    #相機選單切換至網路相機
    @QtCore.Slot()
    def camera_change(self):
        if self.camera_combo.currentText() != '使用網路相機':
            self.recoder_edit1.setDisabled(True)
        else:
            self.recoder_edit1.setDisabled(False)
        print(self.recoder_edit1.text())
    
    #相機儲存的影片尺寸預設修改
    @QtCore.Slot()
    def size_change(self):
        if self.size_combo.currentText() == '480p':
            self.img_W.setText('640')
            self.img_H.setText('480')
        elif self.size_combo.currentText() == '720p':
            self.img_W.setText('1280')
            self.img_H.setText('720')
        elif self.size_combo.currentText() == '1080p':
            self.img_W.setText('1920')
            self.img_H.setText('1080')
        else:
            self.img_W.setText('')
            self.img_H.setText('')
    
    #設定儲存路徑
    @QtCore.Slot()
    def on_open_folder(self):
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Open Directory", QtCore.QDir.homePath(), QtWidgets.QFileDialog.ShowDirsOnly
        )
        if dir_path:
            dest_dir = QtCore.QDir(dir_path)
            self.recoder_folder_edit2.setText(QtCore.QDir.fromNativeSeparators(dest_dir.path()))
    
    #顯示錄影功能介面
    def video_recorder(self):
        self.recorder_ui.show()

    #顯示影片截圖成影像的介面
    def video_cut(self):
        self.recorder_ui.hide()

    #顯示將影像輸出成影片的介面
    def output_video(self):
        self.recorder_ui.hide()
        

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    widget = vt()
    widget.resize(800, 600)
    widget.show()
    sys.exit(app.exec())
