import flet as ft
import datetime
import csv
import traceback
import io

def main(page: ft.Page):
    try:
        # --- 1. 全局 UI 設定 ---
        page.title = "FLEXium"
        page.theme_mode = "light"
        page.padding = 0
        page.bgcolor = "#F5F5F5"
        
        # 定義顏色
        C_GREEN = "#009140"
        C_ORANGE = "#F37021"
        C_WHITE = "#FFFFFF"
        C_GREY = "#9E9E9E"
        C_BLACK = "#000000"
        
        STORAGE_KEY = "flexium_records_v2"

        # --- 2. 資料存取 (Client Storage - 最穩) ---
        def get_records():
            data = page.client_storage.get(STORAGE_KEY)
            return data if data else []

        def save_record(emp, amt, note):
            records = get_records()
            new_row = {
                "id": len(records) + 1,
                "emp_id": str(emp),
                "amount": int(amt),
                "note": str(note),
                "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            records.insert(0, new_row)
            page.client_storage.set(STORAGE_KEY, records)

        def clear_history():
            page.client_storage.remove(STORAGE_KEY)
            update_history()

        # --- 3. UI 元件宣告 ---

        # 標題
        header = ft.Container(
            content=ft.Row([
                ft.Icon(name="qr_code_scanner", color=C_WHITE, size=24),
                ft.Text("FLEXium 掃描作業", size=18, weight="bold", color=C_WHITE)
            ], alignment="center"),
            bgcolor=C_GREEN,
            padding=12
        )

        lbl_msg = ft.Text("等待掃描...", size=16, color=C_GREY, weight="bold")

        # [A] 掃描頁元件
        txt_scan_emp = ft.TextField(
            label="員工工號", hint_text="掃描...", text_size=18,
            bgcolor=C_WHITE, border_color=C_GREEN, border_radius=10,
            autofocus=True, expand=True
        )
        txt_scan_amt = ft.TextField(
            label="消費金額", suffix_text="元", text_size=18,
            bgcolor=C_WHITE, border_color=C_GREEN, border_radius=10,
            keyboard_type="number"
        )

        # [B] 午餐頁元件
        txt_lunch_emp = ft.TextField(
            label="員工工號 (午餐)", hint_text="掃描即確認...", text_size=18,
            bgcolor=C_WHITE, border_color=C_GREEN, border_radius=10,
            expand=True
        )
        txt_lunch_amt = ft.TextField(
            label="固定金額", value="60", read_only=True, suffix_text="元",
            text_size=18, bgcolor="#E0E0E0", border_color=C_GREEN, border_radius=10
        )

        lv_list = ft.ListView(expand=True, spacing=10, padding=20)
        
        # 隱藏按鈕 (收鍵盤用)
        dummy_btn = ft.ElevatedButton(text="", width=0, height=0, visible=False)

        # --- 4. 確認視窗 (Overlay) ---
        t_date = ft.Text(size=18, weight="bold")
        t_emp = ft.Text(size=18, weight="bold", color=C_BLACK)
        t_amt = ft.Text(size=30, weight="bold", color=C_ORANGE)
        t_note = ft.Text(size=16, color=C_GREY)
        
        # 暫存資料
        current_data = {}

        def close_dialog(e):
            overlay.visible = False
            # 關閉後重新聚焦
            if current_data.get("note") == "午餐":
                txt_lunch_emp.value = ""
                txt_lunch_emp.focus()
            else:
                txt_scan_emp.value = ""
                txt_scan_amt.value = ""
                txt_scan_emp.focus()
            page.update()

        def confirm_save(e):
            try:
                save_record(current_data["emp"], current_data["amt"], current_data["note"])
                lbl_msg.value = f"✅ 已儲存: {current_data['emp']} (${current_data['amt']})"
                lbl_msg.color = C_GREEN
                update_history()
            except Exception as err:
                lbl_msg.value = f"錯誤: {err}"
                lbl_msg.color = "red"
            close_dialog(None)

        # 確認卡片
        dialog_card = ft.Container(
            padding=30, bgcolor=C_WHITE, border_radius=15, width=300,
            content=ft.Column([
                ft.Text("⚠️ 請確認資料", size=22, weight="bold", color=C_GREEN),
                ft.Container(height=15),
                ft.Text("日期時間:", size=14, color=C_GREY), t_date,
                ft.Container(height=10),
                ft.Text("員工工號:", size=14, color=C_GREY), t_emp,
                ft.Container(height=10),
                ft.Row([ft.Text("確認金額:", size=14, color=C_GREY), t_note]), t_amt,
                ft.Container(height=20),
                ft.Row([
                    ft.OutlinedButton("取消", on_click=close_dialog),
                    ft.ElevatedButton("確認寫入", on_click=confirm_save, bgcolor=C_ORANGE, color=C_WHITE),
                ], alignment="spaceBetween")
            ])
        )

        overlay = ft.Container(
            content=ft.Container(content=dialog_card, alignment=ft.alignment.center),
            bgcolor="#99000000", visible=False,
        )

        # --- 5. 邏輯處理 ---

        def hide_keyboard():
            try:
                txt_scan_emp.blur()
                txt_scan_amt.blur()
                txt_lunch_emp.blur()
                dummy_btn.focus()
            except:
                pass
            page.update()

        def show_confirm(emp, amt, note):
            if not emp:
                lbl_msg.value = "❌ 請輸入工號"
                lbl_msg.color = "red"
                page.update()
                return
            
            # 1. 隱藏鍵盤 (這是您最需要的功能)
            hide_keyboard()
            
            # 2. 準備資料
            current_data["emp"] = emp
            current_data["amt"] = amt
            current_data["note"] = note
            
            # 3. 更新視窗
            t_date.value = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            t_emp.value = emp
            t_amt.value = f"${amt}"
            t_note.value = f"({note})"
            
            # 4. 顯示
            lbl_msg.value = "等待確認..."
            lbl_msg.color = "blue"
            overlay.visible = True
            page.update()

        # 事件綁定
        def on_scan_submit(e):
            if txt_scan_emp.value: txt_scan_amt.focus()
            
        def on_amt_submit(e):
            val = txt_scan_amt.value
            if val and val.isdigit():
                show_confirm(txt_scan_emp.value, val, "一般")
            else:
                lbl_msg.value = "❌ 金額錯誤"
                page.update()
                
        def on_lunch_submit(e):
            if txt_lunch_emp.value:
                show_confirm(txt_lunch_emp.value, "60", "午餐")

        txt_scan_emp.on_submit = on_scan_submit
        txt_scan_amt.on_submit = on_amt_submit
        txt_lunch_emp.on_submit = on_lunch_submit

        def update_history():
            lv_list.controls.clear()
            rows = get_records()
            if not rows:
                lv_list.controls.append(ft.Text("無資料"))
            for r in rows:
                lv_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Column([
                                ft.Text(f"工號: {r['emp_id']}", weight="bold"),
                                ft.Text(f"{r['time']} ({r['note']})", size=12, color=C_GREY),
                            ]),
                            ft.Text(f"${r['amount']}", size=20, color=C_ORANGE, weight="bold"),
                        ], alignment="spaceBetween"),
                        padding=10, bgcolor=C_WHITE, border_radius=10,
                        border=ft.border.only(left=ft.BorderSide(5, C_GREEN))
                    )
                )
            page.update()

        # 匯出邏輯
        def copy_data(e):
            rows = get_records()
            s = "ID,工號,金額,備註,時間\n"
            for r in rows:
                s += f"{r['id']},{r['emp_id']},{r['amount']},{r['note']},{r['time']}\n"
            page.set_clipboard(s)
            page.show_snack_bar(ft.SnackBar(content=ft.Text("已複製全部資料")))

        # --- 6. 版面組裝 (分頁) ---
        
        tab_scan = ft.Column([
            header,
            ft.Container(padding=20, content=ft.Column([
                ft.Container(padding=20, bgcolor=C_WHITE, border_radius=15, content=ft.Column([
                    ft.Text("一般消費", weight="bold", color=C_GREEN),
                    ft.Container(height=10),
                    ft.Row([txt_scan_emp, ft.IconButton(icon="keyboard", icon_color=C_GREEN, on_click=lambda e: txt_scan_emp.focus())]),
                    ft.Container(height=10),
                    txt_scan_amt,
                    ft.Container(height=20),
                    ft.ElevatedButton("確認", bgcolor=C_ORANGE, color=C_WHITE, width=1000, on_click=on_amt_submit)
                ])),
                ft.Container(height=20), lbl_msg
            ]))
        ])

        tab_lunch = ft.Column([
            header,
            ft.Container(padding=20, content=ft.Column([
                ft.Container(padding=20, bgcolor=C_WHITE, border_radius=15, content=ft.Column([
                    ft.Text("午餐模式 (固定$60)", weight="bold", color=C_ORANGE),
                    ft.Container(height=10),
                    ft.Row([txt_lunch_emp, ft.IconButton(icon="keyboard", icon_color=C_GREEN, on_click=lambda e: txt_lunch_emp.focus())]),
                    ft.Container(height=10),
                    txt_lunch_amt,
                    ft.Container(height=20),
                    ft.ElevatedButton("確認", bgcolor=C_ORANGE, color=C_WHITE, width=1000, on_click=on_lunch_submit)
                ])),
                ft.Container(height=20), lbl_msg
            ]))
        ])

        tab_hist = ft.Column([
            ft.Container(padding=15, bgcolor=C_GREEN, content=ft.Row([
                ft.Text("歷史紀錄", color=C_WHITE, weight="bold"),
                ft.IconButton(icon="refresh", icon_color=C_WHITE, on_click=lambda e: update_history())
            ], alignment="spaceBetween")),
            lv_list
        ])

        tab_export = ft.Column([
            ft.Container(padding=15, bgcolor=C_GREEN, content=ft.Text("資料管理", color=C_WHITE, weight="bold")),
            ft.Container(padding=20, content=ft.Column([
                ft.ElevatedButton("複製資料到剪貼簿", icon="copy", width=1000, on_click=copy_data),
                ft.Container(height=20),
                ft.ElevatedButton("清除所有資料", icon="delete", bgcolor="red", color="white", width=1000, on_click=lambda e: clear_history()),
            ]))
        ])

        def on_tab_change(e):
            idx = e.control.selected_index
            if idx == 0: txt_scan_emp.focus()
            elif idx == 1: txt_lunch_emp.focus()
            elif idx == 2: update_history()

        tabs = ft.Tabs(
            selected_index=0, on_change=on_tab_change,
            tabs=[
                ft.Tab(text="掃描", icon="qr_code", content=tab_scan),
                ft.Tab(text="午餐", icon="restaurant", content=tab_lunch),
                ft.Tab(text="紀錄", icon="history", content=tab_hist),
                ft.Tab(text="匯出", icon="settings", content=tab_export),
            ], expand=True
        )

        page.add(ft.Stack([tabs, overlay, dummy_btn], expand=True))
        update_history()

    except Exception as e:
        page.add(ft.Text(f"ERROR: {e}", color="red"))

ft.app(target=main)
