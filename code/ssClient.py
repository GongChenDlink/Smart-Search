# !/usr/bin/env python
# -*- coding: utf-8 -*-

# WS client example

import asyncio
import websockets
import json

async def hello():
    uri = "ws://localhost:7000/ws"
    async with websockets.connect(uri) as websocket:

        regions = [
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

        params = {'type': 0, 'sources' : ['D:\\projects\\self\\python\\data_images\\testL0_.png', 
                                         'D:\\projects\\self\\python\\data_images\\testL0.png',
                                         'D:\\projects\\self\\python\\data_images\\testL0.aa',
                                         'E:\资料\临时文件\D-Link\Projects\DNH200\SmartSearch\CH05.mp4'],
                  'regions': None, 'hotmap': 1}

        await websocket.send(json.dumps(params))

        while 1:
            msg = await websocket.recv()
            print(msg)

asyncio.run(hello())
