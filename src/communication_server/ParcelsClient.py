#!/usr/bin/env python3
import os
import io
from requests_futures.sessions import FuturesSession
import requests


class ParcelsClient():

    def __init__(self, logger):
        self.logger = logger
        self.session = FuturesSession()

    def callback_request(self, future):
        exc = future.exception()
        if exc is not None:
            self.logger.error(f"{exc}")
        else:
            response = future.result()
            if response.status_code != 200:
                self.logger.error(f"{response.url}:{response.status_code}")
            else:
                self.logger.info(f"{response.url}:{response.status_code} in elapsed={response.elapsed}") 
       
    def post(self,url,headers,data):
        future = self.session.post(url, data=data, headers=headers, timeout=0.01)
        future.add_done_callback(self.callback_request)
    


