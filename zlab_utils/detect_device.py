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