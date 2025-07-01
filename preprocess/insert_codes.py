import pandas as pd
import sqlite3

# CSV 파일 경로
csv_path = "data/codes_20250415.csv"

# CSV 불러오기
df = pd.read_csv(csv_path, encoding='utf-8')

# SQLite DB에 저장
db_path = "database/address.db"
conn = sqlite3.connect(db_path)
df.to_sql('legal_dong', conn, if_exists='replace', index=False)
conn.commit()
conn.close()
