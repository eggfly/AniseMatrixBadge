# tetris_ai_safe.py
# 16x9 自动俄罗斯方块（不会死亡，持续运行），适配 IS31 点阵
# 包含未来场景 AI、闪行动画、死亡监测与自动重开

import is31
from machine import SoftI2C, Pin
import time, random
import math

# --------- DISPLAY SETUP ----------
i2c = SoftI2C(scl=Pin(1), sda=Pin(0))
display = is31.Matrix(i2c)

W = 9
H = 16
FRAME_DELAY = 0.02

# 方块色值
PALETTE = {'I':220,'O':170,'T':150,'S':100,'Z':80,'J':40,'L':20,' ':0}

# --------- TETROMINO 定义 ----------
TETROMINOES = {
    'I': [[1,1,1,1]],
    'O': [[1,1],[1,1]],
    'T': [[0,1,0],[1,1,1]],
    'S': [[0,1,1],[1,1,0]],
    'Z': [[1,1,0],[0,1,1]],
    'J': [[1,0,0],[1,1,1]],
    'L': [[0,0,1],[1,1,1]]
}

# ---------- 旋转、normalize、比较 ----------
def rotate90(m):
    h = len(m); w = len(m[0])
    out = [[0]*h for _ in range(w)]
    for y in range(h):
        for x in range(w):
            out[x][h-1-y] = m[y][x]
    return out

def normalize_matrix(m):
    h = len(m); w = len(m[0])
    top=0; bot=h-1; left=0; right=w-1
    while top<h and all(v==0 for v in m[top]): top+=1
    while bot>=0 and all(v==0 for v in m[bot]): bot-=1
    while left<w and all(m[r][left]==0 for r in range(h)): left+=1
    while right>=0 and all(m[r][right]==0 for r in range(h)): right-=1
    if top>bot or left>right: return [[0]]
    return [m[r][left:right+1] for r in range(top,bot+1)]

def equal_matrix(a,b):
    if len(a)!=len(b) or len(a[0])!=len(b[0]): return False
    for y in range(len(a)):
        for x in range(len(a[0])):
            if a[y][x]!=b[y][x]: return False
    return True

def rotations(mat):
    rots=[]
    cur=normalize_matrix(mat)
    rots.append(cur)
    for _ in range(3):
        cur=rotate90(cur)
        cur=normalize_matrix(cur)
        if not any(equal_matrix(cur,r) for r in rots):
            rots.append(cur)
    return rots

PIECES = {k:rotations(mat) for k,mat in TETROMINOES.items()}

# ---------- 网格工具 ----------
def empty_grid():
    return [[0]*W for _ in range(H)]

def clone_grid(g):
    return [row[:] for row in g]

def is_occupied_val(v):
    return v!=0

def can_place(grid, shape, x, y):
    sh_h = len(shape); sh_w = len(shape[0])
    for ry in range(sh_h):
        for rx in range(sh_w):
            if shape[ry][rx]:
                gx = x+rx; gy=y+ry
                if gx<0 or gx>=W or gy<0 or gy>=H: return False
                if is_occupied_val(grid[gy][gx]): return False
    return True

def place_on(grid, shape, x, y, val):
    sh_h=len(shape); sh_w=len(shape[0])
    for ry in range(sh_h):
        for rx in range(sh_w):
            if shape[ry][rx]:
                gx=x+rx; gy=y+ry
                if 0<=gx<W and 0<=gy<H:
                    grid[gy][gx]=val

def clear_lines(grid):
    cleared=0; new=[]
    for row in grid:
        if all(is_occupied_val(v) for v in row):
            cleared+=1
        else:
            new.append(row)
    while len(new)<H: new.insert(0,[0]*W)
    return new, cleared

# ---------- AI 评估函数 ----------
def column_heights(grid):
    heights=[0]*W
    for x in range(W):
        for y in range(H):
            if is_occupied_val(grid[y][x]):
                heights[x]=H-y
                break
    return heights

def count_holes(grid):
    holes=0
    for x in range(W):
        filled=False
        for y in range(H):
            if is_occupied_val(grid[y][x]): filled=True
            elif filled: holes+=1
    return holes

def evaluate_grid(grid, lines_cleared):
    heights=column_heights(grid)
    max_h=max(heights); min_h=min(heights)
    agg=sum(heights)
    std_h=math.sqrt(sum((h-agg/len(heights))**2 for h in heights)/len(heights))
    first_diff=[heights[i+1]-heights[i] for i in range(len(heights)-1)]
    std_diff=math.sqrt(sum((d-sum(first_diff)/len(first_diff))**2 for d in first_diff)/len(first_diff)) if first_diff else 0
    blocks=sum(sum(1 for v in row if v!=0) for row in grid)
    score=(
        lines_cleared*1000-
        count_holes(grid)*250-
        blocks*10-
        max_h*5-
        std_h*2-
        sum(abs(d) for d in first_diff)*2-
        std_diff*2-
        (max_h-min_h)*2
    )
    return score

# ---------- AI 选择最优位置 ----------
def choose_best_placement_fast(grid, cur_key):
    best_score=-10**9; best_move=None
    cur_rots=PIECES[cur_key]
    for rot_idx, shape in enumerate(cur_rots):
        sh_h, sh_w=len(shape), len(shape[0])
        for x in range(-sh_w+1, W):
            y=0
            if not can_place(grid, shape, x, y): continue
            while can_place(grid, shape, x, y+1): y+=1
            # 临时放置
            for ry in range(sh_h):
                for rx in range(sh_w):
                    if shape[ry][rx]:
                        gx=x+rx; gy=y+ry
                        if 0<=gx<W and 0<=gy<H: grid[gy][gx]=1
            _, lines_cleared=clear_lines(grid)
            score=evaluate_grid(grid, lines_cleared)
            # 清除临时
            for ry in range(sh_h):
                for rx in range(sh_w):
                    if shape[ry][rx]:
                        gx=x+rx; gy=y+ry
                        if 0<=gx<W and 0<=gy<H: grid[gy][gx]=0
            if score>best_score:
                best_score=score
                best_move=(rot_idx,x,y)
    return best_move

# ---------- 游戏死亡检测 ----------
def is_gameover(grid):
    return any(is_occupied_val(v) for v in grid[0])

# ---------- 闪行动画 ----------
def flash_lines(grid, lines, flashes=2, delay=0.1):
    for _ in range(flashes):
        for y in lines:
            grid[y] = [0]*W
        draw_frame(grid)
        time.sleep(delay)
        for y in lines:
            grid[y] = [PALETTE.get('O',120)]*W
        draw_frame(grid)
        time.sleep(delay)

# ---------- 渲染 ----------
def draw_frame(grid, current_piece=None, piece_pos=None, piece_shape=None, current_piece_val=120):
    pixels=[[0]*W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            if is_occupied_val(grid[y][x]): pixels[y][x]=grid[y][x]
    if current_piece and piece_shape and piece_pos:
        px,py=piece_pos
        for ry in range(len(piece_shape)):
            for rx in range(len(piece_shape[0])):
                if piece_shape[ry][rx]:
                    gx,gy=px+rx,py+ry
                    if 0<=gx<W and 0<=gy<H: pixels[gy][gx]=current_piece_val
    for y in range(H):
        for x in range(W):
            color=pixels[y][x]
            new_y=H-1-y
            new_x=x
            try: display.pixel(new_y,new_x,color)
            except: pass

# ---------- 简单移动/旋转 helpers ----------
def step_toward(current,target,modulo):
    if current==target: return current
    diff=(target-current)%modulo
    if diff<=modulo//2: return (current+1)%modulo
    else: return (current-1)%modulo

# ---------- 主循环 ----------
def main_loop():
    while True:
        grid=empty_grid()
        frame=0
        gravity_interval=1
        current=None
        piece_x=piece_y=0
        piece_shape=None
        piece_key=None
        rot_index=0

        # 游戏循环
        while True:
            if is_gameover(grid):
                # 清屏重开
                for y in range(H):
                    for x in range(W):
                        display.pixel(y,x,0)
                time.sleep(0.5)
                break  # 重新初始化

            # spawn new piece
            if current is None:
                piece_key=random.choice(list(PIECES.keys()))
                rots=PIECES[piece_key]
                init_rot=0
                piece_shape=rots[init_rot]
                piece_x=(W-len(piece_shape[0]))//2
                piece_y=0

                # choose best move (考虑下一个随机块)
                next_piece=random.choice(list(PIECES.keys()))
                best=choose_best_placement_fast(grid,piece_key)
                if best:
                    target_rot,target_x,target_y=best
                else:
                    target_rot,target_x=0,piece_x

                current={'key':piece_key,'rots':rots,'rot_idx':init_rot,
                         'target_rot':target_rot,'target_x':target_x,
                         'val':PALETTE.get(piece_key,255)}
                piece_shape=rots[current['rot_idx']]

            # gravity tick
            if frame%gravity_interval==0 and current:
                # 旋转动作在方块出现后才开始
                if piece_y>0 and current['rot_idx']!=current['target_rot']:
                    next_rot=step_toward(current['rot_idx'],current['target_rot'],len(current['rots']))
                    next_shape=current['rots'][next_rot]
                    kicks=[0,-1,1]
                    rotated_ok=False
                    for kx in kicks:
                        if can_place(grid,next_shape,piece_x+kx,piece_y):
                            piece_x+=kx
                            current['rot_idx']=next_rot
                            piece_shape=next_shape
                            rotated_ok=True
                            break

                # 水平移动
                step=0
                if piece_x<current['target_x']: step=1
                elif piece_x>current['target_x']: step=-1
                if step!=0 and can_place(grid,piece_shape,piece_x+step,piece_y):
                    piece_x+=step

                # 下落
                if can_place(grid,piece_shape,piece_x,piece_y+1):
                    piece_y+=1
                else:
                    # lock piece
                    place_on(grid,piece_shape,piece_x,piece_y,current['val'])
                    # 检查消行
                    new_grid=[]
                    lines=[]
                    for y in range(H):
                        if all(is_occupied_val(v) for v in grid[y]): lines.append(y)
                    if lines:
                        flash_lines(grid,lines)
                        grid,_=clear_lines(grid)
                    current=None
                    piece_shape=None

            draw_frame(grid,current_piece=(current is not None),
                       piece_pos=(piece_x,piece_y) if current else None,
                       piece_shape=piece_shape,
                       current_piece_val=(current['val'] if current else 120))

            frame+=1
            time.sleep(FRAME_DELAY)

# ---------- 运行 ----------
if __name__=="__main__":
    main_loop()
