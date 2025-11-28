"""
CPU Scheduling Visualizer - CustomTkinter
Features:
- Supports: FCFS, SJF (Non-preemptive), SJF (Preemptive/SRTF), Priority (Non-preemptive), Priority (Preemptive), Round Robin
- Dynamic rows: enter number of processes -> generates rows to fill Arrival, Burst, Priority
- Gantt Chart drawn on Canvas + Waiting Time + Turnaround Time + averages

Run:
    pip install customtkinter
    python cpu_scheduling_customtkinter_app.py

"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from collections import deque

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class ProcessRow:
    def __init__(self, parent, idx):
        self.idx = idx
        self.frame = ctk.CTkFrame(parent)
        self.frame.grid_columnconfigure((0,1,2,3), weight=1)

        self.pid_var = tk.StringVar(value=f"P{idx+1}")
        self.arrival_var = tk.StringVar(value="0")
        self.burst_var = tk.StringVar(value="1")
        self.priority_var = tk.StringVar(value="1")

        self.pid_entry = ctk.CTkEntry(self.frame, width=80, textvariable=self.pid_var)
        self.arrival_entry = ctk.CTkEntry(self.frame, width=80, textvariable=self.arrival_var)
        self.burst_entry = ctk.CTkEntry(self.frame, width=80, textvariable=self.burst_var)
        self.priority_entry = ctk.CTkEntry(self.frame, width=80, textvariable=self.priority_var)

        self.pid_entry.grid(row=0, column=0, padx=3, pady=3, sticky="ew")
        self.arrival_entry.grid(row=0, column=1, padx=3, pady=3, sticky="ew")
        self.burst_entry.grid(row=0, column=2, padx=3, pady=3, sticky="ew")
        self.priority_entry.grid(row=0, column=3, padx=3, pady=3, sticky="ew")

    def grid(self, **kwargs):
        self.frame.grid(**kwargs)

    def destroy(self):
        self.frame.destroy()

    def get(self):
        try:
            pid = self.pid_var.get().strip()
            arrival = int(float(self.arrival_var.get()))
            burst = int(float(self.burst_var.get()))
            priority = int(float(self.priority_var.get()))
            if burst <= 0:
                raise ValueError("Burst must be > 0")
            if arrival < 0:
                raise ValueError("Arrival must be >= 0")
            return (pid, arrival, burst, priority)
        except Exception as e:
            raise


class SchedulerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CPU Scheduling Visualizer")
        self.geometry("1100x700")

        # top controls
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=12, pady=8)

        self.num_var = tk.IntVar(value=5)
        ctk.CTkLabel(top_frame, text="Number of Processes:").grid(row=0, column=0, padx=6)
        self.num_spin = ctk.CTkEntry(top_frame, width=80, textvariable=self.num_var)
        self.num_spin.grid(row=0, column=1, padx=6)

        self.btn_gen = ctk.CTkButton(top_frame, text="Generate Rows", command=self.generate_rows)
        self.btn_gen.grid(row=0, column=2, padx=6)

        ctk.CTkLabel(top_frame, text="Algorithm:").grid(row=0, column=3, padx=6)
        self.alg_combo = ctk.CTkOptionMenu(top_frame, values=[
            "FCFS",
            "SJF (Non-preemptive)",
            "SJF (Preemptive - SRTF)",
            "Priority (Non-preemptive)",
            "Priority (Preemptive)",
            "Round Robin"
        ])
        self.alg_combo.set("FCFS")
        self.alg_combo.grid(row=0, column=4, padx=6)

        ctk.CTkLabel(top_frame, text="Quantum (for RR):").grid(row=0, column=5, padx=6)
        self.quantum_var = tk.IntVar(value=3)
        self.quantum_entry = ctk.CTkEntry(top_frame, width=60, textvariable=self.quantum_var)
        self.quantum_entry.grid(row=0, column=6, padx=6)

        self.run_btn = ctk.CTkButton(top_frame, text="Run", fg_color="#2ecc71", command=self.run)
        self.run_btn.grid(row=0, column=7, padx=6)

        # middle: process rows (in scrollable area)
        middle = ctk.CTkFrame(self)
        middle.pack(fill="both", expand=True, padx=12, pady=(0,6))

        header = ctk.CTkFrame(middle)
        header.pack(fill="x")
        labels = ["PID", "Arrival", "Burst", "Priority"]
        for i, t in enumerate(labels):
            ctk.CTkLabel(header, text=t).grid(row=0, column=i, padx=28, pady=6)

        # scroll canvas for rows
        canvas = tk.Canvas(middle, height=180)
        scrollbar = ttk.Scrollbar(middle, orient="vertical", command=canvas.yview)
        self.rows_container = ctk.CTkFrame(canvas)

        self.rows_container.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.rows_container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # bottom: Gantt canvas + output text
        bottom = ctk.CTkFrame(self)
        bottom.pack(fill="both", padx=12, pady=6, expand=True)

        # Gantt drawing canvas (with its own horizontal scrollbar)
        gantt_frame = ctk.CTkFrame(bottom)
        gantt_frame.pack(fill="x", pady=(6,4))

        self.gantt_canvas = tk.Canvas(gantt_frame, height=120, bg="#ffffff", highlightthickness=1, highlightbackground="#cccccc")
        self.gantt_hscroll = ttk.Scrollbar(gantt_frame, orient="horizontal", command=self.gantt_canvas.xview)
        self.gantt_canvas.configure(xscrollcommand=self.gantt_hscroll.set)
        self.gantt_canvas.pack(side="top", fill="x", expand=True)
        self.gantt_hscroll.pack(side="bottom", fill="x")

        # output text below for tables
        out_label = ctk.CTkLabel(bottom, text="Results (WT & TAT):")
        out_label.pack(anchor="w")

        self.output_text = tk.Text(bottom, wrap="none", height=10)
        self.output_text.pack(fill="both", expand=True)

        # store rows
        self.rows = []
        self.generate_rows()

    def clear_rows(self):
        for r in self.rows:
            r.destroy()
        self.rows = []

    def generate_rows(self):
        self.clear_rows()
        try:
            n = int(self.num_var.get())
            if n <= 0:
                raise ValueError
        except Exception:
            messagebox.showerror("Input error", "Please enter a valid positive integer for number of processes.")
            return

        for i in range(n):
            row = ProcessRow(self.rows_container, i)
            row.grid(row=i, column=0, sticky="ew", pady=2, padx=2)
            self.rows.append(row)

    def read_processes(self):
        processes = []
        try:
            for r in self.rows:
                processes.append(r.get())
        except Exception as e:
            messagebox.showerror("Input error", f"Invalid input in process rows: {e}")
            return None

        # normalize PIDs to be unique
        seen = set()
        normalized = []
        for i, (pid, arr, burst, pr) in enumerate(processes):
            if not pid:
                pid = f"P{i+1}"
            if pid in seen:
                pid = f"{pid}_{i+1}"
            seen.add(pid)
            normalized.append((pid, arr, burst, pr))

        return normalized

    # ---------------- scheduling algs (adapted) ----------------
    def fcfs(self, process_list):
        gantt = []
        time = 0
        waiting = {}
        tat = {}

        plist = sorted(process_list, key=lambda x: x[1])  # sort by arrival

        for p, arr, burst, pr in plist:
            if time < arr:
                time = arr
            start = time
            end = time + burst
            gantt.append((p, start, end))

            waiting[p] = start - arr
            tat[p] = end - arr

            time = end

        return gantt, waiting, tat

    def sjf_non_pre(self, process_list):
        gantt = []
        waiting = {}
        tat = {}

        time = 0
        done = set()
        n = len(process_list)

        while len(done) < n:
            available = [p for p in process_list if p[1] <= time and p[0] not in done]

            if not available:
                time += 1
                continue

            p, arr, burst, pr = min(available, key=lambda x: x[2])

            start = time
            end = time + burst
            gantt.append((p, start, end))

            waiting[p] = start - arr
            tat[p] = end - arr

            done.add(p)
            time = end

        return gantt, waiting, tat

    def sjf_pre(self, process_list):
        n = len(process_list)
        remaining = {p[0]: p[2] for p in process_list}
        arrival = {p[0]: p[1] for p in process_list}

        time = 0
        done = 0
        gantt = []
        last = None

        finish_time = {}

        while done < n:
            available = [p[0] for p in process_list if arrival[p[0]] <= time and remaining[p[0]] > 0]

            if not available:
                time += 1
                continue

            curr = min(available, key=lambda x: remaining[x])

            if last != curr:
                gantt.append([curr, time])  # temp end time later
                last = curr

            remaining[curr] -= 1

            if remaining[curr] == 0:
                finish_time[curr] = time + 1
                done += 1

            time += 1

        # fix gantt end times
        for i in range(len(gantt)):
            if i < len(gantt) - 1:
                gantt[i].append(gantt[i+1][1])
            else:
                gantt[i].append(time)

        waiting = {}
        tat = {}
        burst = {p[0]: p[2] for p in process_list}

        for p in burst:
            tat[p] = finish_time[p] - arrival[p]
            waiting[p] = tat[p] - burst[p]

        gantt_clean = [(g[0], g[1], g[2]) for g in gantt]

        return gantt_clean, waiting, tat

    def priority_non(self, process_list):
        gantt = []
        waiting = {}
        tat = {}

        time = 0
        done = set()
        n = len(process_list)

        while len(done) < n:
            available = [p for p in process_list if p[1] <= time and p[0] not in done]

            if not available:
                time += 1
                continue

            p, arr, burst, pr = min(available, key=lambda x: x[3])  # smallest priority number

            start = time
            end = time + burst
            gantt.append((p, start, end))

            waiting[p] = start - arr
            tat[p] = end - arr

            done.add(p)
            time = end

        return gantt, waiting, tat

    def priority_pre(self, process_list):
        n = len(process_list)
        remaining = {p[0]: p[2] for p in process_list}
        arrival = {p[0]: p[1] for p in process_list}
        priority = {p[0]: p[3] for p in process_list}

        time = 0
        done = 0
        gantt = []
        last = None
        finish_time = {}

        while done < n:
            available = [p[0] for p in process_list if arrival[p[0]] <= time and remaining[p[0]] > 0]

            if not available:
                time += 1
                continue

            curr = min(available, key=lambda x: priority[x])  # highest priority

            if last != curr:
                gantt.append([curr, time])
                last = curr

            remaining[curr] -= 1

            if remaining[curr] == 0:
                finish_time[curr] = time + 1
                done += 1

            time += 1

        # fix end times
        for i in range(len(gantt)):
            if i < len(gantt) - 1:
                gantt[i].append(gantt[i+1][1])
            else:
                gantt[i].append(time)

        burst = {p[0]: p[2] for p in process_list}
        waiting = {}
        tat = {}

        for p in burst:
            tat[p] = finish_time[p] - arrival[p]
            waiting[p] = tat[p] - burst[p]

        gantt_clean = [(g[0], g[1], g[2]) for g in gantt]

        return gantt_clean, waiting, tat

    def round_robin(self, process_list, quantum):
        gantt = []
        time = 0

        q = deque()
        remaining = {p[0]: p[2] for p in process_list}
        arrival = {p[0]: p[1] for p in process_list}

        visited = set()

        while True:
            # add newly arrived
            for p, arr, burst, pr in process_list:
                if arr <= time and p not in visited:
                    q.append(p)
                    visited.add(p)

            if not q:
                if all(remaining[p] == 0 for p in remaining):
                    break
                time += 1
                continue

            curr = q.popleft()

            start = time
            run = min(quantum, remaining[curr])
            time += run
            end = time
            gantt.append((curr, start, end))

            remaining[curr] -= run

            # after executing, add any new arrivals
            for p, arr, burst, pr in process_list:
                if arr <= time and p not in visited:
                    q.append(p)
                    visited.add(p)

            if remaining[curr] > 0:
                q.append(curr)

        burst = {p[0]: p[2] for p in process_list}
        finish_time = {}

        # last occurrence of each process in Gantt = completion time
        for p, s, e in gantt:
            finish_time[p] = e

        waiting = {}
        tat = {}

        for p in burst:
            tat[p] = finish_time[p] - arrival[p]
            waiting[p] = tat[p] - burst[p]

        return gantt, waiting, tat

    # ---------------- helpers ----------------
    def draw_gantt_canvas(self, gantt):
        """Draws the gantt chart on self.gantt_canvas. Scales blocks by time units.
        Gantt: list of (pid, start, end)
        """
        self.gantt_canvas.delete("all")
        if not gantt:
            return

        # compute scale — determine total time
        start_time = gantt[0][1]
        end_time = gantt[-1][2]
        total = end_time - start_time
        if total <= 0:
            total = 1

        padding = 20
        unit_width = max(20, int((self.winfo_width() - 200) / total))
        canvas_height = 100
        y0 = 20
        box_height = 40

        x = padding
        colors = ["#4caf50", "#2196f3", "#ff9800", "#9c27b0", "#f44336", "#607d8b"]
        color_map = {}

        for p, s, e in gantt:
            w = (e - s) * unit_width
            if p not in color_map:
                color_map[p] = colors[len(color_map) % len(colors)]
            col = color_map[p]
            # draw rectangle and text
            rect = self.gantt_canvas.create_rectangle(x, y0, x + w, y0 + box_height, fill=col, outline="#222")
            self.gantt_canvas.create_text(x + 5, y0 + box_height/2, anchor="w", text=p, fill="#fff", font=("Arial", 10, "bold"))
            # draw start time under rect left, end time under rect right
            self.gantt_canvas.create_text(x, y0 + box_height + 12, anchor="n", text=str(s))
            x += w
        # final end time
        self.gantt_canvas.create_text(x, y0 + box_height + 12, anchor="n", text=str(end_time))

        # set scrollregion to allow horizontal scroll
        self.gantt_canvas.config(scrollregion=(0,0,x+padding, canvas_height))

    def format_table(self, waiting, tat):
        lines = [f"Process\t\tWaiting\t\tTurnaround\n"]
        keys = list(waiting.keys())
        for k in keys:
            lines.append(f"   {k}\t\t   {waiting[k]}\t\t   {tat[k]}")
        avg_wt = sum(waiting.values()) / len(waiting)
        avg_tat = sum(tat.values()) / len(tat)
        lines.append("\n")
        lines.append(f"Average Waiting Time: {avg_wt:.2f} ms")
        lines.append(f"Average Turnaround Time: {avg_tat:.2f} ms")
        return "\n".join(lines)

    def run(self):
        plist = self.read_processes()
        if plist is None:
            return

        alg = self.alg_combo.get()
        quantum = int(self.quantum_var.get()) if self.quantum_var.get() else 1

        proc_list = list(plist)

        try:
            if alg == "FCFS":
                gantt, waiting, tat = self.fcfs(proc_list)
            elif alg == "SJF (Non-preemptive)":
                gantt, waiting, tat = self.sjf_non_pre(proc_list)
            elif alg == "SJF (Preemptive - SRTF)":
                gantt, waiting, tat = self.sjf_pre(proc_list)
            elif alg == "Priority (Non-preemptive)":
                gantt, waiting, tat = self.priority_non(proc_list)
            elif alg == "Priority (Preemptive)":
                gantt, waiting, tat = self.priority_pre(proc_list)
            elif alg == "Round Robin":
                gantt, waiting, tat = self.round_robin(proc_list, quantum)
            else:
                raise ValueError("Unknown algorithm")
        except Exception as e:
            messagebox.showerror("Runtime error", f"Error while running the scheduler: {e}")
            return

        # draw gantt on canvas
        self.draw_gantt_canvas(gantt)

        # show table
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.END, self.format_table(waiting, tat))


if __name__ == "__main__":
    app = SchedulerApp()
    app.mainloop()
