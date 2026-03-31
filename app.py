import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="Laju Express", page_icon="📦", layout="centered")

# === PASTE URL WEB APP DARI GOOGLE APPS SCRIPT DI SINI ===
API_URL = "https://script.google.com/macros/s/AKfycbzhKIB9Q-uz7lskLktJFNRNgCjzlUbghZtVaB2b4O_NXbUz89TDSGRIV2NvySmze6eSKQ/exec"

# === SESSION STATE ===
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'role': '', 'username': '', 'cabang': ''})

def fetch_paket():
    try:
        res = requests.post(API_URL, json={"action": "get_paket"}).json()
        if res['success']:
            data = res['data']
            if len(data) > 1:
                return pd.DataFrame(data[1:], columns=data[0])
    except: pass
    return pd.DataFrame()

def login_form():
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>Laju Express Portal</h1>", unsafe_allow_html=True)
    with st.form("login_form"):
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        if st.form_submit_button("Log In", use_container_width=True):
            with st.spinner("Mencocokkan data..."):
                try:
                    res = requests.post(API_URL, json={"action": "login", "username": user, "password": pwd}).json()
                    if res['success']:
                        st.session_state.update({'logged_in': True, **res['data']})
                        st.rerun()
                    else:
                        st.error(res['message'])
                except:
                    st.error("Gagal konek API. Pastikan URL Web App di app.py sudah benar!")

def dashboard():
    role = st.session_state['role']
    st.success(f"👋 Halo, {st.session_state['username']}! (Akses: {role} | Lokasi: {st.session_state['cabang']})")
    if st.button("Logout", type="primary"):
        st.session_state['logged_in'] = False
        st.rerun()
    st.divider()

    if role == "Customer":
        st.subheader("🔍 Lacak Paket Anda")
        resi = st.text_input("Masukkan No Resi:")
        if st.button("Cek Resi", use_container_width=True):
            df = fetch_paket()
            if not df.empty and resi in df['Resi'].values:
                data = df[df['Resi'] == resi].iloc[0]
                st.info(f"🛣️ Rute: {data['Pengirim']} ➝ {data['Tujuan']}")
                st.success(f"📦 Status Terkini: **{data['Status']}** (📍 {data['Posisi']} - {data['Waktu']})")
            else:
                st.warning("Maaf, Resi tidak ditemukan.")

    elif role == "Admin":
        menu = st.radio("Pilih Menu:", ["📝 Input Resi", "📸 Update Transit", "📊 Data & Laporan"], horizontal=True)

        if menu == "📝 Input Resi":
            with st.form("input_resi"):
                c1, c2 = st.columns(2)
                pengirim = c1.text_input("Nama Pengirim")
                penerima = c2.text_input("Nama Penerima")
                zona = st.selectbox("Zonasi", ["Satu Kota", "Satu Provinsi", "Sesama Jawa", "Lintas Pulau"])
                berat = st.number_input("Berat Aktual (Kg)", min_value=1)
                layanan = st.selectbox("Layanan", ["Reguler", "Sameday", "Instant", "Cargo"])
                
                if st.form_submit_button("Hitung & Buat Resi", type="primary"):
                    base = {"Satu Kota": 8000, "Satu Provinsi": 12000, "Sesama Jawa": 20000, "Lintas Pulau": 45000}.get(zona, 8000)
                    ongkir = base * berat
                    if layanan == "Sameday": ongkir *= 1.5
                    elif layanan == "Instant": ongkir *= 2
                    elif layanan == "Cargo": ongkir = (base * max(berat, 10)) * 0.65
                    
                    resi_baru = f"LAJU-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    waktu = datetime.now().strftime('%Y-%m-%d %H:%M')
                    
                    payload = {"action": "add_paket", "resi": resi_baru, "pengirim": pengirim, "penerima": penerima, "tujuan": zona, "berat": berat, "ongkir": ongkir, "status": "MANIFESTED", "posisi": st.session_state['cabang'], "waktu": waktu}
                    
                    with st.spinner("Menyimpan ke Database..."):
                        res = requests.post(API_URL, json=payload).json()
                        if res['success']:
                            st.success(f"✅ Resi Berhasil Dibuat: **{resi_baru}**")
                            st.metric("Total Ongkir:", f"Rp {ongkir:,.0f}")
                        else:
                            st.error("Gagal menyimpan data!")

        elif menu == "📊 Data & Laporan":
            df = fetch_paket()
            if not df.empty:
                df['Ongkir'] = pd.to_numeric(df['Ongkir'], errors='coerce').fillna(0)
                aktif = df[df['Status'] != 'DELIVERED']
                selesai = df[df['Status'] == 'DELIVERED']
                
                c1, c2, c3 = st.columns(3)
                c1.metric("📦 Paket Aktif", len(aktif))
                c2.metric("✅ Paket Selesai", len(selesai))
                c3.metric("💰 Total Omzet", f"Rp {df['Ongkir'].sum():,.0f}")
                st.dataframe(aktif[['Resi', 'Pengirim', 'Tujuan', 'Status', 'Posisi']], use_container_width=True)
            else:
                st.warning("Belum ada data paket.")

    if role in ["Admin", "Kurir"]:
        if role == "Kurir" or (role == "Admin" and menu == "📸 Update Transit"):
            st.subheader("Update Status Pengiriman")
            resi_scan = st.text_input("Scan / Ketik No Resi:")
            status_baru = st.selectbox("Update Status:", ["ON TRANSIT", "DELIVERED"])
            
            if st.button("Update Posisi Paket", use_container_width=True):
                waktu = datetime.now().strftime('%Y-%m-%d %H:%M')
                payload = {"action": "update_paket", "resi": resi_scan, "status": status_baru, "posisi": st.session_state['cabang'], "waktu": waktu}
                
                with st.spinner("Mengupdate sistem..."):
                    res = requests.post(API_URL, json=payload).json()
                    if res['success']:
                        st.success(f"✅ Status {resi_scan} berhasil diubah jadi {status_baru} di {st.session_state['cabang']}!")
                    else:
                        st.error(res['message'])

if not st.session_state['logged_in']:
    login_form()
else:
    dashboard()
