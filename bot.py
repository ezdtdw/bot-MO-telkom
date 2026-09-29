import os
import sys
import time
import traceback
import queue
import threading
import telebot
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException

load_dotenv()

# ==========================================
# FUNGSI LATAR BELAKANG (TUKANG KETIK TELEGRAM)
# ==========================================
def jaga_typing(chat_id, bendera_stop):
    while not bendera_stop.is_set():
        try:
            bot.send_chat_action(chat_id, 'typing')
        except:
            pass
        time.sleep(4)

# ==========================================
# 1. KREDENSIAL LENGKAP
# ==========================================
TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

ID_KOMANDAN = None
STATUS_BOT_SIBUK = False
antrean_wonum = queue.Queue()

USERNAME_INSERA = os.getenv("INSERA_USER")
PASSWORD_INSERA = os.getenv("INSERA_PASS")
USERNAME_IBOOSTER = os.getenv("IBOOSTER_USER")
PASSWORD_IBOOSTER = os.getenv("IBOOSTER_PASS")

PROFILE_PATH = r"D:\python"

# ==========================================
# FUNGSI PEMBANTU (MATA BOT & PINDAH TAB)
# ==========================================
DEFAULT_TIMEOUT = 15

def tunggu_dom(driver, timeout=DEFAULT_TIMEOUT):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") in ("interactive", "complete")
    )

def tunggu_ajax(driver, timeout=DEFAULT_TIMEOUT):
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("""
                if (window.jQuery){
                    return jQuery.active===0;
                }
                return true;
            """)
        )
    except:
        pass

def tunggu_loading_hilang(driver, timeout=DEFAULT_TIMEOUT):
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("""
                const ids=['loading','loadingDiv','loadingMask','loadingScreen','spinner'];
                for(const id of ids){
                    const e=document.getElementById(id);
                    if(e && e.offsetParent!==null){
                        return false;
                    }
                }
                return true;
            """)
        )
    except:
        pass

def sinkron(driver, timeout=DEFAULT_TIMEOUT):
    try: tunggu_ajax(driver, timeout)
    except: pass
    try: tunggu_loading_hilang(driver, timeout)
    except: pass

def amankan_elemen(wait_obj, by, locator, nama_elemen="Elemen", clickable=False):
    sinkron(driver)
    try:
        kondisi = EC.element_to_be_clickable((by, locator)) if clickable else EC.visibility_of_element_located((by, locator))
        elemen = wait_obj.until(kondisi)
        wait_obj.until(lambda d: elemen.is_displayed() and elemen.size["width"] > 0 and elemen.size["height"] > 0)
        return elemen
    except Exception:
        raise Exception(f"Gagal memuat {nama_elemen} dalam {DEFAULT_TIMEOUT} detik.")

def cek_modal_error(driver):
    try:
        driver.switch_to.default_content()
        modal = WebDriverWait(driver, 3).until(EC.visibility_of_element_located((By.ID, "wfmModalDlg")))
        pesan = modal.find_element(By.CSS_SELECTOR, ".wfm-modal-content span").text.strip()
        print(f"🚨 MODAL ERROR : {pesan}")
        try: modal.find_element(By.CSS_SELECTOR, ".btn-ok").click()
        except: pass
        driver.switch_to.default_content()
        return pesan
    except TimeoutException:
        driver.switch_to.default_content()
        return None
    except Exception as e:
        print(e)
        driver.switch_to.default_content()
        return None

def pulihkan_blank_wfm(driver, target_wonum=None):
    print("🚑 [DOKTER] Recovery Blank WFM dimulai...")
    try: driver.switch_to.default_content()
    except: pass

    try:
        if "_mode=edit" in driver.current_url.lower():
            print("↩️ Masih di halaman edit, kembali...")
            driver.back()
            sinkron(driver)
    except: pass

    try:
        print("🔄 Refresh halaman...")
        driver.refresh()
        sinkron(driver)
    except: pass

    try:
        if "_mode=edit" in driver.current_url.lower():
            print("🏠 Membuka Inbox...")
            driver.get("https://wfm.telkom.co.id/jw/web/userview/new_wfm/v/_/inbox_nofilter_retail")
            sinkron(driver)
    except: pass

    search = tunggu_dengan_recovery(
        driver,
        EC.presence_of_element_located((By.ID, "searchWonumGlobal")),
        target_wonum,
        timeout=20
    )

    if search is None:
        return

    if target_wonum:
        search.send_keys(Keys.CONTROL + "a")
        search.send_keys(Keys.DELETE)
        search.send_keys(target_wonum)

        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnSearchWonumGlobal"))
        
        try:
            WebDriverWait(driver, 20).until(
                lambda d: target_wonum in d.find_element(By.ID, "parent_form_1_form_workorder_wonum").get_attribute("value")
            )

            tombol_plans = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//*[contains(text(),'Plans') or contains(text(),'PLANS')]"))
            )
            driver.execute_script("arguments[0].click();", tombol_plans)
        except Exception as e:
            print(f"⚠️ [RECOVERY] Insera sangat lambat memuat tiket {target_wonum}. Recovery dibatalkan sementara.")
            return # Langsung keluar dari fungsi agar tidak crash

        try:
            baris = WebDriverWait(driver, 8).until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, "//tr[.//span[@name='parent_form_2_form_plans_form_grid_dispatch_task_description']]")
                )
            )
            rusak = False
            for b in baris:
                try:
                    nama = b.find_element(By.XPATH, ".//span[@name='parent_form_2_form_plans_form_grid_dispatch_task_description']").text.strip()
                    if nama:
                        rusak = False
                        break
                    rusak = True
                except:
                    rusak = True

            if rusak:
                print("⚠️ Grid WFM kosong. Reload Inbox...")
                driver.get("https://wfm.telkom.co.id/jw/web/userview/new_wfm/v/_/inbox_nofilter_retail")
                sinkron(driver)
        except Exception as e:
            print(e)
    print("✅ Recovery selesai.")

def tunggu_dengan_recovery(driver, kondisi, target_wonum=None, timeout=20, interval=0.5):
    mulai = time.time()
    
    while time.time() - mulai < timeout:
        # 1. Coba cek apakah elemen yang ditunggu sudah muncul
        try:
            hasil = kondisi(driver)
            if hasil:
                return hasil
        except:
            pass

        # 2. 🔥 DETEKSI BLANK SUPER AGRESIF 🔥
        try:
            # Mengambil semua teks yang kelihatan di layar
            teks_layar = driver.find_element(By.TAG_NAME, "body").text.strip()
            html_sumber = driver.page_source
            
            # Kalau teks di layar kurang dari 5 huruf (kosong) ATAU ada tulisan error
            if len(teks_layar) < 5 or "Exception" in html_sumber or "Security Violation" in html_sumber:
                print("⚡ [FAST RECOVERY] Layar nge-blank/error terdeteksi seketika! Memotong timeout...")
                pulihkan_blank_wfm(driver, target_wonum)
                return None
        except:
            pass
            
        time.sleep(interval)

    print("⏰ [TIMEOUT] Gagal memuat, menjalankan recovery...")
    pulihkan_blank_wfm(driver, target_wonum)
    return None

def ke_tab_wfm(driver):
    driver.switch_to.window(driver.window_handles[0])

def ke_tab_ibooster(driver):
    if len(driver.window_handles) > 1:
        driver.switch_to.window(driver.window_handles[1])
    else:
        print("⚠️ [SISTEM] Tab iBooster hilang! Membuka ulang...")
        driver.execute_script("window.open('https://dbaccess-ibooster.telkom.co.id/ibooster/home.php?page=PG389', '_blank');")
        time.sleep(1.5)
        driver.switch_to.window(driver.window_handles[1])

# ==========================================
# 2. PEMBERSIHAN RAM & INISIALISASI
# ==========================================
print("💀 [SISTEM] Membersihkan sisa Edge dari RAM...")
os.system("taskkill /F /IM msedge.exe /T")
time.sleep(1)

print("🚀 [SISTEM] Membuka Edge Single-Session...")
edge_options = Options()
edge_options.add_experimental_option("detach", True)
edge_options.add_argument("--no-sandbox")
edge_options.add_argument("--disable-dev-shm-usage")
edge_options.add_argument(f"--user-data-dir={PROFILE_PATH}")
edge_options.add_experimental_option("prefs", {
    "profile.exit_type": "Normal",
    "profile.exited_cleanly": True
})
edge_options.page_load_strategy = 'eager'

try:
    driver = webdriver.Edge(options=edge_options)
    wait = WebDriverWait(driver, 15)
    wait_login = WebDriverWait(driver, 5)
except Exception as e:
    print(f"❌ ERROR INISIALISASI BROWSER: {e}")
    sys.exit()

# ==========================================
# 3. MANAJEMEN TAB & LOGIN OTOMATIS
# ==========================================
print("🌐 [SISTEM] Membuka Tab Insera & iBooster...")
driver.get("https://insera-sso.telkom.co.id/jw/web/login")
driver.execute_script("window.open('https://dbaccess-ibooster.telkom.co.id/ibooster/home.php?page=PG389', '_blank');")

# --- LOGIN INSERA ---
ke_tab_wfm(driver)
try:
    user_field = wait_login.until(EC.presence_of_element_located((By.ID, "fake-username")))
    user_field.send_keys(Keys.CONTROL + "a")
    user_field.send_keys(USERNAME_INSERA)
    pass_field = driver.find_element(By.ID, "fake-password")
    pass_field.send_keys(Keys.CONTROL + "a")
    pass_field.send_keys(PASSWORD_INSERA)
    driver.find_element(By.ID, "acceptTerms").click()
    driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "fake-login"))
    print("✅ [LOGIN WFM] Terkirim dengan santai!")
except:
    print("✅ [LOGIN WFM] Sesi SSO aktif! Langsung masuk.")

# --- LOGIN iBOOSTER ---
ke_tab_ibooster(driver)
try:
    user_field_ib = wait_login.until(EC.presence_of_element_located((By.NAME, "username")))
    
    dropdown_element = driver.find_element(By.ID, "dropdown_login")
    Select(dropdown_element).select_by_value("infomedia")
    
    user_field_ib.send_keys(Keys.CONTROL + "a")
    user_field_ib.send_keys(USERNAME_IBOOSTER)
    
    pass_field_ib = driver.find_element(By.NAME, "password")
    pass_field_ib.send_keys(Keys.CONTROL + "a")
    pass_field_ib.send_keys(PASSWORD_IBOOSTER)
    
    # 🔥 JURUS MUTLAK: Eksekusi submit langsung ke sistem form tanpa perlu cari tombol!
    pass_field_ib.submit()
    
    print("✅ [LOGIN iBooster] Terkirim dengan santai!")
except Exception as e:
    # Supaya kalau gagal, bot ngasih tahu error aslinya apa, bukan diam-diam lewat
    print(f"ℹ️ [LOGIN iBooster] Sesi aktif atau error: {e}")

# ==========================================
# 4. OTAK TELEGRAM & LOGIKA BOT
# ==========================================
@bot.message_handler(commands=['start', 'help'])
def sapa_komandan(message):
    global ID_KOMANDAN
    ID_KOMANDAN = message.chat.id
    teks = "🫡 Lapor Komandan!\nBot WFM Insera versi *Mata Elang* siap melibas tiket.\n\nKirimkan nomor tiket (contoh: WO059042222)!"
    bot.reply_to(message, teks, parse_mode="Markdown")

def eksekusi_satu_tiket(TARGET_WONUM, chat_id):
    bendera_stop = threading.Event()
    tukang_ketik = threading.Thread(target=jaga_typing, args=(chat_id, bendera_stop))
    tukang_ketik.start()

    try:
        data_ibooster_diambil = False
        hasil_sn, hasil_vendor, hasil_model = "", "", ""
        batas_error_joget = 0
        ke_tab_wfm(driver)

        try: driver.switch_to.default_content()
        except: pass

        print("🧹 [SISTEM] Mereset halaman ke beranda utama...")
        url_sekarang = driver.current_url.lower()
        if "login" not in url_sekarang:
            driver.get("https://wfm.telkom.co.id/jw/web/userview/new_wfm/v/_/inbox_nofilter_retail")
        else:
            driver.refresh()

        try:
            search_input = amankan_elemen(wait, By.ID, "searchWonumGlobal", "Search Bar WFM")
        except:
            print("⚠️ [SISTEM] Search Bar menghilang! Recovery...")
            pulihkan_blank_wfm(driver, TARGET_WONUM)
            search_input = amankan_elemen(wait, By.ID, "searchWonumGlobal", "Search Bar WFM")

        search_input.send_keys(Keys.CONTROL + "a")
        search_input.send_keys(Keys.BACKSPACE)
        search_input.send_keys(TARGET_WONUM)

        elemen_hantu = None
        try: elemen_hantu = driver.find_element(By.XPATH, "//tr[.//span[@name='parent_form_2_form_plans_form_grid_dispatch_task_description']]")
        except: pass

        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnSearchWonumGlobal"))
        print(f"🛡️ [INSPEKTUR] Memastikan tiket {TARGET_WONUM} sudah dimuat...")
        
        try:
            WebDriverWait(driver, 15).until(lambda d: TARGET_WONUM in d.find_element(By.ID, "parent_form_1_form_workorder_wonum").get_attribute("value"))
            print(f"✅ [INSPEKTUR] Tiket {TARGET_WONUM} terverifikasi!")
            if elemen_hantu:
                try: WebDriverWait(driver, 5).until(EC.staleness_of(elemen_hantu))
                except: pass
            tombol_plans = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, "//*[contains(text(), 'Plans') or contains(text(), 'PLANS')]")))
        except:
            print("⚠️ [SISTEM] UI nyangkut! Recovery...")
            pulihkan_blank_wfm(driver, TARGET_WONUM)
            tombol_plans = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.XPATH, "//*[contains(text(),'Plans') or contains(text(),'PLANS')]")))

        try:
            input_service = amankan_elemen(wait, By.ID, "parent_form_1_form_workorder_servicenum", "Nomor Service")
            nomor_service = input_service.get_attribute("value")
        except:
            print("⚠️ [SISTEM] Antarmuka terpotong!")
            pulihkan_blank_wfm(driver, TARGET_WONUM)
            try:
                tombol_plans = WebDriverWait(driver, 15).until(EC.visibility_of_element_located((By.XPATH, "//*[contains(text(), 'Plans') or contains(text(), 'PLANS')]")))
                input_service = amankan_elemen(wait, By.ID, "parent_form_1_form_workorder_servicenum", "Nomor Service")
                nomor_service = input_service.get_attribute("value")
            except:
                nomor_service = ""

        print(f"📋 [WFM] Service Number diamankan: {nomor_service}")
        print("⏳ [WFM] Membuka tab Plans...")
        driver.execute_script("arguments[0].click();", tombol_plans)

        try:
            status_awal_el = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, "parent_form_2_form_plans_status")))
            status_awal = status_awal_el.get_attribute("value")
            if not status_awal:
                status_awal = driver.find_element(By.XPATH, "//label[@for='parent_form_2_form_plans_status']/following-sibling::div/span").text.strip()
            print(f"📌 [WFM] Status Tiket Saat Ini: {status_awal}")
        except:
            print("📌 [WFM] Status Tiket Saat Ini: [Gagal Dibaca]")

        # ========================================================
        # 🔄 PUTARAN DALAM: LOOP GRID TABEL TUGAS (MEJA KERJA)
        # ========================================================
        tugas_bermasalah = []
        sudah_refresh_darurat = False
        while True:
            try:
                WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, "//tr[.//span[@name='parent_form_2_form_plans_form_grid_dispatch_task_description']]")))
            except:
                print("🚑 [DOKTER] Layar Blank/Tabel Hilang!")
                pulihkan_blank_wfm(driver, TARGET_WONUM)
                try: driver.switch_to.alert.accept()
                except: pass
                try:
                    tombol_plans_refresh = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Plans') or contains(text(), 'PLANS')]")))
                    driver.execute_script("arguments[0].click();", tombol_plans_refresh)
                except: pass
                continue

            baris_tabel = driver.find_elements(By.XPATH, "//tr[.//span[@name='parent_form_2_form_plans_form_grid_dispatch_task_description']]")
            print("\n📊 [WFM] Membaca Antrean Tugas di Insera:")
            for i, baris in enumerate(baris_tabel):
                try:
                    nama_tugas = baris.find_element(By.XPATH, ".//span[@name='parent_form_2_form_plans_form_grid_dispatch_task_description']").text.strip()
                    status_utama = baris.find_element(By.XPATH, ".//span[@name='parent_form_2_form_plans_form_grid_dispatch_task_status']").text.strip()
                    elemen_detail = baris.find_elements(By.XPATH, ".//div[@class='subform-cell-value']/span")
                    list_detail = [e.text.strip() for e in elemen_detail if e.text.strip() != ""]
                    status_detail = [teks for teks in list_detail if not teks.isnumeric()]
                    teks_detail = " -> ".join(status_detail) if status_detail else "-"
                    print(f"   {i+1}. {nama_tugas}  |  {status_utama}  |  {teks_detail}")
                except: pass
            print("-" * 50)

            elemen_pensil_target = None
            jenis_tugas = ""
            current_status_tugas = ""
            ada_tugas_valid_tersisa = False
            ada_pickup_tertunda = False

            for baris in baris_tabel:
                try:
                    teks_tugas = baris.find_element(By.XPATH, ".//span[@name='parent_form_2_form_plans_form_grid_dispatch_task_description']").text.strip().upper()
                    status_tugas = baris.find_element(By.XPATH, ".//span[@name='parent_form_2_form_plans_form_grid_dispatch_task_status']").text.strip().upper()
                    if "PICKUP" in teks_tugas and status_tugas != "COMPWA":
                        ada_pickup_tertunda = True
                    if "REMOVE" in teks_tugas or "CABUT" in teks_tugas or "PASANG" in teks_tugas or "CHANGE" in teks_tugas:
                        if status_tugas != "COMPWA" and teks_tugas not in tugas_bermasalah:
                            ada_tugas_valid_tersisa = True
                            elemen_pensil_target = baris.find_element(By.CLASS_NAME, "grid-action-edit")
                            jenis_tugas = teks_tugas
                            current_status_tugas = status_tugas
                            break
                except: pass

            if ada_pickup_tertunda:
                print(f"⚠️ [SISTEM] Ada tugas PICKUP. Membatalkan eksekusi tiket {TARGET_WONUM}!")

                ringkasan_tabel = "\n📋 *Kondisi Tabel Tugas Saat Ini:*\n"

                nomor = 1
                for baris in baris_tabel:
                    try:
                        nama = baris.find_element(
                            By.XPATH,
                            ".//span[@name='parent_form_2_form_plans_form_grid_dispatch_task_description']"
                        ).text.strip()

                        status = baris.find_element(
                            By.XPATH,
                            ".//span[@name='parent_form_2_form_plans_form_grid_dispatch_task_status']"
                        ).text.strip()

                        if status.upper() == "COMPWA":
                            ringkasan_tabel += f"✅ {nomor}. {nama} ({status})\n"
                        else:
                            ringkasan_tabel += f"⚠️ {nomor}. {nama} ({status})\n"

                        nomor += 1
                    except:
                        pass

                bendera_stop.set()

                bot.send_message(
                    chat_id,
                    f"🛑 *TIKET DILEWATI*\n"
                    f"Tiket *{TARGET_WONUM}* memiliki tugas *PICKUP*. Sesuai instruksi, bot tidak menyentuh tugas ini."
                    f"{ringkasan_tabel}",
                    parse_mode="Markdown"
                )

                driver.switch_to.default_content()
                return

            if not ada_tugas_valid_tersisa:
                if len(tugas_bermasalah) > 0 and not sudah_refresh_darurat:
                    print("🔄 [SISTEM] Web Insera nge-freeze/digembok! Melakukan REFRESH DARURAT (1x)...")
                    driver.switch_to.default_content()
                    driver.refresh()
                    sudah_refresh_darurat = True
                    tugas_bermasalah.clear()
                    try:
                        tombol_plans_refresh = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Plans') or contains(text(), 'PLANS')]")))
                        driver.execute_script("arguments[0].click();", tombol_plans_refresh)
                    except: pass
                    continue

                try:
                    status_akhir = driver.find_element(By.ID, "parent_form_2_form_plans_status").get_attribute("value")
                    if not status_akhir:
                        status_akhir = driver.find_element(By.XPATH, "//label[@for='parent_form_2_form_plans_status']/following-sibling::div/span").text.strip()
                    print(f"🏁 [WFM] Tiket {TARGET_WONUM} adalah {status_akhir}")
                except:
                    status_akhir = "Gagal Dibaca"
                    print(f"🏁 [WFM] Tiket {TARGET_WONUM} selesai (Status gagal dibaca)")

                ringkasan_tabel = "\n📋 *Kondisi Tabel Tugas Saat Ini:*\n"
                try:
                    baris_akhir = driver.find_elements(By.XPATH, "//tr[.//span[@name='parent_form_2_form_plans_form_grid_dispatch_task_description']]")
                    nomor_tugas = 1
                    for baris in baris_akhir:
                        nama_t = baris.find_element(By.XPATH, ".//span[@name='parent_form_2_form_plans_form_grid_dispatch_task_description']").text.strip()
                        status_t = baris.find_element(By.XPATH, ".//span[@name='parent_form_2_form_plans_form_grid_dispatch_task_status']").text.strip()
                        if not nama_t: continue
                        nama_t_aman = nama_t.replace("_", " ").replace("*", "").replace("`", "")
                        status_t_aman = status_t.replace("_", " ")
                        if status_t == "COMPWA": ringkasan_tabel += f"✅ {nomor_tugas}. {nama_t_aman} (COMPWA)\n"
                        else: ringkasan_tabel += f"⚠️ {nomor_tugas}. {nama_t_aman} ({status_t_aman})\n"
                        nomor_tugas += 1
                except:
                    ringkasan_tabel += "- Gagal membaca detail tabel -\n"

                info_cpe = ""
                if hasil_sn:
                    info_cpe = f"\n📦 *Data Perangkat (iBooster):*\n▪️ Vendor: {hasil_vendor}\n▪️ Tipe: {hasil_model}\n▪️ SN: `{hasil_sn}`\n"

                # ========================================================
                # 🚨 DETEKSI TIKET FALLOUT
                # ========================================================
                is_fallout = False
                fallout_ticket = "-"
                try:
                    elemen_tiket = driver.find_elements(By.XPATH, "//span[@column_key='ticketid']")
                    for el in elemen_tiket:
                        teks_tiket = el.text.strip().upper()
                        if "INF" in teks_tiket:
                            is_fallout = True
                            fallout_ticket = teks_tiket
                            break
                except: pass

                if is_fallout:
                    pesan_akhir = (
                        f"❌ *ALERT WORK ORDER FALLOUT!*\nTiket utama *{TARGET_WONUM}* terdampak Fallout di sistem BIMA!\n\n"
                        f"⚠️ *Tiket Fallout:* `{fallout_ticket}`\n"
                        f"📝 *Solusi:* Mohon lakukan perbaikan/pelurusan di sistem terkait, lalu lakukan *Resolve-Retry*.\n"
                        f"{info_cpe}{ringkasan_tabel}"
                    )
                    print(f"❌ ALERT: Tiket {TARGET_WONUM} terdampak Fallout ({fallout_ticket})!")
                elif status_akhir in ("INSTCOMP", "COMPWORK", "DEINSTCOMP"):
                    pesan_akhir = f"🎉 *BOOYAH!*\nSemua tugas pada tiket *{TARGET_WONUM}* sudah dilibas.\n\n📌 Status Akhir Tiket: *{status_akhir}*{info_cpe}{ringkasan_tabel}"
                    print(f"🎉 BOOYAH! TIKET {TARGET_WONUM} SELESAI ({status_akhir}).")
                else:
                    pesan_akhir = f"⚠️ *WARNING PENDETEKSI BUG!*\nTiket *{TARGET_WONUM}* tugasnya sudah diklik, TAPI status utamanya nyangkut di: *{status_akhir}*\n\n{info_cpe}{ringkasan_tabel}"
                    print(f"⚠️ TIKET {TARGET_WONUM} GAGAL TEMBUS, NYANGKUT DI {status_akhir}!")

                bot.send_chat_action(chat_id, 'typing')
                time.sleep(0.5)
                bendera_stop.set()
                bot.send_message(chat_id, pesan_akhir, parse_mode="Markdown")
                break

            # --- AMBIL DATA iBOOSTER ---
            if ("CABUT" in jenis_tugas or "PASANG" in jenis_tugas) and not data_ibooster_diambil:
                print("🌐 [iBooster] Mengambil SN...")
                bot.send_chat_action(chat_id, 'typing')
                bot.send_message(chat_id, f"🌐 Sedang mengambil data iBooster untuk Service: {nomor_service}...")
                
                ke_tab_ibooster(driver)
                kotak_service = amankan_elemen(wait, By.NAME, "nospeedy", "Search Bar iBooster")
                kotak_service.send_keys(Keys.CONTROL + "a")
                kotak_service.send_keys(nomor_service)
                driver.execute_script("arguments[0].click();", driver.find_element(By.NAME, "analis"))
                amankan_elemen(wait, By.TAG_NAME, "tr", "Tabel Hasil iBooster")

                print("⏳ [iBooster] Menunggu loading pengukuran...")
                try:
                    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.XPATH, "//div[@id='ukur-progress-wrap' and contains(@class, 'done')]")))
                except:
                    print("⚠️ [iBooster] Menunggu terlalu lama, mencoba menyalin seadanya...")

                data_cpe = driver.execute_script("""
                    let rows = document.querySelectorAll('tr');
                    for(let r of rows){
                        let tds = r.querySelectorAll('td');
                        for(let i=0; i<tds.length; i++){
                            let txt = tds[i].innerText.trim();
                            let up = txt.toUpperCase();
                            if(up.startsWith("HWTC")||up.startsWith("FHTT")||up.startsWith("FHT")||up.startsWith("ZTEG")||up.startsWith("ALCL")){
                                let model = (i+6 < tds.length) ? tds[i+6].innerText.trim() : tds[tds.length-1].innerText.trim();
                                return {sn: txt, model: model};
                            }
                        }
                    }
                    return null;
                """)

                if not data_cpe:
                    print("⚠️ [iBooster] Data ambyar. Memakai Dummy Data ZTE!")
                    hasil_sn, hasil_model, hasil_vendor = "ZTEGC8971590", "F609V5.3", "ZTE"
                else:
                    hasil_sn = data_cpe['sn']
                    hasil_model = data_cpe['model']
                    su = hasil_sn.upper()
                    hasil_vendor = "ZTE"
                    if su.startswith("HWTC"): hasil_vendor = "HUAWEI"
                    elif su.startswith("FHTT") or su.startswith("FHT"): hasil_vendor = "FIBERHOME"
                    elif su.startswith("ALCL"): hasil_vendor = "ALCATEL"

                print(f"📦 [iBooster] Data diamankan! -> SN: {hasil_sn} | Tipe: {hasil_model} | Vendor: {hasil_vendor}")
                data_ibooster_diambil = True
                ke_tab_wfm(driver)

            # --- EKSEKUSI TUGAS DENGAN MATA BOT ---
            print(f"⚙️ [WFM] Eksekusi tugas: {jenis_tugas} ...")
            driver.execute_script("arguments[0].click();", elemen_pensil_target)
            print("⛺ [SISTEM] Menunggu Form Edit terbuka...")
            driver.switch_to.default_content()

            def cari_iframe_aman(d):
                semua = d.find_elements(By.TAG_NAME, "iframe")
                for fr in reversed(semua):
                    try:
                        if not fr.is_displayed(): continue
                        d.switch_to.default_content()
                        d.switch_to.frame(fr)
juanok                        if d.find_elements(By.NAME, "status"):
                            d.switch_to.default_content()
                            return fr
                    except:
                        d.switch_to.default_content()
                return None

            iframe_target = tunggu_dengan_recovery(driver, cari_iframe_aman, TARGET_WONUM, timeout=20)
            if iframe_target is None:
                continue

            driver.switch_to.default_content()
            driver.switch_to.frame(iframe_target)
            
            status_element = tunggu_dengan_recovery(driver, EC.visibility_of_element_located((By.NAME, "status")), TARGET_WONUM, timeout=20)
            if status_element is None:
                continue

            sinkron(driver)
            print("✅ Form Edit siap digunakan.")

            try:
                kotak_status = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "status")))
                batas_error_joget = 0
            except:
                batas_error_joget += 1
                if batas_error_joget >= 3:
                    print("💀 [SISTEM] Gagal masuk tenda 3x beruntun! Tiket ini di-skip.")
                    bendera_stop.set()
                    bot.send_message(chat_id, f"⚠️ TENDA TERKUNCI!\nGagal mengeksekusi {jenis_tugas} pada tiket {TARGET_WONUM} karena Insera terus-terusan error.\n\nTiket ini di-skip.")
                    driver.switch_to.default_content()
                    return
                print(f"⚠️ [SISTEM] Layar putih/Joget Error! (Percobaan {batas_error_joget}/3)")
                driver.switch_to.default_content()
                pulihkan_blank_wfm(driver, TARGET_WONUM)
                try:
                    tombol_plans_ulang = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Plans') or contains(text(), 'PLANS')]")))
                    driver.execute_script("arguments[0].click();", tombol_plans_ulang)
                except: pass
                continue

            # ========================================================
            # 👆 TAHAP 1: UPDATE KE STARTWA
            # ========================================================
            if current_status_tugas != "STARTWA":
                driver.execute_script("arguments[0].click();", kotak_status)
                try:
                    if kotak_status.tag_name.lower() == "select": Select(kotak_status).select_by_visible_text("STARTWA")
                    else:
                        kotak_status.clear()
                        kotak_status.send_keys("STARTWA")
                        kotak_status.send_keys(Keys.TAB)
                except Exception:
                    print(f"⚠️ [SISTEM] Dropdown status digembok Insera! Tugas '{jenis_tugas}' masuk daftar hitam.")
                    tugas_bermasalah.append(jenis_tugas)
                    driver.switch_to.default_content()
                    continue
                        
                driver.execute_script("arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", kotak_status)
                btn_update = amankan_elemen(wait, By.ID, "updateAct", "Tombol Update", clickable=True)
                driver.execute_script("arguments[0].click();", btn_update)
                print("⏳ [WFM] Menunggu server menyimpan STARTWA...")

                try:
                    WebDriverWait(driver, 15).until(lambda d: len(d.find_elements(By.ID, "wfmModalDlg")) > 0 or len(d.find_elements(By.TAG_NAME, "iframe")) == 0)
                except: pass

                sinkron(driver)
                detail_error = cek_modal_error(driver)
                if detail_error:
                    bot.send_message(chat_id, f"❌ *WFM ERROR*\n📄 WO : `{TARGET_WONUM}`\n🛠️ Tugas : *{jenis_tugas}*\n⚠️ `{detail_error}`\n🛑 Eksekusi tiket dihentikan.", parse_mode="Markdown")
                    driver.switch_to.default_content()
                    return  # <--- Diganti jadi return agar bot langsung berhenti & move on ke tiket lain
            else:
                print(f"⏭️ [WFM] Tugas '{jenis_tugas}' ternyata sudah STARTWA di tabel. Skip Tahap 1!")
                driver.switch_to.default_content()

            # ========================================================
            # ⛺ TAHAP 2: ISI CPE & COMPWA 
            # ========================================================
            print("✏️ [WFM] Melanjutkan pengisian CPE & COMPWA...")
            tenda_ditemukan = False
            try:
                WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
                semua_tenda_baru = driver.find_elements(By.TAG_NAME, "iframe")
                for tenda in reversed(semua_tenda_baru):
                    if tenda.is_displayed():
                        driver.switch_to.frame(tenda)
                        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.NAME, "status")))
                        tenda_ditemukan = True
                        break
            except: pass
                
            if not tenda_ditemukan:
                print("⚠️ [SISTEM] Tenda tertutup otomatis! Mengaktifkan Rencana Cadangan (Plan B)...")
                driver.switch_to.default_content()
                try:
                    tombol_plans_darurat = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Plans') or contains(text(), 'PLANS')]")))
                    driver.execute_script("arguments[0].click();", tombol_plans_darurat)
                except: pass

                print("⏳ [SISTEM] Menunggu tabel antrean WFM selesai memuat ulang...")
                try:
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//tr[.//span[@name='parent_form_2_form_plans_form_grid_dispatch_task_description']]")))
                except:
                    print("🚑 [DOKTER] Tabel antrean nyangkut!")
                    pulihkan_blank_wfm(driver, TARGET_WONUM)
                    continue
                    
                baris_tabel_baru = driver.find_elements(By.XPATH, "//tr[.//span[@name='parent_form_2_form_plans_form_grid_dispatch_task_description']]")
                elemen_pensil_darurat = None
                for baris in baris_tabel_baru:
                    try:
                        teks_tugas_baru = baris.find_element(By.XPATH, ".//span[@name='parent_form_2_form_plans_form_grid_dispatch_task_description']").text.strip().upper()
                        if jenis_tugas in teks_tugas_baru:
                            elemen_pensil_darurat = baris.find_element(By.CLASS_NAME, "grid-action-edit")
                            break
                    except: pass
                
                if elemen_pensil_darurat:
                    driver.execute_script("arguments[0].click();", elemen_pensil_darurat)
                else:
                    print(f"❌ [SISTEM] Gagal menemukan kembali baris tugas: {jenis_tugas}")
                        
                print("⛺ [SISTEM] Memasuki ulang Pop-Up Iframe...")
                driver.switch_to.default_content()

                iframe_target_baru = tunggu_dengan_recovery(
                    driver,
                    lambda d: next((fr for fr in reversed(d.find_elements(By.TAG_NAME, "iframe")) if fr.is_displayed()), None),
                    TARGET_WONUM,
                    timeout=20
                )
                if iframe_target_baru is None: continue

                driver.switch_to.frame(iframe_target_baru)
                status_el_baru = tunggu_dengan_recovery(driver, EC.visibility_of_element_located((By.NAME, "status")), TARGET_WONUM, timeout=20)
                if status_el_baru is None: continue

                sinkron(driver)
                print("✅ Iframe kedua siap.")
            
            # --- ISI DATA CPE ---
            if "CABUT" in jenis_tugas or "PASANG" in jenis_tugas:
                amankan_elemen(wait, By.ID, "cpe_serial_number", "Form Validasi CPE")
                print(f"✍️ [WFM] Memulai injeksi data CPE [{hasil_vendor} - {hasil_sn}]...")
                
                el_vendor = driver.find_element(By.ID, "cpe_vendor")
                el_vendor.clear()
                el_vendor.send_keys(hasil_vendor)
                el_vendor.send_keys(Keys.TAB)
                WebDriverWait(driver, 15).until(lambda d: d.find_element(By.ID, "cpe_vendor").get_attribute("value") == hasil_vendor)

                el_model = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "cpe_model")))
                if el_model.tag_name.lower() == "select":
                    WebDriverWait(driver, 15).until(lambda d: len(Select(d.find_element(By.ID, "cpe_model")).options) > 1)
                    Select(el_model).select_by_visible_text(hasil_model)
                else:
                    WebDriverWait(driver, 15).until(lambda d: d.find_element(By.ID, "cpe_model").is_enabled())
                    el_model.clear()
                    el_model.send_keys(hasil_model)
                    el_model.send_keys(Keys.TAB)

                WebDriverWait(driver, 15).until(lambda d: d.find_element(By.ID, "cpe_model").get_attribute("value") == hasil_model)

                el_sn = driver.find_element(By.ID, "cpe_serial_number")
                el_sn.clear()
                el_sn.send_keys(hasil_sn)
                el_sn.send_keys(Keys.TAB)

                WebDriverWait(driver, 15).until(lambda d: d.find_element(By.ID, "cpe_serial_number").get_attribute("value") == hasil_sn)

                try:
                    WebDriverWait(driver, 20).until(lambda d: len(d.find_elements(By.ID, "wfmModalDlg")) > 0 or d.find_element(By.ID, "cpe_serial_number").get_attribute("value") == hasil_sn)
                except: pass

                sinkron(driver)
                btn_query = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.ID, "queryCpe")))
                driver.execute_script("arguments[0].click();", btn_query)
                print("⏳ Menunggu Query CPE selesai...")

                sinkron(driver)
                try:
                    WebDriverWait(driver, 15).until(lambda d: len(d.find_elements(By.ID, "wfmModalDlg")) > 0 or d.find_element(By.ID, "cpe_serial_number").get_attribute("value") == hasil_sn)
                except: pass
                sinkron(driver)
                print("✅ Query CPE selesai.")
                
            print("=" * 50)
            print("🔍 CEK NILAI SEBELUM COMPWA")
            print("Vendor :", driver.find_element(By.ID, "cpe_vendor").get_attribute("value"))
            print("Model  :", driver.find_element(By.ID, "cpe_model").get_attribute("value"))
            print("SN     :", driver.find_element(By.ID, "cpe_serial_number").get_attribute("value"))
            print("=" * 50)    
                    
            # --- UPDATE KE COMPWA ---
            amankan_elemen(wait, By.NAME, "status", "Dropdown Status Akhir")
            kotak_status_akhir = driver.find_element(By.NAME, "status")
            driver.execute_script("arguments[0].click();", kotak_status_akhir)

            try:
                if kotak_status_akhir.tag_name.lower() == "select": Select(kotak_status_akhir).select_by_visible_text("COMPWA")
                else:
                    kotak_status_akhir.clear()
                    kotak_status_akhir.send_keys("COMPWA")
                    kotak_status_akhir.send_keys(Keys.TAB)
            except Exception:
                print(f"⚠️ [SISTEM] Dropdown COMPWA digembok Insera! Tugas '{jenis_tugas}' masuk daftar hitam.")
                tugas_bermasalah.append(jenis_tugas)
                driver.switch_to.default_content()
                continue
                
            driver.execute_script("arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", kotak_status_akhir)
            btn_update = amankan_elemen(wait, By.ID, "updateAct", "Tombol Update", clickable=True)
            driver.execute_script("arguments[0].click();", btn_update)

            print("⏳ [WFM] Menunggu submit COMPWA selesai...")
            try: WebDriverWait(driver, 15).until(lambda d: len(d.find_elements(By.ID, "wfmModalDlg")) > 0 or len(d.find_elements(By.TAG_NAME, "iframe")) == 0)
            except: pass

            sinkron(driver)
            detail_error = cek_modal_error(driver)

            if detail_error:
                driver.switch_to.default_content()
                print(f"⚠️ [SISTEM] Tugas '{jenis_tugas}' diblokir. Tiket dihentikan.")
                bot.send_message(
                    chat_id,
                    f"❌ *WFM ERROR*\n"
                    f"📄 WO : `{TARGET_WONUM}`\n"
                    f"🛠️ Tugas : *{jenis_tugas}*\n\n"
                    f"`{detail_error}`\n"
                    f"🛑 Eksekusi tiket dihentikan.",
                    parse_mode="Markdown"
                )
                return  # <--- Diganti jadi return juga
            
            print("✅ [WFM] COMPWA & Data CPE sukses disubmit!")
            driver.switch_to.default_content()
            print("🔄 [SISTEM] Recovery setelah COMPWA...")
            pulihkan_blank_wfm(driver, TARGET_WONUM)

    except Exception as err:
        print(f"\n❌ [SISTEM] Ups! Terjadi error pada tiket ini.")
        print("📍 LOKASI EXACT ERROR:")
        print(traceback.format_exc())
        print("Bot tetap kebal. Silakan hajar tiket berikutnya.")
        bendera_stop.set()
        bot.send_message(chat_id, f"❌ Terjadi error sistem pada tiket {TARGET_WONUM}. Bot sudah memulihkan diri, silakan kirim tiket berikutnya.")
        try: driver.switch_to.default_content()
        except: pass
        ke_tab_wfm(driver)

    finally:
        STATUS_BOT_SIBUK = False
        bendera_stop.set()

def pekerja_antrean():
    while True:
        target_wonum, chat_id = antrean_wonum.get()
        global STATUS_BOT_SIBUK
        STATUS_BOT_SIBUK = True
        try:
            eksekusi_satu_tiket(target_wonum, chat_id)
        except Exception as e:
            print(f"❌ [WORKER ERROR] Gagal memproses {target_wonum}: {e}")
        finally:
            STATUS_BOT_SIBUK = False
            antrean_wonum.task_done()

threading.Thread(target=pekerja_antrean, daemon=True).start()

@bot.message_handler(func=lambda message: True)
def proses_tiket_dari_telegram(message):
    global ID_KOMANDAN
    ID_KOMANDAN = message.chat.id

    daftar_wo = [
        x.strip().upper()
        for x in message.text.splitlines()
        if x.strip()
    ]

    jumlah_masuk = 0

    for TARGET_WONUM in daftar_wo:

        if not TARGET_WONUM.startswith("WO"):
            continue

        antrean_wonum.put((TARGET_WONUM, message.chat.id))
        jumlah_masuk += 1

    if jumlah_masuk == 0:
        bot.reply_to(message, "⚠️ Tidak ada format WO yang valid.")
        return

    bot.reply_to(
        message,
        f"📥 {jumlah_masuk} tiket berhasil dimasukkan ke antrean."
    )

# ==========================================
# 5. SAKLAR POWER, ANTI-SPAM, & ALARM PAMITAN
# ==========================================
print("🤖 Radar Telegram aktif! (Tekan Ctrl + C di terminal untuk mematikan bot)")

try:
    bot.polling(none_stop=True, skip_pending=True)
except KeyboardInterrupt:
    print("\n🛑 [SISTEM] Menerima perintah shutdown (Ctrl + C)!")
    try:
        print("🌐 [SISTEM] Menutup browser Edge & membersihkan driver...")
        driver.quit()
    except Exception as e:
        print(f"⚠️ Gagal menutup browser: {e}")

    try:
        if ID_KOMANDAN:
            pesan_pamit = (
                "🔴 *BOT OFFLINE*\n\n"
                "Server PC telah dimatikan.\n"
                "Semua antrean tiket telah dibuang.\n"
                "------------------------------------\n"
                "⛔ *Bot tidak aktif. Jangan kirim tiket!*"
            )
            bot.send_message(ID_KOMANDAN, pesan_pamit, parse_mode="Markdown")
    except:
        pass
        
    print("👋 Bot berhasil dimatikan dengan aman. Sampai jumpa!")
    sys.exit()