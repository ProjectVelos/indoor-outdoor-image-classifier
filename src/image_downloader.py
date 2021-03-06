import requests
import re
from pprint import pprint
import random
import csv
import psycopg2
import _md5
import datetime
#import pytz
import time
#TZ = pytz.timezone('America/Los_Angeles')
import hashlib
import os

import sys
from random import randint
from velos_image_classifier import VelosImageClassifier

classifier = VelosImageClassifier()



DATABASE_NAME='uscovidwatch'
DATABASE_USER='uscovid'
DATABASE_PASSWORD='ve1os_c0v1d_9x'
DATABASE_HOST='db.bluefield.io'

MAX_HOURS_TO_DOWNLOAD = 10 * 24
SAMPLE_SIZE  = 10 #1 - 100 (Percent of images downloaded to run AWS model on

connection = psycopg2.connect(user=DATABASE_USER,
                              password=DATABASE_PASSWORD,
                              host=DATABASE_HOST,
                              port="5432",
                              database=DATABASE_NAME)

cursor = connection.cursor()

STEVIES_TOKEN = '2246052b-b228-467c-ac8b-11c71e6e4fd1'
STEVIES_ENDPOINT = 'https://stevesie.com/cloud/api/v1/endpoints/68cf504a-dea3-4114-a62e-020299915e8e/executions'
#IMG_NUMBER = 0
BASE_DIR = "/home/jim/Devel/indoor-outdoor-image-classifier/test_images/"

classifier = VelosImageClassifier()

def getDir(city,county,state):
  global BASE_DIR

  city = city.lower().replace(" ","_")
  county = county.lower().replace(" ","_")
  state = state.lower().replace(" ","_")

  state_dir = BASE_DIR + state
  county_dir = state_dir + "/" + county
  city_dir = county_dir + "/" + city + "/"
  return city_dir

"""
Download Image to Proper Directory
"""
def downloadImage(img_url,img_hash,city,county,state,img_date):

  img_dir = getDir(city,county,state)

  img_file = img_dir + str(img_date) + "-" + img_hash
  img_file = img_file + ".jpg"
  if os.path.isfile(img_file) == True:
    print("Ignoring image {} - already downloaded".format(img_file))
    return False

  else:
    tic = time.perf_counter()
    img_data = requests.get(img_url).content
    with open(img_file, 'wb') as handler:
      handler.write(img_data)
    toc = time.perf_counter()
    print(f"Downloaded file in {toc - tic:0.4f} seconds")
    return img_file


"""
Ensure Image Time is Within our Window
"""
def _checkImageTime(img_timestamp):
  epoch = time.time()
  hours_ago = (epoch - img_timestamp) / (60 * 60)
  if hours_ago > MAX_HOURS_TO_DOWNLOAD:
    return False

  img_date = time.strftime("%Y-%m-%d", time.gmtime(img_timestamp))
  return img_date



def insertResults(img_date,img_hash,city,county,state,insta_code,img_url,img_file,img_classification):
  tic = time.perf_counter()

  """ Insert Image Scene (Outdoors or Indoors)"""

  scene = img_classification["location"]
  sql = """INSERT into insta_images(img_date,img_hash,city,county,state,insta_location_code,img_url,img_file,scene) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) 
  ON CONFLICT DO NOTHING;"""


  cursor.execute(sql, (img_date,img_hash,city,county,state,insta_code,img_url,img_file,scene,))
  #connection.commit()
  #toc = time.perf_counter()
  #print(f"Inserted Labels To DB in {toc - tic:0.4f} seconds")

  """ Insert Image Categories and Precision"""

  sql = """INSERT into insta_image_category(img_hash,img_category,probability) VALUES(%s,%s,%s) 
  ON CONFLICT DO NOTHING;"""

  for cat in img_classification["categories"]:
    category = cat["category"]
    probability = float(cat["probability"])

    cursor.execute(sql, (img_hash,category, probability,))
    #connection.commit()

  sql = """INSERT into insta_image_attribute(img_hash,img_attribute) VALUES(%s,%s) 
  ON CONFLICT DO NOTHING;"""

  for attribute in img_classification["attributes"]:
    cursor.execute(sql, (img_hash,attribute,))
    #connection.commit()

  connection.commit()
  toc = time.perf_counter()
  print(f"Inserted Image To DB in {toc - tic:0.4f} seconds")



"""
This is where the primary processing occurs
"""
def getImages(city,county,state,insta_code,page_key=''):
  tic = time.perf_counter()
  r = requests.post(
      STEVIES_ENDPOINT,
      headers={
          'Token': STEVIES_TOKEN,
      },
      json={
          'inputs': {
              'location_id': insta_code,
              'max_id': page_key,
          },
          'proxy': {
            'type': 'shared',
            'location': 'nyc',
          },
          'format': 'json'
      },
  )
  try:
    continue_paging = True
    response = r.json()
    response_json = response["object"]["response"]["response_json"]

    page_key = response_json["data"]["location"]["edge_location_to_media"]["page_info"]["end_cursor"]
    results = response_json["data"]["location"]["edge_location_to_media"]["edges"]

    #epoch = datetime.datetime.utcfromtimestamp(0)
    toc = time.perf_counter()
    print(f"Got Insta Image URLS in {toc - tic:0.4f} seconds")
    for result in results:
      print("----------")
      print("DOWNLOADING IMAGE From {}-{}-{}".format(state,county,city))

      img_url = result["node"]["display_url"].strip("'")
      img_timestamp  = result["node"]["taken_at_timestamp"]
      img_id = result["node"]["id"]
      img_hash = hashlib.md5(img_url.encode('UTF')).hexdigest()


      """Check image time to ensure we are within our time window"""
      img_date = _checkImageTime(img_timestamp)
      if img_date != False:

        """Download Image"""
        img_file= downloadImage(img_url,img_hash,city,county,state,img_date)
        if img_file != False:

          #"""Run Sampler"""
          #smp = randint(1,100)
          #if smp < SAMPLE_SIZE:

          """Run ML to detect Labels"""
          img_classification = classifier.classify_file(img_file)

          """Insert results Into DB"""
          insertResults(img_date,img_hash,city,county,state,insta_code,img_url,img_file,img_classification)
  

      else:
        continue_paging = False

    if continue_paging == True:
      print("Recursion - Downloading images from {}-{}-{} current date {}".format(city,county,state,img_date))
      return getImages(city,county,state,insta_code,page_key)

  except Exception as e:
    print(e)

  #print("PAGE KEY")
  #print(page_key)

"""
Create state, county, and city directories if they don't exist
"""
def createDirectory(city,county,state):
  global BASE_DIR

  city = city.lower().replace(" ","_")
  county = county.lower().replace(" ","_")
  state = state.lower().replace(" ","_")

  state_dir = BASE_DIR + state
  county_dir = state_dir + "/" + county
  city_dir = county_dir + "/" + city
  if os.path.isdir(state_dir) == False:
    print("Creating directory", state_dir)
    os.mkdir(state_dir)

  if os.path.isdir(county_dir) == False:
    print("Creating directory", county_dir)
    os.mkdir(county_dir)

  if os.path.isdir(city_dir) == False:
    print("Creating directory", city_dir)
    os.mkdir(city_dir)
"""Main"""

"""Get Cities"""

if (len(sys.argv) < 2):
  print("*********************************************************")
  print("***Please enter a letter to set what cities to process")
  print("Example:  python insta_processor.py C")
  print("Would set this python process to process cities")
  print("starting with the letter C")
  print("*********************************************************")

  quit()

else:
  city_letter = sys.argv[1]
q = "select id,city,county,state,instagram_id from cities where instagram_id is not null and city like '{}%'".format(city_letter)
print(q)

"""
def run_all():
  process.delay('A')
  process.delay('B')
  process.delay('C')


@task()
def run_processor(city_letter):
  #do stuff
"""

cursor.execute(q)
records = cursor.fetchall()

locations = []
for record in records:
  locations.append(record)
  id = record[0]
  city = record[1]
  county = record[2]
  state = record[3]
  instagram_id = record[4]

  """Create Directory If Necessary"""
  createDirectory(city,county,state)

  "Download and Process Images"
  getImages(city,county,state,instagram_id)

