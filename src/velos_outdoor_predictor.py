from src.util.config import load_configuration
from src.util.utils import get_last_checkpoint, load_image
from src.model import CNN_model
import argparse
import logging
import numpy as np
from pprint import pprint
from os import walk
from os import listdir
from os.path import isfile, join
#import ffmpeg
from ffmpy import FFmpeg

import os


class Image:

  def __init__(self,image_location, image_file,location_prediction, prediction_confidence = 0):
    self.image_location = image_location
    self.image_file = image_file
    self.location_prediction = location_prediction
    self.prediction_confidence = prediction_confidence




#Predicts the class for multiple input files
class VelosOutoorPredictor:

  def __init__(self, config_file = 'config/train_params.yml'):
    self.INDOOR_CONFIDENCE_LIMIT = .09
    self.OUTDOOR_CONFIDENCE_LIMIT = .98
    logging.info("Loading model")
    self.config = load_configuration(config_file)
    self.model = CNN_model.CNN(self.config)
    self.model.load_weights()

    #image sizes live in config and each batch/stream of images is assumed to all be the same size
    #images assumed square now until i do more research on keras input config

    self.img_size = (self.config['img_size'], self.config['img_size'])


  def preProcess(self, image_file):

    ff = FFmpeg(
    inputs = {image_file: None},
    outputs = {image_file: '-y -filter:v "scale=64:64"'}
    )
    ff.run()
    #image = ffmpeg.input(image_file)
    #image = ffmpeg.filter(image, 'scale', '64:64')
    #image = ffmpeg.output(image, 'jim.jpg').run()


  def postProcess(self,image_file,prediction):
    new_file_name = image_file.strip(".jpg")
    new_file_name = new_file_name + "_" + prediction + ".jpg"
    os.rename(image_file,new_file_name)


  def predict(self, image_file):
    self.preProcess(image_file)

    image = load_image(image_file, self.img_size)
    image = np.expand_dims(image, 0)

    prediction = self.model.predict(image)

    print("PREDICTION",prediction)

    if prediction < self.INDOOR_CONFIDENCE_LIMIT:
      self.postProcess(image_file, str(prediction) + "_I")

      return "INDOOR"

    elif prediction > self.OUTDOOR_CONFIDENCE_LIMIT:
      self.postProcess(image_file, str(prediction) + "_O")

      return "OUTDOOR"

    else:
      self.postProcess(image_file, str(prediction) + "_U")

      return "UNKNOWN"

    """
    for image_file in image_files:
      full_image_file = path + image_file
      image = load_image(full_image_file, self.img_size)
      image = np.expand_dims(image, 0)
      predictions[image_file] = prediction


    #pprint(predictions)
    for p in predictions:
      print(p,predictions[p])
    """






if __name__ == "__main__":
  vp = VelosOutoorPredictor("config/train_params.yml")
  path = "/Users/jim/Devel/velos_image/app/indoor-outdoor-image-classifier/test_images/"
  image_files = []

  onlyfiles = [f for f in listdir(path) if isfile(join(path, f))]
  pprint(onlyfiles)
  vp.predict(onlyfiles)
