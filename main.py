import customtkinter as ctk
from PIL import Image
import requests
import json
import os
import threading
import re
import psutil
from io import BytesIO
from tkinter import messagebox
import shutil

ctk.set_appearance_mode("Dark")

# Максимально полный словарь ID оружия
WEAPON_MAP = {
    # Пистолеты
    "weapon_deagle": "1", "weapon_elite": "2", "weapon_fiveseven": "3", "weapon_glock": "4",
    "weapon_hkp2000": "32", "weapon_p250": "36", "weapon_usp_silencer": "61", "weapon_cz75a": "63", 
    "weapon_revolver": "64", "weapon_tec9": "30",
    # Тяжелое
    "weapon_mag7": "27", "weapon_nova": "35", "weapon_sawedoff": "29", "weapon_xm1014": "25",
    "weapon_m249": "14", "weapon_negev": "28",
    # ПП
    "weapon_mac10": "17", "weapon_p90": "19", "weapon_mp5sd": "23", "weapon_ump45": "24",
    "weapon_bizon": "26", "weapon_mp7": "33", "weapon_mp9": "34",
    # Винтовки
    "weapon_ak47": "7", "weapon_aug": "8", "weapon_awp": "9", "weapon_famas": "10",
    "weapon_g3sg1": "11", "weapon_galilar": "13", "weapon_m4a1": "16", "weapon_m4a1_silencer": "60",
    "weapon_scar20": "38", "weapon_sg556": "39", "weapon_ssg08": "40",
    # Ножи
    "weapon_knife_bayonet": "500", "weapon_knife_flip": "505", "weapon_knife_gut": "506",
    "weapon_knife_karambit": "507", "weapon_knife_m9_bayonet": "508", "weapon_knife_tactical": "509",
    "weapon_knife_falchion": "512", "weapon_knife_survival_bowie": "514", "weapon_knife_butterfly": "515",
    "weapon_knife_push": "516", "weapon_knife_cord": "517", "weapon_knife_canis": "518",
    "weapon_knife_ursus": "519", "weapon_knife_gypsy_jackknife": "520", "weapon_knife_outdoor": "521",
    "weapon_knife_stiletto": "522", "weapon_knife_widowmaker": "523", "weapon_knife_skeleton": "525",
    "weapon_knife_kukri": "526",
    # Разное
    "weapon_taser": "31"
}

class XChenger(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("XChenger v4.0 Ultimate")
        self.geometry("1400x900")
        self.configure(fg_color="#0a0a0a")

        self.config_path = r"C:\Program Files (x86)\Steam\steamapps\common\csgo legacy\csgo_gc\inventory.txt"
        self.api_url = "https://raw.githubusercontent.com/ByMykel/CSGO-API/refs/heads/main/public/api/en/skins.json"
        
        self.skins_db = []
        self.current_category = "Все"
        self.image_cache = {}

        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        # Верхняя панель
        self.header = ctk.CTkFrame(self, height=60, fg_color="#111", corner_radius=0)
        self.header.pack(fill="x", side="top")
        
        ctk.CTkLabel(self.header, text="XCHENGER", font=("Impact", 28), text_color="#ff3333").pack(side="left", padx=20)
        
        self.server_status = ctk.CTkLabel(self.header, text="📡 Проверка связи...", text_color="#aaa")
        self.server_status.pack(side="left", padx=20)

        ctk.CTkButton(self.header, text="🧹 ОЧИСТИТЬ ИНВЕНТАРЬ", fg_color="#440000", hover_color="#660000", 
                       command=self.clear_full_inventory).pack(side="right", padx=10)
        ctk.CTkButton(self.header, text="🔄 Обновить", width=100, command=self.load_data).pack(side="right", padx=10)

        # Основной контент
        self.tabs = ctk.CTkTabview(self, fg_color="transparent", segmented_button_selected_color="#660000")
        self.tabs.pack(fill="both", expand=True, padx=10)
        
        self.tab_shop = self.tabs.add("🛒 МАГАЗИН")
        self.tab_inv = self.tabs.add("🎒 МОЙ ИНВЕНТАРЬ")

        # --- Вкладка Магазин ---
        shop_container = ctk.CTkFrame(self.tab_shop, fg_color="transparent")
        shop_container.pack(fill="both", expand=True)

        # Категории и Поиск
        filter_frame = ctk.CTkFrame(shop_container, fg_color="#151515", height=50)
        filter_frame.pack(fill="x", pady=(0, 10))
        
        self.search = ctk.CTkEntry(filter_frame, placeholder_text="Поиск скина...", width=300)
        self.search.pack(side="left", padx=10, pady=5)
        self.search.bind("<KeyRelease>", lambda e: self.filter_list())

        self.cat_menu = ctk.CTkSegmentedButton(filter_frame, values=["Все", "Ножи", "Пистолеты", "Винтовки", "ПП", "Тяжелое"],
                                              command=self.set_category)
        self.cat_menu.set("Все")
        self.cat_menu.pack(side="left", padx=20)

        # Список скинов
        self.shop_list = ctk.CTkScrollableFrame(shop_container, fg_color="#0a0a0a")
        self.shop_list.pack(fill="both", expand=True)

        # --- Вкладка Инвентарь ---
        self.inv_list = ctk.CTkScrollableFrame(self.tab_inv, fg_color="#0a0a0a")
        self.inv_list.pack(fill="both", expand=True)

        # Логи
        self.log_area = ctk.CTkFrame(self, height=40, fg_color="#050505")
        self.log_area.pack(fill="x", side="bottom")
        self.log_label = ctk.CTkLabel(self.log_area, text="Система готова", font=("Consolas", 12))
        self.log_label.pack(side="left", padx=20)

    def log(self, msg, color="#aaa"):
        self.log_label.configure(text=f"• {msg}", text_color=color)

    def set_category(self, cat):
        self.current_category = cat
        self.filter_list()

    def load_data(self):
        self.server_status.configure(text="📡 Подключение...", text_color="#ffa500")
        def fetch():
            try:
                # Прямой запрос без кеша
                r = requests.get(self.api_url, timeout=5)
                data = r.json()
                
                new_db = []
                rarity_map = {"rarity_ancient_weapon": "6", "rarity_legendary_weapon": "5", "rarity_mythical_weapon": "4"}
                
                for item in data:
                    w_id = item.get("weapon", {}).get("id", "")
                    num_id = WEAPON_MAP.get(w_id)
                    
                    if num_id and item.get("paint_index"):
                        new_db.append({
                            "def_index": num_id,
                            "name": item.get("name"),
                            "weapon": item.get("weapon", {}).get("name"),
                            "paint": str(item.get("paint_index")),
                            "rarity": rarity_map.get(item.get("rarity", {}).get("id", ""), "1"),
                            "img": item.get("image"),
                            "raw_id": w_id
                        })
                
                self.skins_db = new_db
                self.after(0, lambda: self.server_status.configure(text="🟢 Сервера ONLINE", text_color="#44ff44"))
                self.after(0, self.filter_list)
                self.after(0, self.analyze_inventory)
            except Exception as e:
                self.after(0, lambda: self.server_status.configure(text="🔴 Сервера OFFLINE", text_color="#ff4444"))
                self.after(0, lambda: self.log(f"Ошибка сети: {e}", "#ff4444"))

        threading.Thread(target=fetch, daemon=True).start()

    def filter_list(self):
        query = self.search.get().lower()
        cat = self.current_category
        
        # Очищаем список перед обновлением
        for w in self.shop_list.winfo_children(): 
            w.destroy()
        
        # Конфигурируем колонки, чтобы они растягивались
        # Делаем 4 колонки базовыми, но они будут множиться
        for i in range(4):
            self.shop_list.grid_columnconfigure(i, weight=1)

        filtered = []
        for s in self.skins_db:
            is_match = query in s["name"].lower() or query in s["weapon"].lower()
            if not is_match: continue
            
            # Фильтр категорий
            if cat == "Ножи" and "knife" not in s["raw_id"]: continue
            if cat == "Пистолеты" and s["raw_id"] not in ["weapon_deagle", "weapon_glock", "weapon_usp_silencer", "weapon_p250", "weapon_fiveseven", "weapon_tec9", "weapon_elite", "weapon_hkp2000", "weapon_cz75a", "weapon_revolver"]: continue
            if cat == "Винтовки" and s["raw_id"] not in ["weapon_ak47", "weapon_m4a1", "weapon_m4a1_silencer", "weapon_awp", "weapon_ssg08", "weapon_aug", "weapon_sg556", "weapon_famas", "weapon_galilar", "weapon_scar20", "weapon_g3sg1"]: continue
            
            filtered.append(s)
            if len(filtered) > 60: break # Увеличил лимит до 60 для обзора

        row_idx = 0
        col_idx = 0
        max_cols = 4 # Сколько карточек в одном ряду

        for item in filtered:
            # Создаем контейнер-карточку
            card = ctk.CTkFrame(self.shop_list, fg_color="#151515", corner_radius=10)
            # Используем grid вместо pack
            card.grid(row=row_idx, column=col_idx, padx=10, pady=10, sticky="nsew")
            
            # Большая картинка
            img_lbl = ctk.CTkLabel(card, text="⌛", width=220, height=140)
            img_lbl.pack(pady=(10, 5), padx=10)
            
            if item["img"]:
                self.load_img_to_card(item["img"], img_lbl)

            # Название
            name_text = f"{item['weapon']}\n{item['name']}"
            ctk.CTkLabel(card, text=name_text, font=("Arial", 12, "bold"), height=35).pack(pady=2)
            
            # Кнопка
            ctk.CTkButton(card, text="ДОБАВИТЬ", 
                           fg_color="#660000", hover_color="#990000",
                           height=35,
                           command=lambda i=item: self.inject_skin(i)).pack(fill="x", padx=10, pady=(5, 10))

            # Логика переноса на следующую строку
            col_idx += 1
            if col_idx >= max_cols:
                col_idx = 0
                row_idx += 1

    def load_img_to_card(self, url, label):
        """Специальный метод загрузки для больших превью"""
        def task():
            try:
                if url in self.image_cache:
                    self.after(0, lambda: label.configure(image=self.image_cache[url], text=""))
                    return
                
                res = requests.get(url, timeout=5)
                # Делаем картинку крупнее для карточки
                img = Image.open(BytesIO(res.content))
                # Сохраняем пропорции, делаем ширину 240
                ctk_img = ctk.CTkImage(img, size=(240, 150)) 
                self.image_cache[url] = ctk_img
                self.after(0, lambda: label.configure(image=ctk_img, text=""))
            except:
                self.after(0, lambda: label.configure(text="🖼️ Ошибка"))
        
        threading.Thread(target=task, daemon=True).start()

    def inject_skin(self, item):
        for p in psutil.process_iter(['name']):
            if p.info['name'] in ["csgo.exe", "cs2.exe"]:
                messagebox.showwarning("Внимание", "Закройте игру перед добавлением!")
                return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f: content = f.read()
            ids = re.findall(r'"(\d+)"\s*\{', content)
            new_id = max(map(int, ids)) + 1 if ids else 1
            
            entry = (
                f'\n\t"{new_id}"\n\t{{\n'
                f'\t\t"inventory"\t\t"{new_id}"\n'
                f'\t\t"def_index"\t\t"{item["def_index"]}"\n'
                f'\t\t"level"\t\t"1"\n\t\t"quality"\t\t"4"\n\t\t"flags"\t\t"0"\n'
                f'\t\t"origin"\t\t"24"\n\t\t"in_use"\t\t"0"\n'
                f'\t\t"rarity"\t\t"{item["rarity"]}"\n'
                f'\t\t"attributes"\n\t\t{{\n'
                f'\t\t\t"6"\t\t"{item["paint"]}.000000"\n'
                f'\t\t\t"7"\t\t"1.000000"\n\t\t\t"8"\t\t"0.000001"\n'
                f'\t\t}}\n\t\t"equipped_state"\n\t\t{{\n\t\t\t"3"\t\t"0"\n\t\t}}\n\t}}'
            )
            
            pos = content.rfind('}')
            if pos != -1:
                with open(self.config_path, "w", encoding="utf-8") as f:
                    f.write(content[:pos].rstrip() + entry + "\n}")
                self.log(f"Добавлен {item['name']}", "#44ff44")
                self.analyze_inventory()
        except Exception as e: self.log(f"Ошибка: {e}", "#ff4444")

    def analyze_inventory(self):
        for w in self.inv_list.winfo_children(): w.destroy()
        if not os.path.exists(self.config_path): return
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f: content = f.read()
            items = re.findall(r'"(\d+)"\s*\{\s*"inventory".*?"def_index"\s*"(\d+)".*?"6"\s*"(\d+)\.000000"', content, re.DOTALL)
            
            for eid, di, pt in items:
                skin = next((s for s in self.skins_db if s["def_index"] == di and s["paint"] == pt), None)
                
                row = ctk.CTkFrame(self.inv_list, fg_color="#1a1a1a", height=60)
                row.pack(fill="x", pady=2, padx=10)
                
                # Картинка (если есть в кеше или загружаем)
                img_lbl = ctk.CTkLabel(row, text="🖼️", width=60)
                img_lbl.pack(side="left", padx=5)
                
                if skin and skin["img"]:
                    self.load_img_to_label(skin["img"], img_lbl)

                name = f"{skin['weapon']} | {skin['name']}" if skin else f"Предмет {di} (Paint {pt})"
                ctk.CTkLabel(row, text=name, anchor="w").pack(side="left", padx=10, expand=True, fill="x")
                
                ctk.CTkButton(row, text="❌", width=40, fg_color="#330000", hover_color="#ff0000",
                               command=lambda x=eid: self.delete_item(x)).pack(side="right", padx=10)
        except: pass

    def load_img_to_label(self, url, label):
        def task():
            try:
                if url in self.image_cache:
                    self.after(0, lambda: label.configure(image=self.image_cache[url], text=""))
                    return
                res = requests.get(url, timeout=5)
                img = Image.open(BytesIO(res.content)).resize((50, 35))
                ctk_img = ctk.CTkImage(img, size=(50, 35))
                self.image_cache[url] = ctk_img
                self.after(0, lambda: label.configure(image=ctk_img, text=""))
            except: pass
        threading.Thread(target=task, daemon=True).start()

    def delete_item(self, eid):
        try:
            with open(self.config_path, "r", encoding="utf-8") as f: content = f.read()
            pattern = r'\n\t"' + eid + r'"\s*\{.*?\n\t\}'
            new_content = re.sub(pattern, "", content, flags=re.DOTALL)
            with open(self.config_path, "w", encoding="utf-8") as f: f.write(new_content)
            self.analyze_inventory()
            self.log(f"Удален предмет {eid}", "#ffa500")
        except: pass

    def clear_full_inventory(self):
        if messagebox.askyesno("Очистка", "Вы уверены, что хотите удалить ВСЕ добавленные скины?"):
            try:
                with open(self.config_path, "w", encoding="utf-8") as f:
                    f.write('"items"\n{\n}')
                self.analyze_inventory()
                self.log("Инвентарь полностью очищен", "#ff4444")
            except Exception as e: self.log(f"Ошибка очистки: {e}")

if __name__ == "__main__":
    app = XChenger()
    app.mainloop()