import flet as ft
import sqlite3
import datetime
import csv
import traceback
import os

def main(page: ft.Page):
    try:
        # --- 1. 全局 UI 設定 ---
        page.title = "FLEXium 掃描系統"
        page.theme_mode = "light"
        page.padding = 0
        page.window_width = 360
        page.window_height = 800
        page.bgcolor = "#F5F5F5"
        
        FLEX_GREEN = "#009140"
        FLEX_ORANGE = "#F37021"
        
        # [關鍵修正] 強制鎖定資料庫路徑，避免找不到檔案
        # 使用 app 的內部儲存空間路徑
        db_filename = "flexium_data.db"
        # 在 Android 上，os.getcwd() 通常是內部私有目錄，這樣寫比較保險
        db_path = os.path.join(os.getcwd(), db_filename) 

        # --- 2. 資料庫初始化 ---
        def init_db():
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    emp_id TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()
            conn.close()

        init_db()

        # --- 3. UI 元件宣告 ---

        header_banner = ft.Container(
            content=ft.Row([
                ft.Icon(name="qr_code_scanner", color="white", size=24),
                ft.Text("FLEXium 掃描作業", size=18, weight="bold", color="white")
            ], alignment="center"),
            bgcolor=FLEX_GREEN,
            padding=12,
            shadow=ft.BoxShadow(blur_radius=5, color="grey")
        )

        txt_emp_id = ft.TextField(
            label="員工工號",
            hint_text="請掃描...",
            prefix_icon="badge",
            text_size=18,
            bgcolor="white",
            border_color=FLEX_GREEN,
            focused_border_color=FLEX_ORANGE,
            border_radius=10,
            autofocus=True
        )
        
        txt_amount = ft.TextField(
            label="消費金額",
            prefix_icon="currency_exchange",
            suffix_text="元",
            text_size=18,
            bgcolor="white",
            border_color=FLEX_GREEN,
            focused_border_color=FLEX_ORANGE,
            border_radius=10,
            keyboard_type="number"
        )

        lbl_last_action = ft.Text("等待掃描...", size=16, color="grey", weight="bold")
        
        lv_history = ft.ListView(expand=True, spacing=10, padding=20)
        file_picker = ft.FilePicker()
        page.overlay.append(file_picker)

        # --- 4. 確認視窗 (Overlay) ---
        
        dlg_date_text = ft.Text(size=20, weight="bold")
        dlg_emp_text = ft.Text(size=20, weight="bold", color="black")
        dlg_amt_text = ft.Text(size=30, weight="bold", color=FLEX_ORANGE)

        def close_overlay(e):
            confirm_overlay.visible = False
            page.update()

        def real_save_to_db(e):
            confirm_overlay.visible = False
            
            emp_id = txt_emp_id.value.strip()
            amount_str = txt_amount.value.strip()
            
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("INSERT INTO records (emp_id, amount, created_at) VALUES (?, ?, ?)", 
                               (emp_id, int(amount_str), dt))
                conn.commit()
                conn.close()

                lbl_last_action.value = f"✅ 已儲存: {emp_id} - ${amount_str}"
                lbl_last_action.color = FLEX_GREEN
                
                txt_emp_id.value = ""
                txt_amount.value = ""
                txt_emp_id.focus()
                page.update()
                load_history()

            except Exception as err:
                lbl_last_action.value = f"❌ 錯誤: {err}"
                lbl_last_action.color = "red"
                page.update()

        confirm_card = ft.Container(
            padding=30,
            bgcolor="white",
            border_radius=15,
            width=300, 
            shadow=ft.BoxShadow(blur_radius=20, color="black"),
            content=ft.Column([
                ft.Text("⚠️ 請確認資料正確", size=22, weight="bold", color=FLEX_GREEN),
                ft.Divider(height=20, thickness=2),
                
                ft.Text("日期時間:", size=14, color="grey"),
                dlg_date_text,
                ft.Container(height=10),
                
                ft.Text("員工工號:", size=14, color="grey"),
                dlg_emp_text,
                ft.Container(height=10),
                
                ft.Text("確認金額:", size=14, color="grey"),
                dlg_amt_text,
                
                ft.Divider(height=30, color="transparent"),
                
                ft.Row([
                    ft.OutlinedButton("取消", on_click=close_overlay, width=100),
                    ft.ElevatedButton("確認寫入", on_click=real_save_to_db, 
                                      style=ft.ButtonStyle(bgcolor=FLEX_ORANGE, color="white"),
                                      width=120),
                ], alignment="spaceBetween")
            ])
        )

        confirm_overlay = ft.Container(
            content=ft.Container(content=confirm_card, alignment=ft.alignment.center),
            bgcolor="#80000000", 
            visible=False,
            expand=True
        )

        # --- 5. 觸發邏輯 ---

        def ask_confirm(e=None):
            emp_id = txt_emp_id.value.strip()
            amount_str = txt_amount.value.strip()

            if not emp_id:
                lbl_last_action.value = "❌ 錯誤：工號是空的！"
                lbl_last_action.color = "red"
                txt_emp_id.focus()
                page.update()
                return

            if not amount_str:
                lbl_last_action.value = "❌ 錯誤：金額是空的！"
                lbl_last_action.color = "red"
                txt_amount.focus()
                page.update()
                return

            if not amount_str.isdigit():
                lbl_last_action.value = f"❌ 錯誤：金額 '{amount_str}' 不是數字！"
                lbl_last_action.color = "red"
                txt_amount.focus()
                page.update()
                return

            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            dlg_date_text.value = current_time
            dlg_emp_text.value = emp_id
            dlg_amt_text.value = f"${amount_str}"

            lbl_last_action.value = "等待確認..."
            lbl_last_action.color = "blue"
            confirm_overlay.visible = True
            page.update()

        def load_history():
            lv_history.controls.clear()
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT id, emp_id, amount, created_at FROM records ORDER BY id DESC")
                rows = cursor.fetchall()
                conn.close()

                if not rows:
                    lv_history.controls.append(ft.Text("尚無資料", color="grey", text_align="center"))
                
                for row in rows:
                    rec_id, emp, amt, time = row
                    card = ft.Container(
                        content=ft.Row([
                            ft.Column([
                                ft.Text(f"工號: {emp}", weight="bold", size=16, color="black"),
                                ft.Text(f"{time}", size=12, color="grey"),
                            ]),
                            ft.Text(f"${amt}", size=20, color=FLEX_ORANGE, weight="bold"),
                        ], alignment="spaceBetween"),
                        padding=15,
                        bgcolor="white",
                        border=ft.border.only(left=ft.BorderSide(5, FLEX_GREEN)),
                        border_radius=ft.border_radius.only(top_right=10, bottom_right=10),
                        shadow=ft.BoxShadow(blur_radius=3, color="grey")
                    )
                    lv_history.controls.append(card)
            except Exception as e:
                lv_history.controls.append(ft.Text(f"讀取錯誤: {e}", color="red"))
            page.update()

        def export_data(e):
            filename = f"FLEX_Export_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.csv"
            file_picker.save_file(dialog_title="匯出 CSV", file_name=filename)

        def on_save_file_result(e: ft.FilePickerResultEvent):
            if e.path:
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM records")
                    rows = cursor.fetchall()
                    conn.close()
                    
                    # [關鍵修正] 加入 encoding='utf-8-sig' 確保 Excel 開啟中文不亂碼
                    with open(e.path, mode='w', newline='', encoding='utf-8-sig') as f:
                        writer = csv.writer(f)
                        # 寫入標題
                        writer.writerow(['ID', '工號', '金額', '時間'])
                        # 寫入內容
                        writer.writerows(rows)
                    
                    # [關鍵] 告訴使用者到底匯出了幾筆，方便確認
                    count = len(rows)
                    msg = f"匯出成功！共 {count} 筆資料"
                    if count == 0:
                        msg = "匯出成功，但資料庫是空的！(請先掃描資料)"
                        
                    page.show_snack_bar(ft.SnackBar(content=ft.Text(msg), bgcolor=FLEX_GREEN))
                    
                except Exception as err:
                    page.show_snack_bar(ft.SnackBar(content=ft.Text(f"匯出失敗: {err}"), bgcolor="red"))

        file_picker.on_result = on_save_file_result

        # --- 焦點 ---
        def on_emp_scan(e):
            if txt_emp_id.value:
                txt_amount.focus()
                
        def on_amount_enter(e):
            if txt_amount.value:
                ask_confirm()

        txt_emp_id.on_submit = on_emp_scan
        txt_amount.on_submit = on_amount_enter

        # --- 版面組裝 ---
        
        main_layout = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            indicator_color=FLEX_ORANGE,
            label_color=FLEX_GREEN,
            unselected_label_color="grey",
            divider_color="transparent",
            tabs=[
                ft.Tab(text="掃描", icon="qr_code_scanner", content=ft.Column([
                    header_banner,
                    ft.Container(
                        padding=20,
                        content=ft.Column([
                            ft.Container(
                                padding=25,
                                bgcolor="white",
                                border_radius=15,
                                shadow=ft.BoxShadow(blur_radius=10, color="grey"),
                                content=ft.Column([
                                    ft.Text("新增紀錄", size=16, weight="bold", color=FLEX_GREEN),
                                    ft.Container(height=10),
                                    txt_emp_id,
                                    ft.Container(height=10),
                                    txt_amount,
                                    ft.Container(height=20),
                                    ft.ElevatedButton(
                                        "下一步：確認資料 (Enter)",
                                        icon="arrow_forward",
                                        style=ft.ButtonStyle(
                                            bgcolor=FLEX_ORANGE,
                                            color="white",
                                            shape=ft.RoundedRectangleBorder(radius=10),
                                            padding=20,
                                        ),
                                        width=1000,
                                        on_click=ask_confirm 
                                    )
                                ])
                            ),
                            ft.Container(height=20),
                            lbl_last_action 
                        ])
                    )
                ])),
                ft.Tab(text="紀錄", icon="history", content=ft.Column([
                    ft.Container(
                        padding=15,
                        bgcolor=FLEX_GREEN,
                        content=ft.Row([
                            ft.Text("歷史紀錄", size=18, color="white", weight="bold"),
                            ft.IconButton(icon="refresh", icon_color="white", on_click=lambda e: load_history())
                        ], alignment="spaceBetween")
                    ),
                    lv_history
                ])),
                ft.Tab(text="匯出", icon="settings", content=ft.Column([
                    ft.Container(
                        padding=15,
                        bgcolor=FLEX_GREEN,
                        alignment=ft.alignment.center,
                        content=ft.Text("資料管理", size=18, color="white", weight="bold")
                    ),
                    ft.Container(
                        padding=20,
                        content=ft.Container(
                            bgcolor="white",
                            padding=20,
                            border_radius=10,
                            shadow=ft.BoxShadow(blur_radius=5, color="grey"),
                            content=ft.Row([
                                ft.Icon(name="file_download", color=FLEX_GREEN, size=30),
                                ft.Column([
                                    ft.Text("匯出 CSV", size=16, weight="bold"),
                                    ft.Text("儲存至本機資料夾", size=12, color="grey"),
                                ], expand=True),
                                ft.IconButton(icon="arrow_forward_ios", icon_color=FLEX_ORANGE, on_click=export_data)
                            ])
                        )
                    )
                ])),
            ],
            expand=True,
        )

        page.add(
            ft.Stack(
                [
                    main_layout,
                    confirm_overlay, 
                ],
                expand=True 
            )
        )
        
        load_history()

    except Exception as e:
        page.add(ft.Text(f"嚴重錯誤: {e}", color="red", size=20))
        page.add(ft.Text(traceback.format_exc(), color="red"))
        page.update()

ft.app(target=main)
