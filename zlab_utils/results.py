import numpy as np

class DResults():
    def __init__(self) -> None:
        """
            self.box -> numpy ex:[x1,y1, x2,y2] float64
            self.kpts -> numpy ex:[x1,y1,c1, x2,y2,c2, ...] float64
            self.mask -> numpy ex: shape(480, 640, 3) int8
            self.conf -> float
            self.cls -> int
            self.track_id -> int
        """
        self.box = None
        self.kpts = None
        self.mask = None
        self.conf = None
        self.cls = None
        self.track_id = None
    
    def set_box(self, box:np.array):
        self.box = box
    
    def get_cv_box(self):
        """
            return (c1, c2) c1 = (int, int), c2 = (int, int)
        """
        int_box = [int(e) for e in self.box]
        return (int_box[0], int_box[1]), (int_box[2], int_box[3])


    
    def set_kpts(self, kpts:np.array):
        self.kpts = kpts
    
    def set_mask(self, mask:np.array):
        self.mask = mask
    
    def set_conf(self, conf:float):
        self.conf = conf

    def set_cls(self, cls:int):
        self.cls = cls

    def set_track_id(self, id:int):
        self.track_id = id


