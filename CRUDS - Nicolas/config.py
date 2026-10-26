import os
from dotenv import load_dotenv
load_dotenv()
MYSQL=dict(host=os.getenv('MYSQL_HOST','localhost'),port=int(os.getenv('MYSQL_PORT','3306')),user=os.getenv('MYSQL_USER','root'),password=os.getenv('MYSQL_PASSWORD',''),database=os.getenv('MYSQL_DATABASE','poli_restaurante'))
