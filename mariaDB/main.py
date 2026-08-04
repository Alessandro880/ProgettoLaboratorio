import mariadb

conn = mariadb.connect(
    host="127.0.0.1",
    port=3306,
    user="user",
    password="user",
    database="user_db"
    )

def execute_query(conn:mariadb.Connection, query:str):
    with conn.cursor() as cursor:
        cursor.execute(query)

        if cursor.description is not None:
            result = cursor.fetchall()
        else :
            result = []

    conn.commit()  # necessario per rendere permanente le query eccetto select
    return result

cursor =  conn.cursor()

nome = "Alex"
cursor.execute("Select * FROM users WHERE name = ?", (nome,))
result = cursor.fetchall()
print(result)


result = execute_query(conn, "SELECT * FROM users")
#print(result)

conn.close()