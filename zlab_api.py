import os
import time

import cv2
import torch

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
            #gtime = time.time()
            gtime = 0.0
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

