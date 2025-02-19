//------------------------------------------------------------------------------

#include <raylib.h>
#include <raymath.h>
#include <stdio.h>
#include <time.h>
#include <stdlib.h>

//------------------------------------------------------------------------------

float g = -9.8;
float mu_floor = 0.2;
float mu_board = 0.1;
float yao_speed = 5.8;
float yao_height = 5.0f;

bool game_over;

#define M_SQRT2 1.414

float throw_velocity = 10.0f;

typedef enum {
    PLANE = 1,
    SPHERE = 1,
    CYLINDER = 2,
    BOX = 3
} DIMENSION;

//------------------------------------------------------------------------------

void wrzPrettyText(const char * text, int x, int y, int font_size, Color f_color, Color b_color);
Model wrzModel(Mesh mesh, Texture2D texture);

typedef struct {
    Model model;
    Vector3 position;
    Vector3 rotation;
    float angle;
    Color color;
    int dimensions; // length of size[]
    float * size;
    BoundingBox bb;
} Thing;

Thing * wrzInitThing(Mesh mesh, Vector3 position, Vector3 rotation, float angle, Color color, int dimensions, float size[], Texture2D texture);
void wrzDrawThing(Thing * t, bool wireframe);
bool wrzGrabBall(Camera3D camera, Thing * ball);
void wrzBouncingBall(Camera3D camera, Thing * ball, Vector3 * ball_velocity, int * score, int num_backboards, Thing * backboards[]);
void wrzMingChase(int * score, Thing * yao, Vector3 * yao_velocity, Thing * ball);

//------------------------------------------------------------------------------

int main(void) {

    //------------------------------------------------------------------------------

    int WIDTH = 1;
    int HEIGHT = 1;

    InitWindow(WIDTH, HEIGHT, "WRZ: Bob Dole Basketball [C Edition]");
    InitAudioDevice();
    SetTargetFPS(120);

    time_t start_time = time(NULL);

    WIDTH = GetMonitorWidth(GetCurrentMonitor()) / 2;
    HEIGHT = GetMonitorHeight(GetCurrentMonitor()) / 2;

    SetWindowSize(WIDTH, HEIGHT);
    SetWindowPosition(WIDTH / 2, HEIGHT / 2);

    Camera3D camera = (Camera3D) {
        (Vector3) {0, 2, 0},
        (Vector3) {1, 2, 0},
        (Vector3) {0, 1, 0},
        90.0f,
        CAMERA_PERSPECTIVE
    };

    DisableCursor();

    //------------------------------------------------------------------------------

    Vector3 * ball_velocity = malloc(sizeof(Vector3));

    *(ball_velocity) = (Vector3) {0, 0, 0};
    float ball_radius = 0.5f;

    Vector3 * yao_velocity = malloc(sizeof(Vector3));

    *(yao_velocity) = (Vector3) {0, 5, 0};

    //------------------------------------------------------------------------------

    Texture2D bob = LoadTexture("bobdole.png");
    Texture2D yao_texture = LoadTexture("ming.png");

    //------------------------------------------------------------------------------

    float floor_dimensions[1] = { 100.0f };
    Thing * floor = wrzInitThing(GenMeshPlane(floor_dimensions[0], floor_dimensions[0], 1, 1), (Vector3) {0, 0, 0}, (Vector3) {0, 0, 0}, 0.0f, BROWN, PLANE, floor_dimensions, bob);

    float ball_dimensions[1] = { ball_radius };
    Thing * ball = wrzInitThing(GenMeshSphere(ball_dimensions[0], 20, 20), (Vector3) {5, 2, 0}, (Vector3) {0, 0, 0}, 0.0f, BLUE, SPHERE, ball_dimensions, bob);

    float yao_dimensions[2] = { 2, yao_height };
    Thing * yao = wrzInitThing(GenMeshCube(yao_dimensions[0], yao_dimensions[1], yao_dimensions[0]), (Vector3) {40, yao_dimensions[1] / 2.0f, 40}, (Vector3) {1, 0, 0}, 180, WHITE, CYLINDER, yao_dimensions, yao_texture);

    float board_dimensions[3] = {3.3, 2.0, 0.1};
    float board_height = 6.0f;
    float board_distance = 14.9;

    Thing * west_board =  wrzInitThing(GenMeshCube(board_dimensions[0], board_dimensions[1], board_dimensions[2]), (Vector3) {0, board_height, -board_distance}, (Vector3) {0, 0, 0}, 0, GREEN,  BOX, (float[]) { board_dimensions[0], board_dimensions[1], board_dimensions[2] }, bob);
    Thing * east_board =  wrzInitThing(GenMeshCube(board_dimensions[0], board_dimensions[1], board_dimensions[2]), (Vector3) {0, board_height,  board_distance}, (Vector3) {0, 0, 0}, 0, YELLOW, BOX, (float[]) { board_dimensions[0], board_dimensions[1], board_dimensions[2] }, bob);
    Thing * north_board = wrzInitThing(GenMeshCube(board_dimensions[2], board_dimensions[1], board_dimensions[0]), (Vector3) {-board_distance, board_height, 0}, (Vector3) {0, 0, 0}, 0, PURPLE, BOX, (float[]) { board_dimensions[2], board_dimensions[1], board_dimensions[0] }, bob);
    Thing * south_board = wrzInitThing(GenMeshCube(board_dimensions[2], board_dimensions[1], board_dimensions[0]), (Vector3) { board_distance, board_height, 0}, (Vector3) {0, 0, 0}, 0, BLUE,   BOX, (float[]) { board_dimensions[2], board_dimensions[1], board_dimensions[0] }, bob);

    float pole_dimensions[2] = {0.1, 7};

    Thing * west_pole  = wrzInitThing(GenMeshCylinder(pole_dimensions[0], pole_dimensions[1], 10), (Vector3) {0, 0, -board_distance - pole_dimensions[0]}, (Vector3) {0, 0, 0}, 0.0f, BLACK, CYLINDER, pole_dimensions, bob);
    Thing * east_pole  = wrzInitThing(GenMeshCylinder(pole_dimensions[0], pole_dimensions[1], 10), (Vector3) {0, 0,  board_distance + pole_dimensions[0]}, (Vector3) {0, 0, 0}, 0.0f, BLACK, CYLINDER, pole_dimensions, bob);
    Thing * north_pole = wrzInitThing(GenMeshCylinder(pole_dimensions[0], pole_dimensions[1], 10), (Vector3) {-board_distance - pole_dimensions[0], 0, 0}, (Vector3) {0, 0, 0}, 0.0f, BLACK, CYLINDER, pole_dimensions, bob);
    Thing * south_pole = wrzInitThing(GenMeshCylinder(pole_dimensions[0], pole_dimensions[1], 10), (Vector3) { board_distance + pole_dimensions[0], 0, 0}, (Vector3) {0, 0, 0}, 0.0f, BLACK, CYLINDER, pole_dimensions, bob);

    const int thing_count = 11;
    Thing * things[11] = { floor, ball, yao, west_board, east_board, south_board, north_board, west_pole, east_pole, north_pole, south_pole };
    
    //------------------------------------------------------------------------------

    bool holding_ball = false;
    int score = 0;
    game_over = false;

    int max_frames = 200;
    int frame_count = 0;

    bool wireframe = false;

    Sound bell = LoadSound("bell.mp3");

    //------------------------------------------------------------------------------

    while(!WindowShouldClose()) {

        //------------------------------------------------------------------------------

        if(game_over)
            goto __endgame;

        //------------------------------------------------------------------------------
        
        UpdateCamera(&camera, CAMERA_FIRST_PERSON);
        Vector3 camera_forward = Vector3Normalize(Vector3Subtract(camera.target, camera.position));

        if(holding_ball) {
            if(IsKeyPressed(KEY_SPACE)) {
                *(ball_velocity) = Vector3Scale(camera_forward, throw_velocity);
                holding_ball = false;
            } else if(IsKeyPressed(KEY_LEFT_SHIFT)) {
                *(ball_velocity) = Vector3Scale(camera_forward, 3 * throw_velocity);
                holding_ball = false;
            }
        } else if(!holding_ball) {
            if(IsKeyPressed(KEY_LEFT_SHIFT)) {
                if(wrzGrabBall(camera, ball)) {
                    *(ball_velocity) = Vector3Scale(camera_forward, throw_velocity);
                }
            } else if(IsKeyPressed(KEY_SPACE)) {
                if(wrzGrabBall(camera, ball)) {
                    holding_ball = true;
                }
            }
        }

        if(!holding_ball)
            wrzBouncingBall(camera, ball, ball_velocity, &score, 4, (Thing * []) {west_board, east_board, north_board, south_board});
        else
            ball->position = Vector3Add(camera.position, Vector3Scale(camera_forward, 4));

        wrzMingChase(&score, yao, yao_velocity, ball);

        if(IsKeyPressed(KEY_U)) wireframe = !wireframe;

        //------------------------------------------------------------------------------
        
        BeginDrawing();

            ClearBackground(WHITE);

            BeginMode3D(camera);

                for(int i = 0; i < thing_count; i++) {
                    wrzDrawThing(things[i], wireframe);
                }
            
            EndMode3D();
        
            wrzPrettyText(TextFormat("FPS: %04d", GetFPS()), 10, 10, 20, WHITE, BLACK);
            wrzPrettyText(TextFormat("SCORE: %d", score), 10, 30, 20, RED, BLACK);

            DrawCircle(WIDTH / 2, HEIGHT / 2, 4, BLACK);
            DrawCircle(WIDTH / 2, HEIGHT / 2, 3, WHITE);

        EndDrawing();

        //------------------------------------------------------------------------------

        __endgame:
            if(game_over) {
                const char * banner = "MING DYNASTY!!";
                int font_size = 100;
                int width = MeasureText(banner, font_size);

                if(frame_count == 0)
                    PlaySound(bell);

                BeginDrawing();
                    ClearBackground(WHITE);

                    wrzPrettyText("MING DYNASTY!!", (WIDTH - width) / 2, (HEIGHT - font_size) / 2, font_size, YELLOW, BLACK);
                EndDrawing();

                if(frame_count > max_frames)
                    goto __close;
                
                frame_count++;
            }
    }

    //------------------------------------------------------------------------------

    __close:
    UnloadTexture(bob);
    UnloadTexture(yao_texture);

    CloseWindow();
    CloseAudioDevice();

    free(ball_velocity);
    free(yao_velocity);

    for(int i = 0; i < thing_count; i++) {
        free(things[i]);
    }

    return 0;
}

//------------------------------------------------------------------------------

Thing * wrzInitThing(Mesh mesh, Vector3 position, Vector3 rotation, float angle, Color color, int dimensions, float size[], Texture2D texture) {
    Thing * output = malloc(sizeof(Thing));

    output->model = wrzModel(mesh, texture);
    output->position = position;
    output->rotation = rotation;
    output->angle = angle;
    output->color = color;
    output->dimensions = dimensions;
    output->size = size;

    if(dimensions == 3) {
        Vector3 _size = (Vector3) {size[0], size[1], size[2]};

        float a = position.x - (0.5 * _size.x);
        float b = position.y - (0.5 * _size.y);
        float c = position.z - (0.5 * _size.z);
        float j = position.x + (0.5 * _size.x);
        float k = position.y + (0.5 * _size.y);
        float l = position.z + (0.5 * _size.z);

        output->bb = (BoundingBox) { (Vector3) {a, b, c}, (Vector3) {j, k, l}};
    }

    return output;
}

Model wrzModel(Mesh mesh, Texture2D texture) {
    Model model = LoadModelFromMesh(mesh);
    model.materials[0].maps[MATERIAL_MAP_DIFFUSE].texture = texture;

    return model;
}

void wrzPrettyText(const char * text, int x, int y, int font_size, Color f_color, Color b_color) {
    DrawText(text, x + 2, y + 2, font_size, b_color);
    DrawText(text, x, y, font_size, f_color);
}

void wrzDrawThing(Thing * t, bool wireframe) {
    if(!wireframe) DrawModelEx(t->model, t->position, t->rotation, t->angle, (Vector3) {1.0, 1.0, 1.0}, t->color);
    else DrawModelWiresEx(t->model, t->position, t->rotation, t->angle, (Vector3) {1.0, 1.0, 1.0}, t->color);
    if(t->dimensions == 3) {
        DrawBoundingBox(t->bb, t->color);
    }
}

bool wrzGrabBall(Camera3D camera, Thing * ball) {
    Vector3 forward = Vector3Normalize(Vector3Subtract(camera.target, camera.position));

    forward.y = 0;
    forward = Vector3Normalize(forward);

    return CheckCollisionCircleLine((Vector2) {ball->position.x, ball->position.z}, ball->size[0], (Vector2) {camera.position.x, camera.position.z}, Vector2Add((Vector2) {camera.position.x, camera.position.z}, (Vector2) {forward.x, forward.z}));
}

void wrzBouncingBall(Camera3D camera, Thing * ball, Vector3 * ball_velocity, int * score, int num_backboards, Thing * backboards[]) {
    // apply gravity
    *(ball_velocity) = Vector3Add(*(ball_velocity), Vector3Scale((Vector3) {0, g, 0}, GetFrameTime()));
    ball->position = Vector3Add(ball->position, Vector3Scale(*(ball_velocity), GetFrameTime()));

    if(ball->position.y < ball->size[0]) {
        ball->position.y = ball->size[0];
        ball_velocity->y = -1 * ball_velocity->y;
        *(ball_velocity) = Vector3Scale(*(ball_velocity), 1 - mu_floor);
    }

    if(fabs(ball->position.x) > 50) {
        ball_velocity->x = -1.2 * ball_velocity->x;
    }
    if(fabs(ball->position.z) > 50) {
        ball_velocity->z = -1.2 * ball_velocity->z;
    }

    for(int i = 0; i < num_backboards; i++) {
        Thing b = *(backboards[i]);
        bool orientation = (b.size[0] > b.size[2]) ? true : false;

        if(CheckCollisionBoxSphere(b.bb, ball->position, ball->size[0])) {
            Vector3 normal;
            if(orientation)
                normal = (Vector3) {0, 0, 1};
            else
                normal = (Vector3) {1, 0, 0};
            
            *(ball_velocity) = Vector3Reflect(*(ball_velocity), normal);

            *(score) += 20;
        }
    }

    if(Vector3Length(*(ball_velocity)) > 1000) {
        ball->position = (Vector3) {0, 2, 0};
        *(ball_velocity) = (Vector3) {0, 1, 0};
    }

    if(*(score) > 10000)
        game_over = true;
}

void wrzMingChase(int * score, Thing * yao, Vector3 * yao_velocity, Thing * ball) {
    Vector3 forward = Vector3Subtract(ball->position, yao->position);

    *(yao_velocity) = Vector3Scale(Vector3Normalize(Vector3Add(*(yao_velocity), Vector3Scale(forward, GetFrameTime()))), yao_speed);
    yao->position = Vector3Add(yao->position, Vector3Scale(*(yao_velocity), GetFrameTime()));

    if(yao->position.y < yao->size[1])
        yao->position.y = yao->size[1] / 2;
    
    if(Vector2Distance((Vector2) {yao->position.x, yao->position.z}, (Vector2) {ball->position.x, ball->position.z}) < M_SQRT2)
        *(score) -= 5;
    
    if(*(score) < -1)
        game_over = true;
}