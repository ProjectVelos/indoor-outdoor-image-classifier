import psycopg2



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

