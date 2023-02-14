# 人工智慧影像處理虛實整合系統

## 簡介
* 本系統為開發和整合多個影像處理技術並應用在實際或虛擬的場景上。
* 我們整合了 yolov7、yolo-pose、yolo-segementation 的影像辨識模組，並使用卡爾曼濾波器來追蹤辨識的結果。
* 在應用的層面上我們實現的功能有：
    * 標註行人移動的軌跡、關節點、編號、輪廓
      ![](https://github.com/sheng1124/zlab/blob/main/demo/v0.gif)
    * 將人物從影像上刪除、打馬賽克、遮蔽、隱藏
      ![](https://github.com/sheng1124/zlab/blob/main/demo/g0.gif)
    * 將人物合成到虛擬背景上、去除多餘背景、虛化背景
      ![](https://github.com/sheng1124/zlab/blob/main/demo/b0.gif)
      ![](https://github.com/sheng1124/zlab/blob/main/demo/n0.gif)
 
## 環境要求
* 建議硬體環境
    * CPU : intel i5, i7 第10代
    * GPU : RTX 3060
    * Macbook M1、M2
* 作業系統
    * MacOS、Windows 10 11、Ubuntu 20.04 
* 環境安裝
    * 安裝 python 3.9
        * 參考安裝
    * nvidia GPU 需要安裝 cuda、cuDNN
        * cuda >= 10.2、11.3、11.6
        * 參考安裝
    * 安裝合適的 pytorch 版本(>1.12.1)，
        * cuda 版本需要參考官網安裝
    * 使用 pip 安裝 requirement.txt 的套件

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


* 黑/白名單功能
    * 黑名單模式是針對某些特定編號的物件進行影像後製，例如：在影片上對編號 1 的物件打馬賽克。
    * 白名單模式是對特定編號以外的範圍進行影像後製，例如：除了編號 1 的影像都打馬賽克。
    * 不同的模型會有額外的功能可以選擇，例如： yolo segement 可以選擇使用分割影像處理特定部位

    

## 使用說明、範例
* 標註行人的位置、編號
    * 設定顯示內容： ☑ 標註物件編號框
    ![](https://i.imgur.com/ARpiHxn.png)
    ![](https://i.imgur.com/wYS9kNP.png)

* 標註行人移動的軌跡
    * 設定顯示內容： ☑ 標註追蹤軌跡
    ![](https://i.imgur.com/8T7TMj9.png)
    ![](https://i.imgur.com/bxkZ3Lr.png)



* 標註行人的關節點
    * 

* 標註行人關節點的移動軌跡
* 標註行人的輪廓、分割影像

* 刪除特定人物影像
* 特定人物打馬賽克
* 替換特定人物影像
* 特定人物隱形

* 
