import sqlite3

def init_db():
    conn = sqlite3.connect('assistant.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS threads (
            id TEXT PRIMARY KEY,
            user_message TEXT,
            assistant_message TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_thread(thread_id, user_message, assistant_message):
    try:
        conn = sqlite3.connect('assistant.db')
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO threads (id, user_message, assistant_message) VALUES (?, ?, ?)', 
                       (thread_id, user_message, assistant_message))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

def delete_thread(thread_id):
    try:
        conn = sqlite3.connect('assistant.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM threads WHERE id = ?', (thread_id,))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()