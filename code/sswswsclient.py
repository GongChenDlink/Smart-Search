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

        # params = {'sourceType': 1, 'sources': ['./samples/CH05.mp4'], 'regions': regions, 'degree': 1,
        #           'hotmap': 1}

        params = {'sourceType': 2, 'sources': ['./samples/testL0_.png', './samples/testL0.png'], 'regions': None,
                  'degree': 1, 'hotmap': 1}

        await websocket.send(json.dumps(params))

        cond = 1
        while cond:
            try:
                msg = await websocket.recv()
                obj = json.loads(msg)
                if (obj['status'] == 'finish'):
                    print(f"<<< {msg}")
                    await websocket.close(code=1000, reason='bye')
                    cond = 0
                else:
                    print(f"<<< {msg}")
            except Exception as ex:
                print(ex)
                cond = 0

asyncio.run(hello())
