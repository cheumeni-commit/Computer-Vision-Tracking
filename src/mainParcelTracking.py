#!/usr/bin/env python3
import sys
from threading import Thread
from queue import Queue
import requests
import logging
from logging.handlers import WatchedFileHandler
import traceback
import time
import configparser as cfg
   
from communication_server.HttpServer import HttpServer
from config.directories import directories as dirs
from parcelTrackerWorker import ParcelTrackerWorker

ginstanceID="0"

if(len(sys.argv)>1):
    ginstanceID = sys.argv[1]

def ConfigureLogger(logger):
    #From Sam&Max
    # création de l'objet logger qui va nous servir à écrire dans les logs
    
    # on met le niveau du logger à DEBUG, comme ça il écrit tout
    logger.setLevel(logging.INFO)
    
    # création d'un formateur qui va ajouter le temps, le niveau
    # de chaque message quand on écrira un message dans le log
    formatter = logging.Formatter('%(asctime)s :: %(levelname)s :: %(message)s')
    # création d'un handler qui va rediriger une écriture du log vers un fichier en mode 'append'
    file_handler = WatchedFileHandler('/var/log/solystic/cars-trackers%s.log'%(ginstanceID))
    # on lui met le niveau sur DEBUG, on lui dit qu'il doit utiliser le formateur
    # créé précédement et on ajoute ce handler au logger
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
        
    # création d'un second handler qui va rediriger chaque écriture de log
    # sur la console
    #stream_handler = logging.StreamHandler()
    #stream_handler.setLevel(logging.DEBUG)
    #logger.addHandler(stream_handler)

def readMainConfig(configFile, sectionName = 'DEFAULT'):
    config = cfg.ConfigParser()
    config.read(configFile)
    traitement =  config.getint(sectionName, 'traitement')
    ilot =  config.get(sectionName, 'ilot')
    return ilot, traitement

def mainLiveParcelDetection(logger):
    imageQ = Queue(1)
    incomingQ = Queue(1)

    httpserv = HttpServer(imageQ, incomingQ, logger)
    if ginstanceID != "0":
        numPort = 5000 + (int(ginstanceID)-1)*10
        port = str(numPort)
        httpservProcess = Thread(target=httpservThread, args=(httpserv, '0.0.0.0', numPort))
    else:
        httpservProcess = Thread(target=httpservThread, args=(httpserv, '0.0.0.0', 5000))
        port = '5000'

    ilot, traitement = readMainConfig(dirs.dir_config +  'mainParcelTracking.ini')
    configFile = dirs.dir_config + 'parcelTrackerWorker.ini'
    sectionName = 'DEFAULT'
    if ginstanceID != '0':
        sectionName = 'ParcelTrackerWorker' + str(int(ginstanceID) + (4 * (traitement - 1)))
    
    stopCrashFlag = False
    try:
        liveDetectionProcess = ParcelTrackerWorker(configFile, sectionName, imageQ, incomingQ, logger)
    except Exception as ex:
        print('Tracker worker failed to start !!', ex)
        raise SystemExit()
    
    httpservProcess.start()
    liveDetectionProcess.start()
    while True:
        liveDetectionProcess.join(1)
        if liveDetectionProcess._is_stopped:
            logger.error('Tracker has stopped !!')
            requests.post(url='http://localhost:' + port + '/shutdown')
            logger.error('shutting down httpserv...')
            raise SystemExit()
        httpservProcess.join(1)
        if httpservProcess._is_stopped:
            logger.error('httpserv has stopped !!')
            liveDetectionProcess.stoppingFlag.set()
            logger.error('shutting down tracker...')
            raise SystemExit()
    return

def httpservThread(httpserv, host='0.0.0.0', port=5000, debug=False):    
    httpserv.app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    logger = logging.getLogger()
    ConfigureLogger(logger)
    mainLiveParcelDetection(logger)
    
