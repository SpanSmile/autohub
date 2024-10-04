from dotenv import load_dotenv
import pymysql.cursors
import threading
from datetime import datetime
import time
import os

load_dotenv()

def connect_db():
    db = pymysql.connect(host=os.getenv('DB_HOST'),
                    port = int(os.getenv('DB_PORT')),
                    user=os.getenv('DB_USER'),
                    password=os.getenv('DB_PASSWORD').encode().decode('latin1'),
                    database=os.getenv('DB_NAME'),
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor)
    return db

def key_mapping():
    key_mapping = {
        'Fabrikat': 'manufacturer',
        'Modell': 'model',
        'Fordonsår / Modellår': 'production_year',
        'Registreringsnummer': 'regno',
        'Chassinr / VIN': 'vin',
        'Stöldstatus Sverige': 'theft_status',
        'Status': 'vehicle_status',
        'Import / Införsel': 'imported',
        'Först registrerad': 'first_registered_date',
        'Trafik i Sverige': 'traffic_in_sweden_date',
        'Antal ägare': 'owners_count',
        'Senaste ägarbyte': 'last_owner_change_date',
        'Senast besiktigad': 'last_inspection_date',
        'Mätarställning (besiktning)': 'mileage',
        'Nästa besiktning senast': 'next_inspection_date',
        'Årlig skatt': 'annual_tax',
        'Förhöjd skatt (År 1–3)': 'first_3_years_tax',
        'Årlig skatt (År 4–)': 'after_3_years_tax',
        'Skattemånad': 'tax_month',
        'Kreditköp': 'credit_purchase',
        'Leasad': 'leased',
        'Motoreffekt': 'power',
        'Motorvolym': 'engine_volume',
        'Toppfart': 'top_speed',
        'Drivmedel': 'fuel_type',
        'Växellåda': 'transmission',
        'Fyrhjulsdrift': 'four_wheel_drive',
        'Bränsleförbrukning (NEDC)': 'fuel_consumption',
        'Passagerare': 'passengers',
        'Airbag passagerare': 'passenger_airbag',
        'Draganordning': 'towing_hitch',
        'Färg': 'color',
        'Kaross': 'body_type',
        'Längd': 'length',
        'Bredd': 'width',
        'Höjd': 'height',
        'Tjänstevikt': 'curb_weight',
        'Totalvikt': 'total_weight',
        'Lastvikt': 'payload_capacity',
        'Släpvagnsvikt': 'trailer_weight',
        'Axelavstånd': 'axle_distance',
        'Däck fram': 'tire_front',
        'Däck bak': 'tire_rear'
    }
    return key_mapping

def db_uppload(db, cardata, auction, file, upploads_path):
    try:
        with db.cursor() as cursor:
            cursor.execute(f"SELECT id, regno FROM Vehicle WHERE regno = '{cardata['regno']}';")
            dbcar_regno = cursor.fetchone()

            if dbcar_regno is None:
                columns = ', '.join(cardata.keys())
                placeholders = ', '.join(['%s'] * len(cardata))
                values = tuple(cardata.values())
                sql_query = f"INSERT INTO Vehicle ({columns}) VALUES ({placeholders})"
                cursor.execute(sql_query, values)
                vehicle_id = cursor.lastrowid
                cursor.execute(f"SELECT is_active FROM Auction WHERE vehicle_id = {vehicle_id};")
                is_active = cursor.fetchone()

                if is_active is None or is_active['is_active'] == 0:
                    
                    sql_auction = "INSERT INTO Auction (user_id, vehicle_id, end_time, description) VALUES (%s, %s, %s, %s)"
                    cursor.execute(sql_auction, (auction['id'], vehicle_id, auction['end_date'], auction['description']))
                    auction_id = cursor.lastrowid
                    sql_bid = "INSERT INTO Highest_bid (auction_id, starting_price, reservation_price) VALUES (%s, %s, %s)"
                    cursor.execute(sql_bid, (auction_id, auction['price'], auction['final_p']))


                    create_auction_folder(auction_id, upploads_path)
                    if file:
                        filename = f"image_{len(os.listdir(os.path.join(upploads_path, f'auction_{auction_id}'))) + 1}.jpg"
                        file.save(os.path.join(upploads_path, f'auction_{auction_id}', filename))
                        cursor.execute("INSERT INTO Add_on_url (auction_id, url) VALUES (%s, %s)", (auction_id, f'uploads/auction_{auction_id}/{filename}'))

                    db.commit()
                    return True
                else:
                    return False
            else:

                vehicle_id = dbcar_regno['id']


                cursor.execute(f"SELECT is_active FROM Auction WHERE vehicle_id = {vehicle_id};")
                is_active = cursor.fetchall()

                if not is_active or all(record['is_active'] == 0 for record in is_active):

                    sql_auction = "INSERT INTO Auction (user_id, vehicle_id, end_time, description) VALUES (%s, %s, %s, %s)"
                    cursor.execute(sql_auction, (auction['id'], vehicle_id, auction['end_date'], auction['description']))
                    auction_id = cursor.lastrowid
                    sql_bid = "INSERT INTO Highest_bid (auction_id, starting_price, reservation_price) VALUES (%s, %s, %s)"
                    cursor.execute(sql_bid, (auction_id, auction['price'], auction['final_p']))


                    create_auction_folder(auction_id, upploads_path)
                    if file:
                        filename = f"image_{len(os.listdir(os.path.join(upploads_path, f'auction_{auction_id}'))) + 1}.jpg"
                        file.save(os.path.join(upploads_path, f'auction_{auction_id}', filename))
                        cursor.execute("INSERT INTO Add_on_url (auction_id, url) VALUES (%s, %s)", (auction_id, f'uploads/auction_{auction_id}/{filename}'))

                    db.commit()
                    return True
                else:
                    return False

    except Exception as e:
        print("An error occurred:", e)
        return False

def create_auction_folder(auction_id, uploads_path):
    auction_path = os.path.join(uploads_path, f'auction_{auction_id}')
    if not os.path.exists(auction_path):
        os.makedirs(auction_path)


def schedule(db):
    auction_thread = threading.Thread(target=check_auction_status, args=(db,) )
    auction_thread.daemon = True
    auction_thread.start()

def check_auction_status(db):
    while True:       
        try:
            with db.cursor() as cursor:
                current_time = datetime.now()
                cursor.execute(f"SELECT auction_id FROM Auction WHERE is_active = 1 AND end_time < '{current_time}'")
                ended_auctions = cursor.fetchall()
                print('schedule')
                if ended_auctions:
                    for auction_id in ended_auctions:
                        cursor.execute("UPDATE Auction SET is_active = 0 WHERE auction_id = %s", (auction_id['auction_id']))
                    db.commit()
        except Exception as e:
            print("An error occurred whith scheduler:", e)
        time.sleep(300)