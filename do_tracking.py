import time
import sys
import os
import csv

import cv2
import numpy as np
import PySide6.QtWidgets as QtWidgets
import PySide6.QtCore as QtCore
import PySide6.QtGui as QtGui
import PySide6.QtMultimedia as QtMultimedia

from zlab_utils.detect_device import detect_device
from zlab_utils.image_source import ImageSource
from tracking import ztrack

# 影像後處理功能
class Painter():
    def __init__(self) -> None:
        self.color_seed = (np.random.rand(4)*255).astype('uint8')
        self.tl = 1
        self.ban_list = []
        self.blackwhite_mode = 0
    
    # 設定筆畫線條粗細 line/font thickness
    def set_tl(self, img):
        self.tl = round(0.002 * (img.shape[0] + img.shape[1]) / 2) + 1

    # 設定黑名單(將忽略、不顯示、刪除某個編號的人物影像)
    def set_ban_list(self, ban_text:str):
        self.ban_list = []
        for ban_id in ban_text.split(','):
            try:
                self.ban_list.append(int(ban_id))
            except (ValueError):
                continue 
    
    # 設定用來刪除人的底圖
    def set_baseimage(self, baseimage_edit:QtWidgets.QLineEdit, img_shape=None):
        self.baseimage_edit = baseimage_edit
        baseimage_path = baseimage_edit.text()
        if os.path.exists(baseimage_path):
            baseimage = cv2.imread(baseimage_path)
            if not img_shape is None:
                self.baseimage = cv2.resize(baseimage, img_shape, interpolation = cv2.INTER_AREA)
            else:
                self.baseimage = baseimage
                
        else:
            self.baseimage = None
        self.baseimage_path = baseimage_path

    def plot_track(self, img, results):
        for rs in results:
            id = rs.track_id
            if (id in self.ban_list and self.blackwhite_mode == 0) or (not id in self.ban_list and self.blackwhite_mode == 1):
                continue
            color = self.color_seed * (id * self.color_seed[3] + 1) % 255
            color = color[:3].tolist()

            # 取得定界框座標點
            c1, c2 = rs.get_cv_box()

            # 畫物件的定界框
            self.plot_box(img, c1, c2, color, self.tl)

            # 畫追蹤id
            self.plot_id(img, c1, str(id), color, self.tl)

    # 畫物件的分割圖層
    def plot_segement(self, img, results):
        alpha = 0.5
        for rs in results:
            if rs.mask is None:
                continue
            id = rs.track_id
            if (id in self.ban_list and self.blackwhite_mode == 0) or (not id in self.ban_list and self.blackwhite_mode == 1):
                continue
            color = self.color_seed * (id * self.color_seed[3] + 1) % 255
            color = color[:3].tolist()

            mask = cv2.cvtColor(rs.mask, cv2.COLOR_GRAY2BGR)
            inv_mask = cv2.bitwise_not(mask)
            fg = cv2.bitwise_and(img, mask)
            bg = cv2.bitwise_and(img, inv_mask)
            
            fg = fg.astype(np.float64) * alpha

            color_mask = mask.copy().astype(np.float64) / 255
            color_mask[:, :, 0] *= color[0] * (1 - alpha)
            color_mask[:, :, 1] *= color[1] * (1 - alpha)
            color_mask[:, :, 2] *= color[2] * (1 - alpha)

            new_fg = (fg + color_mask).astype('uint8')
            cv2.add(new_fg, bg, img)
            
    # 標記移動軌跡 中心點是框的下邊部分約腳的位置
    def plot_footpoint(self, img, tracker_list):
        for tracker in tracker_list:
            id = tracker.id
            if id in self.ban_list:
                continue
            color = self.color_seed * (id * self.color_seed[3] + 1) % 255
            color = color[:3].tolist()
            if len(tracker.kpts_list) > 0:
                steps = 3
                lb, rb = steps * 11, steps * 12 # 左邊屁股右邊屁股在 kpts 的index
                for kpts in tracker.kpts_list:
                    lbx, lby, lbconf = kpts[lb], kpts[lb + 1], kpts[lb + 2]
                    rbx, rby, rbconf = kpts[rb], kpts[rb + 1], kpts[rb + 2]

                    if lbconf > 0.5 and rbconf > 0.5:
                        cx, cy = int((lbx + rbx) / 2), int((lby + rby) / 2)
                        cv2.circle(img, (cx, cy), 1, color, self.tl)

            else:
                for x1, y1, x2, y2 in tracker.coord_list:
                    cx, cy = int((x1 + x2) / 2), int((y1 + 19 * y2 ) / 20)
                    cv2.circle(img, (cx, cy), 1, color, self.tl)

    # 對每個追蹤者畫關節點
    def plot_kpts(self, img, results):
        for rs in results:
            if rs.track_id in self.ban_list:
                continue
            # 畫關節點
            if not rs.kpts is None:
                kpts = rs.kpts
                self.plot_skeleton_kpts(img, kpts, 3, self.tl)

    # 顯示每個追蹤者特定關節點的歷史紀錄位置
    def polt_kpt_track(self, img, tracker_list, kpt_list:str):
        kpts_index = kpt_list.split(',')
        for kpt_index in kpts_index:
            try:
                kpt_index = (int(kpt_index) * 3)
                for tracker in tracker_list:
                    id = tracker.id
                    if id in self.ban_list:
                        continue
                    color = self.color_seed * (id * self.color_seed[3] + 1) % 255
                    color = color[:3].tolist()
                    if len(tracker.kpts_list) > 0:
                        for kpts in tracker.kpts_list:
                            x, y, conf = kpts[kpt_index], kpts[kpt_index + 1], kpts[kpt_index + 2]
                            if conf > 0.5:
                                cv2.circle(img, (int(x), int(y)), 1, color, self.tl)
            except (ValueError, IndexError):
                continue

    # 刪除特定人物的影像
    def remove_track_image(self, img, results, mode, is_use_segement, dw, dh):
        backup_img = img.copy()
        if self.baseimage_edit.text() != self.baseimage_path:
            self.set_baseimage(self.baseimage_edit, (img.shape[1], img.shape[0]))
        for rs in results:
            id = rs.track_id
            box = rs.box.copy()
            box[0] -= dw if box[0] - dw > 0 else box[0]
            box[1] -= dh if box[1] - dh > 0 else box[1]
            box[2] = box[2] + dw if box[2] + dw < img.shape[1] else img.shape[1]
            box[3] = box[3] + dh if box[3] + dh < img.shape[0] else img.shape[0]
            
            if id not in self.ban_list:
                continue
            
            if not is_use_segement:
                if mode == 1:
                    self.remove_with_blackmask(img, box)

                elif mode == 2:
                    self.remove_with_mosaic(img, box)
                
                elif mode == 3:
                    self.remove_with_baseimage(img, box)
                
                elif mode == 4:
                    self.remove_with_seamless_clone(img, box)
            
            else:
                if mode == 1:
                    self.remove_with_blackmask_seg(img, rs.mask)

                elif mode == 2:
                    self.remove_with_mosaic_seg(img, box, rs.mask)
                
                elif mode == 3:
                    self.remove_with_baseimage_seg(img, rs.mask)
                
                elif mode == 4:
                    self.remove_with_seamless_clone(img, box)
        
        # 消除某人時，若有重疊到別人需要將別人復原
        if is_use_segement and mode == 4 and len(self.ban_list) >0 :
            for rs in results:
                id = rs.track_id
                if id in self.ban_list:
                    continue
                self.repair_dele_seg(img, backup_img, rs.mask)
                
    
    # 使用黑布條遮蔽人物
    def remove_with_blackmask(self, img, box):
        xyxy = [int(e) for e in box]
        img[xyxy[1]:xyxy[3], xyxy[0]:xyxy[2]] = 0
    
    # 使用分割遮罩刪除人物
    def remove_with_blackmask_seg(self, img, mask):
        if mask is None:
            return
        inv_mask = cv2.bitwise_not(mask)
        cv2.bitwise_and(img, cv2.cvtColor(inv_mask, cv2.COLOR_GRAY2BGR), img)

    # 打馬賽克
    def remove_with_mosaic(self, img, box):
        xyxy = [int(e) for e in box]
        target = cv2.blur(img[xyxy[1]:xyxy[3], xyxy[0]:xyxy[2]], (25,25))
        img[xyxy[1]:xyxy[3], xyxy[0]:xyxy[2]] = target
    
    # 打馬賽克
    def remove_with_mosaic_seg(self, img, box, mask):
        if mask is None:
            return
        xyxy = [int(e) for e in box]
        
        inv_mask = cv2.cvtColor(cv2.bitwise_not(mask), cv2.COLOR_GRAY2BGR)
        target_seg = cv2.cvtColor(mask[xyxy[1]:xyxy[3], xyxy[0]:xyxy[2]], cv2.COLOR_GRAY2BGR)
        target_inv_seg = inv_mask[xyxy[1]:xyxy[3], xyxy[0]:xyxy[2]]

        target = cv2.blur(img[xyxy[1]:xyxy[3], xyxy[0]:xyxy[2]], (25,25))
        cv2.bitwise_and(target, target_seg, target)
        target_no_blur = cv2.bitwise_and(img[xyxy[1]:xyxy[3], xyxy[0]:xyxy[2]], target_inv_seg)
        cv2.bitwise_or(target, target_no_blur, target)
        img[xyxy[1]:xyxy[3], xyxy[0]:xyxy[2]] = target

    # 用底圖覆蓋物件
    def remove_with_baseimage(self, img, box):
        if self.baseimage is None:
            return
        xyxy = [int(e) for e in box]
        target = self.baseimage[xyxy[1]:xyxy[3], xyxy[0]:xyxy[2]].copy()
        img[xyxy[1]:xyxy[3], xyxy[0]:xyxy[2]] = target

    # 用底圖覆蓋物件
    def remove_with_baseimage_seg(self, img, mask):
        if self.baseimage is None:
            return
        baseimage_mask = cv2.bitwise_and(self.baseimage, cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR))
        inv_mask = cv2.cvtColor(cv2.bitwise_not(mask), cv2.COLOR_GRAY2BGR)
        cv2.bitwise_and(img, inv_mask, img)
        cv2.bitwise_or(img, baseimage_mask, img)
        
    # 用seamless_clone將人物去除
    def remove_with_seamless_clone(self, img, box):
        if self.baseimage is None:
            return
        (x1, y1, x2, y2) = [int(e) for e in box]
        
        # 當融合的範圍碰到邊界會有殘影，所以超出範圍的直接用底圖覆蓋
        if x1 < 5:
            img[y1:y2, 0:5] = self.baseimage[y1:y2, 0:5].copy()
        if y1 < 5:
            img[0:5, x1:x2] = self.baseimage[0:5, x1:x2].copy()
        if x2 + 5 > img.shape[1]:
            img[y1:y2, -5:] = self.baseimage[y1:y2, -5:].copy()
        if y2 + 5 > img.shape[0]:
            img[-5:, x1:x2] = self.baseimage[-5:, x1:x2].copy()

        target = self.baseimage[y1:y2, x1:x2].copy()
        mask = np.ones_like(target) * 255

        img[:, :] = cv2.seamlessClone(target, img, mask, ((x1+x2)//2, (y1+y2)//2), cv2.NORMAL_CLONE)

    # 復原被刪除的分割影像
    def repair_dele_seg(self, img, backup_img, mask):
        if mask is None:
            return
        rawseg = cv2.bitwise_and(backup_img, cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR))
        inv_mask = cv2.cvtColor(cv2.bitwise_not(mask), cv2.COLOR_GRAY2BGR)
        cv2.bitwise_and(img, inv_mask, img)
        cv2.bitwise_or(img, rawseg, img)
        

    # 白名單特定人物的影像
    def white_track_image(self, img, results, mode, is_use_segement, dw, dh):
        if self.baseimage_edit.text() != self.baseimage_path:
            self.set_baseimage(self.baseimage_edit, (img.shape[1], img.shape[0]))

        blackboard = np.zeros_like(img)

        if not self.baseimage is None:
            baseimage = self.baseimage.copy()
        
        if mode == 2:
            blur_img = cv2.blur(img, (25,25))

        for rs in results:
            id = rs.track_id
            box = rs.box.copy()
            box[0] -= dw if box[0] - dw > 0 else box[0]
            box[1] -= dh if box[1] - dh > 0 else box[1]
            box[2] = box[2] + dw if box[2] + dw < img.shape[1] else img.shape[1]
            box[3] = box[3] + dh if box[3] + dh < img.shape[0] else img.shape[0]
            
            if id not in self.ban_list:
                continue
            
            if not is_use_segement:
                if mode == 1:
                    self.white_with_blackmask(img, blackboard, box)

                elif mode == 2:
                    self.white_with_blackmask(img, blur_img, box)
                    blackboard = blur_img
                
                elif mode == 3 and not self.baseimage is None:
                    self.white_with_blackmask(img, baseimage, box)
                    blackboard = baseimage
                
                elif mode == 4 and not self.baseimage is None:
                    self.white_with_seamless_clone(img, baseimage, box)
                    blackboard = baseimage
            
            else:
                if mode == 1:
                    self.white_with_segementmask(img, blackboard, rs.mask)

                elif mode == 2:
                    self.white_with_segement_baseimage(img, blur_img, rs.mask)
                    blackboard = blur_img
                
                elif mode == 3 and not self.baseimage is None:
                    self.white_with_segement_baseimage(img, baseimage, rs.mask)
                    blackboard = baseimage
                
                elif mode == 4:
                    self.white_with_segement_seamless_clone(img, baseimage, box, rs.mask)
                    blackboard = baseimage

        img[:] = blackboard[:]

    # 只顯示白名單上面的人
    def white_with_blackmask(self, img, blackboard, box):
        xyxy = [int(e) for e in box]
        blackboard[xyxy[1]:xyxy[3], xyxy[0]:xyxy[2]] = img[xyxy[1]:xyxy[3], xyxy[0]:xyxy[2]]
    
    # 只顯示白名單上面的人 使用分割遮罩
    def white_with_segementmask(self, img, blackboard, mask):
        if mask is None:
            return
        seg = cv2.bitwise_and(img, cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR))
        cv2.bitwise_or(blackboard, seg, blackboard)

    # 替換背景
    def white_with_segement_baseimage(self, img, baseimage, mask):
        if mask is None:
            return
        inv_mask = cv2.bitwise_not(mask)
        seg = cv2.bitwise_and(img, cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR))
        baseimage_seg = cv2.bitwise_and(baseimage, cv2.cvtColor(inv_mask, cv2.COLOR_GRAY2BGR))
        cv2.bitwise_or(baseimage_seg, seg, baseimage)

    # 白名單的人融合到新背景
    def white_with_seamless_clone(self, img, background, box):
        if background is None:
            return
        (x1, y1, x2, y2) = [int(e) for e in box]
        
        # 當融合的範圍碰到邊界會有殘影，所以超出範圍的直接用底圖覆蓋
        if x1 < 5:
            x1 = 5
        if y1 < 5:
            y1 = 5
        if x2 + 5 > img.shape[1]:
            x2 = img.shape[1] - 5
        if y2 + 5 > img.shape[0]:
            y2 = img.shape[0] -5

        target = img[y1:y2, x1:x2].copy()
        mask = np.ones_like(target) * 255

        background[:, :] = cv2.seamlessClone(target, background, mask, ((x1+x2)//2, (y1+y2)//2), cv2.NORMAL_CLONE)
    
    # 白名單的人融合到新背景 用分割摳圖出來
    def white_with_segement_seamless_clone(self, img, background, box, segmask):
        if background is None:
            return
        (x1, y1, x2, y2) = [int(e) for e in box]
        
        # 當融合的範圍碰到邊界會有殘影，所以超出範圍的直接用底圖覆蓋
        if x1 < 5:
            x1 = 5
        if y1 < 5:
            y1 = 5
        if x2 + 5 > img.shape[1]:
            x2 = img.shape[1] - 5
        if y2 + 5 > img.shape[0]:
            y2 = img.shape[0] -5

        # 先將box融合到背景
        target = img[y1:y2, x1:x2].copy()
        mask = np.ones_like(target) * 255
        nbg = background.copy()
        blend_img = cv2.seamlessClone(target, nbg, mask, ((x1+x2)//2, (y1+y2)//2), cv2.NORMAL_CLONE)

        # 融合後的影像用 分割遮罩摳出來 在和背景去掉分割遮罩的部分合成
        inv_segmask= cv2.bitwise_not(segmask)
        blend_img_seg = cv2.bitwise_and(blend_img, cv2.cvtColor(segmask, cv2.COLOR_GRAY2BGR))
        background_seg = cv2.bitwise_and(background, cv2.cvtColor(inv_segmask, cv2.COLOR_GRAY2BGR))
        cv2.bitwise_or(blend_img_seg, background_seg, background)

    def plot_detection_box(self, img, results, trackclass:int):
        # line/font thickness
        tl = round(0.0002 * (img.shape[0] + img.shape[1]) / 2) + 1  
        color = (0,0,255)

        # 從辨識結果取出物件並影像後製
        for rs in results:
            c1, c2 = rs.get_cv_box()
            conf, cls = rs.conf, rs.cls

            # 畫物件的定界框
            self.plot_box(img, c1, c2, color, tl)

            # 標註信心分數
            self.polt_text(img, c2, f'{conf:.2f}', color, tl)

    # 畫物件的定界框
    def plot_box(self, img, c1, c2, color, tl):
        cv2.rectangle(img, c1, c2, color, tl, lineType=cv2.LINE_AA)

    # 寫文字
    def polt_text(self, img, c1, text:str, color, tl):
        tf = max(tl - 1, 1)  # font thickness
        t_size = cv2.getTextSize(text, 0, fontScale=tl / 3, thickness=tf)[0]
        c2 = c1[0] + t_size[0], c1[1] - t_size[1] - 3
        cv2.rectangle(img, c1, c2, color, -1, cv2.LINE_AA)  # filled
        cv2.putText(img, text, (c1[0], c1[1] - 2), 0, tl / 3, [225, 255, 255], thickness=tf, lineType=cv2.LINE_AA)

    # 畫 id
    def plot_id(self, img, c1, id, color, tl):
        label = str(id)
        tf = max(tl - 1, 1)  # font thickness
        t_size = cv2.getTextSize(label, 0, fontScale=tl / 3, thickness=tf)[0]
        c2 = c1[0] + t_size[0], c1[1] - t_size[1] - 3
        cv2.rectangle(img, c1, c2, color, -1, cv2.LINE_AA)  # filled
        cv2.putText(img, label, (c1[0], c1[1] - 2), 0, tl / 3, [225, 255, 255], thickness=tf, lineType=cv2.LINE_AA)

    # 在影像上c1座標標註(類別)名稱
    def plot_label(self, img, c1, label:str, color, tl):
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
class TrackingUI(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        # 定義主介面
        self.main_ui_layout = QtWidgets.QHBoxLayout()
        self.main_ui_layout.setAlignment(QtCore.Qt.AlignTop)

        # 參數設定介面定義
        self.detection_ui = self._ini_detection_ui()
        self.main_ui_layout.addWidget(self.detection_ui)
        
        # 顯示結果介面定義
        self.show_ui = self._show_ui()
        self.main_ui_layout.addWidget(self.show_ui)

        # layout
        self.main_ui = QtWidgets.QWidget()
        self.main_ui.setLayout(self.main_ui_layout)
        self.setCentralWidget(self.main_ui)
    
    def _show_ui(self):
        show_ui = QtWidgets.QGroupBox()
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)

        # 顯示視窗
        line = QtWidgets.QHBoxLayout()
        result_window = QtWidgets.QLabel(self)
        w, h = (640, 480)
        result_window.setFixedSize(w, h)
        line.addWidget(result_window)
        layout.addItem(line)
        frame = np.zeros((h, w, 3), dtype='uint8')
        img = QtGui.QImage(frame.data, w, h, 3 * w, QtGui.QImage.Format_RGB888)
        result_window.setPixmap(QtGui.QPixmap.fromImage(img))
        self.result_window = result_window

        # 表格視窗
        line = QtWidgets.QHBoxLayout()
        table = QtWidgets.QTableWidget()
        #table.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        table.verticalHeader().setDefaultAlignment(QtCore.Qt.AlignCenter)
        table.verticalHeader().setDefaultSectionSize(128)
        
        table.setRowCount(1)
        table.setColumnCount(5)
        table.hideColumn(4)
        table.setHorizontalHeaderLabels(['人物編號', '出現時間', '最後出現時間', '人物特徵', '特徵長寬'])
        table.verticalScrollBar().setVisible(True)
        table.horizontalScrollBar().setVisible(False)
        line.addWidget(table)
        layout.addItem(line)

        #佈局
        show_ui.setLayout(layout)
        self.history_table = table
        return show_ui
    
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
        model_combo.addItems(['YOLOv7', 'YOLOv7 Pose', 'YOLOv8 segement'])
        #model_combo.setCurrentIndex(1)
        line.addWidget(model_combo)
        layout.addItem(line)
        self.model_combo = model_combo

        # 選擇權重檔
        line = QtWidgets.QHBoxLayout()
        line.setAlignment(QtCore.Qt.AlignLeft)
        line.addWidget(QtWidgets.QLabel('開啟類神經網路權重檔: '))
        weights_edit = QtWidgets.QLineEdit()#'/Users/shengfu/Desktop/project/zlab/yolov7-w6-pose.pt')#'/Users/shengfu/Desktop/project/zlab/yolov8l-seg.pt')
        open_weights = weights_edit.addAction(
            qApp.style().standardIcon(QtWidgets.QStyle.SP_DirOpenIcon), QtWidgets.QLineEdit.TrailingPosition
        )
        open_weights.triggered.connect(self.on_open_weights)
        line.addWidget(weights_edit)
        layout.addItem(line)
        self.weights_edit = weights_edit

        # 選擇追蹤方式
        line = QtWidgets.QHBoxLayout()
        line.setAlignment(QtCore.Qt.AlignLeft)
        line.addWidget(QtWidgets.QLabel('選擇追蹤方法: '))
        track_combo = QtWidgets.QComboBox()
        track_combo.addItems(['Zlab'])
        line.addWidget(track_combo)
        layout.addItem(line)
        self.track_combo = track_combo

        # 設定追蹤過濾參數
        track_cfg_box = QtWidgets.QGroupBox()
        layout2 = QtWidgets.QVBoxLayout()
        layout2.setAlignment(QtCore.Qt.AlignTop)

        line = QtWidgets.QHBoxLayout()
        line.addWidget(QtWidgets.QLabel('設定追蹤條件: '))
        layout2.addItem(line)
        line = QtWidgets.QHBoxLayout()
        line.addWidget(QtWidgets.QLabel('設定追蹤物件的類別 id (您需要去參考您的模型可以偵測的類別對應的數字):'))
        layout2.addItem(line)
        line = QtWidgets.QHBoxLayout()
        track_class_id_edit = QtWidgets.QLineEdit('0')
        line.addWidget(track_class_id_edit)
        layout2.addItem(line)

        line = QtWidgets.QHBoxLayout()
        line.setAlignment(QtCore.Qt.AlignLeft)
        line.addWidget(QtWidgets.QLabel('設定偵測物件時的信心分數門檻(信心大於此數的值才追蹤): '))
        conf_label = QtWidgets.QLabel()
        line.addWidget(conf_label)
        layout2.addItem(line)
        line = QtWidgets.QHBoxLayout()
        
        conf_thre_slider = QtWidgets.QSlider(orientation=QtCore.Qt.Horizontal)
        conf_thre_slider.setRange(0, 100)
        conf_thre_slider.setValue(60)
        def show():
            conf_label.setText(str(conf_thre_slider.value()/100))
        conf_thre_slider.valueChanged.connect(show)
        conf_label.setText(str(conf_thre_slider.value()/100))
        line.addWidget(conf_thre_slider)
        layout2.addItem(line)

        track_cfg_box.setLayout(layout2)
        layout.addWidget(track_cfg_box)
        self.track_class_id_edit = track_class_id_edit
        self.conf_thre_slider = conf_thre_slider

        # 選擇輸入方式
        line = QtWidgets.QHBoxLayout()
        line.setAlignment(QtCore.Qt.AlignLeft)
        line.addWidget(QtWidgets.QLabel('選擇輸入影像模式: '))
        input_mode_combo = QtWidgets.QComboBox()
        input_mode_combo.addItems(['圖片集(所有圖片尺寸必須一樣)', '影片', '視訊鏡頭、usb相機、網路攝影機'])
        #input_mode_combo.setCurrentIndex(1)
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
        input_folder_edit = QtWidgets.QLineEdit('')
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
        input_video_edit = QtWidgets.QLineEdit() #'./data/video1.mp4'
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
        start_detection_btn = QtWidgets.QPushButton(text='開始辨識＆追蹤')
        start_detection_btn.clicked.connect(self.start_detection)
        start_detection_btn.setEnabled(True)
        line.addWidget(start_detection_btn)
        self.start_detection_btn = start_detection_btn

        # 暫停辨識按鈕
        halt_detection_btn = QtWidgets.QPushButton(text='暫停辨識＆追蹤')
        halt_detection_btn.clicked.connect(self.halt_detection)
        halt_detection_btn.setEnabled(False)
        line.addWidget(halt_detection_btn)
        self.halt_detection_btn = halt_detection_btn

        # 停止辨識按鈕
        stop_detection_btn = QtWidgets.QPushButton(text='停止辨識＆追蹤')
        stop_detection_btn.clicked.connect(self.stop_detection)
        stop_detection_btn.setEnabled(False)
        line.addWidget(stop_detection_btn)
        layout.addItem(line)
        self.stop_detection_btn = stop_detection_btn

        # 控制顯示選項
        control_cfg_box = QtWidgets.QGroupBox()
        layout2 = QtWidgets.QVBoxLayout()
        layout2.setAlignment(QtCore.Qt.AlignTop)
        line = QtWidgets.QHBoxLayout()
        line.addWidget(QtWidgets.QLabel('設定顯示內容: '))
        layout2.addItem(line)

        line = QtWidgets.QHBoxLayout()
        line.setAlignment(QtCore.Qt.AlignLeft)
        is_show_tracker = QtWidgets.QCheckBox('標註物件編號框        ')
        is_show_tracker.setChecked(True)
        line.addWidget(is_show_tracker)

        is_show_footpoint = QtWidgets.QCheckBox('標註追蹤軌跡        ')
        is_show_footpoint.setChecked(False)
        line.addWidget(is_show_footpoint)
        layout2.addItem(line)

        is_show_detection = QtWidgets.QCheckBox('標註偵測到的物件(紅線)')
        is_show_detection.setChecked(False)
        line.addWidget(is_show_detection)
        layout2.addItem(line)

        line = QtWidgets.QHBoxLayout()
        line.setAlignment(QtCore.Qt.AlignLeft)
        is_show_segement = QtWidgets.QCheckBox('顯示分割        ')
        is_show_segement.setChecked(True)
        line.addWidget(is_show_segement)
        layout2.addItem(line)

        line = QtWidgets.QHBoxLayout()
        line.setAlignment(QtCore.Qt.AlignLeft)
        blackwhite_mode_combo = QtWidgets.QComboBox()
        blackwhite_mode_combo.addItems(['黑名單模式', '白名單模式'])
        line.addWidget(blackwhite_mode_combo)
        line.addWidget(QtWidgets.QLabel('輸入編號'))
        someone_edit = QtWidgets.QLineEdit()
        line.addWidget(someone_edit)
        layout2.addItem(line)

        line = QtWidgets.QHBoxLayout()
        line.setAlignment(QtCore.Qt.AlignLeft)
        black_way =  QtWidgets.QLabel('黑名單處理(刪除)方式: ')
        line.addWidget(black_way)
        remove_mode_combo = QtWidgets.QComboBox()
        remove_mode_combo.addItems(['無', '黑布條遮蔽', '打馬賽克', '底圖覆蓋', '影像融合'])
        line.addWidget(remove_mode_combo)
        layout2.addItem(line)

        line = QtWidgets.QHBoxLayout()
        line.setAlignment(QtCore.Qt.AlignLeft)
        white_way = QtWidgets.QLabel('白名單處理方式: ')
        line.addWidget(white_way)
        white_mode_combo = QtWidgets.QComboBox()
        white_mode_combo.addItems(['無', '刪除背景', '背景馬賽克', '換背景', '影像融合'])
        line.addWidget(white_mode_combo)
        layout2.addItem(line)

        line = QtWidgets.QHBoxLayout()
        width_modify_edit_label = QtWidgets.QLabel('寬度修正: ')
        line.addWidget(width_modify_edit_label)
        line.setAlignment(QtCore.Qt.AlignLeft)
        width_modify_edit = QtWidgets.QLineEdit('0')
        line.addWidget(width_modify_edit)
        hight_modify_edit_label = QtWidgets.QLabel('長度修正: ')
        line.addWidget(hight_modify_edit_label)
        line.setAlignment(QtCore.Qt.AlignLeft)
        hight_modify_edit = QtWidgets.QLineEdit('0')
        line.addWidget(hight_modify_edit)
        layout2.addItem(line)

        line = QtWidgets.QHBoxLayout()
        baseimage_edit_label = QtWidgets.QLabel('開啟底圖或新背景: ')
        line.addWidget(baseimage_edit_label)
        baseimage_edit = QtWidgets.QLineEdit() 
        open_baseimage= baseimage_edit.addAction(
            qApp.style().standardIcon(QtWidgets.QStyle.SP_DirOpenIcon), QtWidgets.QLineEdit.TrailingPosition
        )
        def on_open_baseimage():
            video_path = QtWidgets.QFileDialog.getOpenFileName(parent=self, dir=os.getcwd(), filter='JPG Files(*.jpg);;PNG Files(*.png);;ALL Files(*)')
            if video_path:
                baseimage_edit.setText(video_path[0])
        open_baseimage.triggered.connect(on_open_baseimage)
        line.addWidget(baseimage_edit)
        layout2.addItem(line)

        line = QtWidgets.QHBoxLayout()
        line.setAlignment(QtCore.Qt.AlignLeft)
        is_show_kpts = QtWidgets.QCheckBox('顯示關節點')
        is_show_kpts.setChecked(True)
        line.addWidget(is_show_kpts)
        show_kpt_track_label = QtWidgets.QLabel('        顯示特定關節點的軌跡: ')
        line.addWidget(show_kpt_track_label)
        show_kpt_track_edit = QtWidgets.QLineEdit()
        line.addWidget(show_kpt_track_edit)
        layout2.addItem(line)

        line = QtWidgets.QHBoxLayout()
        line.setAlignment(QtCore.Qt.AlignLeft)

        is_use_segement_mask = QtWidgets.QCheckBox('使用分割遮罩')
        is_use_segement_mask.setChecked(True)
        line.addWidget(is_use_segement_mask)
        layout2.addItem(line)

        control_cfg_box.setLayout(layout2)
        layout.addWidget(control_cfg_box)

        # 顯示 控制每個模型可以設定的選項 ex: 當選擇偵測pose的模型，才顯示調整顯示關節點功能，否則隱藏選項
        def model_on_show_control():
            model = model_combo.currentIndex()
            if model in (1, ):
                is_show_kpts.show()
                show_kpt_track_edit.show()
                show_kpt_track_label.show()
                is_show_segement.hide()
                is_use_segement_mask.hide()
            elif model in (2, ):
                is_show_kpts.hide()
                show_kpt_track_edit.hide()
                show_kpt_track_label.hide()
                is_show_segement.show()
                is_use_segement_mask.show()
            else:
                is_show_kpts.hide()
                show_kpt_track_edit.hide()
                show_kpt_track_label.hide()
                is_show_segement.hide()
                is_use_segement_mask.hide()
        model_on_show_control()
        self.model_combo.currentIndexChanged.connect(model_on_show_control)
        
        def remove_cfg_on_show_control():
            bw = blackwhite_mode_combo.currentIndex()
            removemode = remove_mode_combo.currentIndex()
            whitemode = white_mode_combo.currentIndex()

            if (bw == 0 and removemode == 0) or (bw == 1 and whitemode == 0):
                width_modify_edit.hide()
                width_modify_edit_label.hide()
                hight_modify_edit.hide()
                hight_modify_edit_label.hide()
                baseimage_edit.hide()
                baseimage_edit_label.hide()
            else:
                width_modify_edit.show()
                width_modify_edit_label.show()
                hight_modify_edit.show()
                hight_modify_edit_label.show()

            if (bw == 0 and removemode in (3,4)) or (bw == 1 and whitemode in (3,4)):
                baseimage_edit.show()
                baseimage_edit_label.show()
            else:
                baseimage_edit.hide()
                baseimage_edit_label.hide()
        remove_cfg_on_show_control()
        remove_mode_combo.currentIndexChanged.connect(remove_cfg_on_show_control)
        white_mode_combo.currentIndexChanged.connect(remove_cfg_on_show_control)

        def black_white_mode_show_control():
            remove_cfg_on_show_control()
            bw = blackwhite_mode_combo.currentIndex()
            if bw == 0:
                remove_mode_combo.show()
                black_way.show()
                white_mode_combo.hide()
                white_way.hide()
            else:
                remove_mode_combo.hide()
                black_way.hide()
                white_mode_combo.show()
                white_way.show()
        black_white_mode_show_control()
        blackwhite_mode_combo.currentIndexChanged.connect(black_white_mode_show_control)

        self.is_show_footpoint = is_show_footpoint
        self.is_show_detection = is_show_detection
        self.someone_edit = someone_edit
        self.remove_mode_combo = remove_mode_combo
        self.hight_modify_edit = hight_modify_edit
        self.width_modify_edit = width_modify_edit
        self.baseimage_edit = baseimage_edit
        self.is_show_kpts = is_show_kpts
        self.show_kpt_track_edit = show_kpt_track_edit
        self.is_show_segement = is_show_segement
        self.is_show_tracker = is_show_tracker
        self.is_use_segement_mask = is_use_segement_mask
        self.blackwhite_mode_combo = blackwhite_mode_combo
        self.white_mode_combo = white_mode_combo
        
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
        
        try:
            track_class_id = int(self.track_class_id_edit.text())
        except Exception :
            track_class_id = 0

        conf_filter = self.conf_thre_slider.value() / 100

        cfg = {
            'model_id':model_id,
            'mode':mode, 
            'weight_file_path':weight_file_path,
            'input_folder_path':input_folder_path,
            'input_video_path':input_video_path,
            'input_camera_id':input_camera_id,
            'is_save_raw':is_save_raw,
            'window_size': self.result_window.size().toTuple(),
            'track_class_id':track_class_id,
            'conf_filter':conf_filter,
            'is_show_footpoint':self.is_show_footpoint,
            'is_show_detection':self.is_show_detection,
            'is_show_kpts' : self.is_show_kpts,
            'is_show_segement' : self.is_show_segement,
            'is_use_segement_mask' : self.is_use_segement_mask,
            'is_show_tracker': self.is_show_tracker,
            'show_kpt_track_edit' : self.show_kpt_track_edit,
            'someone_edit' : self.someone_edit,
            'hight_modify_edit' : self.hight_modify_edit,
            'width_modify_edit' : self.width_modify_edit,
            'remove_mode_combo' : self.remove_mode_combo,
            'baseimage_edit' : self.baseimage_edit,
            'blackwhite_mode_combo' : self.blackwhite_mode_combo,
            'white_mode_combo' : self.white_mode_combo
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
        self.exe.update_table.connect(self.set_table)
        self.exe.finished.connect(self.end_detection)

        self.start_detection_btn.setEnabled(False)
        self.halt_detection_btn.setEnabled(True)
        self.halt_detection_btn.setText('暫停辨識＆追蹤')
        self.stop_detection_btn.setEnabled(True)

        # 重置顯示表格
        self.history_table.clearContents()
        if self.history_table.rowCount() > 1:
            for _ in range(self.history_table.rowCount() - 1):
                self.history_table.removeRow(0)
        self.exe.start()
    
    def halt_detection(self):
        if self.exe.control == 0:
            self.exe.control = 1
            self.halt_detection_btn.setText('繼續辨識＆追蹤')
        elif self.exe.control == 1:
            self.exe.control = 0
            self.halt_detection_btn.setText('暫停辨識＆追蹤')

    @QtCore.Slot()
    def stop_detection(self):
        self.exe.control = 2
        time.sleep(1)

    @QtCore.Slot()
    def end_detection(self):
        self.width_modify_edit.setText('0')
        self.hight_modify_edit.setText('0')
        self.baseimage_edit.setText('')

        self.start_detection_btn.setEnabled(True)
        self.halt_detection_btn.setEnabled(False)
        self.stop_detection_btn.setEnabled(False)
        if self.input_mode_combo.currentIndex() == 0:
            return
        (w, h) = self.result_window.size().toTuple()
        frame = np.zeros((h, w, 3), dtype='uint8')
        img = QtGui.QImage(frame.data, w, h, 3 * w, QtGui.QImage.Format_RGB888)
        self.result_window.setPixmap(QtGui.QPixmap.fromImage(img))

    # 將追蹤後的影像顯示在UI上
    @QtCore.Slot(QtGui.QImage)
    def set_image(self, image:QtGui.QImage):
        self.result_window.setPixmap(QtGui.QPixmap.fromImage(image))
    
    # 將追蹤後的資料顯示在表格上
    @QtCore.Slot(dict)
    def set_table(self, history:dict):
        if len(history) < 1:
            return
        elif len(history) > self.history_table.rowCount():
            for _ in range(len(history) - self.history_table.rowCount()):
                self.history_table.insertRow(self.history_table.rowCount())
        
        keys = [e for e in history.keys()]

        # 更新表格
        for i in range(self.history_table.rowCount()):
            # id
            tid = keys[i] #int
            table_tid = self.history_table.item(i, 0)
            table_tid = table_tid.text() if table_tid != None else ''
            if str(tid) != table_tid:
                self.history_table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(tid)))
            
            # 出現時間
            stime = f"{history[tid]['stime'] :.2f}"
            table_stime = self.history_table.item(i, 1)
            table_stime = table_stime.text() if table_stime != None else ''
            if stime != table_stime:
                self.history_table.setItem(i, 1, QtWidgets.QTableWidgetItem(stime))
            
            # 最後出現時間
            etime = f"{history[tid]['etime'] :.2f}"
            table_etime = self.history_table.item(i, 2)
            table_etime = table_etime.text() if table_etime != None else ''
            if etime != table_etime:
                self.history_table.setItem(i, 2, QtWidgets.QTableWidgetItem(etime))
            
            # 人物特徵
            feature = history[tid]['feature']
            color_frame = cv2.cvtColor(feature, cv2.COLOR_BGR2RGB)
            h, w, ch = color_frame.shape
            table_feature_size = self.history_table.item(i, 4)
            if table_feature_size == None:
                tw,th = (0,0)
            else:
                ls = table_feature_size.text().split()
                tw,th = int(ls[0]), int(ls[1])
            if (w, h) != (tw, th):  
                servantIcon = QtWidgets.QLabel('')
                img = QtGui.QImage(color_frame.data, w, h, ch * w, QtGui.QImage.Format_RGB888)
                scaled_img = img.scaled(128, 128, QtCore.Qt.KeepAspectRatio)
                servantIcon.setPixmap(QtGui.QPixmap(scaled_img))
                self.history_table.setCellWidget(i, 3, servantIcon)
                self.history_table.setItem(i, 4, QtWidgets.QTableWidgetItem(f'{w} {h}'))
                
# 後台執行緒，後續流程(讀檔、偵測、後置、資料儲存)
class ExeThread(QtCore.QThread):
    update_frame = QtCore.Signal(QtGui.QImage)
    finished = QtCore.Signal()
    update_table = QtCore.Signal(dict)

    def __init__(self, cfg, parent=None) -> None:
        QtCore.QThread.__init__(self, parent)
        self.cfg = cfg
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
        self.track_class_id = cfg['track_class_id']
        self.conf_filter = cfg['conf_filter']
        self.device = detect_device()
        self.control = 0
        self.is_show_footpoint = cfg['is_show_footpoint']
        self.is_show_detection = cfg['is_show_detection']
        self.is_show_tracker = cfg['is_show_tracker']
        self.is_show_kpts = cfg['is_show_kpts']
        self.is_show_segement = cfg['is_show_segement']
        self.is_use_segement_mask = cfg['is_use_segement_mask']
        self.show_kpt_track_edit = cfg['show_kpt_track_edit']
        self.someone_edit = cfg['someone_edit']
        self.remove_mode_combo = cfg['remove_mode_combo']
        self.baseimage_edit = cfg['baseimage_edit']
        self.hight_modify_edit = cfg['hight_modify_edit']
        self.width_modify_edit = cfg['width_modify_edit']
        self.blackwhite_mode_combo = cfg['blackwhite_mode_combo']
        self.white_mode_combo = cfg['white_mode_combo']

        
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
        output_folder = os.path.join('results', nowtimestr, 'detect')
        if not os.path.isdir(output_folder):
            os.makedirs(output_folder)
        output_csv = os.path.join('results', nowtimestr, csvname)
        self.output_folder = output_folder
        self.csvfile = open(output_csv, 'w', newline='')
        self.csvwriter = csv.writer(self.csvfile)

    # 寫入辨識結果到 csv 檔
    def write_result(self, filename, results):
        for rs in results:
            tid, xyxy, conf, cls = rs.track_id, rs.box, rs.conf, rs.cls
            line = [filename, cls, tid, *xyxy, conf]
            if not rs.kpts is None:
                # 取得關節點座標清單
                kpts = rs.kpts
                kpts_str = ','.join(['%.2f']*len(kpts))
                kpts_str = f'"{kpts_str % tuple(kpts)}"'
                line.append(kpts_str)
            else:
                line.append('')
            self.csvwriter.writerow(line)

    # 回傳影像給主視窗顯示
    def emit_image(self, img0):
        color_frame = cv2.cvtColor(img0, cv2.COLOR_BGR2RGB)
        h, w, ch = color_frame.shape
        img = QtGui.QImage(color_frame.data, w, h, ch * w, QtGui.QImage.Format_RGB888)
        scaled_img = img.scaled(self.simg_w, self.simg_h, QtCore.Qt.KeepAspectRatio)
        # Emit signal
        self.update_frame.emit(scaled_img)

    # 回傳表格資料
    def emit_table(self, history_table):
        self.update_table.emit(history_table)

    # 執行緒
    def run(self):
        # 加載偵測模型、設定
        if self.model_id == 0:
            from detection.yolov7main import YoloV7API
            detector = YoloV7API(self.weights, self.device)
        elif self.model_id == 1:
            from detection.yolov7pose import YoloV7API
            detector = YoloV7API(self.weights, self.device)
        elif self.model_id == 2:
            from detection.yolov8segement import YoloV8SegementAPI
            detector = YoloV8SegementAPI(self.weights)

        # 後製器
        painter = Painter()
        painter.set_baseimage(self.baseimage_edit)

        # 追蹤者管理
        tm = ztrack.TrackManager(self.track_class_id, self.conf_filter)

        # 資料儲存
        self.set_output_data()

        # 使用csv存資料
        if self.csvfile:
            self.csvwriter.writerow(['filename', 'classname', 'id', 'x0', 'y0', 'x1', 'y1', 'conf', 'kpts'])
        
        # 從資料來源辨識東西
        if self.mode == 0:
            imgsource = ImageSource(folder=self.fpath)
        elif self.mode == 1:
            imgsource = ImageSource(video=self.video_path)
        elif self.mode == 2:
            imgsource = ImageSource(camera=self.input_camera_id)

        for img0, filename in imgsource:
            # 影像偵測
            results = detector.detect(img0)

            # 物件追蹤
            tracker_list = tm.tracking(float(os.path.splitext(filename)[0]), img0, results)

            track_results = tm.get_track_result()

            # 影像後製
            def modify_image():
                img1 = img0.copy()
                painter.set_tl(img1)

                if self.someone_edit.text():
                    painter.set_ban_list(self.someone_edit.text())
                    try:
                        dw, dh = int(self.width_modify_edit.text()), int(self.hight_modify_edit.text())
                    except ValueError:
                        dw, dh = 0, 0
                    isusesegement = self.is_use_segement_mask.isChecked() if self.model_id in (2, ) else False
                    bw = self.blackwhite_mode_combo.currentIndex()
                    painter.blackwhite_mode = bw
                    if bw == 0:
                        mode = self.remove_mode_combo.currentIndex()
                        painter.remove_track_image(img1, track_results, mode, isusesegement, dw, dh)
                    else:
                        mode = self.white_mode_combo.currentIndex()
                        painter.white_track_image(img1, track_results, mode, isusesegement, dw, dh)
                
                if self.is_show_tracker.isChecked():
                    painter.plot_track(img1, track_results)

                if self.is_show_detection.isChecked():
                    painter.plot_detection_box(img1, results, tm.track_class_id)
                
                if self.is_show_segement.isChecked():
                    painter.plot_segement(img1, track_results)

                if self.is_show_kpts.isChecked():
                    painter.plot_kpts(img1, track_results)

                if self.is_show_footpoint.isChecked():
                    painter.plot_footpoint(img1, tracker_list)
                
                if self.show_kpt_track_edit.text():
                    painter.polt_kpt_track(img1, tracker_list, self.show_kpt_track_edit.text())

                # 回傳後製影像給主界面顯示
                self.emit_image(img1)
                return img1

            # 若控制台按停止按鈕，就停止偵測，按暫停就停止下一張圖片輸入但不結束偵測
            if self.control == 1:
                while self.control == 1:
                    modify_image()
            elif self.control == 2: # 強制停止
                break
            img1 = modify_image()

            # 儲存後製影像
            cv2.imwrite(os.path.join(self.output_folder, filename), img1)

            # 將 filename 的追蹤結果寫入到 self.csvfile
            self.write_result(filename, track_results)

            # 輸出表格資料
            self.emit_table(tm.get_tracker_history())

        print('tracking finish')
        self.csvfile.close()
        self.finished.emit()
    
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    widget = TrackingUI()
    widget.resize(1200, 800)
    widget.show()
    sys.exit(app.exec())
