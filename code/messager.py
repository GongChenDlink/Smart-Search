# !/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Message Service
"""

from abc import ABCMeta, abstractmethod
import asyncio
import json


class Messager(object):
    """
        Messager Abstract Class
    """
    __metaclass__ = ABCMeta

    def __init__(self, **kwargs):
        """
            Initialization function

            Parameters
            ----------
            kwargs : params
                        taskId: The task id
                        msger : messager
                    
            Returns
            -------
        """
        self.taskId = kwargs.get("taskId")
        self.msger = kwargs.get("msger")

    @abstractmethod
    def send(self, msg):
        """
            Send some data

            Parameters
            ----------
            msg : dict
                        Message
                    
            Returns
            -------
        """
        pass

    @abstractmethod
    def end(self, msg):
        """
            The end

            Parameters
            ----------
            msg : dict
                        Message
                    
            Returns
            -------
        """
        pass


class WSMessager(Messager):
    """
        WebSocket Messager Class
    """

    def __init__(self, **kwargs):
        """
            Initialization function

            Parameters
            ----------
            kwargs : params
                        taskId : The task id
                        msger : messager
                    
            Returns
            -------
        """
        super(WSMessager, self).__init__(**kwargs)


    async def send(self, msg):
        msg['taskId'] = self.taskId
        msg['status'] = 'process'
        await self.msger.send(json.dumps(msg))
        await asyncio.sleep(0.01)


    async def end(self, msg):
        msg['taskId'] = self.taskId
        msg['status'] = 'finish'
        await self.msger.send(json.dumps(msg))
        await asyncio.sleep(0.01)