#------------------------------------------------------------------------------

from raylib import *
from pyray import Camera3D, Mesh, Model, Vector2, Vector3, BoundingBox, Texture2D, Color
# no idea why, but the `raylib` type import stuff just doesn't work?
from typing import Tuple, List, Any
from time import sleep, time
from math import floor as _floor

#------------------------------------------------------------------------------

def wrzUpdateCamera(camera : Camera3D):
    def camera_move_speed(speed = 7.6):
        is_diagonal = False

        if (IsKeyDown(KEY_W) or IsKeyDown(KEY_S)) and (IsKeyDown(KEY_A) or IsKeyDown(KEY_D)): is_diagonal = True
        if is_diagonal: return speed * 0.707 * GetFrameTime()
        return speed * GetFrameTime()

    def CameraYaw(camera : Camera3D, angle):
        up = camera.up
        target_pos = Vector3Subtract(camera.target, camera.position)
        target_pos = Vector3RotateByAxisAngle(target_pos, up, angle)

        camera.target = Vector3Add(camera.position, target_pos)

    def CameraPitch(camera : Camera3D, angle):
        up = camera.up
        target_pos = Vector3Subtract(camera.target, camera.position)

        # if lock_view:

        max_angle_up = Vector3Angle(up, target_pos)
        max_angle_up -= 0.001

        max_angle_down = Vector3Angle(Vector3Negate(up), target_pos)
        max_angle_down *= -1
        max_angle_down += 0.001

        angle = Clamp(angle, max_angle_down, max_angle_up)

        right = Vector3Normalize(Vector3CrossProduct(Vector3Normalize(Vector3Subtract(camera.target, camera.position)), up))

        target_pos = Vector3RotateByAxisAngle(target_pos, right, angle)

        camera.target = Vector3Add(camera.position, target_pos)

    def CameraMoveForward(camera : Camera3D, distance):
        forward = Vector3Normalize(Vector3Subtract(camera.target, camera.position))
        
        # if moveInWorldPlane:
        forward.y = 0
        forward = Vector3Normalize(forward)

        forward = Vector3Scale(forward, distance)

        camera.position = Vector3Add(camera.position, forward)
        camera.target = Vector3Add(camera.target, forward)

    def CameraMoveRight(camera : Camera3D, distance):
        right = Vector3Normalize(Vector3CrossProduct(Vector3Normalize(Vector3Subtract(camera.target, camera.position)), camera.up))
        
        # if moveInWorldPlane:
        right.y = 0
        right = Vector3Normalize(right)

        right = Vector3Scale(right, distance)

        camera.position = Vector3Add(camera.position, right)
        camera.target = Vector3Add(camera.target, right)
    
    def CameraMoveUp(camera : Camera3D, distance):
        up = camera.up

        up = Vector3Scale(up, distance)

        camera.position = Vector3Add(camera.position, up)
        camera.target = Vector3Add(camera.target, up)

    mouse_pos_delta = GetMouseDelta()
    sensitivity = 0.003

    CameraYaw(camera, -mouse_pos_delta.x*sensitivity)
    CameraPitch(camera, -mouse_pos_delta.y*sensitivity)

    if IsKeyDown(KEY_W): CameraMoveForward(camera, camera_move_speed())
    if IsKeyDown(KEY_S): CameraMoveForward(camera, -1 * camera_move_speed())

    if IsKeyDown(KEY_D): CameraMoveRight(camera, camera_move_speed())
    if IsKeyDown(KEY_A): CameraMoveRight(camera, -1 * camera_move_speed())

    def inv_sign(n):
        return n < 0
    
    if abs(camera.position.x) > 50:
        camera.position.x = 49 * inv_sign(camera.position.x)
    if abs(camera.position.z) > 50:
        camera.position.z = 49 * inv_sign(camera.position.x)

    # if IsKeyDown(KEY_SPACE): CameraMoveUp(camera, camera_move_speed())
    # if IsKeyDown(KEY_LEFT_SHIFT): CameraMoveUp(camera, -1 * camera_move_speed())  

#------------------------------------------------------------------------------

def wrzPrettyText(text, x, y, font_size, color = WHITE, background_color = BLACK):
    DrawText(text.encode(), x + 2, y + 2, font_size, background_color)
    DrawText(text.encode(), x, y, font_size, color)

def wrzModel(mesh : Mesh, texture) -> Model:
    model : Model = LoadModelFromMesh(mesh)
    if texture is not None: model.materials[0].maps[MATERIAL_MAP_ALBEDO].texture = texture
    bb : BoundingBox = GetMeshBoundingBox(mesh)

    return model

#------------------------------------------------------------------------------

things = []

class Thing:
    model : Model
    position : Vector3
    rotation : Vector3
    angle : float
    color : Color
    size : Any
    bb : BoundingBox
    # for spheres, this is the radius
    # for boxes, these are the dimensions

    def __init__(self, mesh, pos, rot, angle, color, size, texture = None):
        self.model = wrzModel(mesh, texture)

        self.position = Vector3(pos[0], pos[1], pos[2])
        self.rotation = rot
        self.angle = angle
        self.color = color

        match(len(size)):
            case 1:
                self.size : float = size[0]
                self.bb = None
            case 2:
                self.size : Vector2 = Vector2(size[0], size[1])
                self.bb = None
            case 3:
                self.size : Vector3 = Vector3(size[0], size[1], size[2])
                a = self.position.x - (0.5 * self.size.x)
                b = self.position.y - (0.5 * self.size.y)
                c = self.position.z - (0.5 * self.size.z)
                j = self.position.x + (0.5 * self.size.x)
                k = self.position.y + (0.5 * self.size.y)
                l = self.position.z + (0.5 * self.size.z)
                bb : BoundingBox = Vector3(a, b, c), Vector3(j, k, l)
                if angle == 90 or angle == 270:
                    bb = Vector3(c, b, a), Vector3(l, k, j)
                self.bb = bb
            case _:
                self.size : List[float] = size
                self.bb = None
            
        things.append(self)

#------------------------------------------------------------------------------

g = -9.8
mu_floor = 0.2
mu_board = 0.1
yao_speed = 5.8

def wrzBouncingBall(camera, score, b_p : Tuple, b_v : Tuple, b_r : float, ball : Thing, backboards : List[Thing]) -> Tuple | Tuple:

    # apply gravity

    b_a = (0, g, 0)
    b_v = Vector3Add(b_v, Vector3Scale(b_a, GetFrameTime()))
    b_p = Vector3Add(b_p, Vector3Scale(b_v, GetFrameTime()))

    if b_p.y < b_r:
        b_p.y = b_r
        b_v.y = -1 * b_v.y
        b_v = Vector3Scale(b_v, 1 - mu_floor)
    
    if abs(b_p.x) > 50:
        b_v.x = -1.2 * b_v.x
    if abs(b_p.z) > 50:
        b_v.z = -1.2 * b_v.z

    # find inner planes of each backboard

    for b in backboards:
        orientation = True if (b.size.x > b.size.z) else False

        # bb : BoundingBox = Vector3(b.position.x - (0.5 * b.size.x), b.position.y - (0.5 * b.size.y), b.position.z - (0.5 * b.size.z])), Vector3(b.position.x + (0.5 * b.size.x), b.position.y + (0.5 * b.size.y), b.position.z + (0.5 * b.size.z))

        if CheckCollisionBoxSphere(b.bb, b_p, b_r):
            if orientation: # backboard is facing the z-direction
                normal = (0, 0, 1)
            else:
                normal = (1, 0, 0)
            
            b_v = Vector3Reflect(b_v, normal)
            b_v = Vector3Add(b_v, Vector3Negate(normal))

            score += 20
        # print(normal_vector.x, normal_vector.y, normal_vector.z)
        # exit()
    
    if Vector3Length(b_v) > 1000:
        b_p = (0, 2, 0)
        b_v = (0, 1, 0)
    
    return b_p, b_v, score

def wrzGrabBall(camera : Camera3D, b_p : Tuple, b_r : float) -> bool:
    forward = Vector3Normalize(Vector3Subtract(camera.target, camera.position))
        
    forward.y = 0
    forward = Vector3Normalize(forward)

    return CheckCollisionCircleLine((b_p.x, b_p.z), b_r, (camera.position.x, camera.position.z), Vector2Add((camera.position.x, camera.position.z), (forward.x, forward.z)))
  
def wrzMingChase(score, yao : Thing, y_v : Tuple, ball : Thing) -> Tuple | Tuple:
    forward = Vector3Subtract(ball.position, yao.position)

    y_v = Vector3Scale(Vector3Normalize(Vector3Add(y_v, Vector3Scale(forward, GetFrameTime()))), yao_speed)
    y_p = Vector3Add(yao.position, Vector3Scale(y_v, GetFrameTime()))
    if y_p.y < yao.size / 2:
        y_p.y = yao.size / 2
    
    if Vector2Distance(Vector2(yao.position.x, yao.position.z), Vector2(ball.position.x, ball.position.z)) < 1:
        score -= 1

    return y_p, y_v, score

#------------------------------------------------------------------------------

global fullscreen

def wrzToggleFullscreen(fullscreen):
    if not fullscreen:
        WIDTH = GetMonitorWidth(GetCurrentMonitor()) // 2
        HEIGHT = GetMonitorHeight(GetCurrentMonitor()) // 2
    else:
        WIDTH = GetMonitorWidth(GetCurrentMonitor())
        HEIGHT = GetMonitorHeight(GetCurrentMonitor())

    SetWindowSize(WIDTH, HEIGHT)
    
    if not fullscreen: SetWindowPosition(WIDTH // 2, HEIGHT // 2)
    else: ToggleFullscreen()

    return not fullscreen

#------------------------------------------------------------------------------

def main():

    #------------------------------------------------------------------------------

    WIDTH = 20
    HEIGHT = 20
    
    InitWindow(WIDTH, HEIGHT, b"WRZ: 3D Test")

    InitAudioDevice()

    SetTargetFPS(120)

    start_time = time()

    fullscreen = wrzToggleFullscreen(False)
    WIDTH = GetScreenWidth()
    HEIGHT = GetScreenWidth()

    camera = Camera3D((0, 2, 0), (1, 2, 0), (0, 1, 0), 90, CAMERA_PERSPECTIVE)

    DisableCursor()

    #------------------------------------------------------------------------------
    
    b_p = (0, 4, 0)
    b_v = (0, 1, 0)
    b_r = 0.5

    y_v = (0, 0, 0)

    ming_height = 5

    #------------------------------------------------------------------------------
    
    tex : Texture2D = LoadTexture(b"bobdole.bmp")    
    ming : Texture2D = LoadTexture(b"ming.jpg")
    
    #------------------------------------------------------------------------------
    
    floor = Thing(GenMeshPlane(100, 100, 1, 1), (0, 0, 0), (0, 1, 0), 0, BROWN, [100, 100], tex)

    west_board = Thing(GenMeshCube(3.3, 2, 0.1), (0, 6, -14.9), (0, 1, 0), 0, GREEN, [3.3, 2, 0.1], tex)
    west_pole = Thing(GenMeshCylinder(0.1, 7, 20), (0, 0, -15), (0, 0, 0), 0, BLACK, [0.1, 7], tex)
    # west_rim = Thing(GenMeshTorus(0.05, 2 * b_r + 0.1, 3, 20), (0, 5.2, -15 + b_r + 0.15), (1, 0, 0), 90, RED, [0.05, 2 * b_r + 0.1], tex)

    east_board = Thing(GenMeshCube(3.3, 2, 0.1), (0, 6, 14.9), (0, 2, 0), 0, YELLOW, [3.3, 2, 0.1], tex)
    east_pole = Thing(GenMeshCylinder(0.1, 7, 20), (0, 0, 15), (0, 0, 0), 0, BLACK, [0.1, 7], tex)
    # east_rim = Thing(GenMeshTorus(0.05, 2 * b_r + 0.1, 3, 20), (0, 5.2, 15 - b_r - 0.15), (1, 0, 0), 90, RED, [0.05, 2 * b_r + 0.1], tex)

    north_board = Thing(GenMeshCube(0.1, 2, 3.3), (-14.9, 6, 0), (0, 1, 0), 0, PURPLE, [0.1, 2, 3.3], tex)
    north_pole = Thing(GenMeshCylinder(0.1, 7, 20), (-15, 0, 0), (0, 0, 0), 0, BLACK, [0.1, 7], tex)

    south_board = Thing(GenMeshCube(0.1, 2, 3.3), (14.9, 6, 0), (0, 1, 0), 0, BLUE, [0.1, 2, 3.3], tex)
    south_pole = Thing(GenMeshCylinder(0.1, 7, 20), (15, 0, 0), (0, 0, 0), 0, BLACK, [0.1, 7], tex)


    ball = Thing(GenMeshSphere(b_r, 15, 15), (2, 2, 0), (0, 0, 0), 0, BLUE, [b_r], tex)

    yao = Thing(GenMeshCube(2, 5, 2), (40, 5 / 2, 40), (1, 0, 0), 180, WHITE, [5], ming)

    test_model = Thing(GenMeshCube(2, 1, 1), (0, 0.5, 0), (0, 1, 0), 90, PURPLE, [2, 1, 1])

    bell = LoadSound(b"bell.mp3")

    #------------------------------------------------------------------------------
    
    max_fps = -1
    wireframe_mode = False
    holding_ball = False
    throw_velocity = 10

    kill = 0

    score = 0

    timestamp_font_size = 40
    max_pps = 0

    #------------------------------------------------------------------------------
    
    while not WindowShouldClose():
        #------------------------------------------------------------------------------
        
        wrzUpdateCamera(camera)

        forward = Vector3Normalize(Vector3Subtract(camera.target, camera.position))
        
        if IsKeyPressed(KEY_U):
            wireframe_mode = not wireframe_mode
        
        if holding_ball:
            if IsKeyPressed(KEY_SPACE):
                b_v = Vector3Scale(forward, throw_velocity)
                holding_ball = False
            elif IsKeyPressed(KEY_LEFT_SHIFT):
                b_v = Vector3Scale(forward, 3 * throw_velocity)
                holding_ball = False
        elif not holding_ball:
            if IsKeyPressed(KEY_LEFT_SHIFT):
                if wrzGrabBall(camera, ball.position, ball.size):
                    b_v = Vector3Scale(forward, throw_velocity)
            elif IsKeyPressed(KEY_SPACE):
                if wrzGrabBall(camera, ball.position, ball.size):
                    holding_ball = True
            
        if not holding_ball:
            ball.position, b_v, score = wrzBouncingBall(camera, score, ball.position, b_v, b_r, ball, [west_board, east_board, north_board, south_board])
        else:
            ball.position = Vector3Add(camera.position, Vector3Scale(forward, 4))
            # if score > 2: score -= 2
        
        if Vector3Distance(yao.position, camera.position) < 1:
            kill = 1
            continue

        yao.position, y_v, score = wrzMingChase(score, yao, y_v, ball)

        now = time()
        time_difference = _floor(now - start_time)
        points_per_second = score / time_difference if time_difference > 0 else 0.0
        max_pps = points_per_second if points_per_second > max_pps else max_pps
        m = time_difference // 60
        s = time_difference % 60
        timestamp = f"{int(m):02d}:{int(s):02d}"
        avg = f"PPS: {points_per_second:.2f} [{max_pps:.2f}]"

        if IsKeyPressed(KEY_M):
            fullscreen = wrzToggleFullscreen(fullscreen)
            WIDTH = GetScreenWidth()
            HEIGHT = GetScreenHeight()
    
        #------------------------------------------------------------------------------
        
        BeginDrawing()

        ClearBackground(WHITE)

        BeginMode3D(camera)

        #------------------------------------------------------------------------------
        
        for t in things:
            if wireframe_mode: DrawModelWiresEx(t.model, t.position, t.rotation, t.angle, (1.0, 1.0, 1.0), t.color)
            else: DrawModelEx(t.model, t.position, t.rotation, t.angle, (1.0, 1.0, 1.0), t.color)
            if t.bb is not None: DrawBoundingBox(t.bb, t.color)
        
        #------------------------------------------------------------------------------
        
        EndMode3D()

        max_fps = GetFPS() if GetFPS() > max_fps else max_fps

        if wireframe_mode: wrzPrettyText(f"FPS: {GetFPS():04}", 10, 10, 20)
        # wrzPrettyText(f"MAX: {max_fps:04}", 130, 10, 20)

        if wireframe_mode: wrzPrettyText("Wireframe Mode", 130, 10, 20, RED)

        DrawCircle(int(WIDTH / 2), int(HEIGHT / 2), 4, BLACK)
        DrawCircle(int(WIDTH / 2), int(HEIGHT / 2), 3, WHITE)

        if wireframe_mode: wrzPrettyText(f"CAM: [{camera.position.x:.2f}, {camera.position.y:.2f}, {camera.position.z:.2f}]", 10, HEIGHT - 50, 20, BLACK, RED)
        if wireframe_mode: wrzPrettyText(f"BALL: [{ball.position.x:.2f}, {ball.position.y:.2f}, {ball.position.z:.2f}]", 10, HEIGHT - 30, 20, BLACK, BLUE)

        wrzPrettyText(f"{score:05d}/42000", WIDTH - 350, 0, 50, RED)

        if wireframe_mode: wrzPrettyText(avg, (WIDTH - MeasureText(avg.encode(), 20)) // 2, HEIGHT - timestamp_font_size - 30, 20, RED)
        wrzPrettyText(timestamp, (WIDTH - MeasureText(timestamp.encode(), timestamp_font_size)) // 2, HEIGHT - timestamp_font_size - 10, timestamp_font_size, RED)

        if kill > 0 or score < 0 or score > 42000:
            if score < 0 or kill > 0:
                banner = "MING DYNASTY!!"
                color = YELLOW
            else:
                banner = "TOTAL O'NEAL\n VICTORY..."
                color = PURPLE

            size = 100
            width = MeasureText(banner.encode(), size)

            wrzPrettyText(banner, (WIDTH - width) // 2, (HEIGHT - size) // 2, size, color, BLACK)

            if kill == 200:
                PlaySound(bell)
                sleep(2)
                exit()
            kill += 1

        EndDrawing()

if __name__ == "__main__": main()