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
        
        # 定義儲存的 Key
        STORAGE_KEY = "flexium_scan_records"

        # --- 2. 資料存取邏輯 (改用 client_storage) ---
        
        def get_all_records():
            # 從手機內部儲存讀取列表，如果沒有則回傳空列表
            data = page.client_storage.get(STORAGE_KEY)
            if data is None:
                return []
            return data

        def add_record(emp_id, amount):
            records = get_all_records()
            new_record = {
                "id": len(records) + 1,
                "emp_id": emp_id,
                "amount": int(amount),
                "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            # 新資料插入在最前面 (顯示時會在最上面)
            records.insert(0, new_record)
            page.client_storage.set(STORAGE_KEY, records)
            return new_record

        def clear_all_records():
            page.client_storage.remove(STORAGE_KEY)
            load_history()

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

        def real_save_to_storage(e):
            confirm_overlay.visible = False
            
            emp_id = txt_emp_id.value.strip()
            amount_str = txt_amount.value.strip()
            
            try:
                # 儲存到 client_storage
                add_record(emp_id, amount_str)

                lbl_last_action.value = f"✅ 已儲存: {emp_id} - ${amount_str}"
                lbl_last_action.color = FLEX_GREEN
                
                txt_emp_id.value = ""
                txt_amount.value = ""
                txt_emp_id.focus()
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
                
                ft.Text("確認金額:", size=14, color="grey"),
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
            if not amount_str or not amount_str.isdigit():
                lbl_last_action.value = f"❌ 錯誤：金額異常"
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
            rows = get_all_records()

            if not rows:
                lv_history.controls.append(ft.Text("尚無資料", color="grey", text_align="center"))
            
            for row in rows:
                card = ft.Container(
                    content=ft.Row([
                        ft.Column([
                            ft.Text(f"工號: {row['emp_id']}", weight="bold", size=16, color="black"),
                            ft.Text(f"{row['created_at']}", size=12, color="grey"),
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

        # --- 6. 匯出邏輯 (包含 CSV 存檔 + 複製到剪貼簿) ---

        def generate_csv_string():
            rows = get_all_records()
            if not rows:
                return None
            
            output = io.StringIO()
            # 寫入 BOM 防止 Excel 亂碼
            output.write('\ufeff') 
            writer = csv.writer(output)
            writer.writerow(['ID', '工號', '金額', '時間'])
            for row in rows:
                writer.writerow([row['id'], row['emp_id'], row['amount'], row['created_at']])
            return output.getvalue()

        def copy_to_clipboard(e):
            csv_str = generate_csv_string()
            if csv_str:
                page.set_clipboard(csv_str)
                page.show_snack_bar(ft.SnackBar(content=ft.Text("✅ 資料已複製到剪貼簿！"), bgcolor=FLEX_GREEN))
            else:
                page.show_snack_bar(ft.SnackBar(content=ft.Text("❌ 無資料可複製"), bgcolor="red"))

        def export_data(e):
            rows = get_all_records()
            if not rows:
                page.show_snack_bar(ft.SnackBar(content=ft.Text("沒有資料可以匯出"), bgcolor="red"))
                return
            
            filename = f"FLEX_Export_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.csv"
            file_picker.save_file(dialog_title="匯出 CSV", file_name=filename)

        def on_save_file_result(e: ft.FilePickerResultEvent):
            if e.path:
                try:
                    csv_content = generate_csv_string()
                    with open(e.path, mode='w', encoding='utf-8') as f:
                        f.write(csv_content)
                    
                    page.show_snack_bar(ft.SnackBar(content=ft.Text(f"匯出成功！"), bgcolor=FLEX_GREEN))
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
                            ft.Text("歷史紀錄 (本機儲存)", size=18, color="white", weight="bold"),
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
                        content=ft.Column([
                            # 匯出檔案按鈕
                            ft.Container(
                                bgcolor="white",
                                padding=20,
                                border_radius=10,
                                shadow=ft.BoxShadow(blur_radius=5, color="grey"),
                                content=ft.Row([
                                    ft.Icon(name="file_download", color=FLEX_GREEN, size=30),
                                    ft.Column([
                                        ft.Text("方法 1: 匯出 CSV 檔案", size=16, weight="bold"),
                                        ft.Text("儲存至手機資料夾", size=12, color="grey"),
                                    ], expand=True),
                                    ft.IconButton(icon="arrow_forward_ios", icon_color=FLEX_ORANGE, on_click=export_data)
                                ])
                            ),
                            ft.Container(height=20),
                            # 複製剪貼簿按鈕 (備援方案)
                            ft.Container(
                                bgcolor="white",
                                padding=20,
                                border_radius=10,
                                shadow=ft.BoxShadow(blur_radius=5, color="grey"),
                                content=ft.Row([
                                    ft.Icon(name="copy", color="#007bff", size=30),
                                    ft.Column([
                                        ft.Text("方法 2: 複製全部資料", size=16, weight="bold"),
                                        ft.Text("複製文字，可直接貼到 Line/Email", size=12, color="grey"),
                                    ], expand=True),
                                    ft.IconButton(icon="content_copy", icon_color=FLEX_ORANGE, on_click=copy_to_clipboard)
                                ])
                            )
                        ])
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
