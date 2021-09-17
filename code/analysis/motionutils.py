# !/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Motion Detector Utils

"""

import cv2
import numpy as np


def calculateDegreeBasePHash(image1, image2):
        """
            Calculate similarity of two images base on p-hash

            Parameters
            ----------
            image1 : ndarray
                        The numpy data of first image
            image2 : ndarray
                        The numpy data of first image
                    
            Returns
            -------
            m : int
                        Similarity of two images
        """

        image1 = cv2.resize(image1, (32,32))
        image2 = cv2.resize(image2, (32,32)) 
        gray1 = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY) 
        gray2 = cv2.cvtColor(image2, cv2.COLOR_BGR2GRAY) 
        # 将灰度图转为浮点型，再进行dct变换 
        dct1 = cv2.dct(np.float32(gray1)) 
        dct2 = cv2.dct(np.float32(gray2)) 
        # 取左上角的8*8，这些代表图片的最低频率 
        # 这个操作等价于c++中利用opencv实现的掩码操作 
        # 在python中进行掩码操作，可以直接这样取出图像矩阵的某一部分 
        dct1_roi = dct1[0:8, 0:8] 
        dct2_roi = dct2[0:8, 0:8] 
        hash1 = getHash(dct1_roi) 
        hash2 = getHash(dct2_roi) 
        return calculateHammingDistance(hash1, hash2)

 
def getHash(image):
    """
        Calculate the hash value of image

        Parameters
        ----------
        image : ndarray
                    The numpy data of first image
                    
        Returns
        -------
        m : array_like
                    The hash value of image
    """

    avreage = np.mean(image) 
    hash = [] 
    for i in range(image.shape[0]): 
        for j in range(image.shape[1]): 
            if image[i,j] > avreage: 
                hash.append(1) 
            else: 
                hash.append(0) 
    return hash
 
 
def calculateHammingDistance(hash1, hash2):
    """
        Calculate Hamming distance

        Parameters
        ----------
        hash1 : array_like
                    The first hash value
        hash2 : array_like
                    The second hash value
                    
        Returns
        -------
        m : int
                    The hamming distance value
    """

    num = 0 
    for index in range(len(hash1)): 
        if hash1[index] != hash2[index]: 
            num += 1 
    return num


def getROI(image, points):
    """
        Get the ROI(Region of Interest)

        Parameters
        ----------
        image : ndarray
                    The numpy data of first image
        points : array_like
                    Vertex coordinates of the region
                    
        Returns
        -------
        image : ndarray
                    ROI data
    """


    mask = np.zeros(image.shape, np.uint8)
    pts = np.array(points, np.int32)
    col0 = pts[:, 0]
    col1 = pts[:, 1]
    x1 = np.min(col0)
    y1 = np.min(col1)
    x2 = np.max(col0)
    y2 = np.max(col1)
    # reshape的第一个参数为-1，表明这一维的长度是根据后面的维度的计算出来的
    # opencv中徐娅先将多边形的顶点坐标变成顶点数 x 1 x 2维的矩阵，再来绘制
    pts = pts.reshape((-1, 1, 2))

    # 画多边形
    mask = cv2.polylines(mask, [pts], True, (255, 255, 255))
    # 填充多边形
    mask2 = cv2.fillPoly(mask, [pts], (255, 255, 255))
    ROI = cv2.bitwise_and(mask2, image)

    return ROI[y1:y2, x1:x2]