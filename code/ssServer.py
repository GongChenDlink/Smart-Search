import queue
import threading
import time
import os
import tornado.ioloop
import tornado.web
import tornado.websocket
import json
import uuid
import sqlite3
from tornado import httpserver
from services.detection.motion import motion
from messager import WSSender, TornadoSender

# DNH-200 配置数据库
dbPath = '/userdata/config/config-data.db'

q = queue.Queue()
q.maxsize = 1

# ws clients session
session = []


def TaskAddHandler(arg):
    while True:
        task = q.get()
        print('arg:', arg)
        print('get ws id:', id(task['ws']))
        try:
            dic = task['msg']
            if (dic and 'type' in dic):
                if (dic['type'] == 0):
                    print('Motion detection')
                    messager = TornadoSender(taskId=dic['taskId'], msger=task['ws'])
                    motionDetector = motion.Motion(msger=messager, hotmap=dic['hotmap'],
                                                   regions=dic['regions'], degree=dic['degree'])

                    motionDetector.motionDetect(sources=dic['sources'], sourceType=dic['sourceType'])
                elif (dic['type'] == 1):
                    print('Face recognition')

                else:
                    print('None')
                    sendMsg(task['ws'], json.dumps({"Error": 45003}))
            else:
                print('None')
                sendMsg(task['ws'], json.dumps({"Error": 45002}))

        except Exception as ex:
            sendMsg(task['ws'], json.dumps({"Error": 45000, "Message": ex.__str__()}))
        finally:
            q.task_done()


threading.Thread(target=TaskAddHandler, daemon=True, args=(1,)).start()

q.join()

usage = {'help': {'url': 'ws://server_ip:7000/', 'path': ['add', 'stop', 'cancel']}}


def sendMsg(websocket, msg):
    try:
        websocket.write_message(msg)
    except Exception as ex:
        print('Error:WebSocketClosedError')
        # raise Exception('WebSocketClosedError')


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write(json.dumps(usage))


class Helper(tornado.websocket.WebSocketHandler):
    def open(self):
        print("WebSocket opened")

    def on_message(self, message):
        sendMsg(self, json.dumps(usage))
        self.close(1000, 'bye')

    def on_close(self):
        print("WebSocket closed")


def addCommand(taskBody, websocket):
    dic = json.loads(taskBody)
    if (dic and 'type' in dic):
        uuidObj = uuid.uuid4()
        taskId = str(uuidObj)
        dic['taskId'] = taskId
        dic['status'] = 'added'
        sendMsg(websocket, json.dumps(dic))
        if (dic.get('type') == 0):
            print('Motion detection')
            messager = TornadoSender(taskId=taskId, msger=websocket)
            motionDetector = motion.Motion(msger=messager, hotmap=dic.get('hotmap'), regions=dic.get('regions'),
                                           degree=dic.get('degree'))

            motionDetector.motionDetect(sources=dic.get('sources'))
        elif (dic.get('type') == 1):
            print('Face recognition')
        else:
            print('None')
            sendMsg(websocket, json.dumps({"Error": 45003}))
    else:
        print('None')
        sendMsg(websocket, json.dumps({"Error": 45002}))


class AddTask(tornado.websocket.WebSocketHandler):
    def open(self):
        session.append(self)
        print("WebSocket opened:", id(self))

    def on_message(self, message):
        print(message)
        try:
            addCommand(message, self)

            # dic = json.loads(message)
            # uuidObj = uuid.uuid4()
            # taskId = str(uuidObj)
            # dic['taskId'] = taskId
            #
            # q.put({'ws': self, 'msg': dic})
            #
            # dic['status'] = 'added'
            # sendMsg(self, json.dumps(dic))
        except Exception as ex:
            print(ex.__str__())

    def on_ping(self, data):
        print('ping:', data)

    def on_pong(self, data):
        print('pong:', data)
        if not data:
            byte_ping = round(time.time() * 1000).to_bytes(13, 'big')
            self.ping(byte_ping)

    def on_close(self):
        session.remove(self)
        print("WebSocket closed, code:{0} reason:{1}.".format(self.close_code, self.close_reason))

    # 允许所有跨域通讯，解决403问题
    def check_origin(self, origin):
        return True


def make_app():
    app = tornado.web.Application([
        (r"/", MainHandler),
        (r"/websocket", Helper),
        (r"/websocket/add", AddTask),
    ],
        # websocket_ping_interval=10,
        # websocket_ping_timeout=5,
        # static_path='./',
    )

    return app


def getCert():
    """
    从database获取证书文件路径
    Returns
    -------
    {"certfile": "x.pem", "keyfile": "y.pem"}
    """
    conn = sqlite3.connect(dbPath)
    cur = conn.cursor()
    cur.execute("""SELECT _id,sslCertification FROM CWM_Org_Info;""")
    orgInfo = cur.fetchone()
    sslCfg = {}
    if orgInfo is not None:
        # print(orgInfo)
        sslInfo = json.loads(orgInfo[1])
        if (sslInfo['urlCert'] and sslInfo['urlKeyFile']):
            cur.execute("SELECT path FROM CWM_File where _id ='{0}'".format(sslInfo['urlCert']['fileId']))
            cert = cur.fetchone()
            print(cert[0])
            sslCfg['certfile'] = cert[0]

            cur.execute("SELECT path FROM CWM_File where _id ='{0}'".format(sslInfo['urlKeyFile']['fileId']))
            key = cur.fetchone()
            print(key[0])
            sslCfg['keyfile'] = key[0]

    cur.close()
    conn.close()
    return sslCfg


if __name__ == "__main__":
    print('Booting... ', 'PID:', os.getpid())
    app = make_app()
    sslCfg = getCert()
    if ('certfile' in sslCfg and 'keyfile' in sslCfg):
        server = httpserver.HTTPServer(app, ssl_options=sslCfg)
        server.listen(7000, '')
    else:
        app.listen(7000, '')
    tornado.ioloop.IOLoop.current().start()
