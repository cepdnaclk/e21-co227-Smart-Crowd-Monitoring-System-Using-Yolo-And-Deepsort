# db_handler.py
import psycopg2
import time
import logging

logging.basicConfig(level=logging.INFO)

class CrowdDatabase:
    def __init__(self, host, database, user, password, update_interval=2, max_retries=5):
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.update_interval = update_interval
        self.max_retries = max_retries
        self.conn = None
        self.cur = None
        self.last_update = time.time()
        self.building_ids = []

        self.connect()

    def connect(self):
        """Try to connect with retries."""
        retries = 0
        while retries < self.max_retries:
            try:
                self.conn = psycopg2.connect(
                    host=self.host,
                    database=self.database,
                    user=self.user,
                    password=self.password
                )
                self.cur = self.conn.cursor()
                logging.info("✅ Database connected")
                # Fetch building IDs
                self.cur.execute("SELECT building_id FROM buildings")
                self.building_ids = [row[0] for row in self.cur.fetchall()]
                return
            except Exception as e:
                retries += 1
                logging.error(f"❌ DB connection failed (attempt {retries}): {e}")
                time.sleep(5 * retries)  # exponential backoff

        logging.critical("🚨 Could not connect to DB after several attempts.")
        self.conn = None
        self.cur = None

    def reconnect_if_needed(self):
        """Reconnect if the connection is closed."""
        if self.conn is None or self.conn.closed != 0:
            logging.warning("⚠️ Lost DB connection. Reconnecting...")
            self.connect()

    def insert_count(self, building_id, current_count):
        try:
            self.reconnect_if_needed()
            if self.conn is None:
                return  # Skip if no connection
            if building_id not in self.building_ids:
                logging.warning(f"Building ID '{building_id}' not found in DB")
                return
            self.cur.execute(
                "INSERT INTO crowd_counts (building_id, current_count) VALUES (%s, %s)",
                (building_id, current_count)
            )
            self.conn.commit()
        except Exception as e:
            logging.error(f"❌ Failed to insert count: {e}")
            self.connect()  # force reconnect for next time

    def insert_multiple_counts(self, counters_dict):
        current_time = time.time()
        if current_time - self.last_update >= self.update_interval:
            for bldg_id, count in counters_dict.items():
                self.insert_count(bldg_id, count)
            self.last_update = current_time

    def close(self):
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()
        logging.info("🔌 Database connection closed")
