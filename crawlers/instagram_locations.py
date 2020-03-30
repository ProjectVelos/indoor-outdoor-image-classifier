
"""
from serpapi.google_search_results import GoogleSearchResults
client = GoogleSearchResults({"q": "coffee"})
result = client.get_dict()
"""

import requests
import re
from pprint import pprint
import random
import csv
import psycopg2
from celery import Celery
from celery.task import task
app = Celery('my_app',
             broker='redis://localhost:6379/2',
             backend='redis://localhost:6379/2')


DATABASE_NAME='uscovidwatch'
DATABASE_USER='uscovid'
DATABASE_PASSWORD='ve1os_c0v1d_9x'
DATABASE_HOST='db.bluefield.io'

connection = psycopg2.connect(user=DATABASE_USER,
                              password=DATABASE_PASSWORD,
                              host=DATABASE_HOST,
                              port="5432",
                              database=DATABASE_NAME)
cursor = connection.cursor()

def formatCity(city, state):
  city = city.lower()
  state = state.lower()

  city = city.replace(" ","-")
  city = city + "-" + state
  return city



def getInstagramLocationCode(city,state):
  try:
    fcity = formatCity(city,state)
    url = "https://www.picuki.com/search/{}".format(fcity)
    pattern = 'picuki\.com\/location\/({})\/(\d*)'.format(fcity)

    r = requests.get(url)
    response = r.text
    #m = prog.search(response)
    m = re.search(pattern,response)

    i_city_name = m.group(1)
    i_city_code = m.group(2)

    return {"i_city_name":i_city_name,"i_city_code":i_city_code}

  except Exception as e:
    print(e)
    print(city,state)
    return False

q = 'select id,city,state from cities where instagram_id is null'

cursor.execute(q)
records = cursor.fetchall()
print(records)

for record in records:
  id = record[0]
  city = record[1]
  state = record[2]
  city_code = getInstagramLocationCode(record[1],record[2])
  if city_code != False:
    u = 'update cities set instagram_id = {} where id = {}'.format(city_code['i_city_code'],record[0])
    print(u)

    cursor.execute(u)
    connection.commit()


"""

-------------

IMG_NUMBER = 0

def downloadImage(img_url):
  global IMG_NUMBER

  #img_name = str(random.randrange(1000)) + ".jpg"
  base_dir = "/Users/jim/Devel/velos_image/app/indoor-outdoor-image-classifier/test_images/"

  img_name = base_dir + str(IMG_NUMBER) + ".jpg"
  IMG_NUMBER = IMG_NUMBER + 1

  img_data = requests.get(img_url).content
  with open(img_name, 'wb') as handler:
    handler.write(img_data)

city = 'Agoura Hills'
state = 'California'

icity = getInstagramLocationCode(city,state)
pprint(icity)

r = requests.post(
    'https://stevesie.com/cloud/api/v1/endpoints/68cf504a-dea3-4114-a62e-020299915e8e/executions',
    headers={
        'Token': '2246052b-b228-467c-ac8b-11c71e6e4fd1',
    },
    json={
        'inputs': {
            'location_id': icity["i_city_code"],
            'max_id': '',
        },
        'proxy': {
          'type': 'shared',
          'location': 'nyc',
        },
        'format': 'json'
    },
)

response = r.json()
response_json = response["object"]["response"]["response_json"]
#print(response_json.keys())
#quit()
#print(type(response_json))
#pprint(response_json["data"]["location"]["edge_location_to_media"]["edges"])
#data.location.edge_location_to_media.page_info.end_cursor
page_key = response_json["data"]["location"]["edge_location_to_media"]["page_info"]["end_cursor"]
results = response_json["data"]["location"]["edge_location_to_media"]["edges"]

for result in results:
  img_url = result["node"]["display_url"].strip("'")
  print(img_url)
  downloadImage(img_url)
  print("****************")

print("PAGE KEY")
print(page_key)


r = requests.post(
    'https://stevesie.com/cloud/api/v1/endpoints/68cf504a-dea3-4114-a62e-020299915e8e/executions',
    headers={
        'Token': '2246052b-b228-467c-ac8b-11c71e6e4fd1',
    },
    json={
        'inputs': {
            'location_id': icity["i_city_code"],
            'max_id': page_key,
        },
        'proxy': {
          'type': 'shared',
          'location': 'nyc',
        },
        'format': 'json'
    },
)

response = r.json()
response_json = response["object"]["response"]["response_json"]
#print(response_json.keys())
#quit()
#print(type(response_json))
#pprint(response_json["data"]["location"]["edge_location_to_media"]["edges"])
#data.location.edge_location_to_media.page_info.end_cursor
page_key = response_json["data"]["location"]["edge_location_to_media"]["page_info"]["end_cursor"]
results = response_json["data"]["location"]["edge_location_to_media"]["edges"]

for result in results:
  img_url = result["node"]["display_url"].strip("'")
  print(img_url)
  downloadImage(img_url)

  print("****************")

print("PAGE KEY")
print(page_key)

#print(dir(response_json["object"]))
#print(response_json["object"]["response"]["response_json"].keys())
#pprint(response_json.data.location.edge_location_to_media.edges)
#print(dir(response_json))
#print(response_json.keys)
#data.location.edge_location_to_media.edges



"""