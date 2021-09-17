# !/usr/bin/env python
# -*- coding: utf-8 -*- 

"""
    Motion Analysis
"""
import asyncio
import cv2
import copy
import numpy as np
from matplotlib import pyplot as plt
import os
import time
import math
import base64

from analysis import motionutils


class Motion():
    """
        Motion Analysis
    """

    #def __init__(self, degree = 10, points = None, msger = None, hotmapReturnMode = 0):
    def __init__(self, **kwargs):
        """
            Initialization function

            Parameters
            ----------
            degree : int, optional
                        Threshold of image similarity
                        Default value is 10
            points : array_like, optional
                        Vertex coordinates of the detection area
                        Default value is None
            msger : Messager, optional
                        Send the detected data to other
                        Default value is None
            hotmapReturnMode : int, optional
                        The mode that return hot map to caller
                        Default value is 0
                            0: file path
                            1: base64 string
                    
            Returns
            -------
        """
        self.points = kwargs.get('points')
        self.degree = kwargs.get('degree', 10)
        # 对图像进行二值化处理所需要的一些阈值
        self.threshold = 2
        self.maxValue = 2
        # 睡眠时间
        self.sleepTimes = 0.05
        # 消息发送器
        self.msger = kwargs.get('msger')
        # 热点图的返回方式
        self.hotmapReturnMode = kwargs.get('hotmapReturnMode', 0)
        # hot map图片的存储目录
        self.hotmapDir = 'hotmap'


    async def motionDetect4Video(self, videoFile):
        """
            Motion detection based on video

            Parameters
            ----------
            videoFile : String
                        The video file to be detected
                    
            Returns
            -------
        """

        # 参数检查
        if (videoFile is None) or (not os.path.exists(videoFile)):
             print(f'The video({videoFile}) does not exist')
             return

        # 打开视频
        capture = cv2.VideoCapture(videoFile)

        # 视频不存在
        if not capture.isOpened:
            print(f'The video file({videoFile}) does not exist')
            return

        # 获取视频相关的参数
        # 帧率
        fps = int(capture.get(cv2.CAP_PROP_FPS))
        # 总帧数
        frameCount = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        # 宽度
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        # 高度
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # 当前帧
        currentFrame = None
        # 上一帧 
        lastFrame = None
        # 发生motion的时间点
        motionTimes = []

        # 参数检查
        if fps <= 0 or frameCount <=0 or width <= 0 or height <= 0:
            print('Invalid video')
            return


        # 获取背景剪裁器
        backgroundSubtractor = cv2.bgsegm.createBackgroundSubtractorMOG()
        accumulatedImage = None

        # 没有指定检测区域，则默认检测整个图像区域
        if self.points is None:
            accumulatedImage = np.zeros((height, width), np.uint8)


        # 遍历所有的帧
        for i in range(0, frameCount):

            # 读取一帧数据
            (ret, currentFrame) = capture.read()

            # 判断是否是有效帧
            if not ret:
                continue
            if currentFrame is None:
                continue

            if self.points is not None:
                # 裁剪图片
                currentFrame = motionutils.getROI(currentFrame, self.points)

            # [高|宽|像素值]
            if accumulatedImage is None:
                roiHeight, roiWidth = currentFrame.shape[0:2]
                accumulatedImage = np.zeros((roiHeight, roiWidth), np.uint8)

            # 为计算热力图做数据准备
            # 移除背景
            filter = backgroundSubtractor.apply(currentFrame)
            # 二值化
            ret, thresh = cv2.threshold(filter, self.threshold, self.maxValue, cv2.THRESH_BINARY)
            # 去除图像噪声,先腐蚀再膨胀
            thresh = cv2.erode(thresh,None, iterations=1) 
            thresh = cv2.dilate(thresh, None, iterations=2) 
            # 相加
            accumulatedImage = cv2.add(accumulatedImage, thresh)

            # 是否是第一帧
            if lastFrame is None:
                # 设置上一帧
                lastFrame = copy.deepcopy(currentFrame)
                continue

            # 只处理每秒内第一帧的数据
            if (i + 1) % fps != 0:
                continue

            # 计算上一帧与当前帧的相似度
            degree = motionutils.calculateDegreeBasePHash(lastFrame, currentFrame)

            # 大于指定阈值
            if degree > self.degree:
                milliseconds = capture.get(cv2.CAP_PROP_POS_MSEC)
                motionTimes.append(milliseconds)
                print('Changed: ', milliseconds, ' degree: ', degree)
                # 发送消息
                if self.msger is not None:
                    await self.msger.send({'timestamp': milliseconds, 'degree' : degree})

            # 设置上一帧
            lastFrame = copy.deepcopy(currentFrame)

            # sleep
            time.sleep(self.sleepTimes)


        # 计算热点图
        hotmapImage = cv2.applyColorMap(accumulatedImage, cv2.COLORMAP_HOT)
        # 转换成PNG图像，相对于其它图像，PNG图像多了一个透明通道
        pngImage = cv2.cvtColor(hotmapImage, cv2.COLOR_BGR2BGRA)
        # 将255改变成0
        pngImage[np.all(pngImage == [0, 0, 0, 255], axis=2)] = [0, 0, 0, 0]

        # points不为空，则进行重新resize
        if self.points is not None and pngImage.shape[0:2] != (width, height):
            pngImage = cv2.resize(pngImage, (width, height))

        # 根据指定返回hot map的方式进行处理
        returnedHotmap = None
        # 返回文件路径
        if self.hotmapReturnMode == 0:
            # 存储文件
            # 目录不存在则创建目录
            if not os.path.exists(self.hotmapDir):
                os.mkdir(self.hotmapDir)
            returnedHotmap = os.path.join(os.getcwd(), self.hotmapDir, 
                                          time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime()) + '.png')
            cv2.imwrite(returnedHotmap, pngImage)
        elif self.hotmapReturnMode == 1:
            returnedHotmap = base64.b64encode(pngImage).decode()

        # 结束消息
        if self.msger is not None:
            await self.msger.end({'hotmapImg': returnedHotmap})

        # 显示热力图
        plt.imshow(pngImage)
        plt.show()



    async def motionDetect4Images(self, imageFiles):
        """
            Motion detection based on images

            Parameters
            ----------
            imageFiles : imageFiles
                        The image files to be detected
                    
            Returns
            -------
        """

        # 参数检查
        if imageFiles is None:
             print(f'The image file({imageFiles}) does not exist')
             return

        # 获取背景剪裁器
        backgroundSubtractor = cv2.bgsegm.createBackgroundSubtractorMOG()
        accumulatedImage = None

        # 上一张图片
        lastImage = None
        # 当前图片
        currentImage = None

        # 原始图片的大小
        originalHeight = None
        originalWidth = None

        # motion发生的时刻
        motionTimes = []

        # 遍历进行处理
        for imageFile in imageFiles:
            # 检查图片是否真实存在
            if (imageFile is None) or (not os.path.exists(imageFile)):
                print(f'The image file({imageFile}) does not exist')
                continue

            # 读取图片
            currentImage = cv2.imread(imageFile)
            # 获取图片的高度、宽度
            height, width = currentImage.shape[0:2]
            originalHeight = height
            originalWidth = width

            # 没有指定检测区域，则默认检测整个图像区域
            if self.points is not None:
                # 裁剪图片
                currentImage = motionutils.getROI(currentImage, self.points)
                height, width = currentImage.shape[0:2]

            # 初始化accumulatedImage
            if accumulatedImage is None:
                accumulatedImage = np.zeros((height, width), np.uint8)
            
            # 检查图片的形状是否一样
            if lastImage is not None and lastImage.shape != currentImage.shape:
                print(f'The image file({imageFile}) not the same shape')
                continue

            # 为计算热力图做数据准备
            # 移除背景
            filter = backgroundSubtractor.apply(currentImage)
            # 二值化
            ret, thresh = cv2.threshold(filter, self.threshold, self.maxValue, cv2.THRESH_BINARY)
            # 去除图像噪声,先腐蚀再膨胀
            thresh = cv2.erode(thresh,None, iterations=1)
            thresh = cv2.dilate(thresh, None, iterations=2) 
            # 相加
            accumulatedImage = cv2.add(accumulatedImage, thresh)

            # 初始化第一张图像
            if lastImage is None:
                lastImage = copy.deepcopy(currentImage)
                continue

            # 计算上一帧与当前帧的相似度
            degree = motionutils.calculateDegreeBasePHash(lastImage, currentImage)

            # 大于指定阈值
            if degree > self.degree:
                milliseconds = capture.get(cv2.CAP_PROP_POS_MSEC)
                motionTimes.append(milliseconds)
                print('Changed: ', milliseconds, ' degree: ', degree)
                # 发送消息
                if self.msger is not None:
                    await self.msger.send({'timestamp': milliseconds, 'degree' : degree})

            # 设置上一幅图片
            lastImage = copy.deepcopy(currentImage)

            # sleep
            time.sleep(self.sleepTimes)

    
        # 计算热点图
        hotmapImage = cv2.applyColorMap(accumulatedImage, cv2.COLORMAP_HOT)
        # 转换成PNG图像，相对于其它图像，PNG图像多了一个透明通道
        pngImage = cv2.cvtColor(hotmapImage, cv2.COLOR_BGR2BGRA)
        # 将255改变成0
        pngImage[np.all(pngImage == [0, 0, 0, 255], axis=2)] = [0, 0, 0, 0]

        # points不为空，则进行重新resize
        if self.points is not None and pngImage.shape[0:2] != (originalWidth, originalHeight):
            pngImage = cv2.resize(pngImage, (originalWidth, originalHeight))

        # 根据指定返回hot map的方式进行处理
        returnedHotmap = None
        # 返回文件路径
        if self.hotmapReturnMode == 0:
            # 存储文件
            # 目录不存在则创建目录
            if not os.path.exists(self.hotmapDir):
                os.mkdir(self.hotmapDir)
            returnedHotmap = os.path.join(os.getcwd(), self.hotmapDir, 
                                time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime()) + '.png')
            cv2.imwrite(returnedHotmap, pngImage, [cv2.IMWRITE_JPEG_QUALITY, 100])
        elif self.hotmapReturnMode == 1:
            returnedHotmap = base64.b64encode(pngImage).decode()

        # 结束消息
        if self.msger is not None:
            await self.msger.end({'hotmapImg': returnedHotmap})

        # 显示热力图
        plt.imshow(pngImage)
        plt.show()


if __name__ == '__main__':
    
    start = time.perf_counter()


    # 测试参数
    points = [
        [
            89.1232876712329,
            117.1232876123287
        ],
        [
            517.47945205479454,
            215.06849315068493
        ],
        [
            398.71232876712332,
            823.28767123287672
        ]
    ]

    degree = 10


    # 视频和图像路径
    videoFile = 'E:\资料\临时文件\D-Link\Projects\DNH200\SmartSearch\CH05.mp4'
    images = ['D:\\projects\\self\\python\\data_images\\testL0_.png', 
              'D:\\projects\\self\\python\\data_images\\testL0.png']

    # 构造对象
    motionDetector = MotionDetector(degree = degree, points = points, hotmapReturnMode = 1)
    motionDetector.motionDetect4Video(videoFile)
    #motionDetector.motionDetect4Images(images)


    print('Method execution time: ',  math.ceil(time.perf_counter() - start), ' seconds')

