from flask import Flask, render_template, request
import pandas as pd
import folium
import utm
import math

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)

# =========================
# DMS → DEG
# =========================
def dms_to_deg(d, m, s):
    return d + m/60 + s/3600


# =========================
# HITUNG POLIGON (VERSI COLAB)
# =========================
def hitung_poligon(df, X0, Y0, az_awal):

    # koordinat awal
    X = {"BM": X0}
    Y = {"BM": Y0}

    # azimuth awal
    azimuth = {}
    azimuth[0] = az_awal

    # =========================
    # HITUNG AZIMUTH
    # =========================
    for i in range(len(df)):

        deg = df.loc[i,"deg_b"]
        minute = df.loc[i,"min_b"]
        sec = df.loc[i,"sec_b"]

        sudut = dms_to_deg(deg, minute, sec)

        if i > 0:
            az_prev = azimuth[i-1]

            az = az_prev + sudut - 180

            # normalisasi
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

        deg = df.loc[i,"deg_b"]
        minute = df.loc[i,"min_b"]
        sec = df.loc[i,"sec_b"]

        sudut = dms_to_deg(deg, minute, sec)

        titik_awal = df.loc[i,"standing_alat"]
        titik_tujuan = df.loc[i,"tk_b"]
        jarak = df.loc[i,"distance-b"]

        a = math.radians(azimuth[i])

        dx = jarak * math.sin(a)
        dy = jarak * math.cos(a)

        X[titik_tujuan] = X[titik_awal] + dx
        Y[titik_tujuan] = Y[titik_awal] + dy

        hasil.append({
            "titik": titik_tujuan,
            "sudut": round(sudut,4),
            "azimuth": round(azimuth[i],4),
            "dx": round(dx,3),
            "dy": round(dy,3),
            "X": round(X[titik_tujuan],3),
            "Y": round(Y[titik_tujuan],3)
        })

    return pd.DataFrame(hasil), X, Y


# =========================
# PLOT POLIGON
# =========================
def buat_plot_poligon(X, Y):

    x_coords = []
    y_coords = []
    labels = []

    for titik in X:
        x_coords.append(X[titik])
        y_coords.append(Y[titik])
        labels.append(titik)

    plt.figure()
    plt.plot(x_coords, y_coords, marker='o')

    for i, label in enumerate(labels):
        plt.text(x_coords[i], y_coords[i], label)

    plt.title("Visualisasi Poligon")
    plt.axis("equal")
    plt.grid()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close()

    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode()


# =========================
# PETA (FOLIUM)
# =========================
def buat_peta(df):

    coords = []

    for i in range(len(df)):
        x = df.loc[i, "X"]
        y = df.loc[i, "Y"]

        lat, lon = utm.to_latlon(x, y, 48, "M")
        coords.append((lat, lon))

    m = folium.Map(location=coords[0], zoom_start=18)

    for i, (lat, lon) in enumerate(coords):
        titik = df.loc[i, "titik"]
        folium.Marker([lat, lon], popup=titik).add_to(m)

    folium.PolyLine(coords, color="red").add_to(m)

    return m._repr_html_()


# =========================
# ROUTES
# =========================
@app.route('/')
def index():
    return render_template("index.html")

@app.route('/info')
def info():
    return render_template("info.html")


@app.route('/upload', methods=['POST'])
def upload():

    file = request.files['file']
    if not file:
        return render_template("index.html")

    df = pd.read_csv(file)

    # input form
    X0 = float(request.form.get("x_awal"))
    Y0 = float(request.form.get("y_awal"))

    az_d = float(request.form.get("az_d"))
    az_m = float(request.form.get("az_m"))
    az_s = float(request.form.get("az_s"))

    az_awal = dms_to_deg(az_d, az_m, az_s)

    # =========================
    # HITUNG UTAMA (COLAB STYLE)
    # =========================
    hasil, X, Y = hitung_poligon(df, X0, Y0, az_awal)

    # =========================
    # HITUNG INFO SUDUT (DISPLAY SAJA)
    # =========================
    n = len(df)

    total_sudut = 0
    for i in range(n):
        total_sudut += dms_to_deg(
            df.loc[i,"deg_b"],
            df.loc[i,"min_b"],
            df.loc[i,"sec_b"]
        )

    total_teoritis = (n - 2) * 180
    fs = total_teoritis - total_sudut
    koreksi = fs / n

    info = {
        "total_sudut": total_sudut,
        "total_teoritis": total_teoritis,
        "fs": fs,
        "koreksi": koreksi
    }

    # =========================
    # RENDER
    # =========================
    return render_template(
        "index.html",
        raw_data=df.to_dict(orient="records"),
        raw_columns=df.columns,
        calc_data=hasil.to_dict(orient="records"),
        calc_columns=hasil.columns,
        map_html=buat_peta(hasil),
        plot_img=buat_plot_poligon(X, Y),
        info=info   # 🔥 INI YANG BARU
    )
@app.route('/kdv')
def result():
    return render_template("vertical.html")





# =========================
# FUNCTION PERHITUNGAN KDV
# =========================
def hitung_kdv(df, nilai_awal):
    df.columns = df.columns.str.strip()

    def hitung_data(row):
        bt_b_1 = float(row['bt_b_1'])
        bt_b_2 = float(row['bt_b_2'])
        ba_b_1 = float(row['ba_b_1'])
        bb_b_1 = float(row['bb_b_1'])
        ba_b_2 = float(row['ba_b_2'])
        bb_b_2 = float(row['bb_b_2'])

        bt_m_1 = float(row['bt_m_1'])
        bt_m_2 = float(row['bt_m_2'])
        ba_m_1 = float(row['ba_m_1'])
        bb_m_1 = float(row['bb_m_1'])
        ba_m_2 = float(row['ba_m_2'])
        bb_m_2 = float(row['bb_m_2'])

        # Koreksi tiga benang
        correction_b1 = ba_b_1 + bb_b_1 - (bt_b_1 * 2)
        correction_b2 = ba_b_2 + bb_b_2 - (bt_b_2 * 2)
        correction_m1 = ba_m_1 + bb_m_1 - (bt_m_1 * 2)
        correction_m2 = ba_m_2 + bb_m_2 - (bt_m_2 * 2)

        # Jarak
        db1 = (ba_b_1 - bb_b_1) * 100
        db2 = (ba_b_2 - bb_b_2) * 100
        dm1 = (ba_m_1 - bb_m_1) * 100
        dm2 = (ba_m_2 - bb_m_2) * 100

        db = db1 + db2
        dm = dm1 + dm2
        d_sect = db + dm

        # Beda tinggi
        bts1 = bt_m_1 - bt_b_1
        bts2 = bt_m_2 - bt_b_2
        diff = bts1 + bts2

        return pd.Series({
            'correction_b1': correction_b1,
            'correction_b2': correction_b2,
            'correction_m1': correction_m1,
            'correction_m2': correction_m2,
            'db': db,
            'dm': dm,
            'd_sect': d_sect,
            'bts1': bts1,
            'bts2': bts2,
            'diff': diff
        })

    hasil = df.apply(hitung_data, axis=1)
    df_hasil = pd.concat([df, hasil], axis=1)

    # Akumulasi awal
    df_hasil['hasil_akumulasi'] = nilai_awal + df_hasil['diff'].cumsum()

    # Koreksi KDV Loop Tertutup
    fh = df_hasil['diff'].sum()
    total_jarak = df_hasil['d_sect'].sum()

    df_hasil['koreksi_kdv'] = -fh * (
        df_hasil['d_sect'] / total_jarak
    )

    df_hasil['delta_h_koreksi'] = (
        df_hasil['diff'] + df_hasil['koreksi_kdv']
    )

    # Elevasi terkoreksi
    df_hasil['elevasi_terkoreksi'] = (
        nilai_awal + df_hasil['delta_h_koreksi'].cumsum()
    )

    return df_hasil, fh, total_jarak



# =========================
# ROUTE PROSES DATA
# =========================
@app.route('/uploadkdv', methods=['POST'])
def uploadkdv():
    file = request.files.get('file')

    if not file or file.filename == '':
        return render_template(
            "verticalindex.html",
            error="Silakan unggah file CSV terlebih dahulu."
        )

    try:
        nilai_awal = float(request.form['nilai_awal'])
        df = pd.read_csv(file)  # Dibaca langsung dari memori

        df_hasil, fh, total_jarak = hitung_kdv(df, nilai_awal)

        return render_template(
            "verticalindex.html",
            data_csv=df.to_dict(orient='records'),
            hasil=df_hasil.to_dict(orient='records'),
            fh=round(fh, 6),
            total_jarak=round(total_jarak, 2)
        )

    except Exception as e:
        return render_template(
            "verticalindex.html",
            error=f"Terjadi kesalahan: {e}"
        )


if __name__ == '__main__':
    app.run(debug=True)