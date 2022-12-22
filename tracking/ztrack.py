# 物件追蹤演算法
# 輸入偵測結果 輸出每個物件的編號

import numpy as np

from tracking.hungarian_api import hungarian_algorithm

#儲存box資訊的基本單位，不參與評估，等待指派box
class Tracker():
    def __init__(self, id) -> None:
        # id
        self.id = id
        # 追蹤的座標
        self.coord_list = []
        # 紀錄辨識結果
        self.result_list = []
        # 紀錄時間
        self.time_list = []
        self.frame_count = 0
        # 目前移動方向
        self.direct = 0 # 1 右下 2 右上 3 左下 4 左上
        # 速度
        self.avg_v = 0
        self.avg_v_list = []
        # 特徵圖
        self.feature = None
        self.feature_conf = 0.0
    
    # 取得最後紀錄的box座標
    def get_last_coord(self):
        return self.coord_list[-1]
    
     # 取得最後紀錄的 辨識結果
    def get_last_result(self):
        return self.result_list[-1]

    # 取得最後紀錄的時間點
    def get_last_time(self):
        return self.time_list[-1]

    # 取得表格資料
    def get_table_data(self):
        id = self.id
        starttime = self.time_list[0]
        endtime = self.time_list[-1]
        feature = self.feature
        return(id, starttime, endtime, feature)

    #  紀錄框,足跡,速度 方向
    def set_box(self, gtime:float, img:np.ndarray, result:list):
        self.frame_count = 0
        self.coord_list.append(result[:4])
        self.time_list.append(gtime)
        self.result_list.append(result)
        conf = result[4]

        if type(self.feature) == type(None):
            self.feature = img[int(result[1]):int(result[3]) ,int(result[0]):int(result[2])].copy()
            self.feature_conf = conf
        elif conf > self.feature_conf: #conf > 0.8 :#and img.shape[0] * img.shape[1] > self.feature[0] * self.feature[1]:#
            self.feature = img[int(result[1]):int(result[3]) ,int(result[0]):int(result[2])].copy()
            self.feature_conf = conf

class TrackManager():
    def __init__(self, track_class_id = 0, conf_filter = 0.6) -> None:
        self.track_class_id = track_class_id
        self.conf_filter = conf_filter
        self.trackid = 0
        self.tracker_list = []
        self.tracker_history = {}
        # 鎖定物件

    # 追蹤流程
    def tracking(self, gtime, img,  results):
        # 取得新的辨識結果(results)，追蹤列表重置為未追蹤狀態
        untrack_list = self.tracker_list
        tracked_list = []

        # 過濾不需要的物件
        new_results = self.filter_results(results)
        
        # 若篩選後沒有可用的偵測結果就辨識下一張影像
        if len(new_results) < 1:
            for t in untrack_list:
                if not self.is_tracker_exit(t):
                    tracked_list.append(t)
                else:
                    print(f'in {gtime} tracker {t.id} exit')
            self.tracker_list = tracked_list
            return tracked_list

        # 計算iou 矩陣
        iou_matrix = self.count_iou_mat(new_results, untrack_list)

        # 若偵測新的box沒有重疊 或 沒tracker -> 快速分配
        tracked_list, unmatch_results, iou_matrix = self.fastmatch(gtime, img, new_results, iou_matrix)

        # 最佳化配對 
        if len(iou_matrix) > 0:
            # 取得配對清單 [(0, 2), (1,0)] -> 代表 0 號 box 分配給 2 號 tracker 紀錄/追蹤 
            ans_pos = self.get_match_matrix(iou_matrix)
            matched_result_id_list, matched_tracker_list = ans_pos[:, 0], ans_pos[:, 1]

            for ans in ans_pos:
                row_id, col_id = ans
                result = unmatch_results[row_id]
                tracker = untrack_list[col_id]
                tracker.set_box(gtime, img, result)
                tracked_list.append(tracker)

            # 檢查有沒有box 沒有被追蹤到
            for n in range(len(unmatch_results)):
                if not n in matched_result_id_list:
                    # 有多的box沒被追蹤到(可能有與其他t 重疊但t有更適合的box)-> 建立新的 tracker
                    print(f'in {gtime} new tracker: {self.trackid}')
                    tracked_list.append(self.new_tracker(gtime, img, unmatch_results[n]))
                    
            # 檢查有沒有多的 tracker 沒分配到 box
            for n in range(len(untrack_list)):
                if not n in matched_tracker_list:
                    # 有多的 tracker 沒分配到box 若 tracker 可能還存在就保留，不在就停止追蹤
                    if not self.is_tracker_exit(untrack_list[n]):
                        tracked_list.append(untrack_list[n])
                    else:
                        print(f'in {gtime} tracker {untrack_list[n].id} exit')
        
        self.tracker_list = tracked_list
        self.set_tracker_to_history()
        return tracked_list

    # 對偵測結果做配對 分配對應的物件id
    def fastmatch(self, gtime:float, img:np.ndarray, results:list, iou_matrix:list):
        tracked_list = []
        unmatch_results = []
        new_iou_matrix = []

        for row_id in range(len(iou_matrix)):
            row = iou_matrix[row_id]
            if len(row) > 0 and max(row) > 0:
                # 新偵測到的 box 有與 tracker 重疊，需要最佳化分配
                new_iou_matrix.append(row)
                unmatch_results.append(results[row_id])

            else:
                # 新偵測到的 box 沒有與 tracker 重疊，或是系統中沒有正在追蹤的 tracker -> 生成新的tracker
                print(f'in {gtime} new tracker: {self.trackid}')
                t = self.new_tracker(gtime, img, results[row_id])
                tracked_list.append(t)
    
        return tracked_list, unmatch_results, new_iou_matrix
    
    # 以矩陣中最高分的值來分配，最後取得配對矩陣[(0, 2), (1,0)] -> 代表 i0 配對 j2, i1 配對 j0
    def get_match_matrix(self, matrix):
        matrix = np.array(matrix)
        i, j = matrix.shape

        # 若矩陣非正方形矩陣，需要補零
        if i > j :
            matrix = np.pad(matrix, [(0, 0), (0, i-j)])
        elif i < j:
            matrix = np.pad(matrix, [(0, j-i), (0,0)])

        max_value = np.max(matrix)
        cost_matrix = max_value - matrix

        # 利用匈牙利演算法解決最大權重完美二分匹配 
        ans_pos = hungarian_algorithm(cost_matrix.copy())

        # 若矩陣補零後多出來的row/col 可能會產生多的配對結果，需要將多餘的結果移除
        new_pos = []
        for ans in ans_pos:
            row_id, col_id = ans
            if row_id < i and col_id < j:
                new_pos.append(ans)
        ans_pos = np.array(new_pos, dtype=int)
        return ans_pos

    # 回傳當下追蹤結果
    def get_track_result(self):
        track_results = []
        for t in self.tracker_list:
            result = [t.id]
            result.extend(t.get_last_result())
            track_results.append(result)
        return track_results

    # 設定追蹤歷史
    def set_tracker_to_history(self):
        for t in self.tracker_list:
            (tid, stime, etime, feature) = t.get_table_data()
            if tid not in self.tracker_history:
                self.tracker_history[tid] = {}
            self.tracker_history[tid]['stime'] = stime
            self.tracker_history[tid]['etime'] = etime
            self.tracker_history[tid]['feature'] = feature
    
    # 取得追蹤紀錄
    def get_tracker_history(self):
        return self.tracker_history

    # 檢查 tracker 是否離開
    def is_tracker_exit(self, tracker:Tracker):
        # 檢查停留禎數 
        if tracker.frame_count < 5:
            # < 5保留
            tracker.frame_count += 1
            return False
        else:
            # > 5 格視為離開 
            return True
    
    # 新增 tracker 
    def new_tracker(self, gtime, img, result):
        tracker = Tracker(self.trackid)
        tracker.set_box(gtime, img, result)
        self.trackid += 1
        return tracker

    # 過濾不需要的物件
    def filter_results(self, results):
        new_results = []
        for result in results:
            conf, cls = result[4], int(result[5])
            if conf > self.conf_filter and cls == self.track_class_id:
                new_results.append(result.detach().numpy())
        return new_results

    # 計算 物件和追蹤者的 iou 矩陣
    def count_iou_mat(self, results:list, untrack_list:list):
        iou_matrix = []
        for result in results:
            xyxy = result[0:4]
            # 每個 result 對 tracker 比較
            eval_table = [] # 評估表
            for tracker in untrack_list:
                # 取得 tracker 最新追蹤的 box
                coord = tracker.get_last_coord()
                # 計算 iou
                iou = self.count_iou(xyxy, coord)
                eval_table.append(iou)
            iou_matrix.append(eval_table)
        return iou_matrix
    
    #計算IoU
    def count_iou(self, cA, cB):
        Ax1, Ay1, Ax2, Ay2 = cA
        Bx1, By1, Bx2, By2 = cB

        #計算 cA cB 交集矩形面積 
        ox1, oy1 = max(Ax1, Bx1), max(Ay1, By1)
        ox2, oy2 = min(Ax2, Bx2), min(Ay2, By2)
        #面積 = 最小重疊矩型面積長*寬
        overlap = max(0, ox2 - ox1 + 1) * max(0, oy2 - oy1 + 1)

        #計算 cA cB 聯集面積 = cA 面積 + cB面積 - 交集面積 
        avg_w = ((Ax2 - Ax1 + 1) + (Bx2 - Bx1 + 1))/2
        A = avg_w * (Ay2 - Ay1 + 1)
        B = avg_w * (By2 - By1 + 1)
        union = A + B - overlap

        #iou = 交集面積/聯集面積
        iou = overlap/union
        return iou
