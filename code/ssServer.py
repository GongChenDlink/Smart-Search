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
import sys
from tornado import httpserver
from services.detection.motion import motion
from messager import WSSender, TornadoSender

USAGE = {'help': {'url': 'ws://server_ip:7000/websocket/', 'path': ['add', 'stop', 'cancel']}}
# service listen port
G_LISTEN_PORT = 7000
# DNH-200 config database
CONFIG_DB_PATH = '/userdata/config/config-data.db'

# ws clients sessions
SESSIONS = []


def sendMsg(websocket, msg):
    try:
        websocket.write_message(msg)
    except Exception as ex:
        print('Error:WebSocketClosedError')
        # raise Exception('WebSocketClosedError')


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write(json.dumps(USAGE))


class Helper(tornado.websocket.WebSocketHandler):
    def open(self):
        print("WebSocket opened")

    def on_message(self, message):
        sendMsg(self, json.dumps(USAGE))
        self.close(1000, 'bye')

    def on_close(self):
        print("WebSocket closed")


async def addCommand(taskBody, websocket):
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

            await motionDetector.motionDetect(sources=dic.get('sources'))
        elif (dic.get('type') == 1):
            print('Face recognition')
        else:
            print('Analysis type is not supported')
            sendMsg(websocket,
                    json.dumps({"status": "error", "code": 41141, "message": "Analysis type is not supported"}))
    else:
        print('Missing analysis type')
        sendMsg(websocket, json.dumps({"status": "error", "code": 41140, "message": "Missing analysis type"}))


class AddTask(tornado.websocket.WebSocketHandler):
    async def open(self):
        print('before:', len(SESSIONS))
        SESSIONS.append(self)
        if len(SESSIONS) > 1:
            sendMsg(self, json.dumps(
                {"status": "error", "code": 41143,
                 "message": "There is already a running analysis task. Please try again later."}))
            self.close(1013, 'busy')
        else:
            print("WebSocket opened:", id(self))
        print('after:', len(SESSIONS))

    async def on_message(self, message):
        try:
            await addCommand(message, self)
        except Exception as ex:
            SESSIONS.remove(self)
            print(ex.__str__())

    async def on_ping(self, data):
        print('ping:', data)

    async def on_pong(self, data):
        print('pong:', data)
        if not data:
            byte_ping = round(time.time() * 1000).to_bytes(13, 'big')
            self.ping(byte_ping)

    def on_close(self):
        SESSIONS.remove(self)
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
    conn = sqlite3.connect(CONFIG_DB_PATH)
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
        if sys.platform == "win32":
            print('single_process')
            server.listen(G_LISTEN_PORT)
        else:
            print('multi_process')
            server.bind(G_LISTEN_PORT)
            server.start(0)
    else:
        app.listen(G_LISTEN_PORT)
    tornado.ioloop.IOLoop.current().start()
