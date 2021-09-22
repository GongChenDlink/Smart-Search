# !/usr/bin/env python
# -*- coding: utf-8 -*-

# WS client example

import asyncio
import websockets
import json

async def hello():
    uri = "ws://localhost:7000/add"
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

        params = {'type': 0, 'sources' : ['E:\资料\临时文件\D-Link\Projects\DNH200\SmartSearch\CH05.mp4'], 'regions': regions, 'hotmap': 1, 'sourceType': 1}

        #params = {'type': 0, 'sources' : ['D:\\projects\\self\\python\\data_images\\testL0_.png', 
        #                                 'D:\\projects\\self\\python\\data_images\\testL0.png'], 
        #          'regions': None, 'hotmap': 1, 'sourceType': 2}

        await websocket.send(json.dumps(params))

        while 1:
            msg = await websocket.recv()
            print(f"<<< {msg}")

asyncio.run(hello())
