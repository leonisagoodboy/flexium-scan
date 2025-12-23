import flet as ft
import datetime
import traceback

def main(page: ft.Page):
    # --- 安全啟動：捕捉所有錯誤 ---
    try:
        # 1. 基礎設定
        page.title = "FLEXium"
        page.theme_mode = "light"
        page.padding = 0
        page.bgcolor = "#F5F5F5"
        
        C_GREEN = "#009140"
        C_ORANGE = "#F37021"
        C_WHITE = "#FFFFFF"
        C_GREY = "#9E9E9E"
        
        STORAGE_KEY = "flexium_scan_records"

        # --- 2. UI 元件 (先定義，不讀資料) ---

        header = ft.Container(
            content=ft.Row([
                ft.Icon(name="qr_code", color=C_WHITE, size=24),
                ft.Text("FLEXium 掃描作業", size=18, weight="bold", color=C_WHITE)
            ], alignment="center"),
            bgcolor=C_GREEN,
            padding=12
        )

        lbl_msg = ft.Text("請開始掃描", size=16, color=C_GREY)

        # 掃描輸入框
        txt_scan_emp = ft.TextField(label="工號", bgcolor=C_WHITE, border_color=C_GREEN)
        txt_scan_amt = ft.TextField(label="金額", bgcolor=C_WHITE, border_color=C_GREEN, keyboard_type="number")
        
        # 午餐輸入框
        txt_lunch_emp = ft.TextField(label="午餐工號", bgcolor=C_WHITE, border_color=C_GREEN)

        # 歷史列表 (預設是空的)
        lv_list = ft.ListView(expand=True, spacing=10, padding=20)
        
        # 隱藏按鈕 (收鍵盤用)
        dummy_btn = ft.ElevatedButton(text="", width=0, height=0, visible=False)

        # --- 3. 邏輯處理 ---

        def get_records():
            try:
                # 延遲讀取：只有在需要時才讀取
                data = page.client_storage.get(STORAGE_KEY)
                return data if data else []
            except:
                return []

        def save_record(emp, amt, note):
            try:
                records = get_records()
                new_row = {
                    "e": str(emp), # 縮短 key 名稱以節省空間
                    "a": int(amt),
                    "n": str(note),
                    "t": datetime.datetime.now().strftime("%m-%d %H:%M")
                }
                records.insert(0, new_row)
                # 只保留最近 500 筆，避免舊手機記憶體爆掉
                if len(records) > 500:
                    records = records[:500]
                    
                page.client_storage.set(STORAGE_KEY, records)
                return True
            except Exception as e:
                lbl_msg.value = f"儲存失敗: {str(e)}"
                page.update()
                return False

        def update_history():
            lv_list.controls.clear()
            rows = get_records()
            if not rows:
                lv_list.controls.append(ft.Text("無資料"))
            
            for row in rows:
                item = ft.Container(
                    content=ft.Row([
                        ft.Text(f"{row['e']}", weight="bold"),
                        ft.Text(f"${row['a']} ({row['n']})", color=C_ORANGE),
                    ], alignment="spaceBetween"),
                    padding=10,
                    bgcolor=C_WHITE,
                    border=ft.border.only(left=ft.BorderSide(5, C_GREEN))
                )
                lv_list.controls.append(item)
            page.update()

        def on_confirm_click(e):
            # 簡單版確認：不跳視窗，直接儲存 (減少渲染負擔)
            emp = txt_scan_emp.value
            amt = txt_scan_amt.value
            
            if not emp or not amt:
                lbl_msg.value = "❌ 請輸入完整"
                page.update()
                return
                
            if save_record(emp, amt, "一般"):
                lbl_msg.value = f"✅ 已存: {emp} ${amt}"
                lbl_msg.color = C_GREEN
                txt_scan_emp.value = ""
                txt_scan_amt.value = ""
                txt_scan_emp.focus()
                update_history()
            
        def on_lunch_click(e):
            emp = txt_lunch_emp.value
            if not emp:
                return
            if save_record(emp, 60, "午餐"):
                lbl_msg.value = f"✅ 午餐已存: {emp}"
                lbl_msg.color = C_GREEN
                txt_lunch_emp.value = ""
                txt_lunch_emp.focus()
                update_history()

        # 匯出功能 (純文字複製，最安全)
        def copy_data(e):
            rows = get_records()
            s = "工號,金額,備註,時間\n"
            for r in rows:
                s += f"{r['e']},{r['a']},{r['n']},{r['t']}\n"
            page.set_clipboard(s)
            page.show_snack_bar(ft.SnackBar(content=ft.Text("已複製資料")))

        # --- 4. 版面組裝 (不使用 Tab，直接上下排列，減少記憶體) ---
        
        # 為了避免舊手機渲染 Tab 出錯，我們把所有功能放在單一頁面
        # 用簡單的「展開/收合」或者直接羅列
        
        page.add(
            header,
            ft.Container(
                padding=10,
                content=ft.Column([
                    ft.Text("一般輸入", weight="bold"),
                    ft.Row([txt_scan_emp, ft.IconButton(icon="keyboard", on_click=lambda e: txt_scan_emp.focus())]),
                    txt_scan_amt,
                    ft.ElevatedButton("儲存 (一般)", bgcolor=C_ORANGE, color=C_WHITE, width=1000, on_click=on_confirm_click),
                    
                    ft.Divider(),
                    
                    ft.Text("午餐模式", weight="bold"),
                    ft.Row([txt_lunch_emp, ft.IconButton(icon="keyboard", on_click=lambda e: txt_lunch_emp.focus())]),
                    ft.ElevatedButton("儲存 (午餐 $60)", bgcolor=C_GREEN, color=C_WHITE, width=1000, on_click=on_lunch_click),
                    
                    ft.Divider(),
                    
                    lbl_msg,
                    ft.ElevatedButton("複製所有資料", icon="copy", on_click=copy_data),
                    
                    ft.Text("歷史紀錄 (最近500筆)", size=12),
                    ft.Container(
                        content=lv_list,
                        height=200, # 固定高度，避免無限延伸吃光記憶體
                        border=ft.border.all(1, C_GREY),
                        border_radius=5
                    )
                ], scroll=ft.ScrollMode.ADAPTIVE) # 開啟捲動
            )
        )
        
        # 啟動後才讀取歷史紀錄
        update_history()

    except Exception as e:
        # 如果真的崩潰，顯示錯誤在畫面上
        page.add(ft.Text(f"CRITICAL ERROR: {e}", size=30, color="red"))
        page.add(ft.Text(traceback.format_exc(), color="red"))

ft.app(target=main)
