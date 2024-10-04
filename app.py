from flask import Flask, redirect, url_for, render_template, request, session, flash
from dotenv import load_dotenv
from pullreg_linux import get_reg_data
from functions import connect_db, db_uppload, key_mapping, schedule
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
db = connect_db()
uploads_path = os.path.join(app.root_path, 'static/uploads')
load_dotenv()
schedule(db)

@app.route("/",  methods=["POST", "GET"])
def home():
    if request.method == "POST":
        sort = request.form.get("brand")
        if sort == "":
            return redirect(url_for("home"))
        try:
            with db.cursor() as cursor:
                cursor.execute(f"SELECT t1.auction_id, t4.bid, t1.end_time, t2.manufacturer, t2.model, t2.mileage, t2.production_year, t3.url FROM Auction as t1 JOIN Vehicle as t2 on t1.vehicle_id = t2.id JOIN Add_on_url as t3 on t1.auction_id = t3.auction_id JOIN Highest_bid as t4 on t1.auction_id = t4.auction_id WHERE t1.is_active = True and t2.manufacturer = '{sort}';")
                auctions = cursor.fetchall()
        except Exception as e:
                print("An error occurred:", e)
        return render_template("home.html", auctions=auctions)
    else:
        try:
            with db.cursor() as cursor:
                cursor.execute("SELECT t1.auction_id, t4.bid, t1.end_time, t2.manufacturer, t2.model, t2.mileage, t2.production_year, t3.url FROM Auction as t1 JOIN Vehicle as t2 on t1.vehicle_id = t2.id JOIN Add_on_url as t3 on t1.auction_id = t3.auction_id JOIN Highest_bid as t4 on t1.auction_id = t4.auction_id WHERE t1.is_active = True;")
                auctions = cursor.fetchall()
        except Exception as e:
                print("An error occurred:", e)
        return render_template("home.html", auctions=auctions)

@app.route("/auction/<auction_id>", methods=["POST", "GET"])
def auction_details(auction_id):
    if request.method == "POST":
        bid = int(request.form.get('bid'))
        try:
            with db.cursor() as cursor:

                cursor.execute("START TRANSACTION")
                current_time = datetime.now()
                cursor.execute(f"SELECT t1.bid, t1.starting_price, t2.end_time FROM Highest_bid as t1 JOIN Auction as t2 on t1.auction_id = t2.auction_id WHERE t1.auction_id = {auction_id};")
                highest_bid = cursor.fetchone()
                if highest_bid['end_time'] > current_time:
                    if highest_bid['bid'] is None:
                        highest_bid = highest_bid['starting_price']
                    else:
                        highest_bid = highest_bid['bid']

                    if highest_bid < bid:
                        cursor.execute("UPDATE Highest_bid SET user_id = %s, bid = %s WHERE auction_id = %s", (session['id'], bid, auction_id))

                        db.commit()
                        flash('Budet har accepteras!')
                    else:
                        flash('Budet är för lågt!')
                else:
                    flash('Auktionen är slut!')
                

        except Exception as e:
            db.rollback()
            flash('Error processing bud: ' + str(e), 'error')

        finally:
            cursor.close()
        return redirect(url_for("auction_details", auction_id=auction_id))
    else:
        try:
            with db.cursor() as cursor:
                cursor.execute(f"SELECT t1.auction_id, t5.username, t4.bid, t4.starting_price, t1.end_time, t1.description, t2.manufacturer, t2.model, t2.body_type, t2.color, t2.mileage, t2.production_year, t2.fuel_type, t2.transmission, t2.power, t2.four_wheel_drive, t3.url FROM Auction as t1 JOIN Vehicle as t2 on t1.vehicle_id = t2.id JOIN Add_on_url as t3 on t1.auction_id = t3.auction_id JOIN Highest_bid as t4 on t1.auction_id = t4.auction_id LEFT JOIN User as t5 on t4.user_id = t5.user_id WHERE t1.auction_id = {auction_id} and t1.is_active = True;")
                auction = cursor.fetchone()
                cursor.execute(f"SELECT t2.* FROM Auction as t1 JOIN Vehicle as t2 on t1.vehicle_id = t2.id WHERE t1.auction_id = {auction_id};")
                allcardata = cursor.fetchone()
                mapping = key_mapping()
                mapped_alldata = {}
                for key,value in mapping.items():
                    if value in allcardata and allcardata[value] != None:
                        mapped_alldata[key] = allcardata[value]
        except Exception as e:
                print("An error occurred:", e)
                return redirect(url_for('home'))
        return render_template("carListing.html", auction=auction, allcardata=mapped_alldata)


@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        user = request.form.get("username")
        password = request.form.get("password")
        if not user or not password:
            flash("Skriv lösenord och användarnamn!", "alert")
            return redirect(url_for("login"))

        try:
            with db.cursor() as cursor:
                cursor.execute(f"SELECT user_id, username, password FROM User WHERE username='{user}';")
                dbuser = cursor.fetchone()
        except Exception as e:
                print("An error occurred:", e)
        if dbuser: 
            if user == dbuser['username']:
                if password == dbuser['password']:
                    session["user"] = user
                    session["id"] = dbuser['user_id']
                    flash(f"Inlogging Lyckad!, Välkommen {user}")
                    return redirect(url_for("home"))

        flash("ERROR - Fel användarnamn eller lösenord")
        return redirect(url_for("login"))
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    if "user" in session:
        user = session["user"]
        flash(f"Du är nu utloggad!, {user}", "alert")
    session.pop("user", None)
    session.pop("id", None)
    session.pop("car", None)
    return redirect(url_for("home"))

@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        user = request.form.get("username")
        password = request.form.get("password")
        email = request.form.get("email")
        if user and password and email != "":
            try:
                with db.cursor() as cursor:
                    cursor.execute(f"SELECT username, email FROM User WHERE username = '{user}' OR email = '{email}';")
                    dbdata = cursor.fetchone()
                    if not dbdata:
                        sql = "INSERT INTO User (username, password, email)  VALUES (%s, %s, %s)"
                        cursor.execute(sql, (user, password, email))
                        user_id = cursor.lastrowid
                        db.commit()
                        session["user"] = user
                        session["id"] = user_id
                        return redirect(url_for("home"))
            except Exception as e:
                print("An error occurred:", e)
        flash("Användare finns redan - Välj nytt användarnamn eller epost!", "alert")
        return render_template("register.html")
    else:
        return render_template("register.html")

@app.route("/user")
def profile():
    return render_template("profile.html")

@app.route("/user/ads")
def user_ads():
    if "user" in session:
        try:
            with db.cursor() as cursor:
                cursor.execute(f"SELECT t1.auction_id, t4.bid, t1.end_time, t2.manufacturer, t2.model, t2.mileage, t2.production_year, t3.url FROM Auction as t1 JOIN Vehicle as t2 on t1.vehicle_id = t2.id JOIN Add_on_url as t3 on t1.auction_id = t3.auction_id JOIN Highest_bid as t4 on t1.auction_id = t4.auction_id WHERE t1.is_active = True and t1.user_id = {session['id']};")
                auctions = cursor.fetchall()
        except Exception as e:
            print("An error occurred:", e)
        return render_template("user_ads.html", auctions=auctions)
    else:
        return redirect(url_for("home"))

@app.route("/user/new_ad", methods=["POST","GET"])
def new_ad1():
    if "user" in session:
        if request.method == "POST":
            reg = request.form.get("reg")
            if "car" in session:
                if reg != session['car']['regno']:
                    car = get_reg_data(reg)
                    session["car"] = car
            else:
                car = get_reg_data(reg)
                session["car"] = car
            return redirect(url_for("new_ad2"))
        else:
            return render_template("new_ad_1.html")
    else:
        return redirect(url_for("home"))

@app.route("/user/new_ad2/", methods=["POST","GET"])
def new_ad2():
    if "user" in session and "car" in session:
        if request.method == "POST":
            dict_auction = {}

            mileage = request.form.get("mileage")  

            car = session["car"]
            car["mileage"] = mileage

            dict_auction['id'] = session["id"]
            dict_auction['price'] = request.form.get("price")
            dict_auction['final_p'] = request.form.get("final_price")
            dict_auction['end_date'] = request.form.get("end_time")
            dict_auction['description'] = request.form.get("additional_info")

            file = request.files["image"]

            final = db_uppload(db, car, dict_auction, file, uploads_path)

            session.pop("car", None)

            if final is True:
                flash("Din annons lyckades att laddas upp!", "alert")
                return redirect(url_for("home"))
            else:
                flash("Din annons misslyckades!", "alert")
                return redirect(url_for("new_ad1"))
            
        else:
            car = session["car"]
            show = ["manufacturer", "model", "production_year", "regno", "vin", "mileage", "power", "fuel_type", "transmission", "color", "body_type"]
            cardata = {}
            if car["model"] is not None:
                for spec in car:
                    if spec in show:
                        cardata[spec] = car[spec]
                return render_template("new_ad_2.html", car=cardata)
            else:
                flash("Felaktigt regnummer!")
                return redirect(url_for("new_ad1"))
    else:
         return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)