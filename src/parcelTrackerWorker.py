#!/usr/bin/env python3
import numpy as np
import os
import time
import tensorflow as tf
from io import BytesIO 
import configparser as cfg
import traceback
import cv2
from threading import Thread, Event
from queue import Empty


from communication_server.ParcelsClient import ParcelsClient
from parcelTracker import ParcelTracker
from parcels.parcel import parcelListFromPickle, parcelListToPickle

class ParcelTrackerWorker(Thread):

    def __init__(self, configFile, sectionName, imageQ, incomingQ, logger):
        Thread.__init__(self)

        self._loadConfig(configFile, sectionName)

        self.stoppingFlag = Event()
        self.imageQ = imageQ
        self.incomingQ = incomingQ
        self.logger = logger
        self.httpClient=ParcelsClient(logger)
        try:
            self.parcelTracker = ParcelTracker(self.configFileTracker, self.sectionNameTracker, self.logger)    
        except Exception as ex:
            logger.error('ParcelTracker Creation error:' + str(ex))
            raise SystemExit()
        print('Launching parcelDetection Worker')
    
    def _loadConfig(self, configFile, sectionName):
        
        config = cfg.ConfigParser()
        config.read(configFile)
        try :
            self.configFileTracker =  config.get(sectionName, 'configFileTracker')
            self.sectionNameTracker =  config.get(sectionName, 'sectionNameTracker')
            self.timeoutImage =  config.getint(sectionName, 'timeoutImage')
        except Exception as e:
            if not os.path.isfile(configFile): 
                print('ParcelTrackerWorker: No such config file : ' + configFile)     
                print(str(e))
                print(traceback.format_exc())          
                raise SystemExit('ParcelTrackerWorker: No such config file : ' + configFile)
            else :
                print('ParcelTrackerWorker: Problem loading configuration file : ' + configFile)
                print(str(e))
                print(traceback.format_exc())
                raise SystemExit('ParcelTrackerWorker: Problem loading configuration file : ' + configFile)

    def run(self):
        while not self.stoppingFlag.is_set():
            try:
                fromQ =  self.imageQ.get(timeout=self.timeoutImage)
                imageStream = fromQ['file']
                cam=fromQ['cam']
                ts=fromQ['ts']
            # As soon as we have a new image, we get the previous object from tracker N-1
                incomingParcels = ""

                while self.incomingQ.empty() == False:
                    self.logger.info("--- self.incomingQ is not empty---") 
                    fromIncomingQ = self.incomingQ.get()
                    incomingParcels = fromIncomingQ['file']
                    self.logger.info("--- incomingParcels {} ---".format(incomingParcels))
        
                if len(incomingParcels) > 0:
                    new_parcels = parcelListFromPickle(incomingParcels)
                    self.logger.info("--- new_parcels {} ---".format(new_parcels))
                    for obj in new_parcels:
                        self.logger.info("parcelID :{} parcelBarcode:{} cam:{}: New parcel incoming Id".format(obj.parcelID, obj.parcelBarcode, cam))
                else:
                    new_parcels = [None]
                    self.logger.info("No new incoming parcels")
        
                t0 = time.perf_counter()
                file_bytes = np.asarray(bytearray(imageStream.read()), dtype=np.uint8)
                image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                #if self.imageResize != None:
                #    image = cv2.resize(image, self.imageResize)

                t1 = time.perf_counter()
                timingPrepro = t1-t0        
                self.logger.info("--- Preprocess {} seconds ---".format(timingPrepro)) 
                t2 = time.perf_counter()
                parcels = []
                
                parcels, parcelsinfo, objects, numObj = self.parcelTracker.update(image, new_parcels, cam)
                ## info zone de tracking et association
                self.logger.info("zoneAssociation : {}".format(self.parcelTracker.zoneAssociation))
                if self.parcelTracker.zoneAssociation != '':
                    parcelsinfo["zoneAsso"] = (self.parcelTracker.yMinAss, self.parcelTracker.xMinAss, self.parcelTracker.yMaxAss,  self.parcelTracker.xMaxAss)
                parcelsinfo["zoneTracking"] = (self.parcelTracker.yMinLimit, self.parcelTracker.xMinLimit, self.parcelTracker.yMaxLimit, self.parcelTracker.xMaxLimit)
                parcelsinfo["Cam"] = cam
                # affichage du parcelsinf0
                self.logger.info("parcelsInfo : {}".format(parcelsinfo))
                t3 = time.perf_counter()
                timingTracking = t3 - t2
                self.logger.info("--- Algo tracking {} seconds cam: {} ---".format(timingTracking, cam))
                self.logger.info("--- Tracking {} parcels cam :{} ---".format(len(parcels), cam))
                self.logger.info("--- Number of objects {} cam :{}  ---".format(numObj, cam))
                # for p in parcels:
                    # for attr, value in p.__dict__.items():            
                        # self.logger.info("{} : {}".format(attr, value))
                    # self.logger.info("")
                
            # Envoi trt_result
                jsondump = parcelListFromPickle(parcels)
                
                headers = {'Content-type': 'application/octet-stream'}
                url = "http://127.0.0.1:80/sequenceur/trtresult?from={}&to={}&ts={}".format(cam,cam,ts)

            # Fin envoi trt_result sequenceur 
                self.httpClient.post(url=url,headers=headers,data=jsondump)
                t4 = time.perf_counter()
            # Envoi trt_result ihm
                jsondump1 = parcelListToPickle(parcelsinfo)
                url1 = "http://127.0.0.1:5001/parcelsinfo?Cam={}&ts={}".format(cam, ts)
                self.httpClient.post(url=url1,headers=headers,data=jsondump1)


                endTime = t4 - t0
                self.logger.info("--- Full trt {} seconds ---".format(endTime))
            except Exception as e:
                if isinstance(e, Empty):
                    self.logger.error('Queue was empty, timeout after {}s'.format(self.timeoutImage))
                    print('Queue was empty, timeout after {}s'.format(self.timeoutImage))
                else:                    
                    self.logger.error('--- Crash tracker : {} ---'.format(e))
                    self.logger.error(traceback.format_exc())
                    raise SystemExit()


        print('Exiting tracking loop')
        return
