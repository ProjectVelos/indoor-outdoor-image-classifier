import psycopg2
import psycopg2.extras
from pprint import pprint

DATABASE_NAME='uscovidwatch'
DATABASE_USER='uscovid'
DATABASE_PASSWORD='ve1os_c0v1d_9x'
DATABASE_HOST='db.bluefield.io'



class stayAtHomeScore():

  def __init__(self):

    self.connection = psycopg2.connect(user=DATABASE_USER,
                                  password=DATABASE_PASSWORD,
                                  host=DATABASE_HOST,
                                  port="5432",
                                  database=DATABASE_NAME)

    self.cursor = self.connection.cursor(cursor_factory = psycopg2.extras.DictCursor)

    self.algo_result = {}
    self.gatherDirectLabels()
    self.calculateDirectScore()
    self.insertScore()

  def gatherDirectLabels(self):
    query = """select * from insta_images_categorized """
    self.cursor.execute(query)
    self.results = self.cursor.fetchall()


    for r in self.results:
      img_date = r['img_date']
      city = r['city']
      county = r['county']
      state = r['state']
      label_name = r['label_name']
      label_parent = r['label_parent']

      if img_date not in self.algo_result:
        self.algo_result[img_date] = {}

      if county not in self.algo_result[img_date]:
        self.algo_result[img_date][county] = {"city": city, "state": state, "day": img_date.strftime("%Y-%m-%d"), "direct_indoor_count":0, "direct_outdoor_count":0, "direct_score":0}

      if label_name == 'Outdoors' or label_parent == 'Outdoors':
        self.algo_result[img_date][county]["direct_outdoor_count"]  = self.algo_result[img_date][county]["direct_outdoor_count"] + 1

      elif label_name == 'Indoors' or label_parent == 'Indoors':
        self.algo_result[img_date][county]["direct_indoor_count"]  = self.algo_result[img_date][county]["direct_indoor_count"] + 1

  def gatherInDirectLabels(self):
    query = """select * from insta_images_uncategorized """
    self.cursor.execute(query)
    self.results = self.cursor.fetchall()


    for r in self.results:
      img_date = r['img_date']
      city = r['city']
      county = r['county']
      state = r['state']
      label_name = r['label_name']
      label_parent = r['label_parent']

      if img_date not in self.algo_result:
        self.algo_result[img_date] = {}

      if county not in self.algo_result[img_date]:
        self.algo_result[img_date][county] = {"city": city, "state": state, "day": img_date.strftime("%Y-%m-%d"), "direct_indoor_count":0, "direct_outdoor_count":0, "direct_score":0}

      if label_name == 'Outdoors' or label_parent == 'Outdoors':
        self.algo_result[img_date][county]["direct_outdoor_count"]  = self.algo_result[img_date][county]["direct_outdoor_count"] + 1

      elif label_name == 'Indoors' or label_parent == 'Indoors':
        self.algo_result[img_date][county]["direct_indoor_count"]  = self.algo_result[img_date][county]["direct_indoor_count"] + 1


  def calculateDirectScore(self):
    for day in self.algo_result:
      #if county in self.algo_result[day]:
      for county in self.algo_result[day]:
        indoor_count = self.algo_result[day][county]["direct_indoor_count"]
        outdoor_count = self.algo_result[day][county]["direct_outdoor_count"]

        if indoor_count > 0 and outdoor_count > 0:
          self.algo_result[day][county]['direct_score'] = (indoor_count / (indoor_count + outdoor_count)) * 100


  def insertScore(self):
    for day in self.algo_result:
      #if county in self.algo_result[day]:
      for county in self.algo_result[day]:
        city = self.algo_result[day][county]["city"]
        state = self.algo_result[day][county]["state"]
        indoor_count = self.algo_result[day][county]["direct_indoor_count"]
        outdoor_count = self.algo_result[day][county]["direct_outdoor_count"]
        direct_score = self.algo_result[day][county]["direct_score"]

        self._runquery(city,county,state,day,direct_score)

  def _runquery(self,city,county,state,day,score):

    query = """INSERT INTO social_distancing (city, county, state,day,score) 
            VALUES ({},{},{},{}).format(city,county,state,day,score)
            ON CONFLICT DO UPDATE 
            SET city = {}, 
            county = {},
            state = {},
            day = {},
            score = {}
            """.format(city,county,state,day,score,city,county,state,day,score)

    query2 ="""INSERT INTO social_distancing (city, county, state,day,score) 
            VALUES (%s,%s,%s,%s,%s)
            ON CONFLICT (city,day) DO UPDATE 
            SET city = %s, 
            county = %s,
            state = %s,
            day = %s,
            score = %s
            """
    print(city, county, state,day,score)
    self.cursor.execute(query2,(city, county, state,day,score,city, county, state,day,score))
    self.connection.commit()



s = stayAtHomeScore()



"""
TESTING TO PRINT OUT A PARTICULAR COUNTY
"""
"""
for day in algo_result:
  if county in algo_result[day]:
    for county in algo_result[day]:
      if county == "San Bernardino":
        indoor_count = algo_result[day][county]["indoor_count"]
        outdoor_count = algo_result[day][county]["outdoor_count"]
        day_formatted = algo_result[day][county]["day"]
        score = algo_result[day][county]["score"]
        print(day, county, indoor_count, outdoor_count, score)
"""

#pprint(algo_result)




