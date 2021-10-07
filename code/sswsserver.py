# -*- coding: utf-8 -*-
# !/usr/bin/env python

import asyncio
import json
import uuid
import websockets
import os

from messager import WSMessager
from detection.motion import motion


async def addTask(taskBody, websocket):
    try:
        dic = json.loads(taskBody)
        print(dic, type(dic))
        if (dic and 'sourceType' in dic):
            uuidObj = uuid.uuid4()
            taskId = str(uuidObj)
            if (dic['sourceType'] == 1):
                print('compare video')
                # await websocket.send(json.dumps({'status': 'added', 'taskId': taskId}))
                # await compare.pHashCmp(dic['source'], dic['threshold'], dic['region'], taskId, websocket)

                messager = WSMessager(taskId=taskId, msger=websocket)
                motionDetector = motion.Motion(msger=messager, hotmap=dic['hotmap'], regions=dic['regions'],
                                               degree=dic['degree'])

                await motionDetector.motionDetect(sources=dic['sources'], sourceType=dic['sourceType'])

            elif (dic['sourceType'] == 2):
                print('compare images')
                # await websocket.send(json.dumps({'status': 'added', 'taskId': taskId}))
                # await compare.frameCmp(dic['source'], dic['threshold'], dic['region'], taskId, websocket)

                messager = WSMessager(taskId=taskId, msger=websocket)
                motionAnalysis = motion.Motion(msger=messager, hotmap=dic['hotmap'], regions=dic['regions'],
                                               degree=dic['degree'])

                await motionAnalysis.motionDetect(sources=dic['sources'], sourceType=dic['sourceType'])

            else:
                print('None')
                await websocket.send(json.dumps({"Error": 45003}))
        else:
            print('None')
            await websocket.send(json.dumps({"Error": 45002}))

    except Exception as ex:
        await websocket.send(json.dumps({"Error": 45000, "Message": ex.__str__()}))


async def stopTask(taskBody, websocket):
    print("stop task:", taskBody)
    await websocket.send('task stoped')


async def cancelTask(taskBody, websocket):
    print("cancel task:", taskBody)
    await websocket.send('task canceled')


async def default(taskBody, websocket):
    print("help", taskBody)
    await websocket.send(json.dumps({'help': {'url': 'ws://server_ip:7000/', 'path': ['add', 'stop', 'cancel']}}))


handler = {
    '/add': addTask,
    '/stop': stopTask,
    '/cancel': cancelTask
}


async def service(websocket, path):
    async for message in websocket:
        print(path, '\treceive:', message)
        exec = handler.get(path, default)
        if exec:
            await exec(message, websocket)
        # await websocket.send(message)


async def main():
    async with websockets.serve(service, "0.0.0.0", 7000):
        print('ws service booting...')
        await asyncio.Future()  # run forever


try:
    asyncio.run(main())
except Exception as ex:
    print(ex.__str__())
