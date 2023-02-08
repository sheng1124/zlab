import sys

import torch
import torch.backends.cudnn as cudnn
import numpy as np
from numpy import random

sys.path.extend(['./detection/yolov7_pose'])
from models.experimental import attempt_load
from utils.general import non_max_suppression, scale_coords
from utils.datasets import letterbox

from zlab_utils.results import DResults

def clip_coords(boxes, img_shape, step=2):
    # Clip bounding xyxy bounding boxes to image shape (height, width)
    boxes[:, 0::step].clamp_(0, img_shape[1])  # x1
    boxes[:, 1::step].clamp_(0, img_shape[0])  # y1

def scale_coords(img1_shape, coords, img0_shape, ratio_pad=None, kpt_label=False, step=2):
    # Rescale coords (xyxy) from img1_shape to img0_shape
    if ratio_pad is None:  # calculate from img0_shape
        gain = min(img1_shape[0] / img0_shape[0], img1_shape[1] / img0_shape[1])  # gain  = old / new
        pad = (img1_shape[1] - img0_shape[1] * gain) / 2, (img1_shape[0] - img0_shape[0] * gain) / 2  # wh padding
        
    else:
        gain = ratio_pad[0]
        pad = ratio_pad[1]
    if isinstance(gain, (list, tuple)):
        gain = gain[0]
    if not kpt_label:
        coords[:, [0, 2]] -= pad[0]  # x padding
        coords[:, [1, 3]] -= pad[1]  # y padding
        coords[:, [0, 2]] /= gain
        coords[:, [1, 3]] /= gain
        clip_coords(coords[0:4], img0_shape)
        #coords[:, 0:4] = coords[:, 0:4].round()
    else:
        coords[:, 0::step] -= pad[0]  # x padding
        coords[:, 1::step] -= pad[1]  # y padding
        coords[:, 0::step] /= gain
        coords[:, 1::step] /= gain
        clip_coords(coords, img0_shape, step=step)
        #coords = coords.round()
    return coords

class YoloV7API():
    def __init__(self, weights, device, img_size = 640) -> None:
        # 載入類神經網路
        self.weights = weights
        self.half = device.type != 'cpu' and device.type != 'mps' # half precision only supported on CUDA
        self.device = device

        model = attempt_load(weights, map_location=device)  # load FP32 model
        stride = int(model.stride.max())

        if self.half:
            model.half()  # to FP16
        self.names = model.module.names if hasattr(model, 'module') else model.names
        self.colors = [[np.random.randint(0, 255) for _ in range(3)] for _ in self.names]
        stride = int(model.stride.max())
        
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
            pred = non_max_suppression(pred.to('cpu'), conf_thres, iou_thres, classes=classes, agnostic=agnostic_nms, kpt_label=True)
        else:
            pred = non_max_suppression(pred, conf_thres, iou_thres, classes=classes, agnostic=agnostic_nms, kpt_label=True)
        
        # 恢復定界框正確符合原始影像的尺寸
        for i, det in enumerate(pred):
            if len(det):
                scale_coords(img.shape[2:], det[:, :4], img0.shape, kpt_label=False)
                scale_coords(img.shape[2:], det[:, 6:], img0.shape, kpt_label=True, step=3)
        pred = pred[0].detach().numpy()
        
        # 設定結果
        results = []
        for p in pred:
            rs = DResults()
            rs.set_box(p[:4])
            rs.set_conf(p[4])
            rs.set_cls(int(p[5]))
            rs.set_kpts(p[6:])
            results.append(rs)

        # 回傳預測結果
        return results

