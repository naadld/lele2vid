import os
import sys
import math
import numpy as np
import cv2
import subprocess

def create_cyber_blue_globe_loop(output_path: str, width=1080, height=1920, fps=30, duration=6.0):
    """
    Generate 6.0s 100% seamless looping Cyber Blue Background:
    - Deep midnight blue base (#030712)
    - 3D Wireframe Cyber Globe rotating 360 degrees smoothly in center/lower-mid
    - Floating cyan/blue ambient particles and subtle grid
    """
    total_frames = int(fps * duration)
    temp_raw = output_path.replace(".mp4", "_raw.mp4")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_raw, fourcc, fps, (width, height))

    # Base gradient
    base_bg = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        ratio = y / height
        # Gradient from deep dark navy (#030712) to dark blue (#09152e) to dark (#020617)
        r = int(3 + 8 * math.sin(ratio * math.pi))
        g = int(7 + 16 * math.sin(ratio * math.pi))
        b = int(18 + 42 * math.sin(ratio * math.pi))
        base_bg[y, :] = [b, g, r]  # BGR

    # Seeded particles for seamless looping
    np.random.seed(42)
    num_particles = 70
    p_data = []
    for _ in range(num_particles):
        x0 = np.random.uniform(50, width - 50)
        y0 = np.random.uniform(100, height - 100)
        radius = np.random.uniform(2.5, 6.0)
        speed_x = np.random.uniform(-30, 30)
        speed_y = np.random.uniform(-60, -20)
        phase = np.random.uniform(0, 2 * math.pi)
        color_choice = np.random.choice([0, 1, 2])
        if color_choice == 0:
            color = (248, 189, 56)  # Cyan #38bdf8 in BGR
        elif color_choice == 1:
            color = (199, 132, 2)   # Blue #0284c7 in BGR
        else:
            color = (255, 220, 125) # Soft light cyan in BGR
        p_data.append((x0, y0, radius, speed_x, speed_y, phase, color))

    # Globe 3D points (lat, lon)
    globe_r = 380
    globe_cy = 960
    globe_cx = 540

    lat_lines = 12
    lon_lines = 24

    for f in range(total_frames):
        t = f / fps
        t_norm = f / total_frames
        angle_y = 2 * math.pi * t_norm  # Exactly 1 full 360 rotation in 6s

        frame = base_bg.copy()

        # 1. Subtle horizontal tech scan lines / grid
        grid_alpha = 0.08
        for gy in range(0, height, 80):
            cv2.line(frame, (0, gy), (width, gy), (45, 30, 15), 1)

        # 2. Draw 3D Wireframe Globe
        tilt = math.radians(23.5)
        cos_tilt = math.cos(tilt)
        sin_tilt = math.sin(tilt)

        # Latitude rings
        for lat_idx in range(1, lat_lines):
            lat = -math.pi / 2 + (math.pi / lat_lines) * lat_idx
            r_lat = globe_r * math.cos(lat)
            y_lat = globe_r * math.sin(lat)
            
            pts = []
            for seg in range(60):
                lon = (2 * math.pi / 60) * seg + angle_y
                x3 = r_lat * math.cos(lon)
                z3 = r_lat * math.sin(lon)
                
                # Apply tilt around X axis
                y3_t = y_lat * cos_tilt - z3 * sin_tilt
                z3_t = y_lat * sin_tilt + z3 * cos_tilt
                
                # Only draw front hemisphere for clean look with depth
                if z3_t > -100:
                    depth_factor = (z3_t + globe_r) / (2 * globe_r)
                    px = int(globe_cx + x3)
                    py = int(globe_cy + y3_t)
                    pts.append((px, py, depth_factor))
                else:
                    if len(pts) > 1:
                        for pi in range(len(pts) - 1):
                            df = pts[pi][2]
                            c_val = int(25 + 130 * df)
                            cv2.line(frame, (pts[pi][0], pts[pi][1]), (pts[pi+1][0], pts[pi+1][1]), (c_val, int(c_val*0.8), int(c_val*0.3)), 1, cv2.LINE_AA)
                    pts = []
            if len(pts) > 1:
                for pi in range(len(pts) - 1):
                    df = pts[pi][2]
                    c_val = int(25 + 130 * df)
                    cv2.line(frame, (pts[pi][0], pts[pi][1]), (pts[pi+1][0], pts[pi+1][1]), (c_val, int(c_val*0.8), int(c_val*0.3)), 1, cv2.LINE_AA)

        # Longitude rings
        for lon_idx in range(lon_lines):
            lon = (2 * math.pi / lon_lines) * lon_idx + angle_y
            pts = []
            for seg in range(40):
                lat = -math.pi / 2 + (math.pi / 40) * seg
                r_lat = globe_r * math.cos(lat)
                y_lat = globe_r * math.sin(lat)
                x3 = r_lat * math.cos(lon)
                z3 = r_lat * math.sin(lon)

                y3_t = y_lat * cos_tilt - z3 * sin_tilt
                z3_t = y_lat * sin_tilt + z3 * cos_tilt

                if z3_t > -80:
                    depth_factor = (z3_t + globe_r) / (2 * globe_r)
                    px = int(globe_cx + x3)
                    py = int(globe_cy + y3_t)
                    pts.append((px, py, depth_factor))
                else:
                    if len(pts) > 1:
                        for pi in range(len(pts) - 1):
                            df = pts[pi][2]
                            c_val = int(30 + 140 * df)
                            cv2.line(frame, (pts[pi][0], pts[pi][1]), (pts[pi+1][0], pts[pi+1][1]), (c_val, int(c_val*0.85), int(c_val*0.3)), 1, cv2.LINE_AA)
                    pts = []
            if len(pts) > 1:
                for pi in range(len(pts) - 1):
                    df = pts[pi][2]
                    c_val = int(30 + 140 * df)
                    cv2.line(frame, (pts[pi][0], pts[pi][1]), (pts[pi+1][0], pts[pi+1][1]), (c_val, int(c_val*0.85), int(c_val*0.3)), 1, cv2.LINE_AA)

        # Outer glowing atmosphere ring
        cv2.circle(frame, (globe_cx, globe_cy), globe_r + 4, (120, 70, 20), 2, cv2.LINE_AA)
        cv2.circle(frame, (globe_cx, globe_cy), globe_r + 15, (60, 35, 10), 1, cv2.LINE_AA)

        # 3. Floating Ambient Particles (Seamless loop using sin/cos displacement)
        for x0, y0, r_p, sx, sy, phase, col in p_data:
            # Periodic displacement
            dx = 40 * math.sin(2 * math.pi * t_norm + phase)
            dy = 80 * math.cos(2 * math.pi * t_norm + phase)
            px = int((x0 + dx) % width)
            py = int((y0 + dy) % height)

            alpha = 0.5 + 0.5 * math.sin(2 * math.pi * t_norm + phase)
            p_col = (int(col[0] * alpha), int(col[1] * alpha), int(col[2] * alpha))
            
            cv2.circle(frame, (px, py), int(r_p), p_col, -1, cv2.LINE_AA)
            cv2.circle(frame, (px, py), int(r_p * 2), (int(p_col[0]*0.3), int(p_col[1]*0.3), int(p_col[2]*0.3)), 1, cv2.LINE_AA)

        out.write(frame)

    out.release()

    # Re-encode with FFmpeg for clean H.264, web compatibility & tiny size
    cmd = [
        "ffmpeg", "-y", "-i", temp_raw,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "slow",
        output_path
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(temp_raw):
        os.remove(temp_raw)
    print(f"✅ Generated Cyber Blue Background: {output_path} ({os.path.getsize(output_path)/1024:.1f} KB)")


def create_amber_gold_particle_loop(output_path: str, width=1080, height=1920, fps=30, duration=6.0):
    """
    Generate 6.0s 100% seamless looping Warm Amber Gold Background:
    - Deep obsidian black/slate base (#09090b)
    - Warm glowing gold dust & bokeh particles floating upwards
    - Ambient radial glow pulse
    """
    total_frames = int(fps * duration)
    temp_raw = output_path.replace(".mp4", "_raw.mp4")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_raw, fourcc, fps, (width, height))

    base_bg = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        ratio = y / height
        # Gradient dark obsidian with faint warm dark amber bottom
        r = int(9 + 25 * ratio)
        g = int(9 + 15 * ratio)
        b = int(11 + 4 * ratio)
        base_bg[y, :] = [b, g, r]

    np.random.seed(101)
    num_particles = 90
    p_data = []
    for _ in range(num_particles):
        x0 = np.random.uniform(40, width - 40)
        y0 = np.random.uniform(50, height - 50)
        radius = np.random.uniform(3.0, 10.0)
        phase = np.random.uniform(0, 2 * math.pi)
        c_choice = np.random.choice([0, 1, 2, 3])
        if c_choice == 0:
            col = (11, 158, 245)   # Amber #f59e0b in BGR
        elif c_choice == 1:
            col = (36, 191, 251)   # Gold #fbbf24 in BGR
        elif c_choice == 2:
            col = (77, 211, 252)   # Light Yellow Gold in BGR
        else:
            col = (6, 119, 217)    # Deep Amber #d97706 in BGR
        p_data.append((x0, y0, radius, phase, col))

    for f in range(total_frames):
        t_norm = f / total_frames
        frame = base_bg.copy()

        # Radial soft pulse in center
        pulse_alpha = 0.08 + 0.04 * math.sin(2 * math.pi * t_norm)
        cv2.circle(frame, (540, 960), 450, (int(20 * pulse_alpha), int(60 * pulse_alpha), int(120 * pulse_alpha)), -1, cv2.LINE_AA)

        # Draw Golden Bokeh Dust & Particles
        for x0, y0, r_p, phase, col in p_data:
            # Seamless upward drift using modular math + sinusoidal drift
            drift_y = -height * t_norm
            curr_y = (y0 + drift_y) % height
            curr_x = x0 + 35 * math.sin(2 * math.pi * t_norm + phase)

            # Fade in at bottom, fade out at top
            edge_fade = math.sin((curr_y / height) * math.pi)
            intensity = (0.4 + 0.6 * math.sin(2 * math.pi * t_norm + phase)) * edge_fade

            b_c = int(col[0] * intensity)
            g_c = int(col[1] * intensity)
            r_c = int(col[2] * intensity)

            # Outer glow halo
            cv2.circle(frame, (int(curr_x), int(curr_y)), int(r_p * 2.2), (int(b_c*0.3), int(g_c*0.3), int(r_c*0.3)), -1, cv2.LINE_AA)
            # Solid core
            cv2.circle(frame, (int(curr_x), int(curr_y)), int(r_p), (b_c, g_c, r_c), -1, cv2.LINE_AA)

        out.write(frame)

    out.release()
    cmd = [
        "ffmpeg", "-y", "-i", temp_raw,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "slow",
        output_path
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(temp_raw):
        os.remove(temp_raw)
    print(f"✅ Generated Amber Gold Background: {output_path} ({os.path.getsize(output_path)/1024:.1f} KB)")


def create_emerald_matrix_loop(output_path: str, width=1080, height=1920, fps=30, duration=6.0):
    """
    Generate 6.0s 100% seamless looping Cyber Emerald Green Background:
    - Deep midnight green base (#022c22 / #051f18)
    - Flowing Aurora Matrix waves & mint glowing particles
    """
    total_frames = int(fps * duration)
    temp_raw = output_path.replace(".mp4", "_raw.mp4")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_raw, fourcc, fps, (width, height))

    base_bg = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        ratio = y / height
        r = int(2 + 8 * math.sin(ratio * math.pi))
        g = int(24 + 35 * math.sin(ratio * math.pi))
        b = int(18 + 20 * math.sin(ratio * math.pi))
        base_bg[y, :] = [b, g, r]

    np.random.seed(202)
    num_particles = 80
    p_data = []
    for _ in range(num_particles):
        x0 = np.random.uniform(40, width - 40)
        y0 = np.random.uniform(50, height - 50)
        radius = np.random.uniform(2.5, 7.0)
        phase = np.random.uniform(0, 2 * math.pi)
        c_choice = np.random.choice([0, 1, 2])
        if c_choice == 0:
            col = (129, 185, 16)   # Emerald #10b981 in BGR
        elif c_choice == 1:
            col = (153, 211, 52)   # Mint #34d399 in BGR
        else:
            col = (212, 182, 6)    # Cyber Cyan #06b6d4 in BGR
        p_data.append((x0, y0, radius, phase, col))

    for f in range(total_frames):
        t_norm = f / total_frames
        frame = base_bg.copy()

        # Draw 3 Smooth Aurora Flow Waves (Sine Waves with phase shift)
        for wave_i, (y_center, amp, freq, col_wave) in enumerate([
            (600, 120, 2.0, (80, 130, 10)),
            (1050, 160, 1.5, (100, 160, 15)),
            (1450, 100, 2.5, (90, 140, 20))
        ]):
            pts = []
            for px in range(0, width + 20, 20):
                wave_phase = 2 * math.pi * t_norm + (px / width) * freq * math.pi
                py = int(y_center + amp * math.sin(wave_phase))
                pts.append((px, py))
            for pi in range(len(pts) - 1):
                cv2.line(frame, pts[pi], pts[pi+1], col_wave, 3, cv2.LINE_AA)

        # Draw Floating Mint/Emerald Particles
        for x0, y0, r_p, phase, col in p_data:
            dx = 50 * math.sin(2 * math.pi * t_norm + phase)
            dy = 50 * math.cos(2 * math.pi * t_norm + phase)
            px = int((x0 + dx) % width)
            py = int((y0 + dy) % height)

            alpha = 0.4 + 0.6 * math.sin(2 * math.pi * t_norm + phase)
            b_c = int(col[0] * alpha)
            g_c = int(col[1] * alpha)
            r_c = int(col[2] * alpha)

            cv2.circle(frame, (px, py), int(r_p * 2), (int(b_c*0.25), int(g_c*0.25), int(r_c*0.25)), -1, cv2.LINE_AA)
            cv2.circle(frame, (px, py), int(r_p), (b_c, g_c, r_c), -1, cv2.LINE_AA)

        out.write(frame)

    out.release()
    cmd = [
        "ffmpeg", "-y", "-i", temp_raw,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "slow",
        output_path
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(temp_raw):
        os.remove(temp_raw)
    print(f"✅ Generated Emerald Background: {output_path} ({os.path.getsize(output_path)/1024:.1f} KB)")

if __name__ == "__main__":
    base_dir = "/media/vpsg16gb/HaRiDisk/CHANNELS/lelehoctiengtrung"
    create_cyber_blue_globe_loop(f"{base_dir}/pinyinquiz/assets/images/background.mp4")
    create_amber_gold_particle_loop(f"{base_dir}/vocabVNquiz/assets/images/background.mp4")
    create_emerald_matrix_loop(f"{base_dir}/vocabCNquiz/assets/images/background.mp4")
