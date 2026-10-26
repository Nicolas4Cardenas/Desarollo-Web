from sqlalchemy import create_engine,text
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session
from config import MYSQL
engine=create_engine(URL.create('mysql+pymysql',username=MYSQL['user'],password=MYSQL['password'],host=MYSQL['host'],port=MYSQL['port'],database=MYSQL['database']),pool_pre_ping=True)
class DB:
 def __enter__(self): self.session=Session(engine);return self
 def __exit__(self,t,v,tb):
  try: self.session.rollback() if t else self.session.commit()
  finally: self.session.close()
 def _q(self,q,args):
  # Traducción de parámetros posicionales %s a parámetros nombrados de SQLAlchemy
  parts=q.split('%s');params={f'p{i}':v for i,v in enumerate(args)}
  return text(''.join(s+(f':p{i}' if i<len(parts)-1 else '') for i,s in enumerate(parts))),params
 def execute(self,q,args=()):
  stmt,params=self._q(q,args);result=self.session.execute(stmt,params)
  return result.lastrowid
 def one(self,q,args=()):
  stmt,params=self._q(q,args);r=self.session.execute(stmt,params).mappings().first();return dict(r) if r else None
 def all(self,q,args=()):
  stmt,params=self._q(q,args);return [dict(r) for r in self.session.execute(stmt,params).mappings().all()]
