# !/usr/bin/env python
# -*- coding: utf-8 -*-

# WS client example

import asyncio
import websockets
import json

async def hello():
    uri = "ws://localhost:7000/add"
    async with websockets.connect(uri) as websocket:

        params = {'type': 0, 'source' : 'E:\资料\临时文件\D-Link\Projects\DNH200\SmartSearch\CH05.mp4', 'region': None, 'hotmap': 1}

        await websocket.send(json.dumps(params))

        while 1:
            msg = await websocket.recv()
            print(f"<<< {msg}")

asyncio.run(hello())
