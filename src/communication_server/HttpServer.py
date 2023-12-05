#!/usr/bin/env python3
import os
from flask import Flask, request, redirect, url_for
from werkzeug.utils  import secure_filename
import logging
UPLOAD_FOLDER = '/tmp/'
ALLOWED_EXTENSIONS = set(['jpeg'])

# # Niveau de trace de flask
# log = logging.getLogger('werkzeug')
# log.setLevel(logging.ERROR)

from multiprocessing import SimpleQueue
import threading

import io

class HttpServer():

    def __init__(self, imageQ,incomingQ, logger):
        self.app = Flask(__name__)
        #app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
        self.logger = logger
        @self.app.route("/postimage", methods=['POST'])
        def imageIncoming():
            if request.method == 'POST':
                in_memory_file = io.BytesIO(request.get_data())
                # print("Type:",type(request.data))
                # print("Len:",len(request.data))
                if len(request.data) > 0:
                    if imageQ.full():
                        imageQ.get()
                        print('WARNING : Skipping Image, process took too much time')
                    imageQ.put({'file':in_memory_file,'ts':request.args.get('ts'),'cam':request.args.get('cam')})
                    self.logger.info("--- image bien recue par le trt ---")
            return "Image received(%d)"%len(request.data)

        @self.app.route("/trtresult", methods=['POST'])
        def trt_result_prec():
            # parcels_json=request.get_data(as_text=True)
            parcels_json=request.get_data()
            self.logger.info("--- parcels_json trt {} {} ---".format(request.data, len(request.data)))
            if len(request.data) > 0:
                    # if request.args.get('from')=="0":
                    if incomingQ.full():
                        incomingQ.get()
                    incomingQ.put({'file':parcels_json,'ts':request.args.get('ts')})
                    self.logger.info("--- trt_suivant a bien recu les infos du trt_result_prec ---")
            return "trtresult received(%d)"%len(request.data)

        def shutdown_server():
            func = request.environ.get('werkzeug.server.shutdown')
            if func is None:
                raise RuntimeError('Not running with the Werkzeug Server')
            func()

        @self.app.route('/shutdown', methods=['POST'])
        def shutdown():
            print('Server shutting down...')
            shutdown_server()
            return 'Server shutting down...'

if __name__ == "__main__":
    q = SimpleQueue()
    t = threading.Thread(target=worker,args=(q,))
    t.start()
    app.run(host='0.0.0.0', port=5000, debug=False)
