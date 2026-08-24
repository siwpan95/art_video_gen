    # ===================== 公式驱动 =====================
    @staticmethod
    def _gen_formula(video_writer, w, h, num_frames, fps,
                             palette_name, speed,
                             audio_features=None, audio_reactive=0.5, progress_callback=None):
        """
        公式驱动效果：使用 effects_engine/formula_engine.py 的数学表达式渲染图案。
        支持多种内置模板（spiral, cardioid, lissajous, rose, butterfly 等）。
        音频驱动：音量→公式参数，频率→颜色映射。
        """
        import math, random
        import numpy as np

        from effects_engine.formula_engine import FormulaEngine

        palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
        colors = np.array(palette_info["colors"], dtype=np.float32)
        bg_color = np.array(palette_info["bg"], dtype=np.uint8)

        engine = FormulaEngine()
        template_names = list(engine.TEMPLATES.keys())
        chosen = random.choice(template_names)
        template = engine.get_template_params(chosen)

        x_func = engine.compile_template(chosen, 'x')
        y_func = engine.compile_template(chosen, 'y')

        t_min = template.get('t_min', 0)
        t_max = template.get('t_max', 12.56)
        t_step = template.get('t_step', 0.05)
        t_vals = np.arange(t_min, t_max, t_step)
        n_pts = len(t_vals)

        x_static = x_func(t=t_vals)
        y_static = y_func(t=t_vals)

        for i in range(num_frames):
            vol = 1.0
            bass = 0.0
            onset = 0.0
            if audio_features and i < len(audio_features):
                feat = audio_features[i]
                vol = 1.0 + feat["volume"] * audio_reactive * 1.5
                bass = feat["bass"] * audio_reactive
                onset = feat["onset"] * audio_reactive

            scale = 1.0 + vol * 0.3
            rot = (i * 0.005 * speed) % (2 * math.pi)
            color_off = (i * 0.002 * speed) % 1.0

            cos_r = math.cos(rot)
            sin_r = math.sin(rot)
            x_rot = (x_static * cos_r - y_static * sin_r) * scale
            y_rot = (x_static * sin_r + y_static * cos_r) * scale

            pts_x = ((x_rot + 1.0) * 0.5 * w).astype(np.int32)
            pts_y = ((y_rot + 1.0) * 0.5 * h).astype(np.int32)

            mask = (pts_x >= 0) & (pts_x < w) & (pts_y >= 0) & (pts_y < h)
            pts_x = pts_x[mask]
            pts_y = pts_y[mask]

            frame = np.zeros((h, w, 3), dtype=np.uint8)
            frame[:, :] = bg_color

            n_valid = len(pts_x)
            col_off = int(color_off * len(colors)) % len(colors)

            for pi in range(n_valid - 1):
                x0, y0 = int(pts_x[pi]), int(pts_y[pi])
                x1, y1 = int(pts_x[pi + 1]), int(pts_y[pi + 1])
                ci = (pi + col_off) % len(colors)
                cr, cg, cb = int(colors[ci][0]), int(colors[ci][1]), int(colors[ci][2])
                thickness = max(1, int(1 + vol * 2))
                # 简化绘制：直接画点
                for dx2 in range(-thickness, thickness + 1):
                    for dy2 in range(-thickness, thickness + 1):
                        nx, ny = x0 + dx2, y0 + dy2
                        if 0 <= nx < w and 0 <= ny < h:
                            frame[ny, nx, 0] = min(255, cr)
                            frame[ny, nx, 1] = min(255, cg)
                            frame[ny, nx, 2] = min(255, cb)

            if onset > 0.3:
                cx2, cy2 = w // 2, h // 2
                try:
                    import cv2
                    cv2.circle(frame, (cx2, cy2), int(min(w, h) * 0.1 * bass * 5),
                              (255, 255, 255), -1)
                except ImportError:
                    pass

            video_writer.write(frame)
            if progress_callback and i % 10 == 0:
                progress_callback(int((i / num_frames) * 100))
            if i % 50 == 0:
                print(f"   进度: {i}/{num_frames} 帧 (模板: {chosen})")

        print(f"[OK] 公式驱动视频已保存")
        return True

    # ===================== 流体模拟 =====================
    @staticmethod
    def _gen_fluid(video_writer, w, h, num_frames, fps,
                           palette_name, speed,
                           audio_features=None, audio_reactive=0.5, progress_callback=None):
        """
        流体模拟效果：使用 effects_engine/fluid_engine.py 的 Stable Fluids 算法。
        """
        import math, random
        import numpy as np

        from effects_engine.fluid_engine import FluidEngine, COLOR_MAPS

        palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
        bg_color = np.array(palette_info["bg"]), dtype=np.uint8)

        grid_w = max(32, w // 4)
        grid_h = max(32, h // 4)
        color_map = random.choice(list(COLOR_MAPS.keys()))
        fluid = FluidEngine(grid_w=grid_w, grid_h=grid_h, color_map=color_map)

        cx = grid_w // 2
        cy = grid_h // 2
        fluid.add_density_at(cx, cy, amount=0.5, radius=grid_w * 0.1)

        for i in range(num_frames):
            vol = 1.0
            bass = 0.0
            onset = 0.0
            if audio_features and i < len(audio_features):
                feat = audio_features[i]
                vol = 1.0 + feat["volume"] * audio_reactive * 2.0
                bass = feat["bass"] * audio_reactive
                onset = feat["onset"] * audio_reactive

            if random.random() < 0.1 + vol * 0.2:
                fx = random.randint(1, grid_w - 2)
                fy = random.randint(1, grid_h - 2)
                fluid.add_density_at(fx, fy, amount=0.05 * vol, radius=2.0)

            if onset > 0.4:
                fx = random.randint(1, grid_w - 2)
                fy = random.randint(1, grid_h - 2)
                fluid.add_density_at(fx, fy, amount=0.2 * vol, radius=grid_w * 0.05)

            force_x = math.sin(i * 0.01 * speed) * 3.0 * vol
            force_y = math.cos(i * 0.008 * speed) * 3.0 * vol
            fluid.add_force_at(cx, cy, force_x, force_y, radius=grid_w * 0.08, dt=1.0 / fps)

            fluid.step(dt=1.0 / fps * speed, audio=None)

            frame_rgb = fluid.render_to_numpy(w, h)
            if frame_rgb is not None:
                final = np.zeros((h, w, 3), dtype=np.uint8)
                final[:, :] = bg_color
                # 简化叠加
                for y in range(h):
                    for x in range(w):
                        f = frame_rgb[y, x]
                        if f[0] > 10 or f[1] > 10 or f[2] > 10:
                            a = min(1.0, (f[0] + f[1] + f[2]) / (3 * 255))
                            final[y, x] = [
                                int(bg_color[0] * (1 - a) + f[0] * a),
                                int(bg_color[1] * (1 - a) + f[1] * a),
                                int(bg_color[2] * (1 - a) + f[2] * a),
                            ]
                video_writer.write(final)
            else:
                video_writer.write(np.zeros((h, w, 3), dtype=np.uint8))

            if progress_callback and i % 5 == 0:
                progress_callback(int((i / num_frames) * 100))
            if i % 50 == 0:
                print(f"   进度: {i}/{num_frames} 帧")

        print(f"[OK] 流体模拟视频已保存")
        return True
