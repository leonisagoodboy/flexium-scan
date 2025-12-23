import flet as ft
import datetime
import csv
import traceback
import io

def main(page: ft.Page):
    try:
        # --- 1. 基礎設定 (最保守寫法) ---
        page.title = "FLEXium"
        page.theme_mode = "light"
        page.padding = 0
        page.window_width = 360
        page.window_height = 800
        page.bgcolor = "#F5F5F5"
        
        # 定義顏色 (直接用字串，不依賴 ft.colors)
        C_GREEN = "#009140"
        C_ORANGE = "#F37021"
        C_WHITE = "#FFFFFF"
        C_GREY = "#9E9E9E"
        C_BLACK = "#000000"
        
        STORAGE_KEY = "flexium_scan_records"

        # --- 2. 資料存取 (Client Storage) ---
        
        def get_records():
            # 讀取資料，如果沒有就回傳空陣列
            data = page.client_storage.get(STORAGE_KEY)
            if data is None:
                return []
            return data

        def save_record(emp, amt, note):
            records = get_records()
            # 建立新資料物件
            new_row = {
                "id": len(records) + 1,
                "emp_id": str(emp),
                "amount": int(amt),
                "note": str(note),
                "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            # 插入到最前面
            records.insert(0, new_row)
            page.client_storage.set(STORAGE_KEY, records)

        # --- 3. UI 元件建立 ---

        # 標題列
        header = ft.Container(
            content=ft.Row([
                ft.Icon(name="qr_code_scanner", color=C_WHITE, size=24),
                ft.Text("FLEXium 掃描作業", size=18, weight="bold", color=C_WHITE)
            ], alignment="center"),
            bgcolor=C_GREEN,
            padding=12
        )

        # 狀態文字
        lbl_msg = ft.Text("等待掃描...", size=16, color=C_GREY, weight="bold")

        # [A] 掃描頁面元件
        # 員工工號 (一般)
        txt_scan_emp = ft.TextField(
            label="員工工號",
            hint_text="掃描...",
            text_size=18,
            bgcolor=C_WHITE,
            border_color=C_GREEN,
            border_radius=10,
            autofocus=True,
            expand=True # 佔滿剩餘寬度
        )
        
        # 消費金額 (一般)
        txt_scan_amt = ft.TextField(
            label="消費金額",
            suffix_text="元",
            text_size=18,
            bgcolor=C_WHITE,
            border_color=C_GREEN,
            border_radius=10,
            keyboard_type="number"
        )

        # [B] 午餐頁面元件
        # 員工工號 (午餐)
        txt_lunch_emp = ft.TextField(
            label="員工工號 (午餐)",
            hint_text="掃描即確認...",
            text_size=18,
            bgcolor=C_WHITE,
            border_color=C_GREEN,
            border_radius=10,
            expand=True
        )

        # 固定金額 (午餐)
        txt_lunch_amt = ft.TextField(
            label="固定金額",
            value="60",
            read_only=True, # 唯讀
            suffix_text="元",
            text_size=18,
            bgcolor="#E0E0E0", # 灰色底
            border_color=C_GREEN,
            border_radius=10
        )

        # 歷史列表
        lv_list = ft.ListView(expand=True, spacing=10, padding=20)
        
        # 檔案選取器
        file_picker = ft.FilePicker()
        page.overlay.append(file_picker)

        # 隱藏的按鈕 (用來轉移焦點，達到收起鍵盤的效果)
        dummy_button = ft.ElevatedButton(text="", width=0, height=0, visible=False)

        # --- 4. 確認視窗元件 (手刻 Overlay) ---
        
        t_date = ft.Text(size=18, weight="bold")
        t_emp = ft.Text(size=18, weight="bold", color=C_BLACK)
        t_amt = ft.Text(size=30, weight="bold", color=C_ORANGE)
        t_note = ft.Text(size=16, color=C_GREY)

        # 暫存變數
        temp_data = {"emp": "", "amt": "", "note": ""}

        def close_dialog(e):
            overlay.visible = False
            # 關閉後重新聚焦回原本的輸入框
            if temp_data["note"] == "午餐":
                txt_lunch_emp.focus()
                txt_lunch_emp.value = ""
            else:
                txt_scan_emp.focus()
                txt_scan_emp.value = ""
                txt_scan_amt.value = ""
            page.update()

        def save_and_close(e):
            try:
                save_record(temp_data["emp"], temp_data["amt"], temp_data["note"])
                lbl_msg.value = f"✅ 已儲存: {temp_data['emp']} (${temp_data['amt']})"
                lbl_msg.color = C_GREEN
                update_history()
            except Exception as err:
                lbl_msg.value = "儲存失敗"
                lbl_msg.color = "red"
            
            close_dialog(None)

        # 確認卡片
        dialog_card = ft.Container(
            padding=30,
            bgcolor=C_WHITE,
            border_radius=15,
            width=300,
            content=ft.Column([
                ft.Text("⚠️ 請確認資料", size=22, weight="bold", color=C_GREEN),
                ft.Container(height=15), # 代替 SizedBox
                
                ft.Text("日期時間:", size=14, color=C_GREY),
                t_date,
                ft.Container(height=10),
                
                ft.Text("員工工號:", size=14, color=C_GREY),
                t_emp,
                ft.Container(height=10),
                
                ft.Row([ft.Text("確認金額:", size=14, color=C_GREY), t_note]),
                t_amt,
                
                ft.Container(height=20),
                
                ft.Row([
                    ft.OutlinedButton("取消", on_click=close_dialog),
                    ft.ElevatedButton("確認寫入", on_click=save_and_close, bgcolor=C_ORANGE, color=C_WHITE),
                ], alignment="spaceBetween")
            ])
        )

        # 全螢幕遮罩
        overlay = ft.Container(
            content=ft.Container(content=dialog_card, alignment=ft.alignment.center),
            bgcolor="#99000000", # 半透明黑 (Hex String)
            visible=False,
            # 舊版 expand 寫法：放在 Stack 中會自動填滿
        )

        # --- 5. 邏輯處理 ---

        def hide_keyboard():
            # 嘗試隱藏鍵盤最安全的方法：聚焦到一個看不見的按鈕，或使用 page.focus()
            try:
                txt_scan_emp.blur()
                txt_scan_amt.blur()
                txt_lunch_emp.blur()
            except:
                pass # 如果 blur 不支援就不做動作
            page.update()

        def open_confirm(emp, amt, note):
            if not emp:
                lbl_msg.value = "❌ 請掃描工號"
                lbl_msg.color = "red"
                page.update()
                return

            # 1. 隱藏鍵盤
            hide_keyboard()
            
            # 2. 設定資料
            temp_data["emp"] = emp
            temp_data["amt"] = amt
            temp_data["note"] = note

            # 3. 更新 UI
            t_date.value = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            t_emp.value = emp
            t_amt.value = f"${amt}"
            t_note.value = f"({note})"
            
            # 4. 顯示視窗
            lbl_msg.value = "等待確認..."
            lbl_msg.color = "blue"
            overlay.visible = True
            page.update()

        # [一般] 邏輯
        def scan_emp_done(e):
            if txt_scan_emp.value:
                txt_scan_amt.focus()
        
        def scan_amt_done(e):
            val = txt_scan_amt.value
            if val and val.isdigit():
                open_confirm(txt_scan_emp.value, val, "一般")
            else:
                lbl_msg.value = "❌ 金額錯誤"
                page.update()

        # [午餐] 邏輯
        def lunch_emp_done(e):
            if txt_lunch_emp.value:
                open_confirm(txt_lunch_emp.value, "60", "午餐")

        # 綁定事件
        txt_scan_emp.on_submit = scan_emp_done
        txt_scan_amt.on_submit = scan_amt_done
        txt_lunch_emp.on_submit = lunch_emp_done

        # 鍵盤按鈕邏輯
        def manual_focus_scan(e):
            txt_scan_emp.focus()
            
        def manual_focus_lunch(e):
            txt_lunch_emp.focus()

        # 歷史紀錄
        def update_history():
            lv_list.controls.clear()
            rows = get_records()
            
            if not rows:
                lv_list.controls.append(ft.Text("無資料", text_align="center"))
            
            for row in rows:
                item = ft.Container(
                    content=ft.Row([
                        ft.Column([
                            ft.Text(f"工號: {row['emp_id']}", weight="bold"),
                            ft.Text(f"{row['time']} ({row['note']})", size=12, color=C_GREY),
                        ]),
                        ft.Text(f"${row['amount']}", size=20, color=C_ORANGE, weight="bold"),
                    ], alignment="spaceBetween"),
                    padding=10,
                    bgcolor=C_WHITE,
                    border=ft.border.only(left=ft.BorderSide(5, C_GREEN)),
                    border_radius=10
                )
                lv_list.controls.append(item)
            page.update()

        # 匯出與複製
        def copy_text(e):
            rows = get_records()
            if not rows:
                return
            s = "ID,工號,金額,備註,時間\n"
            for r in rows:
                s += f"{r['id']},{r['emp_id']},{r['amount']},{r['note']},{r['time']}\n"
            page.set_clipboard(s)
            page.show_snack_bar(ft.SnackBar(content=ft.Text("已複製到剪貼簿")))

        def save_csv(e):
            filename = f"FLEX_{datetime.datetime.now().strftime('%m%d_%H%M')}.csv"
            file_picker.save_file(dialog_title="儲存 CSV", file_name=filename)

        def on_file_saved(e: ft.FilePickerResultEvent):
            if e.path:
                try:
                    rows = get_records()
                    with open(e.path, "w", encoding="utf-8") as f:
                        f.write("\ufeff") # BOM
                        f.write("ID,工號,金額,備註,時間\n")
                        for r in rows:
                            f.write(f"{r['id']},{r['emp_id']},{r['amount']},{r['note']},{r['time']}\n")
                    page.show_snack_bar(ft.SnackBar(content=ft.Text("匯出成功")))
                except:
                    page.show_snack_bar(ft.SnackBar(content=ft.Text("匯出失敗")))

        file_picker.on_result = on_file_saved

        # --- 6. 版面組裝 ---

        # 1. 掃描頁
        page_scan = ft.Column([
            header,
            ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Container(
                        padding=20, bgcolor=C_WHITE, border_radius=15,
                        content=ft.Column([
                            ft.Text("一般消費", weight="bold", color=C_GREEN),
                            ft.Container(height=10),
                            ft.Row([
                                txt_scan_emp,
                                # 這裡就是你要的「按鈕開啟鍵盤」
                                ft.IconButton(icon="keyboard", icon_color=C_GREEN, on_click=manual_focus_scan)
                            ]),
                            ft.Container(height=10),
                            txt_scan_amt,
                            ft.Container(height=20),
                            ft.ElevatedButton("確認 (Enter)", bgcolor=C_ORANGE, color=C_WHITE, width=1000, on_click=scan_amt_done)
                        ])
                    ),
                    ft.Container(height=20),
                    lbl_msg
                ])
            )
        ])

        # 2. 午餐頁
        page_lunch = ft.Column([
            header,
            ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Container(
                        padding=20, bgcolor=C_WHITE, border_radius=15,
                        content=ft.Column([
                            ft.Text("午餐模式 (固定$60)", weight="bold", color=C_ORANGE),
                            ft.Container(height=10),
                            ft.Row([
                                txt_lunch_emp,
                                ft.IconButton(icon="keyboard", icon_color=C_GREEN, on_click=manual_focus_lunch)
                            ]),
                            ft.Container(height=10),
                            txt_lunch_amt,
                            ft.Container(height=20),
                            ft.Text("掃描後直接確認", size=12, color=C_GREY),
                            ft.ElevatedButton("手動確認", bgcolor=C_ORANGE, color=C_WHITE, width=1000, on_click=lunch_emp_done)
                        ])
                    ),
                    ft.Container(height=20),
                    lbl_msg
                ])
            )
        ])

        # 3. 紀錄頁
        page_hist = ft.Column([
            ft.Container(padding=15, bgcolor=C_GREEN, content=ft.Row([
                ft.Text("歷史紀錄", color=C_WHITE, weight="bold"),
                ft.IconButton(icon="refresh", icon_color=C_WHITE, on_click=lambda e: update_history())
            ], alignment="spaceBetween")),
            lv_list
        ])

        # 4. 匯出頁
        page_export = ft.Column([
            ft.Container(padding=15, bgcolor=C_GREEN, content=ft.Text("資料匯出", color=C_WHITE, weight="bold")),
            ft.Container(
                padding=20,
                content=ft.Column([
                    ft.ElevatedButton("方法 1: 匯出 CSV 檔案", icon="file_download", width=1000, on_click=save_csv),
                    ft.Container(height=20),
                    ft.ElevatedButton("方法 2: 複製到剪貼簿", icon="copy", width=1000, on_click=copy_text),
                ])
            )
        ])

        # 分頁切換邏輯
        def on_tab_change(e):
            idx = e.control.selected_index
            if idx == 0:
                txt_scan_emp.focus()
            elif idx == 1:
                txt_lunch_emp.focus()
            elif idx == 2:
                update_history()

        tabs = ft.Tabs(
            selected_index=0,
            on_change=on_tab_change,
            tabs=[
                ft.Tab(text="掃描", icon="qr_code", content=page_scan),
                ft.Tab(text="午餐", icon="restaurant", content=page_lunch),
                ft.Tab(text="紀錄", icon="history", content=page_hist),
                ft.Tab(text="匯出", icon="settings", content=page_export),
            ],
            expand=True
        )

        # 堆疊層 (主要介面 + 遮罩 + 隱藏按鈕)
        page.add(
            ft.Stack(
                [
                    tabs,
                    overlay,
                    dummy_button 
                ],
                expand=True
            )
        )
        
        update_history()

    except Exception as e:
        page.add(ft.Text(f"Error: {e}", color="red"))

ft.app(target=main)
