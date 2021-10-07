#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@create: 2021-10-06 10:50:00
@author: GongChen
@description: VGG网络Pytorch的实现
@reference: 
    https://zhuanlan.zhihu.com/p/263527295
"""

import torch.nn as nn
import torch.nn.functional as F
from torchsummary import summary


import torch.nn as nn
import torch.nn.functional as F
from torchsummary import summary


class VGG(nn.Module):
    """
    VGG builder
    """

    def __init__(self, arch: object, num_classes=1000) -> object:
        # __init__作用是初始化已实例化后的对象
        super(VGG, self).__init__()
        self.in_channels = 3
        self.conv3_64 = self.__make_layer(64, arch[0])
        self.conv3_128 = self.__make_layer(128, arch[1])
        self.conv3_256 = self.__make_layer(256, arch[2])
        self.conv3_512a = self.__make_layer(512, arch[3])
        self.conv3_512b = self.__make_layer(512, arch[4])
        self.fc1 = nn.Linear(7 * 7 * 512, 4096)
        self.bn1 = nn.BatchNorm1d(4096)
        self.bn2 = nn.BatchNorm1d(4096)
        self.fc2 = nn.Linear(4096, 4096)
        self.fc3 = nn.Linear(4096, num_classes)

    def __make_layer(self, channels, num):
        layers = []
        for i in range(num):
            # Conv2d(in_channels, out_channels, kernel_size, stride=1,padding=0, dilation=1, groups=1,bias=True, padding_mode=‘zeros’)
            # in_channels: 输入的通道数目
            # out_channels: 输出的通道数目
            # kernel_size: 卷积核的大小，类型为int或者元组，当卷积是方形的时候，只需要一个整数边长即可
            # stride: 卷积每次滑动的步长为多少，默认为1
            # padding: 设置在所有边界增加值为0的边距的大小，例如当padding=1的时候，如果原来大小为3 X 3，那么之后的大小为5 X 5
            # dilation: 控制卷积核之间的间距
            # groups: 控制输入和输出之间的连接（不常用）
            # bias: 是否将一个学习到的bias增加输出中
            # padding_mode: 字符串类型，接收的字符串只有"zeros"和"circular"
            layers.append(nn.Conv2d(self.in_channels, channels, 3, stride=1, padding=1, bias=False))  # same padding
            layers.append(nn.BatchNorm2d(channels))
            layers.append(nn.ReLU())
            self.in_channels = channels
        return nn.Sequential(*layers)

    def forward(self, x):
        out = self.conv3_64(x)
        out = F.max_pool2d(out, 2)
        out = self.conv3_128(out)
        out = F.max_pool2d(out, 2)
        out = self.conv3_256(out)
        out = F.max_pool2d(out, 2)
        out = self.conv3_512a(out)
        out = F.max_pool2d(out, 2)
        out = self.conv3_512b(out)
        out = F.max_pool2d(out, 2)
        out = out.view(out.size(0), -1)
        out = self.fc1(out)
        out = self.bn1(out)
        out = F.relu(out)
        out = self.fc2(out)
        out = self.bn2(out)
        out = F.relu(out)
        return self.fc3(out)


def VGG_11(num_classes=1000):
    return VGG([1, 1, 2, 2, 2], num_classes=num_classes)

def VGG_13(num_classes=1000):
    return VGG([1, 1, 2, 2, 2], num_classes=num_classes)

def VGG_16(num_classes=1000):
    return VGG([2, 2, 3, 3, 3], num_classes=num_classes)

def VGG_19(num_classes=1000):
    return VGG([2, 2, 4, 4, 4], num_classes=num_classes)


def test():
    # net = VGG_11()
    # net = VGG_13()
    # net = VGG_16()
    net = VGG_19()
    summary(net, (3, 224, 224))


if __name__ == '__main__':
    test()