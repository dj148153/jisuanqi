import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import sqlite3
from datetime import datetime
import json
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.font_manager as fm

import traceback
import os

# 配置中文字体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'KaiTi', 'FangSong']
plt.rcParams['axes.unicode_minus'] = False


class DataManager:
    """数据库管理类"""

    def __init__(self):
        self.conn = sqlite3.connect('calc_history.db')
        self._create_table()

    def _create_table(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS calculations(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    page TEXT NOT NULL,
                    result REAL NOT NULL,
                    parameters TEXT NOT NULL
                )""")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON calculations(timestamp)")

    def save_record(self, page_name, result, params):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.conn:
            self.conn.execute("""
                INSERT INTO calculations (timestamp, page, result, parameters)
                VALUES (?, ?, ?, ?)""",
                              (timestamp, page_name, result, json.dumps(params)))

    def get_records(self, start_time=None, end_time=None, page_filter=None, limit=None):
        query = "SELECT id, timestamp, page, result, parameters FROM calculations"
        conditions = []
        params = []

        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time)
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time)
        if page_filter:
            conditions.append("page = ?")
            params.append(page_filter)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY timestamp DESC"

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def delete_record(self, record_id):
        with self.conn:
            self.conn.execute("DELETE FROM calculations WHERE id = ?", (record_id,))

    def get_available_timestamps(self):
        """获取所有有效时间戳"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT timestamp FROM calculations ORDER BY timestamp")
        return [row[0] for row in cursor.fetchall()]


class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("工业数据分析系统 v2.0")
        self.geometry("1200x800")
        self.data_mgr = DataManager()
        self._create_widgets()
        self._create_menu()

    def _create_widgets(self):
        self.notebook = ttk.Notebook(self)

        self.pages = {
            "sum": CalculationPage(self.notebook, self, "参数求和", 6, self._sum_calculation),
            "product": CalculationPage(self.notebook, self, "参数求积", 6, self._product_calculation),
            "final": FinalCalculationPage(self.notebook, self),
            "history": HistoryPage(self.notebook, self.data_mgr, self.refresh_time_range)
        }

        for key, text in [("sum", "求和计算"), ("product", "求积计算"),
                          ("final", "综合计算"), ("history", "历史分析")]:
            self.notebook.add(self.pages[key], text=text)

        self.notebook.pack(expand=True, fill="both")

    def _create_menu(self):
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="导出CSV", command=lambda: self.export_data('csv'))
        file_menu.add_command(label="导出Excel", command=lambda: self.export_data('excel'))
        menubar.add_cascade(label="文件", menu=file_menu)
        self.config(menu=menubar)

    def _sum_calculation(self, params):
        return sum(params)

    def _product_calculation(self, params):
        product = 1
        for num in params:
            product *= num
        return product

    def export_data(self, format_type):
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension='.csv' if format_type == 'csv' else '.xlsx',
                filetypes=[(f"{format_type.upper()}文件", f"*.{format_type}")]
            )
            print(f"DEBUG: 导出路径 -> {file_path}")

            if not file_path:
                print("DEBUG: 用户取消导出")
                return

            # 获取数据
            records = self.data_mgr.get_records()
            print(f"DEBUG: 获取到 {len(records)} 条记录")

            if not records:
                messagebox.showwarning("警告", "数据库中没有可导出的数据")
                return

            # 转换数据
            data = []
            for r in records:
                try:
                    params = json.loads(r[4])
                    param_str = ", ".join(f"{k}={v}" for k, v in params.items()) if isinstance(params,
                                                                                               dict) else ", ".join(
                        map(str, params))
                    data.append({
                        '时间戳': r[1],
                        '页面': r[2],
                        '结果': r[3],
                        '参数': param_str
                    })
                except json.JSONDecodeError:
                    print(f"WARN: 参数解析失败，记录ID {r[0]}")
                    continue

            df = pd.DataFrame(data)
            print("DEBUG: 数据预览：\n", df.head())

            # 写入文件
            if format_type == 'csv':
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
            else:
                df.to_excel(file_path, index=False, engine='openpyxl')

            print(f"DEBUG: 文件已保存，大小：{os.path.getsize(file_path)} 字节")
            messagebox.showinfo("成功", f"数据已保存至：\n{file_path}")

        except PermissionError:
            messagebox.showerror("错误", "文件被其他程序占用，请关闭后重试")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败：{str(e)}")
            print(f"ERROR: {traceback.format_exc()}")
    # def export_data(self, format_type):
    #     file_path = filedialog.asksaveasfilename(
    #         defaultextension='.csv' if format_type == 'csv' else '.xlsx',
    #         filetypes=[(f"{format_type.upper()}文件", f"*.{format_type}")]
    #     )
    #     if not file_path: return
    #
    #     try:
    #         # 获取完整数据
    #         records = self.data_mgr.get_records()
    #         data = [{
    #             '时间戳': r[1],
    #             '页面': r[2],
    #             '结果': r[3],
    #             '参数': self._parse_params(r[4])
    #         } for r in records]
    #
    #         df = pd.DataFrame(data)
    #
    #         if format_type == 'csv':
    #             df.to_csv(file_path, index=False, encoding='utf-8-sig')
    #         else:
    #             df.to_excel(file_path, index=False, engine='openpyxl')
    #
    #         messagebox.showinfo("导出成功", f"数据已保存至：\n{file_path}")
    #     except Exception as e:
    #         messagebox.showerror("导出失败", f"错误信息：{str(e)}")

    def _parse_params(self, param_json):
        params = json.loads(param_json)
        if isinstance(params, dict):
            return ", ".join(f"{k}={v}" for k, v in params.items())
        return ", ".join(map(str, params))

    def refresh_time_range(self):
        """全局刷新时间范围"""
        if hasattr(self.pages['history'], 'update_time_range'):
            self.pages['history'].update_time_range()


class CalculationPage(ttk.Frame):
    def __init__(self, parent, controller, title, num_params, calc_func):
        super().__init__(parent)
        self.controller = controller
        self.page_title = title
        self.calc_func = calc_func
        self._create_interface(num_params)

    def _create_interface(self, num_params):
        self.entries = []
        for i in range(num_params):
            row = i // 2
            col = (i % 2) * 2
            ttk.Label(self, text=f"参数 {i + 1}:").grid(row=row, column=col, padx=5, pady=5)
            entry = ttk.Entry(self)
            entry.grid(row=row, column=col + 1, padx=5, pady=5)
            self.entries.append(entry)

        control_frame = ttk.Frame(self)
        control_frame.grid(row=(num_params + 1) // 2, column=0, columnspan=4, pady=10)
        self.save_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(control_frame, text="自动保存", variable=self.save_var).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="执行计算", command=self._execute).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="历史记录", command=self.show_history).pack(side=tk.LEFT, padx=5)

        self.result_var = tk.StringVar(value="等待计算...")
        ttk.Label(self, textvariable=self.result_var).grid(row=(num_params + 1) // 2 + 1, column=0, columnspan=4)

    def _execute(self):
        try:
            params = [float(ent.get()) for ent in self.entries]
            result = self.calc_func(params)
            self.result_var.set(f"计算结果：{result:.4f}")

            if self.save_var.get():
                self.controller.data_mgr.save_record(self.page_title, result, params)
                self.controller.refresh_time_range()
        except ValueError:
            messagebox.showerror("输入错误", "请检查所有参数为有效数字")

    def show_history(self):
        HistoryDialog(self, self.page_title, self.controller.refresh_time_range)


class FinalCalculationPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._create_interface()

    def _create_interface(self):
        input_frame = ttk.Frame(self)
        input_frame.pack(pady=10)

        ttk.Label(input_frame, text="权重系数 α:").grid(row=0, column=0, padx=5)
        self.alpha_ent = ttk.Entry(input_frame)
        self.alpha_ent.grid(row=0, column=1, padx=5)

        ttk.Label(input_frame, text="权重系数 β:").grid(row=1, column=0, padx=5)
        self.beta_ent = ttk.Entry(input_frame)
        self.beta_ent.grid(row=1, column=1, padx=5)

        control_frame = ttk.Frame(self)
        control_frame.pack(pady=10)
        self.save_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(control_frame, text="自动保存", variable=self.save_var).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="计算", command=self._execute).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="历史", command=self.show_history).pack(side=tk.LEFT, padx=5)

        self.result_var = tk.StringVar(value="等待计算...")
        ttk.Label(self, textvariable=self.result_var).pack()

    def _execute(self):
        try:
            alpha = float(self.alpha_ent.get())
            beta = float(self.beta_ent.get())

            sum_data = self.controller.data_mgr.get_records(page_filter="参数求和", limit=1)
            product_data = self.controller.data_mgr.get_records(page_filter="参数求积", limit=1)

            if not sum_data or not product_data:
                messagebox.showwarning("警告", "请先完成前序计算")
                return

            result = (alpha * sum_data[0][3]) + (beta * product_data[0][3])
            self.result_var.set(f"综合结果：{result:.4f}")

            if self.save_var.get():
                self.controller.data_mgr.save_record("综合计算", result, {"alpha": alpha, "beta": beta})
                self.controller.refresh_time_range()
        except ValueError:
            messagebox.showerror("输入错误", "请输入有效数值")

    def show_history(self):
        HistoryDialog(self, "综合计算", self.controller.refresh_time_range)


class HistoryPage(ttk.Frame):
    def __init__(self, parent, data_mgr, refresh_callback):
        super().__init__(parent)
        self.data_mgr = data_mgr
        self.refresh_callback = refresh_callback
        self._create_interface()
        self.update_time_range()

    def _create_interface(self):
        # 时间选择组件
        time_frame = ttk.Frame(self)
        time_frame.pack(pady=10, fill=tk.X)

        ttk.Label(time_frame, text="起始时间:").grid(row=0, column=0, padx=5)
        self.start_combo = ttk.Combobox(time_frame, width=20, state="readonly")
        self.start_combo.grid(row=0, column=1, padx=5)

        ttk.Label(time_frame, text="结束时间:").grid(row=0, column=2, padx=5)
        self.end_combo = ttk.Combobox(time_frame, width=20, state="readonly")
        self.end_combo.grid(row=0, column=3, padx=5)

        ttk.Button(time_frame, text="筛选", command=self._update_chart).grid(row=0, column=4, padx=10)
        ttk.Button(time_frame, text="刷新", command=self.update_time_range).grid(row=0, column=5, padx=5)

        # 图表区域
        self.figure = plt.Figure(figsize=(10, 5), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, self)
        self.canvas.get_tk_widget().pack(expand=True, fill=tk.BOTH)

    def update_time_range(self):
        """更新时间选择范围"""
        timestamps = self.data_mgr.get_available_timestamps()
        if timestamps:
            self.start_combo['values'] = timestamps
            self.end_combo['values'] = timestamps
            self.start_combo.set(timestamps[0])
            self.end_combo.set(timestamps[-1])
        else:
            self.start_combo.set("")
            self.end_combo.set("")

    def _update_chart(self):
        self.ax.clear()
        try:
            start_time = self.start_combo.get()
            end_time = self.end_combo.get()

            records = self.data_mgr.get_records(start_time, end_time)
            if not records:
                messagebox.showinfo("提示", "选定时间段无数据")
                return

            data = {}
            for r in records:
                key = r[2]
                if key not in data:
                    data[key] = {'x': [], 'y': []}
                data[key]['x'].append(datetime.strptime(r[1], "%Y-%m-%d %H:%M:%S"))
                data[key]['y'].append(r[3])

            for name, values in data.items():
                self.ax.plot(values['x'], values['y'], marker='o', linestyle='-', label=name)

            self.ax.set_title("历史数据趋势分析", fontsize=14)
            self.ax.set_xlabel("时间", fontsize=12)
            self.ax.set_ylabel("结果值", fontsize=12)
            self.ax.legend()
            self.figure.autofmt_xdate()
            self.canvas.draw()
        except Exception as e:
            messagebox.showerror("错误", f"图表生成失败：{str(e)}")


class HistoryDialog(tk.Toplevel):
    def __init__(self, parent, page_name, refresh_callback):
        super().__init__(parent)
        self.title(f"{page_name} - 历史记录")
        self.geometry("800x500")
        self.data_mgr = parent.controller.data_mgr
        self.page_name = page_name
        self.refresh_callback = refresh_callback
        self._create_widgets()

    def _create_widgets(self):
        # 表格组件
        columns = ("ID", "时间", "参数", "结果")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100 if col == "ID" else 200)

        # 滚动条
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # 右键菜单
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="删除记录", command=self._delete_selected)

        # 布局
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 事件绑定
        self.tree.bind("<Button-3>", self._show_context_menu)
        self._load_data()

    def _load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        records = self.data_mgr.get_records(page_filter=self.page_name)
        for r in records:
            params = json.loads(r[4])
            param_str = ", ".join(f"{k}={v}" for k, v in params.items()) if isinstance(params, dict) else ", ".join(
                map(str, params))
            self.tree.insert("", "end", values=(r[0], r[1], param_str, f"{r[3]:.4f}"))

    def _show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def _delete_selected(self):
        selected = self.tree.selection()
        if not selected or not messagebox.askyesno("确认", "确定要删除该记录吗？"):
            return

        try:
            record_id = self.tree.item(selected[0])['values'][0]
            self.data_mgr.delete_record(record_id)
            self._load_data()
            self.refresh_callback()
            messagebox.showinfo("成功", "记录已删除")
        except Exception as e:
            messagebox.showerror("错误", f"删除失败：{str(e)}")


if __name__ == "__main__":
    app = MainApplication()
    app.mainloop()


# import tkinter as tk
# from tkinter import ttk, messagebox, filedialog, simpledialog
# import sqlite3
# from datetime import datetime
# import json
# import pandas as pd
# import matplotlib.pyplot as plt
# from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
# import matplotlib.font_manager as fm
#
# # 配置中文字体
# plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'KaiTi', 'FangSong']
# plt.rcParams['axes.unicode_minus'] = False
#
#
# class DataManager:
#     """数据库管理类"""
#
#     def __init__(self):
#         self.conn = sqlite3.connect('calc_history.db')
#         self._create_table()
#
#     def get_time_range(self):
#         """获取数据库中的最小和最大时间"""
#         cursor = self.conn.cursor()
#         cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM calculations")
#         return cursor.fetchone()
#
#     def _create_table(self):
#         with self.conn:
#             self.conn.execute("""CREATE TABLE IF NOT EXISTS calculations(
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 timestamp DATETIME NOT NULL,
#                 page TEXT NOT NULL,
#                 result REAL NOT NULL,
#                 parameters TEXT NOT NULL)""")
#
#     def save_record(self, page_name, result, params):
#         timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#         with self.conn:
#             self.conn.execute("""INSERT INTO calculations
#                 (timestamp, page, result, parameters)
#                 VALUES (?, ?, ?, ?)""",
#                               (timestamp, page_name, result, json.dumps(params)))
#
#     def get_records(self, start_time=None, end_time=None, page_filter=None, limit=None):
#         query = "SELECT id, timestamp, page, result, parameters FROM calculations"
#         conditions = []
#         params = []
#
#         if start_time:
#             conditions.append("timestamp >= ?")
#             params.append(start_time)
#         if end_time:
#             conditions.append("timestamp <= ?")
#             params.append(end_time)
#         if page_filter:
#             conditions.append("page = ?")
#             params.append(page_filter)
#
#         if conditions:
#             query += " WHERE " + " AND ".join(conditions)
#
#         query += " ORDER BY timestamp DESC"
#
#         if limit is not None:
#             query += " LIMIT ?"
#             params.append(limit)
#
#         cursor = self.conn.cursor()
#         cursor.execute(query, params)
#         return cursor.fetchall()
#
#     def delete_record(self, record_id):
#         with self.conn:
#             self.conn.execute("DELETE FROM calculations WHERE id = ?", (record_id,))
#
#
# class MainApplication(tk.Tk):
#     def __init__(self):
#         super().__init__()
#         self.title("工业数据分析系统")
#         self.geometry("1000x700")
#         self.data_mgr = DataManager()
#         self._create_widgets()
#         self._create_menu()
#
#     def _create_widgets(self):
#         self.notebook = ttk.Notebook(self)
#
#         self.pages = {
#             "sum": CalculationPage(self.notebook, self, "参数求和", 6, self._sum_calculation),
#             "product": CalculationPage(self.notebook, self, "参数求积", 6, self._product_calculation),
#             "final": FinalCalculationPage(self.notebook, self),
#             "history": HistoryPage(self.notebook, self.data_mgr)
#         }
#
#         for key, text in [("sum", "求和计算"), ("product", "求积计算"),
#                           ("final", "综合计算"), ("history", "历史分析")]:
#             self.notebook.add(self.pages[key], text=text)
#
#         self.notebook.pack(expand=True, fill="both")
#
#     def _create_menu(self):
#         menubar = tk.Menu(self)
#         file_menu = tk.Menu(menubar, tearoff=0)
#         file_menu.add_command(label="导出CSV", command=lambda: self.export_data('csv'))
#         file_menu.add_command(label="导出Excel", command=lambda: self.export_data('excel'))
#         menubar.add_cascade(label="文件", menu=file_menu)
#         self.config(menu=menubar)
#
#     def _sum_calculation(self, params):
#         return sum(params)
#
#     def _product_calculation(self, params):
#         return pd.Series(params).product()
#
#     def export_data(self, format_type):
#         file_path = filedialog.asksaveasfilename(
#             defaultextension='.csv' if format_type == 'csv' else '.xlsx',
#             filetypes=[(f"{format_type.upper()}文件", f"*.{format_type}")]
#         )
#         if not file_path: return
#
#         try:
#             df = pd.DataFrame([{
#                 'timestamp': r[1],
#                 'page': r[2],
#                 'result': r[3],
#                 'parameters': self._parse_params(r[4])
#             } for r in self.data_mgr.get_records()])
#
#             if format_type == 'csv':
#                 df.to_csv(file_path, index=False, encoding='utf-8-sig')
#             else:
#                 df.to_excel(file_path, index=False, engine='openpyxl')
#             messagebox.showinfo("导出成功", f"数据已保存至：\n{file_path}")
#         except Exception as e:
#             messagebox.showerror("导出失败", str(e))
#
#     def _parse_params(self, param_json):
#         params = json.loads(param_json)
#         return ", ".join(f"{k}={v}" for k, v in params.items()) if isinstance(params, dict) else ", ".join(
#             map(str, params))
#
#
# class CalculationPage(ttk.Frame):
#     def __init__(self, parent, controller, title, num_params, calc_func):
#         super().__init__(parent)
#         self.controller = controller
#         self.page_title = title
#         self.calc_func = calc_func
#         self._create_interface(num_params)
#
#     def _create_interface(self, num_params):
#         self.entries = [ttk.Entry(self) for _ in range(num_params)]
#         for i, ent in enumerate(self.entries):
#             row, col = divmod(i, 2)
#             ttk.Label(self, text=f"参数 {i + 1}:").grid(row=row, column=col * 2, padx=5, pady=5)
#             ent.grid(row=row, column=col * 2 + 1, padx=5, pady=5)
#
#         control_frame = ttk.Frame(self)
#         control_frame.grid(row=(num_params + 1) // 2, column=0, columnspan=4, pady=10)
#         self.save_var = tk.BooleanVar(value=True)
#         ttk.Checkbutton(control_frame, text="自动保存", variable=self.save_var).pack(side=tk.LEFT, padx=5)
#         ttk.Button(control_frame, text="执行计算", command=self._execute).pack(side=tk.LEFT, padx=5)
#         ttk.Button(control_frame, text="历史记录", command=lambda: HistoryDialog(self, self.page_title)).pack(
#             side=tk.LEFT, padx=5)
#
#         self.result_var = tk.StringVar(value="等待计算...")
#         ttk.Label(self, textvariable=self.result_var).grid(row=(num_params + 1) // 2 + 1, column=0, columnspan=4)
#
#     def _execute(self):
#         try:
#             params = [float(ent.get()) for ent in self.entries]
#             result = self.calc_func(params)
#             self.result_var.set(f"计算结果：{result:.4f}")
#             if self.save_var.get():
#                 self.controller.data_mgr.save_record(self.page_title, result, params)
#         except ValueError:
#             messagebox.showerror("输入错误", "请检查所有参数为有效数字")
#
#
# class FinalCalculationPage(ttk.Frame):
#     def __init__(self, parent, controller):
#         super().__init__(parent)
#         self.controller = controller
#         self._create_interface()
#
#     def _create_interface(self):
#         input_frame = ttk.Frame(self)
#         input_frame.pack(pady=10)
#         ttk.Label(input_frame, text="权重系数 α:").grid(row=0, column=0, padx=5)
#         self.alpha_ent = ttk.Entry(input_frame)
#         self.alpha_ent.grid(row=0, column=1, padx=5)
#         ttk.Label(input_frame, text="权重系数 β:").grid(row=1, column=0, padx=5)
#         self.beta_ent = ttk.Entry(input_frame)
#         self.beta_ent.grid(row=1, column=1, padx=5)
#
#         control_frame = ttk.Frame(self)
#         control_frame.pack(pady=10)
#         self.save_var = tk.BooleanVar(value=True)
#         ttk.Checkbutton(control_frame, text="自动保存", variable=self.save_var).pack(side=tk.LEFT, padx=5)
#         ttk.Button(control_frame, text="计算", command=self._execute).pack(side=tk.LEFT, padx=5)
#         ttk.Button(control_frame, text="历史", command=lambda: HistoryDialog(self, "综合计算")).pack(side=tk.LEFT,
#                                                                                                      padx=5)
#
#         self.result_var = tk.StringVar(value="等待计算...")
#         ttk.Label(self, textvariable=self.result_var).pack()
#
#     def _execute(self):
#         try:
#             alpha = float(self.alpha_ent.get())
#             beta = float(self.beta_ent.get())
#             sum_data = self.controller.data_mgr.get_records(page_filter="参数求和", limit=1)
#             product_data = self.controller.data_mgr.get_records(page_filter="参数求积", limit=1)
#
#             if not sum_data or not product_data:
#                 messagebox.showwarning("警告", "请先完成前序计算")
#                 return
#
#             result = (alpha * sum_data[0][3]) + (beta * product_data[0][3])
#             self.result_var.set(f"综合结果：{result:.4f}")
#             if self.save_var.get():
#                 self.controller.data_mgr.save_record("综合计算", result, {"alpha": alpha, "beta": beta})
#         except ValueError:
#             messagebox.showerror("输入错误", "请输入有效数值")
#
#
# class HistoryPage(ttk.Frame):
#     def __init__(self, parent, data_mgr):
#         super().__init__(parent)
#         self.data_mgr = data_mgr
#         self._create_interface()
#         self._init_time_range()
#
#     def _create_interface(self):
#         # 时间选择组件
#         time_frame = ttk.Frame(self)
#         time_frame.pack(pady=10, fill=tk.X)
#
#         # 起始时间
#         ttk.Label(time_frame, text="起始时间:").grid(row=0, column=0)
#         self.start_combo = ttk.Combobox(time_frame, width=20, state="readonly")
#         self.start_combo.grid(row=0, column=1, padx=5)
#
#         # 结束时间
#         ttk.Label(time_frame, text="结束时间:").grid(row=0, column=2)
#         self.end_combo = ttk.Combobox(time_frame, width=20, state="readonly")
#         self.end_combo.grid(row=0, column=3, padx=5)
#
#         # 操作按钮
#         ttk.Button(time_frame, text="筛选", command=self._update_chart).grid(row=0, column=4, padx=10)
#
#         # 图表区域
#         self.figure = plt.Figure(figsize=(10, 5), dpi=100)
#         self.ax = self.figure.add_subplot(111)
#         self.canvas = FigureCanvasTkAgg(self.figure, self)
#         self.canvas.get_tk_widget().pack(expand=True, fill=tk.BOTH)
#
#     def _init_time_range(self):
#         """初始化时间选择范围"""
#         time_range = self.data_mgr.get_time_range()
#         if time_range and time_range[0]:
#             # 获取所有时间戳并排序
#             records = self.data_mgr.get_records()
#             timestamps = sorted({record[1] for record in records})
#
#             # 设置组合框值
#             self.start_combo['values'] = timestamps
#             self.end_combo['values'] = timestamps
#
#             # 设置默认值
#             self.start_combo.set(timestamps[0])
#             self.end_combo.set(timestamps[-1])
#         else:
#             self.start_combo.set("无数据")
#             self.end_combo.set("无数据")
#
#     def _update_chart(self):
#         """更新图表"""
#         self.ax.clear()
#         try:
#             # 获取时间参数
#             start_time = self.start_combo.get()
#             end_time = self.end_combo.get()
#
#             # 获取数据
#             records = self.data_mgr.get_records(
#                 start_time=start_time,
#                 end_time=end_time
#             )
#
#             # 处理数据
#             plot_data = {}
#             for record in records:
#                 page = record[2]
#                 timestamp = datetime.strptime(record[1], "%Y-%m-%d %H:%M:%S")
#                 if page not in plot_data:
#                     plot_data[page] = {'x': [], 'y': []}
#                 plot_data[page]['x'].append(timestamp)
#                 plot_data[page]['y'].append(record[3])
#
#             # 绘制图表
#             for page, data in plot_data.items():
#                 self.ax.plot(data['x'], data['y'], marker='o', linestyle='-', label=page)
#
#             self.ax.set_title("历史数据趋势分析", fontsize=14)
#             self.ax.set_xlabel("时间", fontsize=12)
#             self.ax.set_ylabel("结果值", fontsize=12)
#             self.ax.legend()
#             self.figure.autofmt_xdate()
#             self.canvas.draw()
#
#         except Exception as e:
#             messagebox.showerror("图表错误", f"无法生成图表: {str(e)}")
# # class HistoryPage(ttk.Frame):
# #     def __init__(self, parent, data_mgr):
# #         super().__init__(parent)
# #         self.data_mgr = data_mgr
# #         self._create_interface()
# #
# #     def _create_interface(self):
# #         filter_frame = ttk.Frame(self)
# #         filter_frame.pack(pady=10, fill=tk.X)
# #         ttk.Label(filter_frame, text="起始时间:").pack(side=tk.LEFT)
# #         self.start_ent = ttk.Entry(filter_frame, width=20)
# #         self.start_ent.pack(side=tk.LEFT, padx=5)
# #         ttk.Label(filter_frame, text="结束时间:").pack(side=tk.LEFT)
# #         self.end_ent = ttk.Entry(filter_frame, width=20)
# #         self.end_ent.pack(side=tk.LEFT, padx=5)
# #         ttk.Button(filter_frame, text="筛选", command=self._update_chart).pack(side=tk.LEFT, padx=10)
# #
# #         self.figure = plt.Figure(figsize=(10, 5), dpi=100)
# #         self.ax = self.figure.add_subplot(111)
# #         self.canvas = FigureCanvasTkAgg(self.figure, self)
# #         self.canvas.get_tk_widget().pack(expand=True, fill=tk.BOTH)
# #         self._update_chart()
# #
# #     def _update_chart(self):
# #         self.ax.clear()
# #         try:
# #             records = self.data_mgr.get_records(
# #                 self.start_ent.get() or None,
# #                 self.end_ent.get() or None
# #             )
# #             data = {}
# #             for r in records:
# #                 key = r[2]
# #                 if key not in data:
# #                     data[key] = {'x': [], 'y': []}
# #                 data[key]['x'].append(datetime.strptime(r[1], "%Y-%m-%d %H:%M:%S"))
# #                 data[key]['y'].append(r[3])
# #
# #             for name, values in data.items():
# #                 self.ax.plot(values['x'], values['y'], marker='o', label=name)
# #
# #             self.ax.set_title("历史数据趋势图", fontsize=14)
# #             self.ax.set_xlabel("时间", fontsize=12)
# #             self.ax.set_ylabel("结果值", fontsize=12)
# #             self.ax.legend()
# #             self.figure.autofmt_xdate()
# #             self.canvas.draw()
# #         except Exception as e:
# #             messagebox.showerror("错误", f"数据加载失败：{str(e)}")
#
#
# class HistoryDialog(tk.Toplevel):
#     def __init__(self, parent, page_name):
#         super().__init__(parent)
#         self.title(f"{page_name} - 历史记录")
#         self.geometry("800x400")
#         self.data_mgr = parent.controller.data_mgr
#         self.page_name = page_name
#         self._create_widgets()
#         self._bind_events()
#
#     def _create_widgets(self):
#         self.tree = ttk.Treeview(self, columns=("ID", "时间", "参数", "结果"), show="headings")
#         for col in self.tree["columns"]:
#             self.tree.heading(col, text=col)
#             self.tree.column(col, width=120 if col == "ID" else 200)
#
#         scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
#         self.tree.configure(yscrollcommand=scrollbar.set)
#         self.tree.pack(side="left", fill="both", expand=True)
#         scrollbar.pack(side="right", fill="y")
#
#         self.context_menu = tk.Menu(self, tearoff=0)
#         self.context_menu.add_command(label="删除记录", command=self._delete_selected)
#         self._load_data()
#
#     def _bind_events(self):
#         self.tree.bind("<Button-3>", self._show_context_menu)
#
#     def _load_data(self):
#         for item in self.tree.get_children():
#             self.tree.delete(item)
#         for r in self.data_mgr.get_records(page_filter=self.page_name):
#             params = json.loads(r[4])
#             param_str = ", ".join(f"{k}={v}" for k, v in params.items()) if isinstance(params, dict) else ", ".join(
#                 map(str, params))
#             self.tree.insert("", "end", values=(r[0], r[1], param_str, f"{r[3]:.4f}"))
#
#     def _show_context_menu(self, event):
#         item = self.tree.identify_row(event.y)
#         if item:
#             self.tree.selection_set(item)
#             self.context_menu.post(event.x_root, event.y_root)
#
#     def _delete_selected(self):
#         if not messagebox.askyesno("确认", "确定要删除这条记录吗？"):
#             return
#
#         selected = self.tree.selection()
#         if not selected: return
#
#         try:
#             record_id = self.tree.item(selected[0])['values'][0]
#             self.data_mgr.delete_record(record_id)
#             self._load_data()
#             messagebox.showinfo("成功", "记录已删除")
#         except Exception as e:
#             messagebox.showerror("错误", f"删除失败：{str(e)}")
#
#
# if __name__ == "__main__":
#     app = MainApplication()
#     app.mainloop()