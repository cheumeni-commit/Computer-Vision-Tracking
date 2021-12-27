import logging
import numpy as np
import tensorflow as tf

from PIL import Image

from src.libs.fasterObjectDetection.util import load_labelmap
                                                 

logger = logging.getLogger(__name__)


class ObjectDetector():
    """
        Classe ObjectDector.
    """
    
    def __init__(self, PATH_TO_CKPT, PATH_TO_LABELS,
                 min_score_threshold=0.5, gpuDevice="0", 
                 gpuFraction=0.4, initSize=(1944,2592,3)):
        
        logger.info('\nInitialization of ObjectDetector, and GPU loadings')
        
        self.category_index = load_labelmap(PATH_TO_LABELS)
        
        self.min_score_threshold = min_score_threshold
        #os.environ["CUDA_VISIBLE_DEVICES"] = gpuDevice
        
        #with tf.device('/device:GPU:1'):
        
        self.detection_graph = tf.Graph()
        with self.detection_graph.as_default():
            od_graph_def = tf.compat.v1.GraphDef() #tf.GraphDef()
            with tf.io.gfile.GFile(str(PATH_TO_CKPT), 'rb') as fid: #tf.gfile.GFile
                serialized_graph = fid.read()
                od_graph_def.ParseFromString(serialized_graph)
                tf.import_graph_def(od_graph_def, name='')

            config = tf.compat.v1.ConfigProto() #tf.ConfigProto()
            config.gpu_options.per_process_gpu_memory_fraction = gpuFraction
            self.sess = tf.compat.v1.Session(graph=self.detection_graph,config=config)

        
        ops = self.detection_graph.get_operations()
        all_tensor_names = {output.name for op in ops for output in op.outputs}
        self.tensor_dict = {}
        for key in ['num_detections', 'detection_boxes',
                    'detection_scores','detection_classes']:
            tensor_name = key + ':0'
            if tensor_name in all_tensor_names:
                self.tensor_dict[key] = self.detection_graph.get_tensor_by_name(tensor_name)          
        
        self.image_tensor = self.detection_graph.get_tensor_by_name('image_tensor:0')        
        
        logger.info('Starting initRun...')
        self.__initRun(initSize)
        logger.info('End of init, ObjectDector ready')
        

    def __initRun(self, initSize):
        data = Image.fromarray(np.random.randint(0, high=255, size=initSize), 'RGB')
        self.run_inference_for_frame(data)
        

    def run_inference_for_frame(self,image):
        # Run inference
        output_dict = self.sess.run(self.tensor_dict,feed_dict={self.image_tensor: np.expand_dims(image, 0)})    
        return self.__transformOutputdictInObjectList(output_dict)
        

    def __transformOutputdictInObjectList(self, output_dict):
        
        objectList = []
        numObjects = 0
        
        classes = output_dict.get('detection_classes')[0].astype(np.uint8)
        detection_boxes = output_dict.get('detection_boxes')[0]
        detection_scores = output_dict.get('detection_scores')[0]
        
        for i in range( int(output_dict.get('num_detections')[0])):
            score = detection_scores[i]
            if score > self.min_score_threshold:
                numObjects += 1
                objectList.append([])
                box = tuple(detection_boxes[i].tolist())
                if classes[i] in self.category_index.keys():
                    class_name = self.category_index[classes[i]].get('name')
                objectList[-1].append(class_name)
                objectList[-1].append(score)
                objectList[-1].append(box)

        return numObjects, objectList

