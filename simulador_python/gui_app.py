"""
Interface Gráfica Interativa em Python (Tkinter Canvas 60 FPS Alta Performance)
Simulador Físico e Cinemático Completo do Rover Frugal 4WD/4WS
"""

import tkinter as tk
from tkinter import messagebox
import numpy as np
import os

from .multibody_dynamics import RoverMultibodySimulator
from .benchmark import run_comparative_benchmark
from .config import (
    STAIR_RISER, STAIR_TREAD, BLONDEL_VALUE, R_WHEEL_MAX, R_WHEEL_MIN,
    WHEELBASE, TRACK_WIDTH, MASS_TOTAL
)

class RoverSimulatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulador Físico Avançado - Rover Frugal 4WD/4WS (60 FPS)")
        self.root.geometry("1366x768")
        self.root.configure(bg="#0a0e17")

        # Motor de Simulação
        self.sim = RoverMultibodySimulator(with_csts=True)
        self.sim.reset(x=0.0, z=0.8, heading=0.0)

        # Comandos de Pilotagem
        self.throttle_cmd = 0.0
        self.steer_cmd = 0.0
        self.current_mode = 'ackermann'
        self.is_e_stopped = False
        self.keys_pressed = set()

        # Configuração da Câmera no Canvas (Pixels por Metro)
        self.ppm = 130.0 # Pixels por metro
        self.cam_target_z = 0.0
        self.cam_target_y = 0.0

        self.build_ui_layout()
        self.bind_events()

        # Iniciar Loop de 60 FPS (16 ms)
        self.animate_loop()

    def build_ui_layout(self):
        # 1. Header Superior
        header = tk.Frame(self.root, bg="#101827", height=45, bd=1, relief="solid")
        header.pack(fill="x", padx=8, pady=(6, 4))

        tk.Label(header, text="UGV-FRUGAL 4WD/4WS", bg="#101827", fg="#ff6b22",
                 font=("Segoe UI", 12, "bold")).pack(side="left", padx=(12, 6))

        tk.Label(header, text="Simulação Física das Rodas de 3 Raios Curvos & Suspensão C-STS",
                 bg="#101827", fg="#00e5ff", font=("Segoe UI", 10, "bold")).pack(side="left", padx=4)

        tk.Label(header, text="| Lei de Blondel: 2E+P = 64cm", bg="#101827", fg="#94a3b8",
                 font=("Segoe UI", 9)).pack(side="left", padx=6)

        btn_bench = tk.Button(header, text="📊 Benchmark C-STS", bg="#1e3a8a", fg="#ffffff",
                              font=("Segoe UI", 9, "bold"), activebackground="#2563eb",
                              cursor="hand2", command=self.run_benchmark)
        btn_bench.pack(side="right", padx=12, pady=4)

        # 2. Área Central: Canvas de Simulação (Esquerda) + Telemetria / Controles (Direita)
        body_frame = tk.Frame(self.root, bg="#0a0e17")
        body_frame.pack(fill="both", expand=True, padx=8, pady=4)

        # Canvas de Alta Performance (Double-Buffered)
        self.canvas = tk.Canvas(body_frame, bg="#0a0f1d", highlightthickness=1,
                                highlightbackground="#1e293b")
        self.canvas.pack(side="left", fill="both", expand=True, padx=(0, 6))

        # Painel Lateral Direito de Telemetria e Comandos
        right_panel = tk.Frame(body_frame, bg="#101827", width=310, bd=1, relief="solid")
        right_panel.pack(side="right", fill="y")
        right_panel.pack_propagate(False)

        self.build_sidebar(right_panel)

    def build_sidebar(self, parent):
        # Telemetria Principal
        tk.Label(parent, text="📊 TELEMETRIA DINÂMICA", bg="#101827", fg="#00e5ff",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=(8, 4))

        telem_box = tk.Frame(parent, bg="#101827")
        telem_box.pack(fill="x", padx=12)

        self.lbl_speed = self.create_row(telem_box, "Velocidade:", "0.00 m/s", 0)
        self.lbl_pitch = self.create_row(telem_box, "Arfagem (Pitch):", "0.0°", 1)
        self.lbl_roll  = self.create_row(telem_box, "Rolamento (Roll):", "0.0°", 2)
        self.lbl_pend  = self.create_row(telem_box, "Pêndulo da Caixa:", "0.0°", 3)
        self.lbl_pos   = self.create_row(telem_box, "Posição (X, Z):", "(0.00, 0.00) m", 4)

        # Roda de 3 Raios e C-STS
        tk.Label(parent, text="🌀 FÍSICA DOS 3 RAIOS & C-STS", bg="#101827", fg="#ffd600",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=(10, 4))

        csts_box = tk.Frame(parent, bg="#101827")
        csts_box.pack(fill="x", padx=12)

        self.lbl_phase = self.create_row(csts_box, "Fase Cinemática:", "CCS (Contínuo)", 0)
        self.lbl_spoke = self.create_row(csts_box, "Raio de Apoio:", "Raio 1 / 3", 1)
        self.lbl_reff  = self.create_row(csts_box, "Raio Efetivo r(t):", "45.0 mm", 2)
        self.lbl_def   = self.create_row(csts_box, "Deflexão C-STS:", "0.0°", 3)
        self.lbl_energ = self.create_row(csts_box, "Energia Elástica U:", "0.000 J", 4)

        # Forças Normais
        tk.Label(parent, text="⚡ REAÇÃO NORMAL (Fz)", bg="#101827", fg="#ff6b22",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=(10, 4))

        fz_box = tk.Frame(parent, bg="#101827")
        fz_box.pack(fill="x", padx=12)

        self.lbl_fz_fl = self.create_row(fz_box, "D.Esq (FL):", "18.5 N", 0)
        self.lbl_fz_fr = self.create_row(fz_box, "D.Dir (FR):", "18.5 N", 1)
        self.lbl_fz_rl = self.create_row(fz_box, "T.Esq (RL):", "18.5 N", 2)
        self.lbl_fz_rr = self.create_row(fz_box, "T.Dir (RR):", "18.5 N", 3)

        # Modos 4WS
        tk.Label(parent, text="🎮 MODOS DE DIREÇÃO 4WS", bg="#101827", fg="#00e5ff",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=(10, 4))

        modes_box = tk.Frame(parent, bg="#101827")
        modes_box.pack(fill="x", padx=12)

        self.mode_var = tk.StringVar(value="ackermann")
        modes = [
            ("Ackermann Duplo", "ackermann"),
            ("Modo Caranguejo", "crab"),
            ("Giro no Eixo (Spin)", "spin"),
            ("Modo Escada (Stair)", "stair")
        ]
        for label, val in modes:
            rb = tk.Radiobutton(modes_box, text=label, value=val, variable=self.mode_var,
                                bg="#101827", fg="#f0f4fc", selectcolor="#ff6b22",
                                activebackground="#101827", activeforeground="#00e5ff",
                                font=("Segoe UI", 8), command=self.on_mode_change)
            rb.pack(anchor="w", pady=1)

        # Botões de Ação
        actions_box = tk.Frame(parent, bg="#101827")
        actions_box.pack(fill="x", padx=12, pady=10)

        btn_climb = tk.Button(actions_box, text="🪜 Alinhar e Subir Escada", bg="#334155", fg="#ffffff",
                              font=("Segoe UI", 9, "bold"), cursor="hand2", command=self.align_stairs)
        btn_climb.pack(fill="x", pady=2)

        btn_reset = tk.Button(actions_box, text="🔄 Resetar Posição", bg="#1e293b", fg="#94a3b8",
                              font=("Segoe UI", 8), cursor="hand2", command=self.reset_sim)
        btn_reset.pack(fill="x", pady=2)

        self.btn_estop = tk.Button(actions_box, text="🛑 E-STOP (EMERGÊNCIA)", bg="#b91c1c", fg="#ffffff",
                                   font=("Segoe UI", 9, "bold"), cursor="hand2", command=self.toggle_estop)
        self.btn_estop.pack(fill="x", pady=(4, 2))

        # Guia Teclado
        hints = tk.Label(parent, text="Teclado: [W/S] Avanço/Ré | [A/D] Esterçar | [Espaço] Freio",
                         bg="#101827", fg="#64748b", font=("Segoe UI", 8), justify="left")
        hints.pack(anchor="w", padx=12, pady=(6, 0))

    def create_row(self, parent, label_text, default_val, row_idx):
        tk.Label(parent, text=label_text, bg="#101827", fg="#94a3b8",
                 font=("Segoe UI", 8)).grid(row=row_idx, column=0, sticky="w", pady=1)
        val = tk.Label(parent, text=default_val, bg="#101827", fg="#00e676",
                       font=("Consolas", 8, "bold"))
        val.grid(row=row_idx, column=1, sticky="e", padx=(8, 0), pady=1)
        return val

    def bind_events(self):
        self.root.bind('<KeyPress>', self.on_key_down)
        self.root.bind('<KeyRelease>', self.on_key_up)

    def on_key_down(self, event):
        key = event.keysym.lower()
        self.keys_pressed.add(key)
        self.update_drive_commands()

    def on_key_up(self, event):
        key = event.keysym.lower()
        self.keys_pressed.discard(key)
        self.update_drive_commands()

    def update_drive_commands(self):
        if self.is_e_stopped:
            self.throttle_cmd = 0.0
            self.steer_cmd = 0.0
            return

        throttle = 0.0
        if 'w' in self.keys_pressed or 'up' in self.keys_pressed:
            throttle += 0.9
        if 's' in self.keys_pressed or 'down' in self.keys_pressed:
            throttle -= 0.6
        self.throttle_cmd = throttle

        steer = 0.0
        if 'a' in self.keys_pressed or 'left' in self.keys_pressed:
            steer += 1.0
        if 'd' in self.keys_pressed or 'right' in self.keys_pressed:
            steer -= 1.0
        self.steer_cmd = steer

        if 'space' in self.keys_pressed:
            self.throttle_cmd = 0.0

    def on_mode_change(self):
        self.current_mode = self.mode_var.get()

    def align_stairs(self):
        self.sim.reset(x=0.0, z=-1.0, heading=0.0)
        self.mode_var.set("stair")
        self.current_mode = "stair"

    def reset_sim(self):
        self.sim.reset(x=0.0, z=0.8, heading=0.0)

    def toggle_estop(self):
        self.is_e_stopped = not self.is_e_stopped
        if self.is_e_stopped:
            self.btn_estop.config(text="⚡ REATIVAR SISTEMA", bg="#059669")
            self.throttle_cmd = 0.0
        else:
            self.btn_estop.config(text="🛑 E-STOP (EMERGÊNCIA)", bg="#b91c1c")

    def run_benchmark(self):
        img_path = run_comparative_benchmark()
        messagebox.showinfo("Benchmark Científico",
                            f"Ensaio concluído com sucesso!\nGráficos salvos em:\n{os.path.abspath(img_path)}")

    def world_to_screen(self, wz, wy, cw, ch):
        """
        Converte coordenadas mundiais (Z, Y) para pixels no Canvas centralizado na câmera.
        Z: avança para a esquerda (-Z)
        """
        # Centralização suave da câmera no rover
        cx = cw * 0.45 + (self.cam_target_z - wz) * self.ppm
        cy = ch * 0.65 - (wy - self.cam_target_y) * self.ppm
        return cx, cy

    def animate_loop(self):
        # 1. Integração Física (60 Hz)
        dt = 0.016
        if not self.is_e_stopped:
            self.sim.step(self.throttle_cmd, self.steer_cmd, mode=self.current_mode, dt=dt)

        # Câmera segue o rover suavemente
        self.cam_target_z += (self.sim.z - self.cam_target_z) * 0.1
        self.cam_target_y += (self.sim.y - self.cam_target_y) * 0.1

        # 2. Renderização no Canvas
        self.draw_scene()

        # 3. Atualização de Labels de Telemetria
        fl_wheel = self.sim.wheels['FL']
        self.lbl_speed.config(text=f"{abs(self.sim.speed):.2f} m/s")
        self.lbl_pitch.config(text=f"{np.degrees(self.sim.pitch):.1f}°")
        self.lbl_roll.config(text=f"{np.degrees(self.sim.roll):.1f}°")
        self.lbl_pend.config(text=f"{np.degrees(self.sim.pendulum_pitch):.1f}°")
        self.lbl_pos.config(text=f"({self.sim.x:.2f}, {self.sim.z:.2f}) m")

        self.lbl_phase.config(text=f"{fl_wheel.phase_name} ({'Contínuo' if fl_wheel.phase_name=='CCS' else 'Transição'})")
        self.lbl_spoke.config(text=f"Raio {fl_wheel.active_spoke_idx + 1} / 3")
        self.lbl_reff.config(text=f"{fl_wheel.effective_radius*1000:.1f} mm")
        self.lbl_def.config(text=f"{np.degrees(fl_wheel.torsional_deflection):.1f}°")
        total_e = sum(w.stored_energy for w in self.sim.wheels.values())
        self.lbl_energ.config(text=f"{total_e:.3f} J")

        self.lbl_fz_fl.config(text=f"{self.sim.normal_forces['FL']:.1f} N")
        self.lbl_fz_fr.config(text=f"{self.sim.normal_forces['FR']:.1f} N")
        self.lbl_fz_rl.config(text=f"{self.sim.normal_forces['RL']:.1f} N")
        self.lbl_fz_rr.config(text=f"{self.sim.normal_forces['RR']:.1f} N")

        # Agendar próximo frame a 60 FPS
        self.root.after(16, self.animate_loop)

    def draw_scene(self):
        self.canvas.delete("all")
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 50 or ch < 50:
            return

        # 1. Grid e Fundo
        self.canvas.create_line(0, ch*0.65, cw, ch*0.65, fill="#1e293b", dash=(4, 4))

        # 2. Desenho da Escada de Blondel (E = 17cm, P = 30cm)
        # Solo inferior (Z de +2.0 a -2.0)
        sx1, sy1 = self.world_to_screen(2.5, -0.15, cw, ch)
        sx2, sy2 = self.world_to_screen(-2.0, -0.15, cw, ch)
        self.canvas.create_line(sx1, sy1, sx2, sy2, fill="#475569", width=3)

        # 3 Degraus de Blondel
        cur_z = -2.0
        cur_y = -0.15
        for i in range(3):
            # Espelho vertical E = 0.17m
            p1 = self.world_to_screen(cur_z, cur_y, cw, ch)
            cur_y += STAIR_RISER
            p2 = self.world_to_screen(cur_z, cur_y, cw, ch)
            self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill="#00e5ff", width=3)

            # Piso horizontal P = 0.30m
            cur_z -= STAIR_TREAD
            p3 = self.world_to_screen(cur_z, cur_y, cw, ch)
            self.canvas.create_line(p2[0], p2[1], p3[0], p3[1], fill="#00e5ff", width=3)

            # Marcador de cota do degrau
            self.canvas.create_text(p2[0]+15, p2[1]-8, text=f"D{i+1}: +{(i+1)*17}cm",
                                   fill="#94a3b8", font=("Consolas", 8))

        # Patamar superior
        p_plat_end = self.world_to_screen(cur_z - 1.5, cur_y, cw, ch)
        self.canvas.create_line(p3[0], p3[1], p_plat_end[0], p_plat_end[1], fill="#00e5ff", width=3)

        # 3. Desenho do Rover
        rover_z = self.sim.z
        rover_y = self.sim.y
        rover_pitch = self.sim.pitch

        # Eixos Dianteiro e Traseiro
        front_z = rover_z - (WHEELBASE / 2.0) * np.cos(rover_pitch)
        front_y = self.sim.wheel_heights['FL']
        rear_z  = rover_z + (WHEELBASE / 2.0) * np.cos(rover_pitch)
        rear_y  = self.sim.wheel_heights['RL']

        # Chassi em V Invertido e Vértice Superior
        apex_z = rover_z
        apex_y = rover_y + 0.32

        p_front = self.world_to_screen(front_z, front_y, cw, ch)
        p_rear  = self.world_to_screen(rear_z, rear_y, cw, ch)
        p_apex  = self.world_to_screen(apex_z, apex_y, cw, ch)

        # Tubos de PVC do V Invertido (Branco/Cinza Claro)
        self.canvas.create_line(p_front[0], p_front[1], p_apex[0], p_apex[1], fill="#f8fafc", width=5)
        self.canvas.create_line(p_rear[0], p_rear[1], p_apex[0], p_apex[1], fill="#f8fafc", width=5)
        # Junta 3D Split-Clamp no Ápice (Laranja)
        self.canvas.create_oval(p_apex[0]-8, p_apex[1]-8, p_apex[0]+8, p_apex[1]+8, fill="#ff6b22", outline="#ffffff")

        # Caixa Organizadora Pendular
        box_z = rover_z
        box_y = rover_y + 0.02 - 0.06 * np.sin(self.sim.pendulum_pitch)
        p_box = self.world_to_screen(box_z, box_y, cw, ch)
        bw = 0.46 * self.ppm * 0.5
        bh = 0.22 * self.ppm * 0.5
        self.canvas.create_rectangle(p_box[0]-bw, p_box[1]-bh, p_box[0]+bw, p_box[1]+bh,
                                     fill="#0c4a6e", outline="#38bdf8", width=2)
        # Notebook no interior da caixa
        self.canvas.create_rectangle(p_box[0]-bw+6, p_box[1]+bh-12, p_box[0]+bw-6, p_box[1]+bh-4,
                                     fill="#00e5ff", outline="")
        self.canvas.create_text(p_box[0], p_box[1], text="NOTEBOOK TI", fill="#ffffff", font=("Segoe UI", 7, "bold"))

        # 4. Desenho das Rodas com 3 Raios Curvos Físicos Reais (Jeong & Kim, 2025)
        for (az, ay, wheel, color) in [(front_z, front_y, self.sim.wheels['FL'], "#ff6b22"),
                                       (rear_z, rear_y, self.sim.wheels['RL'], "#f97316")]:
            p_axle = self.world_to_screen(az, ay, cw, ch)

            # Cubo Central com Mola C-STS
            self.canvas.create_oval(p_axle[0]-10, p_axle[1]-10, p_axle[0]+10, p_axle[1]+10,
                                    fill="#38bdf8", outline="#ffffff", width=1)

            # Os 3 Raios Curvos Espiralados
            spokes_geo = wheel.get_spoke_geometry(num_points=18)
            for s_idx, pts in enumerate(spokes_geo):
                screen_pts = []
                for pt in pts:
                    # pt[0] é Z local, pt[1] é Y local
                    px, py = self.world_to_screen(az + pt[0], ay + pt[1], cw, ch)
                    screen_pts.extend([px, py])

                # Destaque no raio ativo de contato
                is_active = (s_idx == wheel.active_spoke_idx)
                c_spoke = "#00e676" if is_active else color
                w_spoke = 4 if is_active else 2.5
                self.canvas.create_line(screen_pts, fill=c_spoke, width=w_spoke, smooth=True)

                # Garra de borracha na ponta do raio
                tip_px, tip_py = screen_pts[-2], screen_pts[-1]
                self.canvas.create_rectangle(tip_px-3, tip_py-3, tip_px+3, tip_py+3, fill="#111827", outline="#ffffff")

        # 5. Loupe de Zoom da Roda Dianteira FL e Mola C-STS (Canto Superior Direito)
        self.draw_wheel_loupe(cw, ch)

    def draw_wheel_loupe(self, cw, ch):
        # Caixa de Zoom 180x180 no canto superior direito
        zx = cw - 190
        zy = 20
        zw = 170
        zh = 170

        self.canvas.create_rectangle(zx, zy, zx+zw, zy+zh, fill="#0f172a", outline="#00e5ff", width=1)
        self.canvas.create_text(zx + zw/2, zy + 12, text="LOUPE RODA FL (C-STS)",
                                fill="#00e5ff", font=("Segoe UI", 7, "bold"))

        center_x = zx + zw/2
        center_y = zy + zh/2 + 6
        fl_wheel = self.sim.wheels['FL']
        zoom_scale = 480.0 # Pixels/metro no zoom

        # Desenhar Cubo
        self.canvas.create_oval(center_x - R_WHEEL_MIN*zoom_scale, center_y - R_WHEEL_MIN*zoom_scale,
                                center_x + R_WHEEL_MIN*zoom_scale, center_y + R_WHEEL_MIN*zoom_scale,
                                outline="#38bdf8", fill="#1e293b", dash=(2, 2))

        # Desenhar 3 Raios Curvos
        spokes = fl_wheel.get_spoke_geometry(num_points=20)
        for s_idx, pts in enumerate(spokes):
            s_pts = []
            for pt in pts:
                # Na vista lateral: Z para esquerda, Y para cima
                px = center_x - pt[0] * zoom_scale
                py = center_y - pt[1] * zoom_scale
                s_pts.extend([px, py])

            is_active = (s_idx == fl_wheel.active_spoke_idx)
            c = "#00e676" if is_active else "#ff6b22"
            self.canvas.create_line(s_pts, fill=c, width=3 if is_active else 1.5, smooth=True)
            self.canvas.create_rectangle(s_pts[-2]-3, s_pts[-1]-3, s_pts[-2]+3, s_pts[-1]+3, fill="#111827")

        # Desenhar Espiral C-STS no Centro
        spiral_u = np.linspace(0, 1, 30)
        spiral_r = (0.015 + spiral_u * (R_WHEEL_MIN - 0.015)) * zoom_scale
        spiral_theta = spiral_u * 3.2 * np.pi + fl_wheel.torsional_deflection
        sp_pts = []
        for i in range(len(spiral_u)):
            px = center_x + spiral_r[i] * np.sin(spiral_theta[i])
            py = center_y - spiral_r[i] * np.cos(spiral_theta[i])
            sp_pts.extend([px, py])
        self.canvas.create_line(sp_pts, fill="#00e5ff", width=2, smooth=True)
