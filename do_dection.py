import time
import sys
import os
import csv

import cv2
import torch
import numpy as np

import PySide6.QtWidgets as QtWidgets
import PySide6.QtCore as QtCore
import PySide6.QtGui as QtGui
import PySide6.QtMultimedia as QtMultimedia

# 偵測硬體環境
def detect_device():
    print('start detect device')
    print(f'torch version : {torch.__version__}')

    # 檢查 nvdia 顯示卡的 cuda cudnn 支援，若支援，回傳 cuda 設備
    try:
        if torch.cuda.is_available():
            print('cuda is available: ')
            return torch.device('cuda:0')
        raise RuntimeError('no cuda')
    except Exception:
        print('cuda is not available')
    
    # 檢查 apple gpu(m1) 的支援，若支援，回傳 mps 設備
    try:
        if torch.backends.mps.is_available():
            if torch.backends.mps.is_built():
                print('mps is available: ')
                return torch.device("mps")
        raise RuntimeError('no mps')
    except Exception:
        print('mps is not available')
    
    # 系統可能不支援顯示卡運算，使用cpu來偵測
    print('use cpu device')
    return torch.device('cpu')

# 影像來源，
class ImageSource():
    def __init__(self, folder=None, video=None, camera=None) -> None:
        if folder and os.path.isdir(folder):
            self.folder = folder
        else:
            self.folder = None

        self.video, self.camera = video, camera

    def __iter__(self):
        if self.folder:
            # 取的資料夾下所有檔案
            fp_list = os.listdir(self.folder)
            fp_list2 = []
            # 過濾非影像格式的檔案
            for filename in fp_list:
                if filename[-4:].lower() in ('.jpg', '.png'):
                    fp_list2.append(filename)

            # 整理檔名 
            try:
                # 取得所有錄影影像路徑 按時間大小排序
                files = sorted(fp_list2, key = lambda id:float(id[:-4]))
            except Exception:
                # 無法以時間排序影像 就不排序
                files = fp_list2
            
            # 取得所有檔名
            for filename in files:
                filepath = os.path.join(self.folder, filename)
                img0 = cv2.imread(filepath)
                yield img0, filename
        
        elif self.video:
            # 讀取影片
            video = cv2.VideoCapture(self.video)
            fps = video.get(cv2.CAP_PROP_FPS)
            print('video fps = ', fps)
            if fps<=0:
                fps = 15
            gtime = time.time()
            ret, frame = video.read()
            while ret:
                # 讀取每一格影格
                yield frame, f'{gtime}.jpg'
                gtime += 1/fps
                ret, frame = video.read()
            return 

        elif self.camera != None:
            # 開啟相機
            cam = cv2.VideoCapture(self.camera)
            print(f'open camera {self.camera}')
            ret, frame = cam.read()
            while ret:
                gtime = time.time()
                yield frame, f'{gtime}.jpg'
                ret, frame = cam.read()

# 影像後處理
class Painter():
    def pplot(self, img, results, clsnames, colors):
        # line/font thickness
        tl = round(0.002 * (img.shape[0] + img.shape[1]) / 2) + 1  

        # 從辨識結果取出物件並影像後製
        for det_index, (*xyxy, conf, cls) in enumerate(reversed(results[:,:6])):
            label = f'{clsnames[int(cls)]} {conf:.2f}'
            color = colors[int(cls)]

            # 取得定界框座標點
            c1, c2 = (int(xyxy[0]), int(xyxy[1])), (int(xyxy[2]), int(xyxy[3]))

            # 取得關節點座標清單
            kpts = results[det_index, 6:]

            # 畫物件的定界框
            self.plot_box(img, c1, c2, color, tl)

            # 畫類別標籤
            if label:
                self.plot_label(img, c1, label, color, tl)
            
            # 畫關節點
            if len(kpts):
                self.plot_skeleton_kpts(img, kpts, 3, tl)
                    
    # 畫物件的定界框
    def plot_box(self, img, c1, c2, color, tl):
        cv2.rectangle(img, c1, c2, color, tl, lineType=cv2.LINE_AA)

    # 在影像上c1座標標註(類別)名稱
    def plot_label(self, img, c1, label, color, tl):
        if len(label.split(' ')) > 1:
            label = label.split(' ')[-1]
            tf = max(tl - 1, 1)  # font thickness
            t_size = cv2.getTextSize(label, 0, fontScale=tl / 3, thickness=tf)[0]
            c2 = c1[0] + t_size[0], c1[1] - t_size[1] - 3
            cv2.rectangle(img, c1, c2, color, -1, cv2.LINE_AA)  # filled
            cv2.putText(img, label, (c1[0], c1[1] - 2), 0, tl / 3, [225, 255, 255], thickness=tf, lineType=cv2.LINE_AA)
    
    # 在影像上標註物件的關節點
    def plot_skeleton_kpts(self, im, kpts, steps, tl):        
        #Plot the skeleton and keypointsfor coco datatset
        palette = np.array([[255, 128, 0], [255, 153, 51], [255, 178, 102],
                            [230, 230, 0], [255, 153, 255], [153, 204, 255],
                            [255, 102, 255], [255, 51, 255], [102, 178, 255],
                            [51, 153, 255], [255, 153, 153], [255, 102, 102],
                            [255, 51, 51], [153, 255, 153], [102, 255, 102],
                            [51, 255, 51], [0, 255, 0], [0, 0, 255], [255, 0, 0],
                            [255, 255, 255]])

        skeleton = [[16, 14], [14, 12], [17, 15], [15, 13], [12, 13], [6, 12],
                    [7, 13], [6, 7], [6, 8], [7, 9], [8, 10], [9, 11], [2, 3],
                    [1, 2], [1, 3], [2, 4], [3, 5], [4, 6], [5, 7]]

        pose_limb_color = palette[[9, 9, 9, 9, 7, 7, 7, 0, 0, 0, 0, 0, 16, 16, 16, 16, 16, 16, 16]]
        pose_kpt_color = palette[[16, 16, 16, 16, 16, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9]]
        
        radius = 2 * tl 
        num_kpts = len(kpts) // steps

        for kid in range(num_kpts):
            r, g, b = pose_kpt_color[kid]
            x_coord, y_coord = kpts[steps * kid], kpts[steps * kid + 1]
            if not (x_coord % 640 == 0 or y_coord % 640 == 0):
                if steps == 3:
                    conf = kpts[steps * kid + 2]
                    if conf < 0.5:
                        continue
                cv2.circle(im, (int(x_coord), int(y_coord)), radius, (int(r), int(g), int(b)), -1)
                cv2.putText(im, str(kid), (int(x_coord), int(y_coord) - 10), 0, tl / 3, [225, 255, 255], thickness=tl, lineType=cv2.LINE_AA)

        for sk_id, sk in enumerate(skeleton):
            r, g, b = pose_limb_color[sk_id]
            pos1 = (int(kpts[(sk[0]-1)*steps]), int(kpts[(sk[0]-1)*steps+1]))
            pos2 = (int(kpts[(sk[1]-1)*steps]), int(kpts[(sk[1]-1)*steps+1]))
            if steps == 3:
                conf1 = kpts[(sk[0]-1)*steps+2]
                conf2 = kpts[(sk[1]-1)*steps+2]
                if conf1<0.5 or conf2<0.5:
                    continue
            if pos1[0]%640 == 0 or pos1[1]%640==0 or pos1[0]<0 or pos1[1]<0:
                continue
            if pos2[0] % 640 == 0 or pos2[1] % 640 == 0 or pos2[0]<0 or pos2[1]<0:
                continue
            cv2.line(im, pos1, pos2, (int(r), int(g), int(b)), thickness=tl)#

#介面定義(介面功能設計)
class DetectionUI(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        # 定義主介面
        self.main_ui_layout = QtWidgets.QVBoxLayout()
        self.main_ui_layout.setAlignment(QtCore.Qt.AlignTop)

        # 錄影介面定義
        self.detection_ui = self._ini_detection_ui()
        self.main_ui_layout.addWidget(self.detection_ui)
        
        # layout
        self.main_ui = QtWidgets.QWidget()
        self.main_ui.setLayout(self.main_ui_layout)
        self.setCentralWidget(self.main_ui)
    
    # 初始化偵測介面(介面設計)
    def _ini_detection_ui(self):
        detection_ui = QtWidgets.QGroupBox()
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)

        # 選擇 ai 模型
        line = QtWidgets.QHBoxLayout()
        line.setAlignment(QtCore.Qt.AlignLeft)
        line.addWidget(QtWidgets.QLabel('選擇 AI 模型: (執行後無法更改)'))
        model_combo = QtWidgets.QComboBox()
        model_combo.addItems(['YOLOv7', 'YOLOv7 Pose'])
        line.addWidget(model_combo)
        layout.addItem(line)
        self.model_combo = model_combo

        # 選擇權重檔
        line = QtWidgets.QHBoxLayout()
        line.setAlignment(QtCore.Qt.AlignLeft)
        line.addWidget(QtWidgets.QLabel('開啟類神經網路權重檔: '))
        weights_edit = QtWidgets.QLineEdit()
        open_weights = weights_edit.addAction(
            qApp.style().standardIcon(QtWidgets.QStyle.SP_DirOpenIcon), QtWidgets.QLineEdit.TrailingPosition
        )
        open_weights.triggered.connect(self.on_open_weights)
        line.addWidget(weights_edit)
        layout.addItem(line)
        self.weights_edit = weights_edit

        # 選擇輸入方式
        line = QtWidgets.QHBoxLayout()
        line.setAlignment(QtCore.Qt.AlignLeft)
        line.addWidget(QtWidgets.QLabel('選擇輸入影像模式:'))
        input_mode_combo = QtWidgets.QComboBox()
        input_mode_combo.addItems(['圖片集', '影片', '視訊鏡頭、usb相機、網路攝影機'])
        input_mode_combo.currentIndexChanged.connect(self.input_switch)
        line.addWidget(input_mode_combo)
        layout.addItem(line)
        self.input_mode_combo = input_mode_combo

        # 選擇輸入資料夾
        input_folder_box = QtWidgets.QGroupBox()
        layout2 = QtWidgets.QVBoxLayout()
        layout2.setAlignment(QtCore.Qt.AlignTop)
        line = QtWidgets.QHBoxLayout()
        line.addWidget(QtWidgets.QLabel('選擇要偵測的資料夾: '))
        input_folder_edit = QtWidgets.QLineEdit()
        input_folder = input_folder_edit.addAction(
            qApp.style().standardIcon(QtWidgets.QStyle.SP_DirOpenIcon), QtWidgets.QLineEdit.TrailingPosition
        )
        input_folder.triggered.connect(self.on_open_input_folder)
        line.addWidget(input_folder_edit)
        layout2.addItem(line)
        self.input_folder_edit = input_folder_edit
        input_folder_box.setLayout(layout2)
        layout.addWidget(input_folder_box)
        self.input_folder_box = input_folder_box

        # 選擇輸入影片位置
        input_video_box = QtWidgets.QGroupBox()
        layout2 = QtWidgets.QVBoxLayout()
        layout2.setAlignment(QtCore.Qt.AlignTop)
        line = QtWidgets.QHBoxLayout()
        line.addWidget(QtWidgets.QLabel('開啟影片: '))
        input_video_edit = QtWidgets.QLineEdit()
        open_video = input_video_edit.addAction(
            qApp.style().standardIcon(QtWidgets.QStyle.SP_DirOpenIcon), QtWidgets.QLineEdit.TrailingPosition
        )
        open_video.triggered.connect(self.on_open_video)
        line.addWidget(input_video_edit)
        layout2.addItem(line)
        self.input_video_edit = input_video_edit
        input_video_box.setLayout(layout2)
        layout.addWidget(input_video_box)
        self.input_video_box = input_video_box
        self.input_video_box.hide()
        
        # 選擇輸入相機位置
        input_camera_box = QtWidgets.QGroupBox()
        layout2 = QtWidgets.QVBoxLayout()
        layout2.setAlignment(QtCore.Qt.AlignTop)
        line = QtWidgets.QHBoxLayout()
        line.setAlignment(QtCore.Qt.AlignLeft)
        line.addWidget(QtWidgets.QLabel('開啟相機: '))
        # 偵測連接到的相機並製作成選單
        available_cameras = QtMultimedia.QMediaDevices.videoInputs()
        camera_combo = QtWidgets.QComboBox()
        camera_combo.addItems([e.description() for e in available_cameras])
        camera_combo.addItems(['使用網路相機'])
        camera_combo.currentIndexChanged.connect(self.camera_change)
        line.addWidget(camera_combo)
        layout2.addItem(line)
        self.camera_combo = camera_combo
        # 是否保存原始影像
        line = QtWidgets.QHBoxLayout()
        line.setAlignment(QtCore.Qt.AlignLeft)
        is_save_raw = QtWidgets.QCheckBox('是否保存原始影像')
        is_save_raw.setChecked(True)
        line.addWidget(is_save_raw)
        layout2.addItem(line)
        self.is_save_raw = is_save_raw

        # 若選擇使用網路相機 要可以輸入網址
        input_webcam_box = QtWidgets.QGroupBox()
        layout3 = QtWidgets.QVBoxLayout()
        layout3.setAlignment(QtCore.Qt.AlignTop)
        line = QtWidgets.QHBoxLayout()
        line.addWidget(QtWidgets.QLabel('網路相機位置: '))
        web_cam_edit = QtWidgets.QLineEdit()
        web_cam_edit.setPlaceholderText("ex: rtsp://163.0.0.1 、 http://163.0.0.1")
        line.addWidget(web_cam_edit)
        self.web_cam_edit = web_cam_edit
        layout3.addItem(line)
        input_webcam_box.setLayout(layout3)
        layout2.addWidget(input_webcam_box)
        self.input_webcam_box = input_webcam_box
        if camera_combo.currentText() != '使用網路相機':
            input_webcam_box.hide()
        input_camera_box.setLayout(layout2)
        layout.addWidget(input_camera_box)
        self.input_camera_box = input_camera_box
        self.input_camera_box.hide()
 
        # 開始辨識按鈕
        line = QtWidgets.QHBoxLayout()
        start_detection_btn = QtWidgets.QPushButton(text='開始辨識')
        start_detection_btn.clicked.connect(self.start_detection)
        start_detection_btn.setEnabled(True)
        line.addWidget(start_detection_btn)
        layout.addItem(line)
        self.start_detection_btn = start_detection_btn

        # 停止辨識按鈕
        line = QtWidgets.QHBoxLayout()
        stop_detection_btn = QtWidgets.QPushButton(text='停止辨識')
        stop_detection_btn.clicked.connect(self.stop_detection)
        stop_detection_btn.setEnabled(False)
        line.addWidget(stop_detection_btn)
        layout.addItem(line)
        self.stop_detection_btn = stop_detection_btn

        # 顯示視窗
        line = QtWidgets.QHBoxLayout()
        result_window = QtWidgets.QLabel(self)
        result_window.setFixedSize(640, 480)
        line.addWidget(result_window)
        layout.addItem(line)
        self.result_window = result_window

        #佈局
        detection_ui.setLayout(layout)
        return detection_ui
    
    # 取得並檢查使用者的設定是否正確
    def get_cfg(self):
        model_id = self.model_combo.currentIndex()
        mode = self.input_mode_combo.currentIndex()
        weight_file_path = self.weights_edit.text()
        if not weight_file_path:
            print('error1')
        input_folder_path = self.input_folder_edit.text()
        input_video_path = self.input_video_edit.text()
        input_camera_id = self.camera_combo.currentText()
        if input_camera_id == '使用網路相機':
            input_camera_id = self.web_cam_edit.text()
        else:
            input_camera_id = self.camera_combo.currentIndex()
        is_save_raw = self.is_save_raw.isChecked()
        if not (input_folder_path or input_video_path or input_camera_id):
            print('error2')
        
        cfg = {
            'model_id':model_id,
            'mode':mode, 
            'weight_file_path':weight_file_path,
            'input_folder_path':input_folder_path,
            'input_video_path':input_video_path,
            'input_camera_id':input_camera_id,
            'is_save_raw':is_save_raw,
            'window_size': self.result_window.size().toTuple()
            }
        return cfg

    @QtCore.Slot()
    def input_switch(self):
        mode = self.input_mode_combo.currentIndex()
        if mode == 0:
            self.input_folder_box.show()
            self.input_video_box.hide()
            self.input_camera_box.hide()
        elif mode == 1:
            self.input_folder_box.hide()
            self.input_video_box.show()
            self.input_camera_box.hide()
        elif mode ==2:
            self.input_folder_box.hide()
            self.input_video_box.hide()
            self.input_camera_box.show()
    
    @QtCore.Slot()
    def camera_change(self):
        if self.camera_combo.currentText() != '使用網路相機':
            self.input_webcam_box.hide()
        else:
            self.input_webcam_box.show()

    @QtCore.Slot()
    def on_open_weights(self):
        video_path = QtWidgets.QFileDialog.getOpenFileName(
            parent=self,
            caption='Select a pt file',
            dir=os.getcwd(),
            filter='(*.pt)')
        if video_path:
            self.weights_edit.setText(video_path[0])
    
    @QtCore.Slot()
    def on_open_input_folder(self):
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Open Directory", os.getcwd(), QtWidgets.QFileDialog.ShowDirsOnly)
        if dir_path:
            dest_dir = QtCore.QDir(dir_path)
            self.input_folder_edit.setText(QtCore.QDir.fromNativeSeparators(dest_dir.path()))
    
    @QtCore.Slot()
    def on_open_video(self):
        video_path = QtWidgets.QFileDialog.getOpenFileName(
            parent=self,
            caption='Select a mp4 file',
            dir=os.getcwd(),
            filter='(*.mp4)')
        if video_path:
            self.input_video_edit.setText(video_path[0])

    @QtCore.Slot()
    def start_detection(self):
        self.model_combo.setEnabled(False)
        # 整理使用者參數
        cfg = self.get_cfg()
        self.exe = ExeThread(cfg)
        self.exe.update_frame.connect(self.set_image)
        self.exe.finished.connect(self.end_detection)

        self.start_detection_btn.setEnabled(False)
        self.stop_detection_btn.setEnabled(True)
        self.exe.start()
    
    @QtCore.Slot()
    def stop_detection(self):
        self.exe.control = True
        time.sleep(1)

    @QtCore.Slot()
    def end_detection(self):
        self.start_detection_btn.setEnabled(True)
        self.stop_detection_btn.setEnabled(False)
        if self.input_mode_combo.currentIndex() == 0:
            return
        (w, h) = self.result_window.size().toTuple()
        frame = np.zeros((h, w, 3), dtype='uint8')
        img = QtGui.QImage(frame.data, w, h, 3 * w, QtGui.QImage.Format_RGB888)
        scaled_img = img.scaled(w, h, QtCore.Qt.KeepAspectRatio)
        self.result_window.setPixmap(QtGui.QPixmap.fromImage(scaled_img))

    # 將偵測後的影像顯示在UI上
    @QtCore.Slot(QtGui.QImage)
    def set_image(self, image:QtGui.QImage):
        self.result_window.setPixmap(QtGui.QPixmap.fromImage(image))
            
# 後台執行緒，後續流程(讀檔、偵測、後置、資料儲存)
class ExeThread(QtCore.QThread):
    update_frame = QtCore.Signal(QtGui.QImage)
    finished = QtCore.Signal()

    def __init__(self, cfg, parent=None) -> None:
        QtCore.QThread.__init__(self, parent)
        self.model_id = cfg['model_id']
        self.simg_w, self.simg_h = cfg['window_size']
        self.weights = cfg['weight_file_path']
        mode = cfg['mode']
        if mode == 0:
            self.fpath = cfg['input_folder_path']
        elif mode == 1:
            self.video_path = cfg['input_video_path']
        elif mode == 2:
            self.input_camera_id = cfg['input_camera_id']
            self.is_save_raw = cfg['is_save_raw']
        self.mode = mode
        self.device = detect_device()
        self.control = False

    # 設定讀取影像的資料夾
    def set_fpath(self, fpath):
        self.fpath = fpath
    
    # 設定權重檔位置
    def set_weights(self, weights):
        self.weights = weights
    
    # 設定資料輸出 影像 csv
    def set_output_data(self):
        nowtimestr = time.ctime().replace(':', '-').replace(' ', '-')[4:-5]
        csvname = f'{nowtimestr}.csv'
        output_folder = os.path.join('results', nowtimestr)
        if not os.path.isdir(output_folder):
            os.makedirs(output_folder)
        output_csv = os.path.join('results', csvname)
        self.output_folder = output_folder
        self.csvfile = open(output_csv, 'w', newline='')
        self.csvwriter = csv.writer(self.csvfile)

    # 寫入辨識結果到 csv 檔
    def write_result(self, filename, results):
        for det_index, (*xyxy, conf, cls) in enumerate(reversed(results[:,:6])):
            # 取得關節點座標清單
            kpts = results[det_index, 6:].detach().numpy()
            kpts_str = ','.join(['%.2f']*len(kpts))
            kpts_str = f'"{kpts_str % tuple(kpts)}"'

            xyxy = [xyxy[0].detach().numpy(), xyxy[1].detach().numpy(), xyxy[2].detach().numpy(), xyxy[3].detach().numpy()]
            if len(kpts):
                line = [filename, cls.detach().numpy(), *xyxy, conf.detach().numpy(), kpts_str]
            else:
                line = [filename, cls.detach().numpy(), *xyxy, conf.detach().numpy(), '']
            self.csvwriter.writerow(line)

    # 回傳影像給主視窗顯示
    def emit_image(self, img0):
        color_frame = cv2.cvtColor(img0, cv2.COLOR_BGR2RGB)
        h, w, ch = color_frame.shape
        img = QtGui.QImage(color_frame.data, w, h, ch * w, QtGui.QImage.Format_RGB888)
        scaled_img = img.scaled(self.simg_w, self.simg_h, QtCore.Qt.KeepAspectRatio)
        # Emit signal
        self.update_frame.emit(scaled_img)

    # 執行緒
    def run(self):
        # 加載模型、設定
        if self.model_id == 0:
            from detection.yolov7main import YoloV7API
            detector = YoloV7API(self.weights, self.device)
        elif self.model_id == 1:
            from detection.yolov7pose import YoloV7API
            detector = YoloV7API(self.weights, self.device)

        # 後製器
        painter = Painter()

        # 資料儲存
        self.set_output_data()

        # 使用csv存資料
        if self.csvfile:
            self.csvwriter.writerow(['filename', 'classname', 'x0', 'y0', 'x1', 'y1', 'conf', 'kpts'])
        
        # 從資料來源辨識東西
        if self.mode == 0:
            imgsource = ImageSource(folder=self.fpath)
        elif self.mode == 1:
            imgsource = ImageSource(video=self.video_path)
        elif self.mode == 2:
            imgsource = ImageSource(camera=self.input_camera_id)

        for img0, filename in imgsource:
            if self.control: # 強制停止
                break
            # 影像偵測
            results = detector.detect(img0)
            # 影像後製
            painter.pplot(img0, results, detector.names, detector.colors)

            # 儲存後製影像
            cv2.imwrite(os.path.join(self.output_folder, filename), img0)

            # 將 filename 的辨識結果寫入到 self.csvfile
            self.write_result(filename, results)

            # 顯示後製影像
            self.emit_image(img0)

        print('detection finish')
        self.csvfile.close()
        self.finished.emit()
        
    
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    widget = DetectionUI()
    widget.resize(800, 600)
    widget.show()
    sys.exit(app.exec())

if __name__ == '__main__4':
    a = ImageSource('img3')
    for e in a:
        print()

if __name__ == '__main__2':
    # 加載模型、設定
    detector = YoloV7API('./yolov7-w6-pose.pt', detect_device())

    imgsource = ImageSource(folder='./images')

    for img0, filename in imgsource:
        # 影像偵測
        results = detector.detect(img0)
        
        # 影像後製 標註定界框
        for det_index, (*xyxy, conf, cls) in enumerate(reversed(results[:,:6])):
            kpts = results[det_index, 6:]
            label = f'{detector.names[int(cls)]} {conf:.2f}'

            plot_one_box_kpt(xyxy, img0, label=label, color=detector.colors[int(cls)], kpt_label=True, kpts=kpts, steps=3, orig_shape=img0.shape[:2])

            cv2.imwrite(os.path.join('./results', filename), img0)

