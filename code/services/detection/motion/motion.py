# !/usr/bin/env python
# -*- coding: utf-8 -*- 

"""
    Motion Analysis
"""
import asyncio
import json

import cv2
import copy
import numpy as np
from matplotlib import pyplot as plt
import os
import time
import math
import base64

from services.detection.motion import motionutils


class Motion():
    """
        Motion Detection
    """

    def __init__(self, **kwargs):
        """
            Initialization function

            Parameters
            ----------
            degree : int, optional
                        Threshold of image similarity
                        Default value is 10
            regions : array_like, optional
                        Vertex coordinates of the detection area
                        Default value is None
            msger : Messager, optional
                        Send the detected data to caller
                        Default value is None
            hotmap : int, optional
                        Does it need to generate a hotmap?
                        Default value is 0
                            0: Do not generate hotmap
                            1: Generate hotmap and return the file path of image
                            2: Generate hotmap and return the base64 string of image
                    
            Returns
            -------
        """
        self.regions = kwargs.get('regions')
        self.degree = kwargs.get('degree', 10)
        # 对图像进行二值化处理所需要的一些阈值
        self.threshold = kwargs.get('threshold', 2)
        self.maxValue = kwargs.get('maxValue', 2)
        # 睡眠时间
        self.sleepTimes = kwargs.get('sleepTimes', 0.1)
        # 消息发送器
        self.msger = kwargs.get('msger')
        # 是否生成hotmap并且返回的方式
        self.hotmap = kwargs.get('hotmap', 0) or 0
        # hot map图片的存储目录
        self.defaultHotmapDir = 'hotmap'
        self.hotmapDir = kwargs.get('hotmapDir', self.defaultHotmapDir) or self.defaultHotmapDir

    async def motionDetect(self, sources):
        """
            Motion detection

            Parameters
            ----------
            sources : array_like
                        The video or image files to be detected
                    
            Returns
            -------
            source : string, optional
                        The source name
            degree : int, optional
                        The value of similarity
            index : int or string, optional
                        The time or index of the motion
            hotmapImg : string, optional
                        hot map image
			progress : int
						Motion detection progress

        """

        # 参数检查
        if sources is None:
            print('Invalid sources value')
            return
			
		# 进行数据拆分，拆分为video和image
        videoFiles = []
        imageFiles = []
        for source in sources:
            # 检查文件是否真实存在
            if (source is None) or (not os.path.exists(source)):
                print('The file {0} does not exist'.format(source))
                continue
            # 获取文件后缀
            suffixName = os.path.splitext(source)[1]
            if suffixName in ['.mp4']:
                videoFiles.append(source)
            elif suffixName in ['.bmp', '.jpeg', '.jpg', '.png']:
                imageFiles.append(source)
            else:
                print('Unsupported file format {0}'.format(suffixName))


        # 视频方式
        await self.motionDetect4Videos(videoFiles)
        # 图片方式
        await self.motionDetect4Images(imageFiles)


    async def motionDetect4Videos(self, videoFiles):
        """
            Motion detection based on videos file

            Parameters
            ----------
            videoFiles : array_like
                        The video files to be detected
                    
            Returns
            -------
            source : string, optional
                        The source name
            degree : int, optional
                        The value of similarity
            index : int, optional
                        The time or index of the motion
            hotmapImg : string, optional
                        hot map image
			progress : int
						Motion detection progress						
        """

        # 参数检查
        if videoFiles is None or len(videoFiles) < 1:
            print('Empty video files')
            return

        # 遍历进行处理
        for videoFile in videoFiles:
            # 检查视频路径是否真实存在
            if (videoFile is None) or (not os.path.exists(videoFile)):
                print('The video file({0}) does not exist'.format(videoFile))
                continue

            # 进行视频检测
            await self.motionDetect4Video(videoFile)

    async def motionDetect4Video(self, videoFile):
        """
            Motion detection based on video file

            Parameters
            ----------
            videoFile : String
                        The video file to be detected
                    
            Returns
            -------
            source : string, optional
                        The source name
            degree : int, optional
                        The value of similarity
            index : int, optional
                        The time or index of the motion
            hotmapImg : string, optional
                        hot map image
			progress : int
						Motion detection progress
        """

        # 参数检查
        if (videoFile is None) or (not os.path.exists(videoFile)):
            print('The video({0}) does not exist'.format(videoFile))
            return

        # 打开视频
        capture = cv2.VideoCapture(videoFile)

        # 视频不存在
        if not capture.isOpened:
            print(r'The video file({0}) does not exist'.format(videoFile))
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
        # 生成的hotmap
        hotmapImg = None
        # 发生motion的时间点
        motionTimes = []

        # 参数检查
        if fps <= 0 or frameCount <= 0 or width <= 0 or height <= 0:
            print('Invalid video')
            return

        # 背景剪裁器
        backgroundSubtractor = None
        accumulatedImage = None

        # 生成hotmap
        if (self.hotmap is not None) and (self.hotmap != 0) and (self.hotmap in [1, 2]):
            # 获取背景剪裁器
            backgroundSubtractor = cv2.bgsegm.createBackgroundSubtractorMOG()
            # 没有指定检测区域，则默认检测整个图像区域
            if self.regions is None:
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
				
			# 计算检测进度
            progress = int(i / frameCount * 100)

            if self.regions is not None:
                # 裁剪图片
                currentFrame = motionutils.getROI(currentFrame, self.regions)

            # 生成hotmap
            if (self.hotmap is not None) and (self.hotmap != 0) and (self.hotmap in [1, 2]):
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
                thresh = cv2.erode(thresh, None, iterations=1)
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
                    try:
                        self.msger.send(
                            {'source': videoFile, 'index': milliseconds, 'degree': degree, 'hotmapImg': None,
                             'progress': progress, 'status': 'process'})
                    except Exception as ex:
                        # 发生异常时，释放打开的文件句柄
                        capture.release()

            # 设置上一帧
            lastFrame = copy.deepcopy(currentFrame)

            # sleep
            await asyncio.sleep(self.sleepTimes)

        # 生成hotmap
        if (self.hotmap is not None) and (self.hotmap != 0) and (self.hotmap in [1, 2]):
            # 计算热点图
            colorMapImage = cv2.applyColorMap(accumulatedImage, cv2.COLORMAP_HOT)
            # 转换成PNG图像，相对于其它图像，PNG图像多了一个透明通道
            pngImage = cv2.cvtColor(colorMapImage, cv2.COLOR_BGR2BGRA)
            # 将255改变成0
            pngImage[np.all(pngImage == [0, 0, 0, 255], axis=2)] = [0, 0, 0, 0]

            # regions不为空，则进行重新resize
            if self.regions is not None and pngImage.shape[0:2] != (width, height):
                pngImage = cv2.resize(pngImage, (width, height))

            # 根据指定返回hot map的方式进行处理
            # 返回文件路径
            if self.hotmap == 1:
                # 存储文件
                # 目录不存在则创建目录
                if not os.path.exists(self.hotmapDir):
                    try:
                        os.mkdir(self.hotmapDir)
                        hotmapImg = os.path.join(self.hotmapDir, 
                                                      time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime()) + '.png')
                        cv2.imwrite(hotmapImg, pngImage)
                    except BaseException:
                        try:
                            if not os.path.exists(self.defaultHotmapDir):
                                os.mkdir(self.defaultHotmapDir)
                                hotmapImg = os.path.join(os.getcwd(), self.defaultHotmapDir, 
                                                    time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime()) + '.png')
                                cv2.imwrite(hotmapImg, pngImage)
                        except BaseException:
                            print('Invalid hot map directory')
            elif self.hotmap == 2:
                hotmapImg = base64.b64encode(pngImage).decode()

            # 显示热力图
            plt.imshow(pngImage)
            plt.show()

        # 结束消息
        if self.msger is not None:
            try:
                self.msger.send(
                    {'source': videoFile, 'index': None, 'degree': None, 'hotmapImg': hotmapImg, 'progress': 100,
                     'status': 'finish'})
            except Exception as ex:
                # 发生异常时，释放打开的文件句柄
                capture.release()

    async def motionDetect4Images(self, imageFiles):
        """
            Motion detection based on images

            Parameters
            ----------
            imageFiles : imageFiles
                        The image files to be detected
                    
            Returns
            -------
            source : string, optional
                        The source name
            degree : int, optional
                        The value of similarity
            index : string, optional
                        The time or index of the motion
            hotmapImg : string, optional
                        hot map image
			progress : int
						Motion detection progress
        """

        # 参数检查
        if imageFiles is None or len(imageFiles) < 1:
            print('Empty image files')
            return

        # 背景剪裁器
        backgroundSubtractor = None
        accumulatedImage = None

        # 生成hotmap
        if (self.hotmap is not None) and (self.hotmap != 0) and (self.hotmap in [1, 2]):
            # 获取背景剪裁器
            backgroundSubtractor = cv2.bgsegm.createBackgroundSubtractorMOG()

        # 上一张图片
        lastImage = None
        # 当前图片
        currentImage = None
        # 生成的hotmap
        hotmapImg = None

        # 原始图片的大小
        originalHeight = None
        originalWidth = None

        # 发生motion的图片
        motionFiles = []
		
		# 图片的总数
        imageCount = len(imageFiles)

        # 遍历进行处理
        for i in range(0, len(imageFiles)):
		    # 计算进度
            progress = int(i / imageCount * 100)
            # 图片路径
            imageFile = imageFiles[i]
            # 检查图片是否真实存在
            if (imageFile is None) or (not os.path.exists(imageFile)):
                print('The image file({0}) does not exist'.format(imageFile))
                continue

            # 读取图片
            currentImage = cv2.imread(imageFile)
            # 获取图片的高度、宽度
            height, width = currentImage.shape[0:2]
            originalHeight = height
            originalWidth = width

            # 没有指定检测区域，则默认检测整个图像区域
            if self.regions is not None:
                # 裁剪图片
                currentImage = motionutils.getROI(currentImage, self.regions)
                height, width = currentImage.shape[0:2]

            # 生成hotmap
            if (self.hotmap is not None) and (self.hotmap != 0) and (self.hotmap in [1, 2]):
                # 初始化accumulatedImage
                if accumulatedImage is None:
                    accumulatedImage = np.zeros((height, width), np.uint8)

            # 检查图片的形状是否一样
            if lastImage is not None and lastImage.shape != currentImage.shape:
                print('The image file({0}) not the same shape'.format(imageFile))
                continue

            # 生成hotmap
            if (self.hotmap is not None) and (self.hotmap != 0) and (self.hotmap in [1, 2]):
                # 为计算热力图做数据准备
                # 移除背景
                filter = backgroundSubtractor.apply(currentImage)
                # 二值化
                ret, thresh = cv2.threshold(filter, self.threshold, self.maxValue, cv2.THRESH_BINARY)
                # 去除图像噪声,先腐蚀再膨胀
                thresh = cv2.erode(thresh, None, iterations=1)
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
                motionFiles.append(imageFile)
                # print('Changed: ', milliseconds, ' degree: ', degree)
                # 发送消息
                if self.msger is not None:
                    try:
                        self.msger.send({'source': imageFile, 'index': imageFile, 'degree': degree, 'hotmapImg': None,
                                         'progress': progress, 'status': 'process'})
                    except Exception as ex:
                        # 发生异常时
                        print('Exception:', ex.__doc__)

            # 设置上一幅图片
            lastImage = copy.deepcopy(currentImage)

            # sleep
            await asyncio.sleep(self.sleepTimes)

        # 生成hotmap
        if (self.hotmap is not None) and (self.hotmap != 0) and (self.hotmap in [1, 2]):
            # 计算热点图
            colorMapImg = cv2.applyColorMap(accumulatedImage, cv2.COLORMAP_HOT)
            # 转换成PNG图像，相对于其它图像，PNG图像多了一个透明通道
            pngImage = cv2.cvtColor(colorMapImg, cv2.COLOR_BGR2BGRA)
            # 将255改变成0
            pngImage[np.all(pngImage == [0, 0, 0, 255], axis=2)] = [0, 0, 0, 0]

            # regions不为空，则进行重新resize
            if self.regions is not None and pngImage.shape[0:2] != (originalWidth, originalHeight):
                pngImage = cv2.resize(pngImage, (originalWidth, originalHeight))

            # 根据指定返回hot map的方式进行处理
            # 返回文件路径
            if self.hotmap == 1:
                # 存储文件
                # 目录不存在则创建目录
                if not os.path.exists(self.hotmapDir):
                    try:
                        os.mkdir(self.hotmapDir)
                        hotmapImg = os.path.join(self.hotmapDir, 
                                            time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime()) + '.png')
                        cv2.imwrite(hotmapImg, pngImage)
                    except BaseException:
                        try:
                            if not os.path.exists(self.defaultHotmapDir):
                                os.mkdir(self.defaultHotmapDir)
                                hotmapImg = os.path.join(os.getcwd(), self.defaultHotmapDir, 
                                                    time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime()) + '.png')
                                cv2.imwrite(hotmapImg, pngImage)
                        except BaseException:
                            print('Invalid hot map directory')
            elif self.hotmap == 2:
                hotmapImg = base64.b64encode(pngImage).decode()

            # 显示热力图
            plt.imshow(pngImage)
            plt.show()

        # 结束消息
        if self.msger is not None:
            try:
                self.msger.send({'source': None, 'index': None, 'degree': None, 'hotmapImg': hotmapImg, 'progress': 100,
                                 'status': 'finish'})
            except Exception as ex:
                # 发生异常时
                print('Exception:', ex.__doc__)
