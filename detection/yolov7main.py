import sys
import torch
import numpy as np

sys.path.extend(['../yolov7_main'])
from models.experimental import attempt_load
from utils.datasets import letterbox
from utils.general import non_max_suppression

class YoloV7API():
    def __init__(self, weights, device, img_size = 640) -> None:
        # 載入類神經網路
        self.weights = weights
        self.half = device.type != 'cpu' and device.type != 'mps' # half precision only supported on CUDA
        self.device = device

        model = attempt_load(weights, device)  # load FP32 model
        stride = int(model.stride.max())

        if self.half:
            model.half()  # to FP16
        self.names = model.module.names if hasattr(model, 'module') else model.names
        self.colors = [[np.random.randint(0, 255) for _ in range(3)] for _ in self.names]
        
        self.model = model
        self.img_size = img_size
        self.stride = stride
        
    # 偵測圖片，輸入影像，回傳偵測結果
    def detect(self, img0):
        # Padded resize
        img = letterbox(img0, self.img_size, stride=self.stride)[0]
        xy_rate = (img0.shape[1] / img.shape[1], img0.shape[0] / img.shape[0])

        # Convert
        img = img[:, :, ::-1].transpose(2, 0, 1)  # BGR to RGB, to 3x416x416
        img = np.ascontiguousarray(img)
        img = torch.from_numpy(img).to(self.device)
        img = img.half() if self.half else img.float()  # uint8 to fp16/32
        img /= 255.0  # 0 - 255 to 0.0 - 1.0
        if img.ndimension() == 3:
            img = img.unsqueeze(0)

        # Inference
        with torch.no_grad():   # Calculating gradients would cause a GPU memory leak
            pred = self.model(img, augment=False)[0]
        
        # Apply NMS
        conf_thres, iou_thres, classes, agnostic_nms = (0.25, 0.45, None, False)
        if self.device.type == 'mps':
            pred = non_max_suppression(pred.to('cpu'), conf_thres, iou_thres, classes=classes, agnostic=agnostic_nms)
        else:
            pred = non_max_suppression(pred, conf_thres, iou_thres, classes=classes, agnostic=agnostic_nms)
        
        # 恢復定界框正確符合原始影像的尺寸
        pred[0][:, 0:4:2] *= xy_rate[0]
        pred[0][:, 1:4:2] *= xy_rate[1]

        # 回傳預測結果
        return pred[0]