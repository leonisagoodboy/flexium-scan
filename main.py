import flet as ft
import datetime
import csv
import traceback
import io

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
        
        STORAGE_KEY = "flexium_scan_records"

        # --- 2. 資料存取邏輯 (Client Storage) ---
        
        def get_all_records():
            data = page.client_storage.get(STORAGE_KEY)
            if data is None:
                return []
            return data

        def add_record(emp_id, amount, note=""):
            records = get_all_records()
            new_record = {
                "id": len(records) + 1,
                "emp_id": emp_id,
                "amount": int(amount),
                "note": note, # 新增備註欄位 (區分午餐或一般)
                "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            records.insert(0, new_record)
            page.client_storage.set(STORAGE_KEY, records)
            return new_record

        def clear_all_records():
            page.client_storage.remove(STORAGE_KEY)
            load_history()

        # --- 3. UI 元件宣告 ---

        # 共用標題
        def get_header():
            return ft.Container(
                content=ft.Row([
                    ft.Icon(name="qr_code_scanner", color="white", size=24),
                    ft.Text("FLEXium 掃描作業", size=18, weight="bold", color="white")
                ], alignment="center"),
                bgcolor=FLEX_GREEN,
                padding=12,
                shadow=ft.BoxShadow(blur_radius=5, color="grey")
            )

        # 狀態文字
        lbl_last_action = ft.Text("等待掃描...", size=16, color="grey", weight="bold")

        # --- [A] 一般掃描頁面元件 ---
        txt_scan_emp = ft.TextField(
            label="員工工號",
            hint_text="請掃描...",
            prefix_icon="badge",
            text_size=18,
            bgcolor="white",
            border_color=FLEX_GREEN,
            focused_border_color=FLEX_ORANGE,
            border_radius=10,
            autofocus=True,
            expand=True # 讓它佔滿剩餘空間
        )
        
        txt_scan_amount = ft.TextField(
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

        # --- [B] 午餐專用頁面元件 ---
        txt_lunch_emp = ft.TextField(
            label="員工工號 (午餐)",
            hint_text="掃描即確認...",
            prefix_icon="badge",
            text_size=18,
            bgcolor="white",
            border_color=FLEX_GREEN,
            focused_border_color=FLEX_ORANGE,
            border_radius=10,
            autofocus=True, # 切換到此頁籤時可能會自動聚焦
            expand=True
        )

        txt_lunch_amount = ft.TextField(
            label="固定金額",
            value="60",
            read_only=True, # 唯讀
            prefix_icon="restaurant",
            suffix_text="元",
            text_size=18,
            bgcolor="#E0E0E0", # 灰色底代表唯讀
            border_color=FLEX_GREEN,
            border_radius=10
        )

        lv_history = ft.ListView(expand=True, spacing=10, padding=20)
        file_picker = ft.FilePicker()
        page.overlay.append(file_picker)

        # --- 4. 確認視窗與邏輯 ---
        
        dlg_date_text = ft.Text(size=20, weight="bold")
        dlg_emp_text = ft.Text(size=20, weight="bold", color="black")
        dlg_amt_text = ft.Text(size=30, weight="bold", color=FLEX_ORANGE)
        dlg_note_text = ft.Text(size=16, color="grey") # 顯示這是午餐還是一般

        # 暫存當前要寫入的資料
        current_confirm_data = {} 

        def close_keyboard():
            # 強制讓所有輸入框失去焦點，以隱藏手機鍵盤
            txt_scan_emp.blur()
            txt_scan_amount.blur()
            txt_lunch_emp.blur()
            page.update()

        def close_overlay(e):
            confirm_overlay.visible = False
            # 關閉後重新聚焦回原本的輸入框
            if current_confirm_data.get("type") == "lunch":
                txt_lunch_emp.focus()
            else:
                txt_scan_emp.focus()
            page.update()

        def real_save_to_storage(e):
            confirm_overlay.visible = False
            
            emp_id = current_confirm_data.get("emp_id")
            amount = current_confirm_data.get("amount")
            note = current_confirm_data.get("note", "")
            
            try:
                add_record(emp_id, amount, note)

                lbl_last_action.value = f"✅ 已儲存: {emp_id} - ${amount} ({note})"
                lbl_last_action.color = FLEX_GREEN
                
                # 清空輸入框
                txt_scan_emp.value = ""
                txt_scan_amount.value = ""
                txt_lunch_emp.value = ""
                
                # 重新聚焦
                if note == "午餐":
                    txt_lunch_emp.focus()
                else:
                    txt_scan_emp.focus()
                    
                page.update()
                load_history()

            except Exception as err:
                lbl_last_action.value = f"❌ 儲存錯誤: {err}"
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
                
                ft.Row([
                    ft.Text("確認金額:", size=14, color="grey"),
                    dlg_note_text # 顯示(午餐)字樣
                ]),
                dlg_amt_text,
                
                ft.Divider(height=30, color="transparent"),
                
                ft.Row([
                    ft.OutlinedButton("取消", on_click=close_overlay, width=100),
                    ft.ElevatedButton("確認寫入", on_click=real_save_to_storage, 
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

        # --- 觸發確認視窗 (通用) ---
        def show_confirm_dialog(emp_id, amount, note):
            # 1. 先收起鍵盤 (解決需求 2)
            close_keyboard()

            if not emp_id:
                lbl_last_action.value = "❌ 錯誤：工號是空的！"
                lbl_last_action.color = "red"
                page.update()
                return
            
            # 記錄當前資料
            current_confirm_data["emp_id"] = emp_id
            current_confirm_data["amount"] = amount
            current_confirm_data["note"] = note
            current_confirm_data["type"] = "lunch" if note == "午餐" else "normal"

            # 更新視窗內容
            dlg_date_text.value = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            dlg_emp_text.value = emp_id
            dlg_amt_text.value = f"${amount}"
            dlg_note_text.value = f"({note})" if note else ""

            lbl_last_action.value = "等待確認..."
            lbl_last_action.color = "blue"
            confirm_overlay.visible = True
            page.update()

        # [A] 一般掃描流程
        def on_scan_emp_submit(e):
            if txt_scan_emp.value:
                txt_scan_amount.focus()
                
        def on_scan_amount_submit(e):
            if txt_scan_amount.value:
                if not txt_scan_amount.value.isdigit():
                    lbl_last_action.value = "❌ 金額必須是數字"
                    page.update()
                    return
                show_confirm_dialog(txt_scan_emp.value.strip(), txt_scan_amount.value.strip(), "一般")

        # [B] 午餐掃描流程
        def on_lunch_emp_submit(e):
            if txt_lunch_emp.value:
                # 午餐金額固定 60，直接跳出確認
                show_confirm_dialog(txt_lunch_emp.value.strip(), "60", "午餐")

        txt_scan_emp.on_submit = on_scan_emp_submit
        txt_scan_amount.on_submit = on_scan_amount_submit
        txt_lunch_emp.on_submit = on_lunch_emp_submit

        # 解決需求 1：手動開啟鍵盤按鈕 (因為預設掃描可能不想跳鍵盤)
        # 點擊按鈕後，強制聚焦輸入框
        def focus_scan_emp(e):
            txt_scan_emp.focus()
        
        def focus_lunch_emp(e):
            txt_lunch_emp.focus()

        # 歷史紀錄顯示
        def load_history():
            lv_history.controls.clear()
            rows = get_all_records()

            if not rows:
                lv_history.controls.append(ft.Text("尚無資料", color="grey", text_align="center"))
            
            for row in rows:
                note_str = f"({row.get('note')})" if row.get('note') else ""
                card = ft.Container(
                    content=ft.Row([
                        ft.Column([
                            ft.Text(f"工號: {row['emp_id']}", weight="bold", size=16, color="black"),
                            ft.Text(f"{row['created_at']} {note_str}", size=12, color="grey"),
                        ]),
                        ft.Text(f"${row['amount']}", size=20, color=FLEX_ORANGE, weight="bold"),
                    ], alignment="spaceBetween"),
                    padding=15,
                    bgcolor="white",
                    border=ft.border.only(left=ft.BorderSide(5, FLEX_GREEN)),
                    border_radius=ft.border_radius.only(top_right=10, bottom_right=10),
                    shadow=ft.BoxShadow(blur_radius=3, color="grey")
                )
                lv_history.controls.append(card)
            page.update()

        # --- 匯出功能 ---
        def generate_csv_string():
            rows = get_all_records()
            if not rows:
                return None
            output = io.StringIO()
            output.write('\ufeff') 
            writer = csv.writer(output)
            writer.writerow(['ID', '工號', '金額', '備註', '時間'])
            for row in rows:
                writer.writerow([row['id'], row['emp_id'], row['amount'], row.get('note', ''), row['created_at']])
            return output.getvalue()

        def copy_to_clipboard(e):
            csv_str = generate_csv_string()
            if csv_str:
                page.set_clipboard(csv_str)
                page.show_snack_bar(ft.SnackBar(content=ft.Text("✅ 資料已複製！"), bgcolor=FLEX_GREEN))
            else:
                page.show_snack_bar(ft.SnackBar(content=ft.Text("❌ 無資料"), bgcolor="red"))

        def export_data(e):
            if not get_all_records():
                page.show_snack_bar(ft.SnackBar(content=ft.Text("無資料"), bgcolor="red"))
                return
            filename = f"FLEX_Export_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.csv"
            file_picker.save_file(dialog_title="匯出 CSV", file_name=filename)

        def on_save_file_result(e: ft.FilePickerResultEvent):
            if e.path:
                try:
                    with open(e.path, mode='w', encoding='utf-8') as f:
                        f.write(generate_csv_string())
                    page.show_snack_bar(ft.SnackBar(content=ft.Text(f"匯出成功！"), bgcolor=FLEX_GREEN))
                except Exception as err:
                    page.show_snack_bar(ft.SnackBar(content=ft.Text(f"匯出失敗: {err}"), bgcolor="red"))

        file_picker.on_result = on_save_file_result

        # --- 版面配置 ---

        # 1. 掃描頁籤
        tab_scan_content = ft.Column([
            get_header(),
            ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Container(
                        padding=25,
                        bgcolor="white",
                        border_radius=15,
                        shadow=ft.BoxShadow(blur_radius=10, color="grey"),
                        content=ft.Column([
                            ft.Text("一般消費", size=16, weight="bold", color=FLEX_GREEN),
                            ft.Container(height=10),
                            # 工號輸入框 + 鍵盤按鈕 Row
                            ft.Row([
                                txt_scan_emp,
                                ft.IconButton(
                                    icon=ft.icons.KEYBOARD, 
                                    icon_color=FLEX_GREEN,
                                    tooltip="開啟鍵盤",
                                    on_click=focus_scan_emp
                                )
                            ]),
                            ft.Container(height=10),
                            txt_scan_amount,
                            ft.Container(height=20),
                            ft.ElevatedButton(
                                "確認 (Enter)",
                                icon="arrow_forward",
                                style=ft.ButtonStyle(bgcolor=FLEX_ORANGE, color="white", shape=ft.RoundedRectangleBorder(radius=10), padding=20),
                                width=1000,
                                on_click=lambda e: on_scan_amount_submit(e) 
                            )
                        ])
                    ),
                    ft.Container(height=20),
                    lbl_last_action 
                ])
            )
        ])

        # 2. 午餐頁籤 (新功能)
        tab_lunch_content = ft.Column([
            get_header(),
            ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Container(
                        padding=25,
                        bgcolor="white",
                        border_radius=15,
                        shadow=ft.BoxShadow(blur_radius=10, color="grey"),
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(name="restaurant", color=FLEX_ORANGE),
                                ft.Text("午餐模式 (固定$60)", size=16, weight="bold", color=FLEX_ORANGE),
                            ]),
                            ft.Container(height=10),
                            # 工號輸入框 + 鍵盤按鈕
                            ft.Row([
                                txt_lunch_emp,
                                ft.IconButton(
                                    icon=ft.icons.KEYBOARD, 
                                    icon_color=FLEX_GREEN, 
                                    tooltip="開啟鍵盤",
                                    on_click=focus_lunch_emp
                                )
                            ]),
                            ft.Container(height=10),
                            txt_lunch_amount, # 唯讀的60元
                            ft.Container(height=20),
                            ft.Text("💡 掃描工號後將直接跳出確認視窗", size=12, color="grey"),
                            ft.ElevatedButton(
                                "手動確認",
                                icon="check",
                                style=ft.ButtonStyle(bgcolor=FLEX_ORANGE, color="white", shape=ft.RoundedRectangleBorder(radius=10), padding=20),
                                width=1000,
                                on_click=lambda e: on_lunch_emp_submit(e)
                            )
                        ])
                    ),
                    ft.Container(height=20),
                    lbl_last_action 
                ])
            )
        ])

        # 3. 紀錄與匯出頁籤 (略作簡化，邏輯不變)
        tab_history_content = ft.Column([
            ft.Container(
                padding=15, bgcolor=FLEX_GREEN,
                content=ft.Row([ft.Text("歷史紀錄", size=18, color="white", weight="bold"), ft.IconButton(icon="refresh", icon_color="white", on_click=lambda e: load_history())], alignment="spaceBetween")
            ),
            lv_history
        ])

        tab_export_content = ft.Column([
            ft.Container(padding=15, bgcolor=FLEX_GREEN, alignment=ft.alignment.center, content=ft.Text("資料管理", size=18, color="white", weight="bold")),
            ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Container(
                        bgcolor="white", padding=20, border_radius=10, shadow=ft.BoxShadow(blur_radius=5, color="grey"),
                        content=ft.Row([
                            ft.Icon(name="file_download", color=FLEX_GREEN, size=30),
                            ft.Column([ft.Text("方法 1: 匯出 CSV", size=16, weight="bold"), ft.Text("儲存至手機", size=12, color="grey")], expand=True),
                            ft.IconButton(icon="arrow_forward_ios", icon_color=FLEX_ORANGE, on_click=export_data)
                        ])
                    ),
                    ft.Container(height=20),
                    ft.Container(
                        bgcolor="white", padding=20, border_radius=10, shadow=ft.BoxShadow(blur_radius=5, color="grey"),
                        content=ft.Row([
                            ft.Icon(name="copy", color="#007bff", size=30),
                            ft.Column([ft.Text("方法 2: 複製文字", size=16, weight="bold"), ft.Text("貼上至 Line/Email", size=12, color="grey")], expand=True),
                            ft.IconButton(icon="content_copy", icon_color=FLEX_ORANGE, on_click=copy_to_clipboard)
                        ])
                    )
                ])
            )
        ])

        # 主畫面 Tabs
        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            indicator_color=FLEX_ORANGE,
            label_color=FLEX_GREEN,
            unselected_label_color="grey",
            divider_color="transparent",
            tabs=[
                ft.Tab(text="掃描", icon="qr_code_scanner", content=tab_scan_content),
                ft.Tab(text="午餐", icon="restaurant", content=tab_lunch_content),
                ft.Tab(text="紀錄", icon="history", content=tab_history_content),
                ft.Tab(text="匯出", icon="settings", content=tab_export_content),
            ],
            expand=True,
            on_change=lambda e: focus_scan_emp(e) if e.control.selected_index == 0 else (focus_lunch_emp(e) if e.control.selected_index == 1 else None)
        )

        page.add(
            ft.Stack(
                [tabs, confirm_overlay],
                expand=True 
            )
        )
        
        load_history()

    except Exception as e:
        page.add(ft.Text(f"嚴重錯誤: {e}", color="red", size=20))
        page.add(ft.Text(traceback.format_exc(), color="red"))
        page.update()

ft.app(target=main)
