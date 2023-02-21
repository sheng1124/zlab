# 人工智慧影像處理虛實整合系統

## 簡介
* 本系統為開發和整合多個影像處理技術並應用在實際或虛擬的場景上。
* 我們整合了 yolov7、yolo-pose、yolo-segementation 的影像辨識模組，並使用卡爾曼濾波器來追蹤辨識的結果。
* 在應用的層面上我們實現的功能有：
    * 標註行人移動的軌跡、關節點、編號、輪廓
      ![](https://github.com/sheng1124/zlab/blob/main/demo/v0.gif)
    * 將人物從影像上刪除、打馬賽克、遮蔽、隱藏
      ![](https://github.com/sheng1124/zlab/blob/main/demo/g1.gif)
    * 將人物合成到虛擬背景上、去除多餘背景、虛化背景
      ![](https://github.com/sheng1124/zlab/blob/main/demo/b0.gif)
      ![](https://github.com/sheng1124/zlab/blob/main/demo/n2.gif)
 
## 環境要求
* 建議硬體環境
    * CPU : intel i5, i7 第10代
    * GPU : RTX 3060
    * Macbook M1、M2
* 作業系統
    * MacOS、Windows 10 11、Ubuntu 20.04 
* 環境安裝
    1. 安裝 python 3.9
        * [參考安裝](https://medium.com/datainpoint/python-essentials-conda-quickstart-1f1e9ecd1025)
    * nvidia GPU 需要安裝 cuda、cuDNN
        * cuda >= 11.3、11.6
        * [參考安裝](https://zhuanlan.zhihu.com/p/106133822)
    2. 安裝合適的 pytorch 版本(>1.12.1)，
        * cuda 版本需要參考官網安裝
        * 如圖所示，若cuda版本為11.7必須加上```--extra-index-url https://download.pytorch.org/whl/cu117```
        ![](https://i.imgur.com/OXkY8zs.png)

    3. 使用 pip 安裝 zlab/requirement.txt 的套件

## 系統介面
* MacOS
    ![](https://i.imgur.com/NJZNcHc.png)

* Windows 11
    ![](https://i.imgur.com/T5MiiBB.png)

* 開啟系統
    * 開啟 zlab 目錄，執行 do_tracking.py

* 選擇 AI 模型
    * 目前可用的模型有 Yolo v7, Yolo Pose, Yolo segement
    * 開始執行時便不能選擇
    * 開始前要開啟模型對應的類神經網路權重檔
    ![](https://i.imgur.com/SwifqNd.png)
    
* 設定追蹤條件
    * 目前使用的追蹤方式為 IoU 比對和卡爾曼濾波器。
    * 模型偵測輸出的類別為數值的表示方法，0 可能代表人，1 可能代表汽車，每個類神經網路權重的類別輸出數值可能代表不同的種類，必須參考訓練用的類神經網路權重檔的類別檔。
    * 模型偵測後的物件有信心分數，為模型是否判斷預測正確的指標，0~1，信心分數越接近1代表模型預測的物件位置越準確，若將信心門檻拉高，意味者只有預測後的物件的信心分數高於這個數值才會被追蹤，若發現物件的編號斷斷續續請將門檻拉低。
    ![](https://i.imgur.com/tvbjZli.png)
    
* 設定輸入來源
    * 辨識影像需要有圖片，所以需要開啟資料夾或是影片或是相機
        * 若要開啟資料夾必須將要辨識的圖片放進資料夾且每張圖片的尺寸要一樣
        * 若要開啟相機(筆電視訊鏡頭、USB 攝影機)必須確認相機連接正確，系統會自動偵測
        * 確認好模型選擇、權重檔有開啟、來源有選擇好就可以按下開始辨識&追蹤，執行時可以按下暫停辨識&追蹤調整右側視窗顯示的內容，按下停止辨識&追蹤或是辨識完所有的影片或影像即會停止模型，此時可以重新選擇輸入來源。
    ![](https://i.imgur.com/SZa6wQA.png)

* 輸出視窗
    * 右側視窗會顯示追蹤後的結果並且會將辨識影像儲存成到程式目錄底下的 results 資料夾。
    ![](https://i.imgur.com/Qw6wD4O.jpg)

* 表格清單
    * 右側表格會呈現系統追蹤物件後的清單，會有物件的編號、物件出現和離開的時間，單位秒數，且會擷取人物特徵
    ![](https://i.imgur.com/0pQ6vDJ.png)

* 設定顯示內容
    * 可以設定的顯示內容會以模型選擇的不同而有所限制，例如：無法輸出關節點的模型便無法設定可以顯示的關節點和軌跡。
        ![](https://i.imgur.com/gaHUafB.png)

    * 通用：
        * 標註物件編號框：將追蹤後的物件編號和位置標註在影像上
        * 標註追蹤軌跡：將物件開始移動的軌跡標註在影像上
        * 標註偵測到的物件(紅線)：顯示當下模型辨識出來的物件位置，以紅色的細框來標注，通常用來測試模型是否有辨識到物件
        ![](https://i.imgur.com/GPE7M6C.png)

    * 關節點：
        * 顯示關節點：將追蹤後的人物的關節點標註在影像上
        * 顯示特定關節點軌跡：顯示人物特定編號關節點出現到目前位置的移動軌跡，可輸入多個編號，使用","分隔編號 ex: 1,2,4
        ![](https://i.imgur.com/wxTfBYe.png)
    
    * 分割：
        * 顯示分割：將追蹤後的人物的分割影像標注在影像上，可以明確了解分割模型偵測的範圍在影像上哪個地方。
        

* 黑/白名單功能
    * 黑名單模式是針對某些特定編號的物件進行影像後製，例如：在影片上對編號 1 的物件打馬賽克。
    * 白名單模式是對特定編號以外的範圍進行影像後製，例如：除了編號 1 的影像都打馬賽克。
    * 不同的模型會有額外的功能可以選擇，例如： yolo segement 可以選擇使用分割影像處理特定部位
    * 影像後製的方式有影像塗黑、打馬賽克、影像替換、影像融合，黑白名單模式都會有不同的效果，可以用不同的後製方法來做到一些特殊功能。
    * 可以輸入多個編號 ex: 1,2,4
    * 在某些後製功能中可以調整物件的範圍，長寬度修正是指將後製的範圍，例如：寬度修正10可以讓打馬賽克的範圍變寬 10 像素點
    ![](https://i.imgur.com/sNkKn8t.png)
    ![](https://i.imgur.com/qOIZFoF.png)


## 使用說明、範例
* 標註行人的位置、編號
    * 設定顯示內容： 勾選標註物件編號框
    ![](https://i.imgur.com/ARpiHxn.png)
    ![](https://i.imgur.com/wYS9kNP.png)



* 標註行人移動的軌跡
    * 設定顯示內容： 勾選標註追蹤軌跡
    ![](https://i.imgur.com/8T7TMj9.png)
    ![](https://i.imgur.com/bxkZ3Lr.png)



* 標註行人的關節點
    * 選擇 AI 模型 YOLOv7 Pose
    * 設定顯示內容： 勾選顯示關節點
    ![](https://i.imgur.com/AIjDW52.png)
    ![](https://i.imgur.com/XDmEH9w.png)



* 標註行人關節點的移動軌跡
    * 選擇 AI 模型 YOLOv7 Pose
    * 設定顯示內容： 顯示特定關節點的軌跡，輸入要觀察的關節點軌跡，逗號分割
    ![](https://i.imgur.com/xH3Yx8N.png)
    ![](https://i.imgur.com/9tkYXGO.png)



* 標註行人的輪廓、分割影像
    * 選擇 AI 模型 YOLOv8 segement
    * 設定顯示內容： 勾選顯示分割
    ![](https://i.imgur.com/XAMiBUp.png)
    ![](https://i.imgur.com/6qsXYTA.png)



* 刪除特定人物影像
    1. 選擇黑名單模式，輸入要刪除人物的編號
    2. 黑名單處理方式：黑布條遮蔽
    3. 長寬修正：輸入要調整邊界框大小的範圍
    ![](https://i.imgur.com/9vKEQzb.png)
    ![](https://i.imgur.com/U9lKlFp.jpg)
    1. 選擇 AI 模型 YOLOv8 segement
    2. 勾選使用分割遮罩
    3. 選擇黑名單模式，輸入要刪除人物的編號
    4. 黑名單處理方式：黑布條遮蔽
    ![](https://i.imgur.com/5et3D1X.png)
    ![](https://i.imgur.com/ZKzuF6J.jpg)
    
    

* 刪除特定人物背景
    1. 選擇 AI 模型 YOLOv8 segement
    2. 勾選使用分割遮罩
    3. 選擇黑名單模式，輸入要刪除人物的編號
    4. 黑名單模式: 刪除背景
    ![](https://i.imgur.com/lZSmlcr.png)
    ![](https://i.imgur.com/SEK33px.png)



* 特定人物打馬賽克
    1. 選擇黑名單模式，輸入要刪除人物的編號
    2. 黑名單處理方式：打馬賽克
    3. 長寬修正：輸入要調整邊界框大小的範圍
      ![](https://i.imgur.com/0bPo3cM.png)
      ![](https://i.imgur.com/x8u0cO4.jpg)
    1. 選擇 AI 模型 YOLOv8 segement
    2. 黑名單處理方式：打馬賽克
    3. 勾選使用分割遮罩
    4. 選擇黑名單模式，輸入要刪除人物的編號
      ![](https://i.imgur.com/x8a0Iiw.png)
      ![](https://i.imgur.com/L9C4obB.jpg)
  


* 特定人物背景虛化
    1. 選擇 AI 模型 YOLOv8 segement
    2. 勾選使用分割遮罩
    3. 選擇白名單模式，輸入要保留人物的編號
    4. 白名單處理方式：背景馬賽克
      ![](https://i.imgur.com/qZMY0Zq.png)
      ![](https://i.imgur.com/fkboGBI.png)



* 替換特定人物影像
    1. 選擇黑名單模式，輸入要刪除人物的編號
    2. 黑名單處理方式：底圖覆蓋
    3. 長寬修正：輸入要調整邊界框大小的範圍
    4. 開啟底圖的圖片位置
    ![](https://i.imgur.com/LJesjIP.png)
    ![](https://i.imgur.com/PmILZD5.jpg)



* 特定人物影像替換背景
    1. 選擇 AI 模型 YOLOv8 segement
    2. 勾選使用分割遮罩
    3. 選擇白名單模式，輸入要保留人物的編號
    4. 白名單處理方式：換背景
    5. 開啟底圖的圖片位置
    ![](https://i.imgur.com/IOlHald.png)
    ![](https://i.imgur.com/5pLnXBh.jpg)



* 特定人物隱形
    1. 選擇黑名單模式，輸入要刪除人物的編號
    2. 黑名單處理方式：底圖覆蓋
    3. 長寬修正：輸入要調整邊界框大小的範圍
    4. 開啟底圖的圖片位置
    ![](https://i.imgur.com/SKWxY9a.png)
    ![](https://i.imgur.com/Fa97UGC.jpg)



* 特定人物影像融合進新背景
    1. 選擇 AI 模型 YOLOv8 segement
    2. 勾選使用分割遮罩
    3. 選擇白名單模式，輸入要保留人物的編號
    4. 白名單處理方式：影像融合
    5. 開啟底圖的圖片位置
    ![](https://i.imgur.com/3Ml0Gtp.png)
    ![](https://i.imgur.com/pOXTMyy.jpg)


# 資料儲存
* 當系統追蹤完時，會在 zlab 資料夾中的 results 建立以目前時間點的資料夾(ex: Feb--9-14-45-37)格式為 月--日-時-分-秒
* 在這些資料夾中會生成 detect 資料夾和一個csv檔
* detect 資料夾中會生成所有系統追蹤後製的圖片，會以秒的單位建立檔名
    ![](https://i.imgur.com/Sg7zeFD.png)
* 可以利用在 video_tool 資料夾裡的 vt.py 將 detect 資料夾的圖片轉成影片
* csv 格式的資料紀錄所有追蹤的結果
    * filename: 對應的後製圖片檔名，可到 detect 資料夾中查看
    * classname: 物件類別對應的id
    * id: 追蹤的id
    * x0, y0, x1, y1: 物件的偵測框的座標
    * conf： 判斷物件是否正確偵測到的程度
    * kpts: 關節點座標，若使用 yolo pose 模組會有這個資料
    ![](https://i.imgur.com/gsEH40G.png)


# 資料下載
* 類神經網路權重檔(pretrain model)
    * yolov7
        * [v7](https://github.com/WongKinYiu/yolov7/releases/download/v0.1/yolov7.pt)
    * yolo-pose
        * [w6](https://github.com/WongKinYiu/yolov7/releases/download/v0.1/yolov7-w6-pose.pt)
    * yolo-segment
        * [v8l](https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8l-seg.pt)
        * [v8x(參數較大，精確度高，速度慢)](https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8x-seg.pt)
    * 備註：若要使用自己的模型要確認是否是 yolov7 v8 可讀取的模型架構，詳細請看參考資料
* 影像資料
    * 不提供影像資料，請自行錄影成 mp4 的格式
    * 若要自行錄影可以使用 video_tool 裡的 vt.py 程式可以選擇存成影像或影片

# 參考資料
* Yolo v7
    * [github](https://github.com/WongKinYiu/yolov7)
* Yolo v8
    * [github](https://github.com/ultralytics/ultralytics)
