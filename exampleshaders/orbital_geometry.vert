#version 330 core

layout(location = 0) in vec2 a_position;

out vec2 vUV;
out vec2 vScreen;

void main() {
    vUV = a_position * 0.5 + 0.5;
    vScreen = a_position;
    gl_Position = vec4(a_position, 0.0, 1.0);
}
