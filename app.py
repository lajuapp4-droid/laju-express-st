import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. KONFIGURASI HALAMAN & DATABASE
# ==========================================
st.set_page_config(page_title="Laju Express", page_icon="📦", layout="centered")

# Koneksi ke Google Sheets
# Nanti URL ini diganti sama URL Google Sheets kamu yang udah di-share public/editor
GSHEETS_URL = "https://docs.google.com/spreadsheets/d/1mqAYhGEDgw6Fiu2yHUug16QXrzJO-7Jgr1Z4UTt0DOM/edit?usp=sharing"

@st.cache_resource(ttl=10)
def load_data(sheet_name):
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=GSHEETS_URL, worksheet=sheet_name)
    return df.dropna(how="all") # Bersihin baris kosong

def save_data(df, sheet_name):
    conn = st.connection("gsheets", type=GSheetsConnection)
    conn.update(worksheet=sheet_name, data=df)
    st.cache_resource.clear()

# ==========================================
# 2. LOGIKA PRICING & VOLUME
# ==========================================
def hitung_ongkir(zona, berat, layanan, p, l, t, kategori, asuransi_val, is_cod):
    # Base Rate
    harga_dasar = {"Satu Kota": 8000, "Satu Provinsi": 12000, "Sesama Jawa": 20000, "Lintas Pulau": 45000}
    base = harga_dasar.get(zona, 8000)
    
    # Kargo minimal 10kg
    if layanan == "Cargo" and berat < 10:
        berat = 10
        st.warning("Layanan Cargo otomatis dihitung minimal 10kg ya bosku!")

    # Multiplier
    multiplier = {"Reguler": 1, "Sameday": 1.5, "Instant": 2, "Cargo": 0.65}
    ongkir_berat = base * berat * multiplier.get(layanan, 1)

    # Volume Surcharge
    volume = p * l * t
    biaya_oversize = 0
    if volume > 40000:
        kelebihan = volume - 40000
        biaya_oversize = ((kelebihan // 250) + 1) * 1500 if kelebihan % 250 != 0 else (kelebihan // 250) * 1500

    # Kategori Surcharge
    biaya_kategori = 0
    if kategori == "Pecah Belah": biaya_kategori = 5000
    elif kategori == "Elektronik": biaya_kategori = 10000
    elif kategori == "Makanan": biaya_kategori = 3000

    # Asuransi & COD
    biaya_asuransi = asuransi_val * 0.005 # 0.5%
    biaya_cod = 5000 if is_cod else 0

    total = ongkir_berat + biaya_oversize + biaya_kategori + biaya_asuransi + biaya_cod
    return total

# ==========================================
# 3. SISTEM LOGIN (SESSION STATE)
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['role'] = ''
    st.session_state['username'] = ''
    st.session_state['cabang'] = ''

def login_form():
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>Laju Express Portal</h1>", unsafe_allow_html=True)
    with st.form("login_form"):
        user_input = st.text_input("Username")
        pass_input = st.text_input("Password", type="password")
        submit = st.form_submit_button("Masuk", use_container_width=True)
        
        if submit:
            try:
                users_df = load_data("USERS")
                user_match = users_df[(users_df['Username'] == user_input) & (users_df['Password'] == pass_input)]
                
                if not user_match.empty:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = user_match.iloc[0]['Username']
                    st.session_state['role'] = user_match.iloc[0]['Role']
                    st.session_state['cabang'] = user_match.iloc[0]['Cabang']
                    st.rerun()
                else:
                    st.error("Username atau password salah, coba cek lagi bosku!")
            except Exception as e:
                st.error(f"Gagal konek database. Pastikan URL GSheets benar! Error: {e}")

# ==========================================
# 4. DASHBOARD & FITUR (RBAC)
# ==========================================
def main_dashboard():
    role = st.session_state['role']
    st.success(f"Selamat datang, {st.session_state['username']}! (Role: {role} | Cabang: {st.session_state['cabang']})")
    
    if st.button("Logout"):
        st.session_state['logged_in'] = False
        st.rerun()

    st.divider()

    # --- FITUR CUSTOMER (Tracking Saja) ---
    if role == "Customer":
        st.subheader("🔍 Lacak Paket")
        resi_cari = st.text_input("Masukkan No Resi:")
        if st.button("Cek Resi"):
            df_paket = load_data("PAKET")
            hasil = df_paket[df_paket['Resi'] == resi_cari]
            if not hasil.empty:
                data = hasil.iloc[0]
                st.info(f"Rute: {data['Pengirim']} ➝ {data['Tujuan']}")
                st.success(f"Status: {data['Status']} (📍 {data['Posisi']} - {data['Waktu']})")
            else:
                st.warning("Resi tidak ditemukan.")

    # --- FITUR ADMIN (Akses Penuh) ---
    elif role == "Admin":
        menu = st.radio("Pilih Menu:", ["📝 Input Resi", "📸 Update Transit", "📊 Laporan"])
        
        if menu == "📝 Input Resi":
            st.subheader("Input Paket Baru")
            with st.form("input_resi"):
                col1, col2 = st.columns(2)
                pengirim = col1.text_input("Nama Pengirim")
                penerima = col2.text_input("Nama Penerima")
                zona = st.selectbox("Zonasi Pengiriman", ["Satu Kota", "Satu Provinsi", "Sesama Jawa", "Lintas Pulau"])
                berat = st.number_input("Berat (Kg)", min_value=1)
                
                st.markdown("**Dimensi Paket (cm)**")
                cp, cl, ct = st.columns(3)
                p = cp.number_input("Panjang", 1)
                l = cl.number_input("Lebar", 1)
                t = ct.number_input("Tinggi", 1)
                
                kategori = st.selectbox("Kategori Barang", ["Barang Umum", "Pecah Belah", "Elektronik", "Makanan"])
                layanan = st.selectbox("Layanan", ["Reguler", "Sameday", "Instant", "Cargo"])
                is_cod = st.checkbox("Metode Bayar COD (+Rp 5.000)")
                
                asuransi_val = 0
                if kategori == "Elektronik":
                    st.info("Barang Elektronik Wajib Asuransi!")
                    asuransi_val = st.number_input("Masukkan Harga Barang (Rp)", min_value=0)
                else:
                    pakai_asuransi = st.checkbox("Tambah Asuransi (0.5%)")
                    if pakai_asuransi:
                        asuransi_val = st.number_input("Masukkan Harga Barang (Rp)", min_value=0)

                submit_paket = st.form_submit_button("Hitung & Simpan Resi")
                
                if submit_paket:
                    total_harga = hitung_ongkir(zona, berat, layanan, p, l, t, kategori, asuransi_val, is_cod)
                    resi_baru = f"LAJU-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    
                    # Simpan ke Sheets
                    df_paket = load_data("PAKET")
                    new_row = {"Resi": resi_baru, "Pengirim": pengirim, "Penerima": penerima, "Tujuan": zona, 
                               "Berat": berat, "Ongkir": total_harga, "Status": "MANIFESTED", 
                               "Posisi": st.session_state['cabang'], "Waktu": datetime.now().strftime('%Y-%m-%d %H:%M')}
                    
                    df_update = pd.concat([df_paket, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(df_update, "PAKET")
                    
                    st.success(f"Resi Berhasil Dibuat: {resi_baru}")
                    st.metric("Total Ongkir yang harus ditagih:", f"Rp {total_harga:,.0f}")

    # --- FITUR KURIR & ADMIN (Update Transit) ---
    if role in ["Admin", "Kurir"]:
        if role == "Kurir" or (role == "Admin" and menu == "📸 Update Transit"):
            st.subheader("Update Status Pengiriman")
            resi_scan = st.text_input("Scan / Ketik No Resi:")
            # Pakai text input biasa karena scanner barcode USB itu kerjanya kayak keyboard yang ngetik cepat lalu Enter.
            status_baru = st.selectbox("Update Status Menjadi:", ["ON TRANSIT", "DELIVERED"])
            
            if st.button("Update Paket"):
                df_paket = load_data("PAKET")
                idx = df_paket.index[df_paket['Resi'] == resi_scan].tolist()
                
                if idx:
                    if df_paket.at[idx[0], 'Status'] == "DELIVERED":
                        st.error("Paket ini sudah diterima sebelumnya!")
                    else:
                        df_paket.at[idx[0], 'Status'] = status_baru
                        df_paket.at[idx[0], 'Posisi'] = st.session_state['cabang']
                        df_paket.at[idx[0], 'Waktu'] = datetime.now().strftime('%Y-%m-%d %H:%M')
                        save_data(df_paket, "PAKET")
                        st.success(f"✅ Paket {resi_scan} berhasil diupdate di {st.session_state['cabang']}!")
                else:
                    st.warning("Resi tidak ditemukan.")

# ==========================================
# RENDER APLIKASI
# ==========================================
if not st.session_state['logged_in']:
    login_form()
else:
    main_dashboard()
