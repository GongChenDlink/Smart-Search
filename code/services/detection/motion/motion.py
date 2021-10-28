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
            heatmap : int, optional
                        Does it need to generate a heatmap?
                        Default value is 0
                            0: Do not generate heatmap
                            1: Generate heatmap and return the file path of image
                            2: Generate heatmap and return the base64 string of image
                    
            Returns
            -------
        """
        self.regions = kwargs.get('regions')
        self.degree = kwargs.get('degree', 10) if kwargs.get('degree', 10) else 10
        # 对图像进行二值化处理所需要的一些阈值
        self.threshold = kwargs.get('threshold', 2) if kwargs.get('threshold', 2) else 2
        self.maxValue = kwargs.get('maxValue', 80) if kwargs.get('maxValue', 80) else 80
        # 睡眠时间
        self.sleepTimes = kwargs.get('sleepTimes', 0.1) if kwargs.get('sleepTimes', 0.1) else 0.1
        # 消息发送器
        self.msger = kwargs.get('msger')
        # 是否生成heatmap并且返回的方式
        self.heatmap = kwargs.get('heatmap', 0) if kwargs.get('heatmap', 0) else 0
        # heat map图片的存储目录
        self.defaultHeatmapDir = os.path.join(os.getcwd(), 'heatmap')
        self.heatmapDir = kwargs.get('heatmapDir', self.defaultHeatmapDir) or self.defaultHeatmapDir
        # 生成heatmap的标识
        self.heatmapTags = [1, 2]
        # 支持的视频格式
        self.supportedVideoFormats = ['.mp4', '.avi']
        # 支持的图片格式
        self.supportedImageFormats = ['.bmp', '.jpeg', '.jpg', '.png']

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
            heatmapImg : string, optional
                        heat map image
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
            if suffixName in self.supportedVideoFormats:
                videoFiles.append(source)
            elif suffixName in self.supportedImageFormats:
                imageFiles.append(source)
            else:
                print('Unsupported file format {0}'.format(suffixName))


        # 视频方式
        if (videoFiles is not None) and (len(videoFiles) > 0):
            await self.motionDetect4Videos(videoFiles)
        # 图片方式
        if (imageFiles is not None) and (len(imageFiles) > 0):
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
            heatmapImg : string, optional
                        heat map image
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
            heatmapImg : string, optional
                        heat map image
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
        # 生成的heatmap
        heatmapImg = None
        # 发生motion的时间点
        motionTimes = []

        # 参数检查
        if fps <= 0 or frameCount <= 0 or width <= 0 or height <= 0:
            print('Invalid video')
            return

        # 背景剪裁器
        backgroundSubtractor = None
        accumulatedImage = None

        # 生成heatmap
        if self.heatmap in self.heatmapTags:
            # 获取背景剪裁器
            backgroundSubtractor = cv2.bgsegm.createBackgroundSubtractorMOG()
            # 没有指定检测区域，则默认检测整个图像区域
            if self.regions is None:
                accumulatedImage = np.zeros((height, width), np.uint8)

        # 遍历所有的帧
        for i in range(1, frameCount + 1):

            # 读取一帧数据
            (ret, currentFrame) = capture.read()

            # 判断是否是有效帧
            if not ret:
                continue
            if currentFrame is None:
                continue

			# 计算检测进度
            progress = int(i / frameCount * 100)

            # 裁剪图片
            if self.regions is not None:
                currentFrame = motionutils.getROI(currentFrame, self.regions)

            # 是否是第一帧
            if lastFrame is None:
                # 设置上一帧
                lastFrame = copy.deepcopy(currentFrame)
				# 生成heatmap
                if self.heatmap in self.heatmapTags:
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
					# iterations的值越高，模糊程度（腐蚀程度）就越高 呈正相关
                    # thresh = cv2.erode(thresh, None, iterations=1)
                    # thresh = cv2.dilate(thresh, None, iterations=2)
                    # 相加
                    accumulatedImage = cv2.add(accumulatedImage, thresh)
                continue

            # 只处理每秒内第一帧的数据
            if i % fps != 0:
                continue

            # 计算上一帧与当前帧的相似度
            degree = motionutils.calculateDegreeBasePHash(lastFrame, currentFrame)

            # 大于指定阈值
            if degree >= self.degree:
				# 生成heatmap
                if self.heatmap in self.heatmapTags:
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
					# iterations的值越高，模糊程度（腐蚀程度）就越高 呈正相关
                    # thresh = cv2.erode(thresh, None, iterations=1) 
                    # thresh = cv2.dilate(thresh, None, iterations=2) 
                    # 相加
                    accumulatedImage = cv2.add(accumulatedImage, thresh)

                # 获取当前帧的所对应的时间
                milliseconds = capture.get(cv2.CAP_PROP_POS_MSEC)
                motionTimes.append(milliseconds)
                print('Changed: ', milliseconds, ' degree: ', degree)
                # 发送消息
                if self.msger is not None:
                    try:
                        self.msger.send(
                            {'source': videoFile, 'index': milliseconds, 'degree': degree, 'heatmapImg': None,
                             'progress': progress, 'status': 'process'})
                    except Exception as ex:
                        # 发生异常时，释放打开的文件句柄
                        capture.release()

            # 设置上一帧
            lastFrame = copy.deepcopy(currentFrame)

            # sleep
            await asyncio.sleep(self.sleepTimes)

        # 生成heatmap
        if (self.heatmap in self.heatmapTags) and (accumulatedImage is not None):
            # 计算热点图
            colorMapImage = cv2.applyColorMap(accumulatedImage, cv2.COLORMAP_HOT)
            # 转换成PNG图像，相对于其它图像，PNG图像多了一个透明通道
            pngImage = cv2.cvtColor(colorMapImage, cv2.COLOR_BGR2BGRA)
            # 将255改变成0
            pngImage[np.all(pngImage == [0, 0, 0, 255], axis=2)] = [0, 0, 0, 0]
            # 调整透明度
            pngImage[np.any(pngImage != [0, 0, 0, 0], axis=2)] = np.subtract(
                pngImage[np.any(pngImage != [0, 0, 0, 0], axis=2)], [0, 0, 0, 55])

            # regions不为空，则进行重新resize
            if (self.regions is not None) and (pngImage.shape[0:2] != (width, height)):
                pngImage = cv2.resize(pngImage, (width, height))

            # 根据指定返回heat map的方式进行处理
            if not os.path.exists(self.heatmapDir):
                try:
                    os.mkdir(self.heatmapDir)
                    heatmapImg = self.buildHeatmapFileName()
                    cv2.imwrite(heatmapImg, pngImage, [int(cv2.IMWRITE_PNG_COMPRESSION), 9])
                except BaseException:
                    try:
                        if not os.path.exists(self.defaultHeatmapDir):
                            os.mkdir(self.defaultHeatmapDir)
                            heatmapImg = self.buildHeatmapFileName()
                            cv2.imwrite(heatmapImg, pngImage, [int(cv2.IMWRITE_PNG_COMPRESSION), 9])
                    except BaseException:
                        print('Invalid heat map directory')
            else:
                heatmapImg = self.buildHeatmapFileName()
                cv2.imwrite(heatmapImg, pngImage, [int(cv2.IMWRITE_PNG_COMPRESSION), 9])

            # 以Base64格式返回生成的heatmap
            if self.heatmap == 2:
                with open(heatmapImg, "rb") as f:
                    heatmapImg = 'data:image/png;base64,' + base64.b64encode(f.read()).decode()

            # 显示热力图
            plt.imshow(pngImage)
            plt.show()

        # 结束消息
        if self.msger is not None:
            try:
                self.msger.send(
                    {'source': videoFile, 'index': None, 'degree': None, 'heatmapImg': heatmapImg, 'progress': 100,
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
            heatmapImg : string, optional
                        heat map image
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

        # 生成heatmap
        if self.heatmap in self.heatmapTags:
            # 获取背景剪裁器
            backgroundSubtractor = cv2.bgsegm.createBackgroundSubtractorMOG()

        # 上一张图片
        lastImage = None
        # 当前图片
        currentImage = None
        # 生成的heatmap
        heatmapImg = None

        # 原始图片的大小
        originalHeight = None
        originalWidth = None

        # 发生motion的图片
        motionFiles = []

		# 图片的总数
        imageCount = len(imageFiles)

        # 遍历进行处理
        for i in range(0, imageCount):
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

            # 没有指定检测区域，则默认检测整个图像区域，否则则获取指定区域的图像
            if self.regions is not None:
                # 裁剪图片
                currentImage = motionutils.getROI(currentImage, self.regions)
                height, width = currentImage.shape[0:2]

            # 检查图片的形状是否一样
            if (lastImage is not None) and (lastImage.shape != currentImage.shape):
                print('The image file({0}) not the same shape'.format(imageFile))
                continue

            # 初始化第一张图像
            if lastImage is None:
                lastImage = copy.deepcopy(currentImage)
                if self.heatmap in self.heatmapTags:
                    # 初始化accumulatedImage
                    if accumulatedImage is None:
                        accumulatedImage = np.zeros((height, width), np.uint8)
                    # 为计算热力图做数据准备
                    # 移除背景
                    filter = backgroundSubtractor.apply(currentImage)
                    # 二值化
                    ret, thresh = cv2.threshold(filter, self.threshold, self.maxValue, cv2.THRESH_BINARY)
                    # 去除图像噪声,先腐蚀再膨胀
                    # thresh = cv2.erode(thresh,None, iterations=1)
                    # thresh = cv2.dilate(thresh, None, iterations=2)
                    # 相加
                    accumulatedImage = cv2.add(accumulatedImage, thresh)
                continue

            # 计算上一帧与当前帧的相似度
            degree = motionutils.calculateDegreeBasePHash(lastImage, currentImage)

            # 大于指定阈值
            if degree >= self.degree:
				# 生成heatmap
                if self.heatmap in self.heatmapTags:
                    # 初始化accumulatedImage
                    if accumulatedImage is None:
                        accumulatedImage = np.zeros((height, width), np.uint8)
                    # 为计算热力图做数据准备
                    # 移除背景
                    filter = backgroundSubtractor.apply(currentImage)
                    # 二值化
                    ret, thresh = cv2.threshold(filter, self.threshold, self.maxValue, cv2.THRESH_BINARY)
                    # 去除图像噪声,先腐蚀再膨胀
                    # thresh = cv2.erode(thresh,None, iterations=1)
                    # thresh = cv2.dilate(thresh, None, iterations=2) 
                    # 相加
                    accumulatedImage = cv2.add(accumulatedImage, thresh)

                motionFiles.append(imageFile)
                # print('Changed: ', milliseconds, ' degree: ', degree)
                # 发送消息
                if self.msger is not None:
                    try:
                        self.msger.send({'source': imageFile, 'index': imageFile, 'degree': degree, 'heatmapImg': None,
                                         'progress': progress, 'status': 'process'})
                    except Exception as ex:
                        # 发生异常时
                        print('Exception:', ex.__doc__)

            # 设置上一幅图片
            lastImage = copy.deepcopy(currentImage)

            # sleep
            await asyncio.sleep(self.sleepTimes)

        # 生成heatmap
        if (self.heatmap in self.heatmapTags) and (accumulatedImage is not None):
            # 计算热点图
            colorMapImg = cv2.applyColorMap(accumulatedImage, cv2.COLORMAP_HOT)
            # 转换成PNG图像，相对于其它图像，PNG图像多了一个透明通道
            pngImage = cv2.cvtColor(colorMapImg, cv2.COLOR_BGR2BGRA)
            # 将255改变成0
            pngImage[np.all(pngImage == [0, 0, 0, 255], axis=2)] = [0, 0, 0, 0]
            # 调整透明度
            pngImage[np.any(pngImage != [0, 0, 0, 0], axis=2)] = np.subtract(
                pngImage[np.any(pngImage != [0, 0, 0, 0], axis=2)], [0, 0, 0, 55])

            # regions不为空，则进行重新resize
            if (self.regions is not None) and (pngImage.shape[0:2] != (originalWidth, originalHeight)):
                pngImage = cv2.resize(pngImage, (originalWidth, originalHeight))

            # 根据指定返回heat map的方式进行处理
            if not os.path.exists(self.heatmapDir):
                try:
                    os.mkdir(self.heatmapDir)
                    heatmapImg = self.buildHeatmapFileName()
                    cv2.imwrite(heatmapImg, pngImage, [int(cv2.IMWRITE_PNG_COMPRESSION), 9])
                except BaseException:
                    try:
                        if not os.path.exists(self.defaultHeatmapDir):
                            os.mkdir(self.defaultHeatmapDir)
                            heatmapImg = self.buildHeatmapFileName()
                            cv2.imwrite(heatmapImg, pngImage, [int(cv2.IMWRITE_PNG_COMPRESSION), 9])
                    except BaseException:
                        print('Invalid heat map directory')
            else:
                heatmapImg = self.buildHeatmapFileName()
                cv2.imwrite(heatmapImg, pngImage, [int(cv2.IMWRITE_PNG_COMPRESSION), 9])

            if self.heatmap == 2:
                with open(heatmapImg, "rb") as f:
                    heatmapImg = 'data:image/png;base64,' + base64.b64encode(f.read()).decode()

            # 显示热力图
            plt.imshow(pngImage)
            plt.show()

        # 结束消息
        if self.msger is not None:
            try:
                self.msger.send({'source': None, 'index': None, 'degree': None, 'heatmapImg': heatmapImg, 'progress': 100,
                                 'status': 'finish'})
            except Exception as ex:
                # 发生异常时
                print('Exception:', ex.__doc__)


    def buildHeatmapFileName(self, heatmapDir=None):
        """
            Build the heatmap file name according to time strategy

            Parameters
            ----------
        """
        fileName = None
        # 根据传参目录生成文件名
        if (heatmapDir is not None) and (os.path.exists(heatmapDir)):
            fileName = os.path.join(heatmapDir, time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime()) + '.png')
        # 根据初始化时给的目录生成文件名
        elif (self.heatmapDir is not None) and (os.path.exists(self.heatmapDir)):
            fileName = os.path.join(self.heatmapDir, time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime()) + '.png')
        # 根据初始化时的默认路径生成文件名
        elif (self.defaultHeatmapDir is not None) and (os.path.exists(self.defaultHeatmapDir)):
            fileName = os.path.join(self.defaultHeatmapDir, time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime()) + '.png')
        return fileName


