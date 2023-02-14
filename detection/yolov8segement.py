from ultralytics import YOLO # yolo v8
import numpy as np

from ultralytics.yolo.utils.ops import scale_image

from zlab_utils.results import DResults

class YoloV8SegementAPI():
    def __init__(self, weights, device=None, img_size = 640) -> None:
        # 載入類神經網路
        self.weights = weights
        #self.half = device.type != 'cpu' and device.type != 'mps' # half precision only supported on CUDA
        #self.device = device

        model = YOLO(weights)
        model.overrides['verbose'] = False

        self.names = model.module.names if hasattr(model, 'module') else model.names
        self.colors = [[np.random.randint(0, 255) for _ in range(3)] for _ in self.names]
        
        self.model = model
        self.img_size = img_size
        
    # 偵測圖片，輸入影像，回傳偵測結果
    def detect(self, img0):
        # detect
        img0_shape = (img0.shape[0], img0.shape[1])
        rs = self.model(img0)[0]

        boxes = rs.boxes
        masks = rs.masks.data
        pred = []
        for i, box in enumerate(boxes):
            # [x1, y1, x2, y2, conf, cls, mask]
            box = box.data[0].cpu().detach().numpy()
            mask = (masks[i] *255).cpu().byte().detach().numpy()

            # 座標、尺寸轉換
            img1_shape = (mask.shape[0], mask.shape[1])
            mask = scale_image(img1_shape, mask, img0_shape)

            # 設定 dresult
            ds = DResults()
            ds.set_box(box[0:4])
            ds.set_conf(box[4])
            ds.set_cls(int(box[5]))
            ds.set_mask(mask)
            
            pred.append(ds)

        return pred
    

if __name__ == '__main__':
    p = '/Users/shengfu/Desktop/project/zlab/data/images/1670774408.3784478.jpg'
    w = '/Users/shengfu/Desktop/project/zlab/yolov8l-seg.pt'

    k = YoloV8SegementAPI(w)
    import cv2
    im = cv2.imread(p)

    pred = k.detect(im)

    for rs in pred:
        x1, y1, x2, y2 = rs[0], rs[1], rs[2], rs[3]
        conf, cls = rs[4], int(rs[5])

        print(x1, x2, y1, y2)
        im = cv2.rectangle(im, (int(x1), int(y1)), (int(x2), int(y2)), (255, 255, 255), 1, lineType=cv2.LINE_AA)

        print(conf, cls)


    while 1:

        cv2.imshow('oxxostudio', im)
        if cv2.waitKey(1) == ord('q'):
            break     # 按下 q 鍵停止

    cv2.destroyAllWindows()


