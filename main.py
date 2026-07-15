"""互动地图游戏 - 使用 pgzero 实现

功能：
  1. 地图背景展示
  2. 鼠标悬停在兴趣点（POI）上时弹出菜单
  3. 菜单项：简介、习题
"""

import os
os.environ['SDL_VIDEO_CENTERED'] = '1'

# ── 应用图标 ──────────────────────────────────────────────
def _make_icon_png():
    """将军旗图片处理为 64x64 图标并保存"""
    from PIL import Image as PILImage
    icon_path = '/tmp/_red_army_icon.png'
    src = PILImage.open('images/junqi.jpeg')
    # 中心裁剪为正方形
    w, h = src.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    src = src.crop((left, top, left + side, top + side))
    # 缩放到 64x64
    src = src.resize((64, 64), PILImage.LANCZOS)
    src.save(icon_path, format='PNG')
    return icon_path

# 预生成图标文件
_ICON_PATH = _make_icon_png()

import pgzrun
import pygame
from map_data import POIS

# ── 窗口设置 ──────────────────────────────────────────────
WIDTH = 1096
HEIGHT = 800
TITLE = "互动地图"

# ── 字体 ───────────────────────────────────────────────────
FONT_NAME = "stheiti.ttc"

# ── 游戏 UI 颜色 ──────────────────────────────────────────
# RPG 暗色主题 + 金色/琥珀色点缀
COLOR_POI        = (220, 180, 60)     # 金铜色 POI 标记
COLOR_POI_GLOW   = (255, 200, 80)     # POI 发光色
COLOR_POI_RING   = (180, 140, 40)     # POI 外圈
COLOR_MENU_BG    = (20, 18, 30, 220)  # 深色半透明菜单背景
COLOR_MENU_BORDER = (180, 150, 60)    # 金色边框
COLOR_MENU_HOVER = (60, 55, 80, 200)  # 悬停项高亮
COLOR_MENU_ICON  = (255, 200, 80)     # 菜单图标色
COLOR_PANEL_BG   = (25, 22, 40, 240)  # 深色面板背景
COLOR_PANEL_BORDER = (160, 130, 50)   # 面板金色边框
COLOR_BTN        = (60, 55, 80)       # 按钮
COLOR_BTN_HOVER  = (100, 90, 130)     # 按钮悬停
COLOR_BTN_GOLD   = (180, 150, 60)     # 金色按钮
COLOR_TEXT       = (220, 215, 200)    # 米白文字
COLOR_TITLE      = (255, 200, 80)     # 金色标题
COLOR_FEEDBACK_OK = (80, 200, 80)     # 正确
COLOR_FEEDBACK_NO = (220, 80, 70)     # 错误
COLOR_CLOSE_BTN  = (180, 60, 50)      # 关闭按钮

# ── 状态 ──────────────────────────────────────────────────
mouse_pos = (0, 0)
hovered_poi = None          # 当前悬停的 POI 对象
menu_poi = None             # 菜单显示的 POI
menu_items = ["简介", "习题"]
menu_item_rects = []        # 菜单项矩形区域
selected_menu_idx = None    # 悬停的菜单项索引

# 菜单尺寸常量（与 draw_context_menu 保持一致）
MENU_W = 130
MENU_H = 38
MENU_PAD = 8

# 内容面板
panel_poi = None
panel_mode = None           # "intro" | "exercise"
panel_close_rect = None
exercise_idx = 0
feedback_msg = None
feedback_color = None
feedback_timer = 0
next_btn_rect = None        # "下一题" 按钮区域
exercise_done = False       # 是否已完成所有习题

# ── 地图背景 ──────────────────────────────────────────────
def draw_map():
    """绘制地图背景"""
    screen.blit("cz-bg", (0, 0))

# ── 工具函数 ──────────────────────────────────────────────
def get_menu_rect(poi):
    """计算给定 POI 的菜单整体范围矩形"""
    px, py = poi["x"], poi["y"]
    mx = px + 28
    my = py - 20
    if mx + MENU_W > WIDTH - 10:
        mx = px - MENU_W - 28
    if my + len(menu_items) * MENU_H > HEIGHT - 10:
        my = HEIGHT - 10 - len(menu_items) * MENU_H
    if my < 10:
        my = 10
    return Rect(mx - MENU_PAD, my - MENU_PAD,
                MENU_W + MENU_PAD * 2,
                len(menu_items) * MENU_H + MENU_PAD * 2)

def draw_rounded_rect(surf, rect, color, radius=8, border_color=None, border_width=2):
    """绘制圆角矩形（使用 pygame 的 gfxdraw 或 Surface）"""
    r = pygame.Rect(rect)
    # 创建带 alpha 的圆角表面
    s = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
    # 用圆角矩形填充
    pygame.draw.rect(s, color, (2, 2, r.w - 4, r.h - 4), border_radius=radius)
    if border_color:
        pygame.draw.rect(s, border_color, (2, 2, r.w - 4, r.h - 4), border_width, border_radius=radius)
    surf.blit(s, (r.x, r.y))

# ── POI 标记绘制 ──────────────────────────────────────────
def draw_poi_markers():
    """在地图上绘制兴趣点标记（黑色实心小圆）"""
    for poi in POIS:
        x, y = poi["x"], poi["y"]
        is_hovered = (poi is hovered_poi)
        # 悬停时发光外圈
        if is_hovered:
            for r in range(6, 0, -1):
                alpha = 20 + r * 6
                pygame.draw.circle(
                    screen.surface, (*COLOR_POI_GLOW[:3], alpha),
                    (x, y), 18 + r * 3, 2
                )
        # 黑色实心圆标记
        pygame.draw.circle(screen.surface, (0, 0, 0), (x, y), 2)

# ── 上下文菜单 ────────────────────────────────────────────
def draw_context_menu():
    """在悬停的 POI 旁绘制游戏风格菜单"""
    global menu_item_rects, selected_menu_idx
    if not hovered_poi:
        return
    px, py = hovered_poi["x"], hovered_poi["y"]
    menu_w, item_h = MENU_W, MENU_H
    pad = MENU_PAD
    mx = px + 28
    my = py - 20
    # 确保菜单不超出屏幕
    if mx + menu_w > WIDTH - 10:
        mx = px - menu_w - 28
    if my + len(menu_items) * item_h > HEIGHT - 10:
        my = HEIGHT - 10 - len(menu_items) * item_h
    if my < 10:
        my = 10

    # 菜单背景（圆角半透明）
    menu_rect = Rect(mx - pad, my - pad,
                     menu_w + pad * 2,
                     len(menu_items) * item_h + pad * 2)
    draw_rounded_rect(screen.surface, menu_rect, COLOR_MENU_BG,
                      radius=6, border_color=COLOR_MENU_BORDER, border_width=2)

    # 装饰顶线
    top_line = Rect(mx + 20, my - pad + 3, menu_w - 40, 2)
    pygame.draw.rect(screen.surface, (*COLOR_MENU_BORDER[:3], 60), top_line)

    # 图标
    icons = {"简介": "📖", "习题": "⚔"}

    menu_item_rects = []
    for i, item in enumerate(menu_items):
        ir = Rect(mx, my + i * item_h, menu_w, item_h)
        menu_item_rects.append(ir)
        hovered = (i == selected_menu_idx)
        if hovered:
            # 悬停高亮背景
            hl = Rect(mx, my + i * item_h, menu_w, item_h)
            draw_rounded_rect(screen.surface, hl, COLOR_MENU_HOVER, radius=4)
            # 左侧装饰条
            bar = Rect(mx, my + i * item_h + 6, 3, item_h - 12)
            pygame.draw.rect(screen.surface, COLOR_MENU_ICON, bar)
        # 图标
        icon_text = icons.get(item, "•")
        screen.draw.text(icon_text,
                         topleft=(mx + 10, my + i * item_h + 4),
                         fontname=FONT_NAME,
                         fontsize=16, color=COLOR_MENU_ICON)
        # 文字
        text_color = COLOR_TEXT if not hovered else (255, 230, 150)
        screen.draw.text(item,
                         topleft=(mx + 36, my + i * item_h + 5),
                         fontname=FONT_NAME,
                         fontsize=16, color=text_color)
        # 分隔线
        if i < len(menu_items) - 1:
            sep = Rect(mx + 15, ir.bottom - 1, menu_w - 30, 1)
            pygame.draw.rect(screen.surface, (*COLOR_MENU_BORDER[:3], 40), sep)

# ── 内容面板（简介 / 习题） ──────────────────────────────
def draw_content_panel():
    """绘制 RPG 风格的内容面板"""
    global panel_close_rect, feedback_msg, feedback_color
    if not panel_poi:
        return

    pw, ph = 420, 340
    px, py = (WIDTH - pw) // 2, (HEIGHT - ph) // 2
    panel_rect = Rect(px, py, pw, ph)

    # 半透明遮罩
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(140)
    overlay.fill((0, 0, 0))
    screen.surface.blit(overlay, (0, 0))

    # 面板阴影
    shadow_rect = Rect(px + 4, py + 4, pw, ph)
    shadow = pygame.Surface((pw, ph), pygame.SRCALPHA)
    shadow.fill((0, 0, 0, 80))
    screen.surface.blit(shadow, (px + 4, py + 4))

    # 面板主体（圆角半透明）
    draw_rounded_rect(screen.surface, panel_rect, COLOR_PANEL_BG,
                      radius=10, border_color=COLOR_PANEL_BORDER, border_width=2)

    # 装饰顶框
    top_bar = Rect(px + 2, py + 2, pw - 4, 4)
    pygame.draw.rect(screen.surface, COLOR_PANEL_BORDER, top_bar, border_radius=2)

    # 标题装饰：小菱形
    pygame.draw.polygon(screen.surface, COLOR_TITLE,
                        [(px + 18, py + 22), (px + 24, py + 16),
                         (px + 30, py + 22), (px + 24, py + 28)])

    # 标题
    screen.draw.text(panel_poi["name"],
                     topleft=(px + 38, py + 14),
                     fontname=FONT_NAME,
                     fontsize=20, color=COLOR_TITLE)

    # 关闭按钮（游戏风格 X）
    close_rect = Rect(px + pw - 38, py + 10, 28, 28)
    panel_close_rect = close_rect
    draw_rounded_rect(screen.surface, close_rect, COLOR_CLOSE_BTN, radius=4)
    screen.draw.text("✕", center=close_rect.center, fontname=FONT_NAME, fontsize=16, color=(255, 255, 255))

    if panel_mode == "intro":
        _draw_intro_content(px, py, pw, ph)
    elif panel_mode == "exercise":
        _draw_exercise_content(px, py, pw, ph)

def _get_font(size):
    """获取字体对象，优先使用项目字体，回退到系统字体"""
    import os
    font_path = os.path.join("fonts", FONT_NAME)
    try:
        return pygame.font.Font(font_path, size)
    except (FileNotFoundError, pygame.error):
        try:
            return pygame.font.SysFont(FONT_NAME.replace(".ttc", ""), size)
        except pygame.error:
            return pygame.font.Font(None, size)

def _render_text_line(font, text, x, y, color):
    """使用 pygame 字体渲染单行文字"""
    surf = font.render(text, True, color)
    screen.surface.blit(surf, (x, y))

def _load_poi_image(poi):
    """加载 POI 的配图（根据 poi["image"] 字段），缓存结果"""
    if not hasattr(_load_poi_image, "cache"):
        _load_poi_image.cache = {}
    img_name = poi.get("image")
    if not img_name:
        return None
    if img_name in _load_poi_image.cache:
        return _load_poi_image.cache[img_name]
    img_path = os.path.join("images", img_name)
    try:
        img = pygame.image.load(img_path).convert()
        _load_poi_image.cache[img_name] = img
        return img
    except (FileNotFoundError, pygame.error):
        _load_poi_image.cache[img_name] = None
        return None

def _draw_intro_content(px, py, pw, ph):
    """绘制古卷轴风格的简介内容"""
    # 计算配图尺寸（如有），在内容区域底部预留空间
    poi_img = _load_poi_image(panel_poi)
    img_display_w, img_display_h = 0, 0
    padding_bottom = 8
    if poi_img:
        img_w, img_h = poi_img.get_size()
        max_img_w = pw - 60
        max_img_h = 140
        scale = min(max_img_w / img_w, max_img_h / img_h, 1.0)
        img_display_w = int(img_w * scale)
        img_display_h = int(img_h * scale)

    # 内容区域——羊皮纸风格
    content_rect = Rect(px + 16, py + 50, pw - 32, ph - 70)
    scroll_surf = pygame.Surface((content_rect.w, content_rect.h), pygame.SRCALPHA)
    pygame.draw.rect(scroll_surf, (60, 52, 40, 230), (0, 0, content_rect.w, content_rect.h),
                     border_radius=4)
    for yy in (4, content_rect.h - 5):
        pygame.draw.rect(scroll_surf, (120, 100, 60, 100),
                         (10, yy, content_rect.w - 20, 2))
    for xx in (6, content_rect.w - 7):
        pygame.draw.line(scroll_surf, (120, 100, 60, 60),
                         (xx, 6), (xx, content_rect.h - 6))
    screen.surface.blit(scroll_surf, (content_rect.x, content_rect.y))

    # 小标题装饰图标
    screen.draw.text("◇ 介 绍 ◇",
                     center=(px + pw // 2, py + 56),
                     fontname=FONT_NAME,
                     fontsize=13, color=(180, 160, 100))

    # ── 手动换行绘制简介文字（预留图片空间） ──
    max_width = pw - 60
    line_height = 22
    text_x = px + 30
    text_y = py + 78
    # 文字可用底部边界（预留图片空间）
    text_bottom = py + 50 + (ph - 70) - padding_bottom
    if img_display_h > 0:
        text_bottom -= img_display_h + 6

    font = _get_font(16)
    text_color = (230, 215, 180)

    for paragraph in panel_poi["intro"].split("\n"):
        if text_y + line_height > text_bottom:
            break
        if not paragraph:
            text_y += line_height
            continue
        line = ""
        for ch in paragraph:
            test_line = line + ch
            if font.size(test_line)[0] > max_width:
                if text_y + line_height > text_bottom:
                    break
                _render_text_line(font, line, text_x, text_y, text_color)
                text_y += line_height
                line = ch
            else:
                line = test_line
        if line and text_y + line_height <= text_bottom:
            _render_text_line(font, line, text_x, text_y, text_color)
            text_y += line_height

    # ── 显示 POI 配图 ──
    if poi_img and img_display_h > 0:
        scaled = pygame.transform.smoothscale(poi_img, (img_display_w, img_display_h))
        img_x = px + (pw - img_display_w) // 2
        img_y = py + 50 + (ph - 70) - img_display_h - padding_bottom
        screen.surface.blit(scaled, (img_x, img_y))

def _draw_exercise_content(px, py, pw, ph):
    """绘制习题内容"""
    global feedback_msg, feedback_color, next_btn_rect, exercise_done

    # 内容区域背景
    content_rect = Rect(px + 16, py + 50, pw - 32, ph - 70)
    draw_rounded_rect(screen.surface, content_rect, (35, 32, 50, 200), radius=6)

    ex = panel_poi["exercises"]
    if not ex:
        screen.draw.text("暂无习题",
                         center=(px + pw // 2, py + ph // 2),
                         fontname=FONT_NAME,
                         fontsize=18, color=COLOR_TEXT)
        return

    # 全部完成
    if exercise_done:
        screen.draw.text("🎉 全部完成！",
                         center=(px + pw // 2, py + 100),
                         fontname=FONT_NAME,
                         fontsize=22, color=COLOR_FEEDBACK_OK)
        screen.draw.text(f"共完成 {len(ex)} 道题",
                         center=(px + pw // 2, py + 140),
                         fontname=FONT_NAME,
                         fontsize=16, color=COLOR_TEXT)
        return

    q = ex[exercise_idx]
    # 问题编号
    screen.draw.text(f"第 {exercise_idx + 1}/{len(ex)} 题",
                     topleft=(px + 30, py + 56),
                     fontname=FONT_NAME,
                     fontsize=12, color=(COLOR_MENU_BORDER[0], COLOR_MENU_BORDER[1], COLOR_MENU_BORDER[2], 150))

    # 问题文字
    screen.draw.text(q["q"],
                     topleft=(px + 30, py + 74),
                     fontname=FONT_NAME,
                     fontsize=16, color=COLOR_TEXT,
                     width=pw - 60)

    # 选项按钮（游戏风格）
    opt_y = py + 120
    for i, opt in enumerate(q["options"]):
        btn_rect = Rect(px + 30, opt_y + i * 42, pw - 60, 34)
        hovered = btn_rect.collidepoint(mouse_pos)
        bg = COLOR_BTN_HOVER if hovered else COLOR_BTN
        bc = COLOR_BTN_GOLD if hovered else (80, 75, 100)
        draw_rounded_rect(screen.surface, btn_rect, bg, radius=5,
                          border_color=bc, border_width=1 if not hovered else 2)
        # 选项字母
        letter = chr(65 + i)  # A, B, C, D
        screen.draw.text(f"{letter}",
                         topleft=(btn_rect.x + 10, btn_rect.y + 7),
                         fontname=FONT_NAME,
                         fontsize=14, color=COLOR_BTN_GOLD)
        screen.draw.text(opt,
                         topleft=(btn_rect.x + 32, btn_rect.y + 7),
                         fontname=FONT_NAME,
                         fontsize=14, color=COLOR_TEXT)

    # 反馈信息 + 下一题按钮（同一行，不重叠）
    if feedback_msg:
        fc = feedback_color or COLOR_TEXT
        fb_rect = Rect(px + 30, py + ph - 54, pw - 140, 30)
        fb_alpha = (*fc[:3], 30)
        draw_rounded_rect(screen.surface, fb_rect, fb_alpha, radius=4,
                          border_color=fc, border_width=1)
        screen.draw.text(feedback_msg,
                         center=fb_rect.center,
                         fontname=FONT_NAME,
                         fontsize=15, color=fc)

    # 回答正确后显示"下一题"按钮（在反馈文字右侧）
    if feedback_msg and feedback_color == COLOR_FEEDBACK_OK:
        next_btn_rect = Rect(px + pw - 110, py + ph - 54, 80, 30)
        hovered = next_btn_rect.collidepoint(mouse_pos)
        btn_bg = COLOR_BTN_GOLD if hovered else COLOR_BTN
        btn_border = (255, 220, 120) if hovered else COLOR_BTN_GOLD
        label = "完成" if exercise_idx + 1 >= len(ex) else "下一题 →"
        draw_rounded_rect(screen.surface, next_btn_rect, btn_bg, radius=5,
                          border_color=btn_border, border_width=2)
        screen.draw.text(label,
                         center=next_btn_rect.center,
                         fontname=FONT_NAME,
                         fontsize=14, color=COLOR_TEXT if not hovered else (255, 240, 200))
    else:
        next_btn_rect = None

# ── 逻辑更新 ──────────────────────────────────────────────
def update():
    pass  # 大部分逻辑在鼠标事件中处理

# ── 绘制 ──────────────────────────────────────────────────
_window_icon_set = False

def _set_dock_icon_via_ctypes():
    """通过 ctypes 调用 macOS AppKit 设置 Dock 图标（不干扰 SDL 事件循环）"""
    import ctypes
    import ctypes.util
    try:
        objc = ctypes.cdll.LoadLibrary('/usr/lib/libobjc.A.dylib')
        objc.objc_getClass.restype = ctypes.c_void_p
        objc.objc_getClass.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]
        objc.objc_msgSend.restype = ctypes.c_void_p
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

        # 加载 AppKit
        ctypes.cdll.LoadLibrary('/System/Library/Frameworks/AppKit.framework')

        # NSImage *img = [[NSImage alloc] initWithContentsOfFile:path]
        NSImage = objc.objc_getClass(b'NSImage')
        alloc_sel = objc.sel_registerName(b'alloc')
        init_sel = objc.sel_registerName(b'initWithContentsOfFile:')
        path = _ICON_PATH.encode('utf-8')
        img = objc.objc_msgSend(NSImage, alloc_sel)
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        img = objc.objc_msgSend(img, init_sel, ctypes.c_char_p(path))

        # [[NSApplication sharedApplication] setApplicationIconImage:img]
        NSApp = objc.objc_getClass(b'NSApplication')
        shared_sel = objc.sel_registerName(b'sharedApplication')
        app = objc.objc_msgSend(NSApp, shared_sel)
        set_icon_sel = objc.sel_registerName(b'setApplicationIconImage:')
        objc.objc_msgSend(app, set_icon_sel, img)
    except Exception:
        pass

def draw():
    global _window_icon_set
    if not _window_icon_set:
        try:
            icon_img = pygame.image.load(_ICON_PATH)
            pygame.display.set_icon(icon_img)
            _set_dock_icon_via_ctypes()
        except Exception:
            pass
        _window_icon_set = True
    screen.clear()
    draw_map()
    draw_poi_markers()
    draw_context_menu()
    draw_content_panel()

# ── 鼠标事件 ──────────────────────────────────────────────
def on_mouse_move(pos):
    global mouse_pos, hovered_poi, selected_menu_idx
    mouse_pos = pos

    # 如果面板打开，不处理地图悬停
    if panel_poi:
        hovered_poi = None
        selected_menu_idx = None
        return

    # 检测悬停 POI
    new_hovered = None
    for poi in POIS:
        dx = pos[0] - poi["x"]
        dy = pos[1] - poi["y"]
        if dx * dx + dy * dy <= poi["radius"] * poi["radius"]:
            new_hovered = poi
            break

    # 保持菜单可见：如果鼠标在之前 POI 的菜单区域内，不切换
    # 无论鼠标进入另一个 POI 的感应区还是离开所有 POI，都优先保留当前菜单
    if hovered_poi is not None:
        on_menu = any(ir.collidepoint(pos) for ir in menu_item_rects)
        if not on_menu:
            menu_rect = get_menu_rect(hovered_poi)
            if not menu_rect.collidepoint(pos):
                hovered_poi = new_hovered
    else:
        hovered_poi = new_hovered

    # 检测菜单项悬停
    selected_menu_idx = None
    if hovered_poi:
        for i, ir in enumerate(menu_item_rects):
            if ir.collidepoint(pos):
                selected_menu_idx = i
                break

def on_mouse_down(pos, button):
    global panel_poi, panel_mode, menu_poi, exercise_idx
    global feedback_msg, feedback_color, feedback_timer, hovered_poi
    global exercise_done

    # ── 关闭面板 ──
    if panel_poi and panel_close_rect and panel_close_rect.collidepoint(pos):
        panel_poi = None
        panel_mode = None
        feedback_msg = None
        exercise_idx = 0
        exercise_done = False
        return

    # ── 面板打开时，处理习题点击 ──
    if panel_poi and panel_mode == "exercise":
        if _handle_exercise_click(pos):
            return

    # ── 点击菜单项 ──
    if hovered_poi and selected_menu_idx is not None:
        item = menu_items[selected_menu_idx]
        panel_poi = hovered_poi
        feedback_msg = None
        exercise_idx = 0
        exercise_done = False
        if item == "简介":
            panel_mode = "intro"
        elif item == "习题":
            panel_mode = "exercise"
        return

    # ── 点击空白区域关闭菜单 ──
    hovered_poi = None

def _handle_exercise_click(pos):
    """处理习题面板中的选项点击，返回 True 表示已处理"""
    global feedback_msg, feedback_color, exercise_idx, exercise_done
    pw, ph = 420, 340
    px, py = (WIDTH - pw) // 2, (HEIGHT - ph) // 2
    ex = panel_poi["exercises"]
    if not ex:
        return False

    # ── 点击"下一题"按钮 ──
    if next_btn_rect and next_btn_rect.collidepoint(pos):
        if exercise_idx + 1 >= len(ex):
            exercise_done = True
        else:
            exercise_idx += 1
        feedback_msg = None
        feedback_color = None
        return True

    # ── 点击选项按钮 ──
    q = ex[exercise_idx]
    opt_y = py + 120
    for i, opt in enumerate(q["options"]):
        btn_rect = Rect(px + 30, opt_y + i * 42, pw - 60, 34)
        if btn_rect.collidepoint(pos):
            if opt == q["a"]:
                feedback_msg = "✓ 回答正确！"
                feedback_color = COLOR_FEEDBACK_OK
            else:
                feedback_msg = f"✗ 回答错误，正确答案是：{q['a']}"
                feedback_color = COLOR_FEEDBACK_NO
            return True
    return False

# ── 启动 ──────────────────────────────────────────────────
pgzrun.go()
