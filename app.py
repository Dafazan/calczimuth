from flask import Flask, render_template, request
import pandas as pd
import folium
import utm

app = Flask(__name__)

import math

import matplotlib.pyplot as plt
import io
import base64

def buat_plot_poligon(X, Y):

    x_coords = []
    y_coords = []
    labels = []

    for titik in X:
        x_coords.append(X[titik])
        y_coords.append(Y[titik])
        labels.append(titik)

    plt.figure()

    # garis poligon
    plt.plot(x_coords, y_coords, marker='o')

    # label titik
    for i, label in enumerate(labels):
        plt.text(x_coords[i], y_coords[i], label)

    plt.title("Visualisasi Poligon Koordinat")
    plt.xlabel("X")
    plt.ylabel("Y")

    plt.axis("equal")
    plt.grid()

    # simpan ke memory buffer
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close()

    buf.seek(0)

    # convert ke base64
    plot_base64 = base64.b64encode(buf.getvalue()).decode()

    return plot_base64

def dms_to_deg(d, m, s):
    """Convert degree minute second to decimal degree"""
    return d + m/60 + s/3600


def hitung_poligon(df):

    # koordinat awal BM (ubah sesuai data kamu)
    X = {"BM": 786289.114}
    Y = {"BM": 9240733.076}

    # azimuth awal BM -> TK1
    azimuth = {}
    azimuth[0] = 34.4514

    # =========================
    # HITUNG AZIMUTH
    # =========================
    for i in range(len(df)):

        sudut = dms_to_deg(
            df.loc[i, "deg_b"],
            df.loc[i, "min_b"],
            df.loc[i, "sec_b"]
        )

        if i > 0:

            az_prev = azimuth[i-1]

            az = az_prev + sudut - 180

            # normalisasi 0-360
            if az < 0:
                az += 360
            if az > 360:
                az -= 360

            azimuth[i] = az

    # =========================
    # HITUNG KOORDINAT
    # =========================
    hasil = []

    for i in range(len(df)):

        titik_awal = df.loc[i, "standing_alat"]
        titik_tujuan = df.loc[i, "tk_b"]

        jarak = df.loc[i, "distance-b"]

        a = math.radians(azimuth[i])

        dx = jarak * math.sin(a)
        dy = jarak * math.cos(a)

        X[titik_tujuan] = X[titik_awal] + dx
        Y[titik_tujuan] = Y[titik_awal] + dy

        hasil.append({
            "titik": titik_tujuan,
            "azimuth": round(azimuth[i],4),
            "dx": round(dx,3),
            "dy": round(dy,3),
            "X": round(X[titik_tujuan],3),
            "Y": round(Y[titik_tujuan],3)
        })

    return pd.DataFrame(hasil), X, Y

def buat_peta(df):

    coords = []

    # ubah koordinat UTM → lat lon
    for i in range(len(df)):

        x = df.loc[i, "X"]
        y = df.loc[i, "Y"]

        lat, lon = utm.to_latlon(x, y, 48, "M")

        coords.append((lat, lon))

    # buat map di titik pertama
    m = folium.Map(
    location=coords[0],
    zoom_start=18,
    width="100%",
    height="100%"
)

    # marker tiap titik
    for i, (lat, lon) in enumerate(coords):

        titik = df.loc[i, "titik"]

        folium.Marker(
            [lat, lon],
            popup=titik
        ).add_to(m)

    # garis poligon
    folium.PolyLine(coords, color="red", weight=3).add_to(m)

    return m._repr_html_()


@app.route('/')
def index():
    return render_template("index.html", data=None, columns=None, map_html=None)


@app.route('/upload', methods=['POST'])
def upload():

    file = request.files['file']

    if not file:
        return render_template("index.html")

    # ==============================
    # 1. BACA CSV
    # ==============================
    df = pd.read_csv(file)

    # tabel csv asli
    raw_data = df.to_dict(orient="records")
    raw_columns = df.columns


    # ==============================
    # 2. HITUNG POLIGON
    # ==============================
    hasil, X, Y = hitung_poligon(df)

    calc_data = hasil.to_dict(orient="records")
    calc_columns = hasil.columns


    # ==============================
    # 3. BUAT PETA LEAFLET
    # ==============================
    map_html = buat_peta(hasil)


    # ==============================
    # 4. BUAT PLOT MATPLOTLIB
    # ==============================
    plot_img = buat_plot_poligon(X, Y)


    # ==============================
    # 5. KIRIM KE HTML
    # ==============================
    return render_template(
        "index.html",

        raw_data=raw_data,
        raw_columns=raw_columns,

        calc_data=calc_data,
        calc_columns=calc_columns,

        map_html=map_html,
        plot_img=plot_img
    )

if __name__ == "__main__":
    app.run(debug=True)