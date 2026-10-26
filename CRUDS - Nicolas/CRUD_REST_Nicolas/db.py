import mysql.connector
from config import MYSQL
class DB:
 def __enter__(self): self.conn=mysql.connector.connect(**MYSQL);self.cur=self.conn.cursor(dictionary=True);return self
 def __exit__(self,t,v,tb):
  try: self.conn.rollback() if t else self.conn.commit()
  finally: self.cur.close();self.conn.close()
 def execute(self,q,args=()): self.cur.execute(q,args);return self.cur.lastrowid
 def one(self,q,args=()): self.cur.execute(q,args);return self.cur.fetchone()
 def all(self,q,args=()): self.cur.execute(q,args);return self.cur.fetchall()
