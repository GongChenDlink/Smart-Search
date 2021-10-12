import tornado.ioloop
import tornado.web
import tornado.websocket
import json
import uuid
from services.detection.motion import motion
from messager import WSSender


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write(r"{'help':{'command':['add','cancel']}}")


class EchoWebSocket(tornado.websocket.WebSocketHandler):
    def open(self):
        print("WebSocket opened")

    def on_message(self, message):
        self.write_message(json.dumps({'help': {'url': 'ws://server_ip:7000/', 'path': ['add', 'stop', 'cancel']}}))
        msgHandller(self, message)

    def on_close(self):
        print("WebSocket closed")


def addCommand(taskBody, websocket):
    try:
        dic = json.loads(taskBody)
        print("task:",type(taskBody),taskBody)
        print(dic, type(dic))
        if (dic and 'type' in dic):
            # if (obj and hasattr(obj,'type')):
            uuidObj = uuid.uuid4()
            taskId = str(uuidObj)
            if (dic['type'] == 0):
                print('Motion detection')
                messager = WSSender(taskId=taskId, msger=websocket)
                motionDetector = motion.Motion(msger=messager, hotmap=dic['hotmap'], regions=dic['regions'],
                                               degree=dic['degree'])

                motionDetector.motionDetect(sources=dic['sources'])
            elif (dic['type'] == 1):
                print('Face recognition')

            else:
                print('None')
                websocket.write_message(json.dumps({"Error": 45003}))
        else:
            print('None')
            websocket.write_message(json.dumps({"Error": 45002}))

    except Exception as ex:
        websocket.write_message(json.dumps({"Error": 45000, "Message": ex.__str__()}))


class AddTask(tornado.websocket.WebSocketHandler):
    def open(self):
        print("WebSocket opened")

    def on_message(self, message):
        print(message)
        obj = json.loads(message)
        addCommand(message, self)

    def on_close(self):
        print("WebSocket closed")


def msgHandller(ws, msg):
    obj = json.loads(msg)
    obj['finish'] = True
    ws.write_message(json.dumps(obj))


def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/websocket", EchoWebSocket),
        (r"/websocket/add", AddTask),
    ],
        static_path='./'
    )


if __name__ == "__main__":
    app = make_app()
    app.listen(7000)
    tornado.ioloop.IOLoop.current().start()
